import os
import pandas as pd
import numpy as np
cols_headers = ["SS","Addr","Sel","Name","Vol_Max","Vol_Min","DataSize","EnbBits","BinR","DecR","VolR","BinW","DecW","VolW","Steps"]


def load(path):
    _, extension = os.path.splitext(path)
    if '.xlsm' in extension:
        data = loadxlsm(path)
    elif '.csv' in extension:
        data = loadcsv(path)
    else:
        data = loadxls(path)
    data["SS"].replace('', np.nan, inplace=True)
    data.dropna(subset=['SS'], inplace=True)
    data["Addr"].replace('', np.nan, inplace=True)
    data.dropna(subset=['Addr'], inplace=True)
    data['SS'] = data['SS'].astype('int')
    data['Addr'] = data['Addr'].astype('int')
    #data = data.dropna(axis=0, subset=['SS'])
    #data = data.dropna(axis=0, subset=['Addr'])
    data.reset_index(drop=True, inplace=True)
    return data

def loadxlsm(path):
    data = pd.read_excel(open(path, 'rb'),sheet_name="SPI",usecols="C:M,O:Q,U",skiprows=4,names=cols_headers,dtype=object,na_filter = False)
    return data

def loadcsv(path):
    data = pd.read_csv(path,skiprows=1,names=cols_headers,dtype=object,na_filter = False)
    return data

def loadxls(path):
    data = pd.read_excel(open(path, 'rb'), skiprows=1, names=cols_headers,dtype=object)
    return data

def df2csv(path,df):
    df.to_csv(path,index=False)


if __name__ == '__main__':
    data = load("C:\\Users\op\Documents\\0723.csv")
    print(data)
    print(data.dtypes)
    newRowSeries = pd.Series([0, 0, 0, "", 1.0, 0.0, 0, 0, "", "", "", "", "", "", ""], index=cols_headers)
    print(newRowSeries)
    newRowSeries = data.iloc[-1]
    print(newRowSeries)
    print(type(newRowSeries))
    newRowSeries.loc[["Name","BinR","DecR","VolR","BinW","DecW","VolW"]] = ""
    print(newRowSeries)
    #for index, row in data.iterrows():
