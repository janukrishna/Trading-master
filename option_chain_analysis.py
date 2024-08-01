# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 22:53:59 2020

@author: Anvesh
"""
import xlwings as xw
import requests
import json
import pandas as pd
from time import sleep
from datetime import datetime
import os


url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"

headers = { "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0",
           "Accept-Language" : "en-US,en;q=0.5",
           "Accept-Encoding" : "gzip, deflate, br"}

expiry = "27-Aug-2020"
excel_file = "option_chain_analysis.xlsx"
wb = xw.Book(excel_file)
sheet_oi_single = wb.sheets("oidata2608")
sht_live = wb.sheets("MPData")
df_list = []
mp_list = []

oi_filename = os.path.join("Files", "oi_data_records_{0}.json".format(datetime.now().strftime("%d%m%y")))
mp_filename = os.path.join("Files", "mp_data_records_{0}.json".format(datetime.now().strftime("%d%m%y")))

def fetch_oi(df, mp_df):
    tries = 1
    max_tries = 2
    while tries <= max_tries:
        try:
            r = requests.get(url, headers = headers).json()
            if expiry:
                ce_values = [data['CE'] for data in r['records']['data'] if "CE" in data and str(data['expiryDate']).lower() == str(expiry).lower()]
                pe_values = [data['PE'] for data in r['records']['data'] if "PE" in data and str(data['expiryDate']).lower() == str(expiry).lower()]
            else:
                ce_values = [data['CE'] for data in r['records']['data'] if "CE" in data]
                pe_values = [data['PE'] for data in r['records']['data'] if "PE" in data]
            ce_data = pd.DataFrame(ce_values)
            pe_data = pd.DataFrame(pe_values)
            ce_data = ce_data.sort_values(['strikePrice'])
            pe_data = pe_data.sort_values(['strikePrice'])
            sheet_oi_single.range("A2").options(index=False, header=False).value = ce_data.drop(
                ['askPrice', 'askQty', 'bidQty', 'bidprice', 'expiryDate', 'identifier',
                 'totalBuyQuantity', 'totalSellQuantity', 'totalTradedVolume',
                 'underlying', 'underlyingValue'], axis=1)[
                ['openInterest', 'changeinOpenInterest', 'pchangeinOpenInterest',
                 'impliedVolatility', 'lastPrice', 'change', 'pChange', 'strikePrice']]
            sheet_oi_single.range("I1").options().value = pe_data.drop(
                ['askPrice', 'askQty', 'bidQty', 'bidprice', 'expiryDate', 'identifier',
                 'totalBuyQuantity', 'totalSellQuantity', 'totalTradedVolume', 'strikePrice',
                 'underlying', 'underlyingValue'], axis=1)[
                ['openInterest', 'changeinOpenInterest', 'pchangeinOpenInterest',
                 'impliedVolatility', 'lastPrice', 'change', 'pChange']]
            ce_data['type'] = "CE"
            pe_data['type'] = "PE"
            df1 = pd.concat([ce_data, pe_data])
            if len(df_list) > 0:
                df1['Time'] = df_list[-1][0]['Time']
            if len(df_list) > 0 and df1.to_dict('records') == df_list[-1]:
                print("Duplicate data: Not recording")
                sleep(2)
                tries =+ 1
                continue
            df1['Time'] = datetime.now().strftime("%H:%M")
            
            pcr = pe_data['totalTradedVolume'].sum()/ce_data['totalTradedVolume'].sum()
            mp_dict = {datetime.now().strftime("%H:%M"): {'underlying': df1['underlyingValue'].iloc[-1],
                                                          'MaxPain': wb.sheets("Dashboard").range("G8").value,
                                                          'pcr': pcr,
                                                          # 'call_decay': ce_data['change'].mean(),  # 'call decay' of 'change in price'
                                                          'call_decay' : ce_data.nlargest(5, 'openInterest', keep='last')['change'].mean(), # 'call_decay' for 'highest OI'
                                                          # 'put_decay': pe_data['change'].mean()}}  # 'put decay' of 'change in price'
                                                          'put_decay' : pe_data.nlargest(5, 'openInterest', keep='last')['change'].mean()}}  # 'put_decay' for 'highest OI'
            df3 = pd.DataFrame(mp_dict).transpose()
            mp_df = pd.concat([mp_df, df3])
            wb.sheets['MPData'].range("A2").options(header=False).value = mp_df
            with open(mp_filename, "w") as files:
                files.write(json.dumps(mp_df.to_dict(), indent=4, sort_keys=True))
            if not df.empty:
                df = df[
                    ['strikePrice', 'expiryDate', 'underlying', 'identifier', 'openInterest',
                     'changeinOpenInterest', 'pchangeinOpenInterest', 'totalTradedVolume',
                     'impliedVolatility', 'lastPrice', 'change', 'pChange',
                     'totalBuyQuantity', 'totalSellQuantity', 'bidQty', 'bidPrice',
                     'askQty', 'askPrice', 'underlyingValue','type', 'Time']]
                df1 = df1 [
                    ['strikePrice', 'expiryDate', 'underlying', 'identifier', 'openInterest',
                     'changeinOpenInterest', 'pchangeinOpenInterest', 'totalTradedVolume',
                     'impliedVolatility', 'lastPrice', 'change', 'pChange',
                     'totalBuyQuantity', 'totalSellQuantity', 'bidQty', 'bidPrice',
                     'askQty', 'askPrice', 'underlyingValue','type', 'Time']]
            
            df = pd.concat([df, df1])
            df_list.append(df1.to_dict('records'))
            with open(oi_filename, "w") as files:
                files.write(json.dumps(df_list, indent=4, sort_keys=True))
            return df, mp_df
        except Exception as error:
            print("error {0}".format(error))
            tries += 1
            sleep(2)
            continue
    if tries >= max_tries:
        print("Max tries exceeded. No new data at time {0}".format(datetime.now()))
        return df, mp_df

def main():
    global df_list
    try:
        df_list = json.loads(open(oi_filename).read())
    except Exception as error:
        print("Error reading data. Error : {0}".format(error))
        df_list = []
    if df_list:
        df = pd.DataFrame()
        for item in df_list:
            df = pd.concat([df, pd.DataFrame(item)])
    else:
        df = pd.DataFrame()
        
    try:
        mp_list = json.loads(open(mp_filename).read())
        mp_df = pd.DataFrame().from_dict(mp_list)
    except Exception as error:
        print("Error reading data. Error : {0}".format(error))
        mp_list = []
        mp_df = pd.DataFrame()
        
    df, mp_df = fetch_oi(df, mp_df)
    if not df.empty:
        df['impliedVolatility'] = df['impliedVolatility'].replace(to_replace=0,method='bfill').values
        df['identifier'] = df['strikePrice'].astype(str) + df['type']
        sht_live.range("A1").value = df


if __name__ == '__main__':
    main()






