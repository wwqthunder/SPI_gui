import os
import pandas as pd
import numpy as np
cols_headers = ["SS","Addr","Sel","Name","VolMax","VolMin","DataSize","EnbBits","BinR","DecR","VolR","BinW","DecW","VolW"]
cols_box = ["SS","Addr","Sel","Name","VolMax","VolMin","DataSize","EnbBits","BinVal","DecVal"]

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
    data['SS'] = data['SS'].astype('float')
    data['Addr'] = data['Addr'].astype('float')
    data['Sel'] = data['Sel'].astype('float')
    data['DataSize'] = data['DataSize'].astype('float')
    data['EnbBits'] = data['EnbBits'].astype('float')
    data['SS'] = data['SS'].astype('int')
    data['Addr'] = data['Addr'].astype('int')
    data['Sel'] = data['Sel'].astype('int')
    data['DataSize'] = data['DataSize'].astype('int')
    data['EnbBits'] = data['EnbBits'].astype('int')
    # NEED a better way to transfer (string)"0.0" to (int)0.

    #data = data.dropna(axis=0, subset=['SS'])
    #data = data.dropna(axis=0, subset=['Addr'])
    data.reset_index(drop=True, inplace=True)
    return data

def loadxlsm(path):
    data = pd.read_excel(open(path, 'rb'),sheet_name="SPI",usecols="C:M,O:Q",skiprows=4,names=cols_headers,dtype=object,na_filter = False)
    return data

def loadcsv(path):
    data = pd.read_csv(path,skiprows=1,names=cols_headers,dtype=object,na_filter = False)
    return data

def loadxls(path):
    raw = pd.read_excel(open(path, 'rb'), header=None,dtype=object,na_filter = False)
    headers = raw.iloc[0].values.tolist()
    raw = raw.iloc[1:]
    data = pd.DataFrame()
    colsFill = cols_headers.copy()
    for _ in cols_box:
        if _ in headers:
            _header = _.replace("Val", "W")
            data[_header] = raw[headers.index(_)]
            colsFill.remove(_header)

    for _ in colsFill:
        data[_] = ""
    data = data[cols_headers]
    return data

def df2csv(path,df):
    df.to_csv(path,index=False)


if __name__ == '__main__':
    path = "C:\\Users\op\Documents\\1020.csv"
    data = load(path)
    print(data)
    #print(data)
    #print(data.dtypes)

    #newRowSeries = pd.Series([0, 0, 0, "", 1.0, 0.0, 0, 0, "", "", "", "", "", "", ""], index=cols_headers)
    #newRowSeries = data.iloc[-1]
    #newRowSeries.loc[["Name","BinR","DecR","VolR","BinW","DecW","VolW"]] = ""
    #for index, row in data.iterrows():
