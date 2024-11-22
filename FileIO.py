import os
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
#from lxml import etree
xlsm_headers = ["SS", "Addr", "Pos", "Name", "VolMax", "VolMin", "RegSize", "Size", "BinR", "DecR", "VolR", "BinW", "DecW", "VolW"]
cols_headers = ["SS", "CAddr", "Addr", "Sel", "Name", "VolMax", "VolMin", "DataSize", "EnbBits", "BinR", "DecR", "VolR", "BinW", "DecW", "VolW"]
cols_box = ["SS","Addr","Sel","Name","VolMax","VolMin","DataSize","EnbBits","BinVal","DecVal"]
data_headers = ["Term", "SS", "CAddr", "Addr", "Pos", "Name", "VolMax", "VolMin", "RegSize", "Size",
                             "BinR", "DecR", "VolR", "BinW", "DecW", "VolW", "Unit"]

def load(path):
    _, extension = os.path.splitext(path)
    if '.xlsm' in extension:
        data = loadxlsm(path)
    elif '.csv' in extension:
        data = loadcsv(path)
    else:
        data = loadxls(path)
    for col in ["BinR", "BinW"]:
        data[col] = data[col].apply(lambda x: str(x) if is_bin(x) else "")
    for col in ["SS", "CAddr", "Addr", "Pos", "RegSize", "Size", "DecR", "DecW", "Unit"]:
        data[col] = data[col].apply(lambda x: str(x) if is_int(x) else "")
    for col in ["VolMax", "VolMin", "VolR", "VolW"]:
        data[col] = data[col].apply(lambda x: str(x) if is_float(x) else "")
    data.reset_index(drop=True, inplace=True)
    return data


def loadxlsm(path):
    raw = pd.read_excel(open(path, 'rb'), sheet_name="SPI", usecols="C:M,O:Q", skiprows=4, names=xlsm_headers, dtype=object, na_filter=False)
    data = pd.DataFrame(data=[[""] * len(data_headers) for _ in range(raw.shape[0])], index=range(raw.shape[0]), columns=data_headers)
    for _ in data_headers:
        if _ in raw.columns:
            data[_] = raw[_]
        else:
            continue
    return data


def loadcsv(path):
    raw = pd.read_csv(path, dtype=object, na_filter=False)
    data = pd.DataFrame(data=[[""] * len(data_headers) for _ in range(raw.shape[0])], index=range(raw.shape[0]), columns=data_headers)
    for _ in data_headers:
        if _ in raw.columns:
            data[_] = raw[_]
        elif _ == "Pos" and "Sel" in raw.columns:
            data[_] = raw["Sel"]
        elif _ == "RegSize" and "DataSize" in raw.columns:
            data[_] = raw["DataSize"]
        elif _ == "Size" and "EnbBits" in raw.columns:
            data[_] = raw["EnbBits"]
        else:
            continue
    return data


def loadxls(path):
    raw = pd.read_excel(open(path, 'rb'), dtype=object, na_filter=False)
    data = pd.DataFrame(data=[[""] * len(data_headers) for _ in range(raw.shape[0])], index=range(raw.shape[0]),
                        columns=data_headers)
    for _ in data_headers:
        if _ in raw.columns:
            data[_] = raw[_]
        elif _ == "Pos" and "Sel" in raw.columns:
            data[_] = raw["Sel"]
        elif _ == "RegSize" and "DataSize" in raw.columns:
            data[_] = raw["DataSize"]
        elif _ == "Size" and "EnbBits" in raw.columns:
            data[_] = raw["EnbBits"]
        else:
            continue
    return data


def is_bin(value):
    if str(value):
        return set(str(value)).issubset({'0', '1'})
    else:
        return False


def is_int(value):
    try:
        int(float(value))
        return True
    except ValueError:
        return False

def is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def df2csv(path, df):
    df.to_csv(path, index=False)


def df2xml(path, df):
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
    root = ET.fromstring(xml_data, method="html")
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
    #data = pd.read_csv('spi_test_file.csv', usecols=lambda col: col in cols_headers, dtype=object, na_filter=False)
    #for _ in cols_headers:
    #    if _ not in data.columns:
    #        data[_] = ""
    #data = data[cols_headers]
    #data["CAddr"].replace('', 0, inplace=True)
    #test = data[["Sel", "DataSize", "EnbBits"]]
    #data = data.assign(Sel=1, DataSize=10, EnbBits=10)
    #data[["Sel", "DataSize", "EnbBits"]] = test
    #print(data)
    cols = len(data_headers)
    data = pd.DataFrame(data=[[""] * cols for _ in range(100)], index=range(100),
                        columns=data_headers)
    print(data)
