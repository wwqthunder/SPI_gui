import os
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
from lxml import etree
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

def df2xml(path,df):
    root = ET.Element('root')  # Root element

    for column in df.columns:
        entry = ET.SubElement(root, column)  # Adding element
        for row in df.index:
            schild = row
            child = ET.SubElement(entry, str(schild))  # Adding sub-element
            child.text = str(df[column][schild])

    xml_data = ET.tostring(root)  # binary string
    with open(path, 'w') as f:  # Write in file as utf-8
        f.write(xml_data.decode('utf-8'))

def loadxml(path):
    xml_data = open(path, 'r').read()  # Read file
    print(xml_data)
    # tree = ET.parse(path)
    # root = tree.getroot()
    # print(root)
    root = ET.fromstring(xml_data,method="html")
    #root = ET.XML(xml_data)  # Parse XML

    data = []
    cols = []
    for i, child in enumerate(root):
        data.append([subchild.text for subchild in child])
        cols.append(child.tag)

    df = pd.DataFrame(data).T  # Write in DF and transpose it
    df.columns = cols  # Update column names
    print(df)

    def multiXLSwriter(path,df_list):
        for _ in range(len(df_list)):
            with pd.ExcelWriter(path) as writer:
                df_list[_].to_excel(writer, sheet_name='Sheet'+str(_+1))

if __name__ == '__main__':
    # path = "1020.csv"
    # data = load(path)
    # print(data)
    # df2xml('test.xml',data)
    path = 'test.xml'
    loadxml(path)


    #newRowSeries = pd.Series([0, 0, 0, "", 1.0, 0.0, 0, 0, "", "", "", "", "", "", ""], index=cols_headers)
    #newRowSeries = data.iloc[-1]
    #newRowSeries.loc[["Name","BinR","DecR","VolR","BinW","DecW","VolW"]] = ""
    #for index, row in data.iterrows():
