import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets
import FileIO
import led
import pandas as pd
import ni845x_if as ni
import numpy as np
from Picker import *

# NI SPI interface
ni8452 = ni.ni845x_if()
SPIConnFlag = bool(False)

def spi_read(add,size):
    size = np.int(size)
    if size < 6:
        cmd = 2
        ret = ni8452.ni845xSpiWriteRead([((cmd << 5) + (add >> 3)) % 256, (add << 5) %256])
        print("Addr:"+str(add)+"_Rd:"+str(ret[1] % 32))
        return (ret[1] % 32)
    else:
        cmd = 1
        ret = ni8452.ni845xSpiWriteRead([((cmd << 5) + (add >> 3)) % 256, (add << 5) % 256, 0])
        print("Addr:" + str(add) + "_Rd:" + str((ret[1] % 32) * 256 + ret[2] % 256))
        return ((ret[1] % 32) * 256 + ret[2] % 256)

def spi_write(add,data,size):
    data = np.int(data)
    size = np.int(size)
    if size < 6:
        cmd = 6
        ret = ni8452.ni845xSpiWriteRead([((cmd << 5) + (add >> 3)) % 256, ((add << 5) + data) %256])
        print('Wr:'+str(data)+"_Rd:"+str(ret[1] % 32))
    else:
        cmd = 5
        ret = ni8452.ni845xSpiWriteRead([((cmd << 5) + (add >> 3)) % 256, ((add << 5) + (data >> 8)) % 256, data % 256])
        print('Wr:' + str(data) + "_Rd:" + str((ret[1] % 32) * 256 + ret[2] % 256))



# Main Control Table
class LoadTable(QtWidgets.QTableWidget):
    SelectedTx = QtCore.pyqtSignal(int,str,int)
    def __init__(self,parent=None):
        super(LoadTable, self).__init__(0,16,parent)
        self.data = pd.DataFrame()
        self.onLoading = False
        # Store button handle
        self.button_read = []
        self.button_write = []
        self.button_read_en = []
        self.button_write_en = []
        self.cols_headers = ["SS", "Addr", "Sel", "Name", "VolMax", "VolMin", "DataSize", "EnbBits", "BinR",
                        "DecR", "VolR", "Read", "BinW", "DecW", "VolW", "Write"]
        self.data_headers = ["SS","Addr","Sel","Name","VolMax","VolMin","DataSize","EnbBits","BinR","DecR","VolR","BinW","DecW","VolW"]
        self.data = pd.DataFrame(columns = self.data_headers)

        self.setHorizontalHeaderLabels(self.cols_headers)
        self.horizontalHeader().setHighlightSections(True)
        # Draw Borders for Cols' Headers on Win10
        self.horizontalHeader().setStyleSheet("QHeaderView::section{"
            "border-top:0px solid #D8D8D8;"
            "border-left:0px solid #D8D8D8;"
            "border-right:1px solid #D8D8D8;"
            "border-bottom: 1px solid #D8D8D8;"
            "background-color:white;"
            "padding:4px;"
        "}")
        #self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.setColumnHidden(4,True)
        self.setColumnHidden(5, True)
        self.setColumnHidden(10, True)
        self.setColumnHidden(14, True)
        #self.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.setColumnWidth(0, 20)
        self.setColumnWidth(1, 50)
        self.setColumnWidth(2, 20)
        self.setColumnWidth(3, 250)
        self.setColumnWidth(4, 20)
        self.setColumnWidth(5, 20)
        self.setColumnWidth(6, 20)
        self.setColumnWidth(7, 20)
        self.setColumnWidth(8, 100)
        self.setColumnWidth(9, 60)
        self.setColumnWidth(10, 80)
        self.setColumnWidth(11, 60)
        self.setColumnWidth(12, 100)
        self.setColumnWidth(13, 60)
        self.setColumnWidth(14, 80)
        self.setColumnWidth(15, 60)
        #self.setColumnWidth(16, 30)
        self.cellChanged.connect(self._cellclicked)
        self.itemSelectionChanged.connect(self._itemclicked)

    @QtCore.pyqtSlot(int, int)
    def _cellclicked(self, r, c):
        it = self.item(r, c)
        it.setTextAlignment(QtCore.Qt.AlignCenter)
        if self.onLoading is False and c not in [8,9,10]:
            self.onLoading = True
            text = it.text().replace(" ", "")
            if c is 13:
                if text.isdigit():
                    self.item(r, c).setData(QtCore.Qt.EditRole, int(text))
                else:
                    self.item(r, c).setData(QtCore.Qt.EditRole, self.data.at[r,self.cols_headers[c]])
                    self.onLoading = False
                    return
            elif c is 12:
                for _ in text:
                    if _ not in '01':
                        self.item(r, c).setData(QtCore.Qt.EditRole, self.data.at[r, self.cols_headers[c]])
                        self.onLoading = False
                        return
            elif c is 14:
                try:
                    data = float(text)
                    self.item(r, c).setData(QtCore.Qt.EditRole, data)
                except Exception as e:
                    self.item(r, c).setData(QtCore.Qt.EditRole, self.data.at[r, self.cols_headers[c]])
                    self.onLoading = False
                    return
            self.data.at[r,self.cols_headers[c]] = text
            # Bin Dec data sync
            if c is 13 and str(self.data.at[r,"EnbBits"]).isdigit():
                if int(self.data.at[r,"EnbBits"]) is not 0:
                    _dec = int(text)
                    _format = "0"+ str(self.data.at[r,"EnbBits"]) + "b"
                    _bin = format(_dec, _format)
                    self.data.at[r, self.cols_headers[12]] = _bin
                    self.setItem(r, 12, QtWidgets.QTableWidgetItem(_bin))
                    _vol = self.dec2voltage(self.data.at[r,"VolMax"],self.data.at[r,"VolMin"],_dec,self.data.at[r,"EnbBits"])
                    if _vol is not None:
                        self.data.at[r, self.cols_headers[14]] = _vol
                        _temp = QtWidgets.QTableWidgetItem()
                        _temp.setData(QtCore.Qt.EditRole,_vol)
                        self.setItem(r, 14, _temp)
            elif c is 12:
                _dec = int(text,2)
                self.data.at[r, self.cols_headers[13]] = _dec
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, _dec)
                self.setItem(r, 13, _temp)
                if str(self.data.at[r,"EnbBits"]).isdigit():
                    if int(self.data.at[r,"EnbBits"]) is not 0:
                        _format = "0" + str(self.data.at[r, "EnbBits"]) + "b"
                        _bin = format(_dec, _format)
                        self.item(r, 12).setData(QtCore.Qt.EditRole, _bin)
                _vol = self.dec2voltage(self.data.at[r,"VolMax"],self.data.at[r,"VolMin"],_dec,self.data.at[r,"EnbBits"])
                if _vol is not None:
                    self.data.at[r, self.cols_headers[14]] = _vol
                    _temp = QtWidgets.QTableWidgetItem()
                    _temp.setData(QtCore.Qt.EditRole,_vol)
                    self.setItem(r, 14, _temp)
            elif c is 14:
                _dec = self.voltage2dec(self.data.at[r,"VolMax"],self.data.at[r,"VolMin"],text,self.data.at[r,"EnbBits"])
                if _dec is not None:
                    self.data.at[r, self.cols_headers[13]] = _dec
                    _temp = QtWidgets.QTableWidgetItem()
                    _temp.setData(QtCore.Qt.EditRole, _dec)
                    self.setItem(r, 13, _temp)
                    _format = "0" + str(self.data.at[r, "EnbBits"]) + "b"
                    _bin = format(_dec, _format)
                    self.data.at[r, self.cols_headers[12]] = _bin
                    self.setItem(r, 12, QtWidgets.QTableWidgetItem(_bin))
            else:
                pass
            # Status Update
            if c in [0,1,2,6,7,12,13]:
                _enRead = str(self.data.at[r,"SS"]).isdigit() and str(self.data.at[r,"Addr"]).isdigit() and str(
                    self.data.at[r, "DataSize"]).isdigit() and str(self.data.at[r,"EnbBits"]).isdigit() and str(self.data.at[r, "Sel"]).isdigit()
                _enWrite = _enRead and str(self.data.at[r, "DecW"]).isdigit()
                self.button_read_en[r] = _enRead
                self.button_write_en[r] = _enWrite
                self.button_read[r].setEnabled(SPIConnFlag and self.button_read_en[r])
                self.button_write[r].setEnabled(SPIConnFlag and self.button_write_en[r])
            self.onLoading = False


    @QtCore.pyqtSlot()
    def _itemclicked(self):
        for index in self.selectedIndexes():
            r = index.row()
            if self.button_read_en[r] is True:
                nbit = int(self.data.at[r, self.cols_headers[7]])
                self.SelectedTx.emit(r+1,self.data.at[r, self.cols_headers[3]],nbit)



    @QtCore.pyqtSlot()
    def dataload(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import SPI File", os.getcwd(),"Data Files (*.xlsm *.xls *.xlsx *.csv)")
        if (path):
            self.onLoading = True
            try:
                self.data = FileIO.load(path)
            except Exception as e:
                QtWidgets.QMessageBox.critical(self,"Error","FAIL TO LOAD!")
                return
            self.setRowCount(0)
            self.setRowCount(self.data.shape[0])
            self.button_read = []
            self.button_write = []
            self.button_read_en = []
            self.button_write_en = []

            for index, row in self.data.iterrows():
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, int(row["SS"]))
                self.setItem(index, 0, _temp)
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, int(row["Addr"]))
                self.setItem(index, 1, _temp)
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, int(row["Sel"]))
                self.setItem(index, 2, _temp)
                self.setItem(index, 3, QtWidgets.QTableWidgetItem(str(row["Name"])))
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, float(row["VolMax"]))
                self.setItem(index, 4, _temp)
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, float(row["VolMin"]))
                self.setItem(index, 5, QtWidgets.QTableWidgetItem(str(row["VolMin"])))
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, int(row["DataSize"]))
                self.setItem(index, 6, _temp)
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, int(row["EnbBits"]))
                self.setItem(index, 7, _temp)
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.DisplayRole, str(row["BinR"]))
                _temp.setFlags(QtCore.Qt.ItemIsEnabled)
                self.setItem(index, 8, _temp)
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.DisplayRole, str(row["DecR"]))
                _temp.setFlags(QtCore.Qt.ItemIsEnabled)
                self.setItem(index, 9, _temp)
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.DisplayRole, str(row["VolR"]))
                _temp.setFlags(QtCore.Qt.ItemIsEnabled)
                self.setItem(index, 10, _temp)
                self.setItem(index, 12, QtWidgets.QTableWidgetItem(str(row["BinW"])))
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, row["DecW"])
                self.setItem(index, 13, _temp)
                self.setItem(index, 14, QtWidgets.QTableWidgetItem(str(row["VolW"])))

                button_read = QtWidgets.QPushButton('Read')
                button_write = QtWidgets.QPushButton('Write')
                button_read.clicked.connect(lambda *args, rowcount=index: self.handleReadClicked(rowcount))
                button_write.clicked.connect(lambda *args, rowcount=index: self.handleWriteClicked(rowcount))
                self.button_read.append(button_read)
                self.button_write.append(button_write)
                _enRead = str(row["SS"]).isdigit() and str(row["Addr"]).isdigit() and str(row["DataSize"]).isdigit() and str(row["EnbBits"]).isdigit() and str(row["Sel"]).isdigit()
                _enWrite = _enRead and str(row["DecW"]).isdigit()
                self.button_read_en.append(_enRead)
                self.button_write_en.append(_enWrite)
                button_read.setEnabled(SPIConnFlag and _enRead)
                button_write.setEnabled(SPIConnFlag and _enWrite)
                self.setCellWidget(index, 11, button_read)
                self.setCellWidget(index, 15, button_write)
            #self.resizeColumnsToContents()
            self.onLoading = False

    @QtCore.pyqtSlot()
    def addrow(self):
        if len(self.selectedIndexes()) is 0:
            rowcount = self.rowCount()
            if rowcount is 0:
                newRowSeries = pd.Series([0, 0, 0, "", 1.0, 0.0, 0, 0, "", "", "", "", "", ""],index = self.data_headers)
            else:
                newRowSeries = self.data.iloc[-1]
                newRowSeries["Name","BinR","DecR","VolR","BinW","DecW","VolW"] = ""
                addr = newRowSeries["Addr"]
                sel = newRowSeries["Sel"]
                size = newRowSeries["DataSize"]
                en = newRowSeries["EnbBits"]
                if str(sel).isdigit() and str(size).isdigit() and str(en).isdigit():
                    if int(sel) is 0:
                        newRowSeries["Addr"] = int(addr) + 1
                    elif int(size) > int(en) * int(sel):
                        newRowSeries["Sel"] = int(sel) + 1
                    else:
                        newRowSeries["Addr"] = int(addr) + 1
                        newRowSeries["Sel"] = 1
                else:
                    newRowSeries["Addr"] = int(addr) + 1
        else:
            rowcount = self.selectedIndexes()[-1].row() + 1
            newRowSeries = self.data.iloc[rowcount-1]
            newRowSeries.loc[["Name", "BinR", "DecR", "VolR", "BinW", "DecW", "VolW"]] = ""
            sel = newRowSeries["Sel"]
            size = newRowSeries["DataSize"]
            en = newRowSeries["EnbBits"]
            if str(sel).isdigit() and str(size).isdigit() and str(en).isdigit():
                if int(sel) is 0:
                    newRowSeries.loc[["Addr"]] = int(newRowSeries["Addr"]) + 1
                elif int(size) > int(en) * int(sel):
                    newRowSeries.loc[["Sel"]] = int(newRowSeries["Sel"]) + 1
                else:
                    newRowSeries.loc[["Addr"]] = int(newRowSeries["Addr"]) + 1
                    newRowSeries.loc[["Sel"]] = 1
            else:
                newRowSeries.loc[["Addr"]] = int(newRowSeries["Addr"]) + 1
        self.insertRow(rowcount)

        _data = self.data[0:rowcount]
        self.data = _data.append(newRowSeries, ignore_index=True).append(self.data[rowcount:], ignore_index=True)
        self.data.reset_index(drop=True, inplace=True)

        button_read = QtWidgets.QPushButton('Read')
        button_write = QtWidgets.QPushButton('Write')
        button_read.clicked.connect(lambda *args, rowcount=rowcount:self.handleReadClicked(rowcount))
        button_write.clicked.connect(lambda *args, rowcount=rowcount: self.handleWriteClicked(rowcount))
        self.button_read.insert(rowcount, button_read)
        self.button_write.insert(rowcount, button_write)
        self.button_read_en.insert(rowcount, False)
        self.button_write_en.insert(rowcount, False)
        button_read.setEnabled(False)
        button_write.setEnabled(False)
        self.setCellWidget(rowcount, 11, button_read)
        self.setCellWidget(rowcount, 15, button_write)

        self.onLoading = True
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.EditRole, int(newRowSeries["SS"]))
        self.setItem(rowcount, 0, _temp)
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.EditRole, int(newRowSeries["Addr"]))
        self.setItem(rowcount, 1, _temp)
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.EditRole, int(newRowSeries["Sel"]))
        self.setItem(rowcount, 2, _temp)
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.EditRole, float(newRowSeries["VolMax"]))
        self.setItem(rowcount, 4, _temp)
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.EditRole, float(newRowSeries["VolMin"]))
        self.setItem(rowcount, 5, _temp)
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.EditRole, int(newRowSeries["DataSize"]))
        self.setItem(rowcount, 6, _temp)
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.EditRole, int(newRowSeries["EnbBits"]))
        self.setItem(rowcount, 7, _temp)
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.DisplayRole, "")
        _temp.setFlags(QtCore.Qt.ItemIsEnabled)
        self.setItem(rowcount, 8, _temp)
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.DisplayRole, "")
        _temp.setFlags(QtCore.Qt.ItemIsEnabled)
        self.setItem(rowcount, 9, _temp)
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.DisplayRole, "")
        _temp.setFlags(QtCore.Qt.ItemIsEnabled)
        self.setItem(rowcount, 10, _temp)
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.EditRole, "")
        self.setItem(rowcount, 12, _temp)
        self.onLoading = False


    @QtCore.pyqtSlot()
    def removerow(self):
        rows = set()
        for index in self.selectedIndexes():
            rows.add(index.row())
        if len(rows) > 0:
            for row in sorted(rows, reverse=True):
                self.removeRow(row)
                del self.button_read[row]
                del self.button_write[row]
                del self.button_read_en[row]
                del self.button_write_en[row]

            self.data = self.data.drop(index=rows)
            self.data.reset_index(drop=True, inplace=True)
            #rows.sort()
            #print(rows[0])
            #print(len(self.button_read))
            rows = sorted(rows)

            if rows[0] < len(self.button_read):
                for _ in range(rows[0],len(self.button_read)):
                    print(_)
                    self.button_write[_].clicked.disconnect()
                    self.button_write[_].clicked.connect(lambda *args, rowcount=_: self.handleWriteClicked(rowcount))
                    self.button_read[_].clicked.disconnect()
                    self.button_read[_].clicked.connect(lambda *args, rowcount=_: self.handleReadClicked(rowcount))

    @QtCore.pyqtSlot(int)
    def handleReadClicked(self,r):
        size = int(self.data.at[r, "DataSize"])
        Addr = int(self.data.at[r, "Addr"])
        Sel =  int(self.data.at[r, "Sel"])
        nBits = int(self.data.at[r, "EnbBits"])
        res = spi_read(Addr,size)
        if Sel == 0:
            if size is not nBits:
                res = res % (2 ** nBits)
        else:
            res = (res >> (Sel - 1)) % (2 ** nBits)
        self.data.at[r, "DecR"] = res
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.DisplayRole, int(res))
        _temp.setFlags(QtCore.Qt.ItemIsEnabled)
        self.setItem(r, 9, _temp)

        _format = "0" + str(nBits) + "b"
        _bin = format(int(res), _format)
        self.data.at[r, "BinR"] = _bin
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.DisplayRole, _bin)
        _temp.setFlags(QtCore.Qt.ItemIsEnabled)
        self.setItem(r, 8, _temp)

        _vol = self.dec2voltage(self.data.at[r,"VolMax"],self.data.at[r,"VolMin"],res,self.data.at[r,"EnbBits"])
        if _vol is not None:
            _temp = QtWidgets.QTableWidgetItem()
            _temp.setData(QtCore.Qt.DisplayRole, _vol)
            _temp.setFlags(QtCore.Qt.ItemIsEnabled)
            self.setItem(r, 10, _temp)


    @QtCore.pyqtSlot(int)
    def handleWriteClicked(self, r):
        data = int(self.data.at[r, "DecW"])
        size = int(self.data.at[r, "DataSize"])
        Addr = int(self.data.at[r, "Addr"])
        Sel =  int(self.data.at[r, "Sel"])
        nBits = int(self.data.at[r, "EnbBits"])
        if Sel is not 0:
            res = spi_read(Addr, size)
            _format = "0" + str(size) + "b"
            _mask = 2 ** size - 1 - (2 ** nBits - 1) * (2 ** (Sel - 1))
            mask = format(_mask, _format)
            data = (res & int(mask,2)) | (data << (Sel - 1))
        spi_write(int(Addr), data, size)
        self.handleReadClicked(r)

    def button_update(self):
        for _ in range(len(self.button_read)):
            self.button_read[_].setEnabled(SPIConnFlag and self.button_read_en[_])
        for _ in range(len(self.button_write)):
            self.button_write[_].setEnabled(SPIConnFlag and self.button_write_en[_])

    def dec2voltage(self,Volmax,Volmin,dec,nbits):
        try:
            Volmax = float(Volmax)
            Volmin = float(Volmin)
            dec = float(dec)
            nbits = float(nbits)
        except Exception as e:
            return None
        if nbits == 0:
            return None
        voltage = (Volmax - Volmin) * dec/(2**nbits-1) + Volmin
        if voltage > Volmax:
            voltage = Volmax
        elif voltage < Volmin:
            voltage = Volmin
        return voltage

    def voltage2dec(self, Volmax, Volmin, Vol, nbits):
        try:
            Volmax = float(Volmax)
            Volmin = float(Volmin)
            Vol = float(Vol)
            nbits = float(nbits)
        except Exception as e:
            return None
        if Volmax == Volmin:
            return None
        dec = (2**nbits-1) * (Vol - Volmin) / (Volmax - Volmin)
        if dec > (2**nbits-1):
            dec = (2**nbits-1)
        elif dec < 0:
            dec = 0
        return int(round(dec))


class ShortCutList(QtWidgets.QTableWidget):
    Tx = QtCore.pyqtSignal(bool,int)
    def __init__(self,parent=None):
        super(ShortCutList, self).__init__(0,6,parent)
        self.verticalHeader().hide()
        self.setHorizontalHeaderLabels(["Name","Range","Bin","Dec","Read","Write"])
        self.button_read = []
        self.button_write = []
        self.ReadData = []
        self.ReadList = []
        self.data = pd.DataFrame(columns=["Name","Range","Bin","Dec"])
        self.onLoading = False
        self.setColumnWidth(0, 100)
        self.setColumnWidth(1, 80)
        self.setColumnWidth(2, 80)
        self.setColumnWidth(3, 80)
        self.setColumnWidth(4, 60)
        self.setColumnWidth(5, 60)

        self.setRowCount(1)
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.DisplayRole, "All")
        _temp.setFlags(QtCore.Qt.ItemIsEnabled)
        self.setItem(0, 0, _temp)
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.DisplayRole, "All")
        _temp.setFlags(QtCore.Qt.ItemIsEnabled)
        self.setItem(0, 1, _temp)
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.DisplayRole, "")
        _temp.setFlags(QtCore.Qt.ItemIsEnabled)
        self.setItem(0, 2, _temp)
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.DisplayRole, "")
        _temp.setFlags(QtCore.Qt.ItemIsEnabled)
        self.setItem(0, 3, _temp)

        button_read = QtWidgets.QPushButton('Read')
        button_write = QtWidgets.QPushButton('Write')
        button_read.setEnabled(SPIConnFlag)
        button_write.setEnabled(SPIConnFlag)
        button_read.clicked.connect(lambda *args, rowcount=0: self.handleReadRunClicked(rowcount))
        button_write.clicked.connect(lambda *args, rowcount=0: self.handleWriteRunClicked(rowcount))
        self.button_read.append(button_read)
        self.button_write.append(button_write)
        self.setCellWidget(0, 4, button_read)
        self.setCellWidget(0, 5, button_write)
        self.cellChanged.connect(self._cellchanged)

    @QtCore.pyqtSlot(int, int)
    def _cellchanged(self, r, c):
        it = self.item(r, c)
        it.setTextAlignment(QtCore.Qt.AlignCenter)
        row = r -1
        if self.onLoading is False:
            self.onLoading = True
            if c is 2:
                if (it.text().count(".") > 1 and [-1, -1] in self.ReadData[row]) or (it.text().count(".") > 0 and [-1, -1] not in self.ReadData[row]):
                    self.item(r, c).setData(QtCore.Qt.EditRole, self.data.at[row, "Bin"])
                    self.onLoading = False
                    return
                for _ in it.text():
                    if _ not in '.01':
                        self.item(r, c).setData(QtCore.Qt.EditRole, self.data.at[row, "Bin"])
                        self.onLoading = False
                        return

                self.data.at[row, "Bin"] = it.text()
                _dec = self.Bin2FixPointFloat(it.text())
                self.data.at[row, "Dec"] = _dec
                self.item(r, 3).setData(QtCore.Qt.EditRole, _dec)
                if [-1, -1] not in self.ReadData[row]:
                    _format = "0" + str(len(self.ReadData[row])) + "b"
                    _bin = format(int(_dec), _format)
                else:
                    _index = self.ReadData[row].index([-1, -1])
                    if _index is 0:
                        nint = 1
                    else:
                        nint = _index
                    _bin = self.Float2FixPointBin(_dec, nint, len(self.ReadData[row]) - _index - 1)
                self.data.at[row, "Bin"] = _bin
                self.item(r, 2).setData(QtCore.Qt.EditRole, _bin)
            elif c is 3:
                if float(it.text()) < 0:
                    if [-1, -1] not in self.ReadData[row]:
                        self.item(r, c).setData(QtCore.Qt.EditRole, int(self.data.at[row, "Dec"]))
                    else:
                        self.item(r, c).setData(QtCore.Qt.EditRole, float(self.data.at[row, "Dec"]))
                    self.onLoading = False
                    return

                if [-1, -1] not in self.ReadData[row]:
                    _format = "0" + str(len(self.ReadData[row])) + "b"
                    self.data.at[row, "Dec"] = int(it.text())
                    _bin = format(int(it.text()), _format)
                else:
                    _index = self.ReadData[row].index([-1, -1])
                    if _index is 0:
                        nint = 1
                    else:
                        nint = _index
                    self.data.at[row, "Dec"] = float(it.text())
                    _bin = self.Float2FixPointBin(float(it.text()), nint, len(self.ReadData[row]) - _index - 1)
                self.data.at[row, "Bin"] = _bin
                self.item(r, 2).setData(QtCore.Qt.EditRole, _bin)
            else:
                pass
            self.onLoading = False

    @QtCore.pyqtSlot()
    def removerow(self):
        rows = set()
        for index in self.selectedIndexes():
            rows.add(index.row()-1)
        if -1 in rows:
            rows.remove(-1)

        if len(rows) > 0:
            for row in sorted(rows, reverse=True):
                self.removeRow(row+1)
                del self.button_read[row+1]
                del self.button_write[row+1]
                del self.ReadData[row]
                del self.ReadList[row]

            self.data = self.data.drop(index=rows)
            self.data.reset_index(drop=True, inplace=True)

            rows = sorted(rows)
            if rows[0]+1 < len(self.button_read):
                for _ in range(rows[0]+1, len(self.button_read)):
                    self.button_write[_].clicked.disconnect()
                    self.button_write[_].clicked.connect(lambda *args, rowcount=_: self.handleWriteRunClicked(rowcount))
                    self.button_read[_].clicked.disconnect()
                    self.button_read[_].clicked.connect(lambda *args, rowcount=_: self.handleReadRunClicked(rowcount))


    @QtCore.pyqtSlot(int)
    def handleReadRunClicked(self,r):
        self.Tx.emit(True,r)

    @QtCore.pyqtSlot(int)
    def handleWriteRunClicked(self,r):
        self.Tx.emit(False,r)

    def button_update(self):
        for button in self.button_write+self.button_read:
            button.setEnabled(SPIConnFlag)

    def Float2FixPointBin(self,float,nint,nfrac):
        _Dec = round(float*(2**nfrac))
        _format = "0" + str(nint + nfrac) + "b"
        _bin = format(_Dec, _format)
        bin = _bin[:nint] + "." + _bin[nint:]
        return bin

    def Bin2FixPointFloat(self,_bin):
        if "." in _bin:
            index = _bin.index(".")
            e = len(_bin) - index - 1
            _bin = _bin.replace(".","")
            _dec = int(_bin, 2)
            dec = float(_dec)/(2**e)
            return dec
        else:
            return float(int(_bin, 2))



class MainWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.picker = None
        self.table = LoadTable()
        self.list = ShortCutList()

        self.list.Tx.connect(self.handleBackbone)

        load_button = QtWidgets.QPushButton("Load")
        load_button.setFixedSize(QtCore.QSize(100, 30))
        load_button.clicked.connect(self.table.dataload)
        save_button = QtWidgets.QPushButton("Save")
        save_button.setFixedSize(QtCore.QSize(100, 30))
        save_button.clicked.connect(self.save_data)

        filehbox = QtWidgets.QHBoxLayout()
        filehbox.addWidget(load_button)
        filehbox.addWidget(save_button)
        #filebox = QtWidgets.QGroupBox()
        #filebox.setLayout(filehbox)

        self.add_button = QtWidgets.QPushButton("Add")
        self.add_button.setFixedSize(QtCore.QSize(100, 30))
        self.add_button.clicked.connect(self.table.addrow)
        self.delete_button = QtWidgets.QPushButton("Delete")
        self.delete_button.setFixedSize(QtCore.QSize(100, 30))
        self.delete_button.clicked.connect(self.table.removerow)
        self.lock_button = QtWidgets.QPushButton("Lock")
        self.lock_button.setFixedSize(QtCore.QSize(100, 30))
        self.lock_button.clicked.connect(self.lock_switch)
        self.vol_button = QtWidgets.QPushButton("Show Voltage")
        self.vol_button.setFixedSize(QtCore.QSize(120, 30))
        self.vol_button.clicked.connect(self.voltageModeSwitch)

        button_layout1 = QtWidgets.QHBoxLayout()
        button_layout1.addWidget(self.add_button)
        button_layout1.addWidget(self.delete_button)
        button_layout1.addWidget(self.lock_button)
        button_layout1.addWidget(self.vol_button)
        button_layout1.addStretch(1)
        button_box1 = QtWidgets.QGroupBox("Main Table")
        button_box1.setLayout(button_layout1)

        self.add_button_sc = QtWidgets.QPushButton("Add")
        self.add_button_sc.setFixedSize(QtCore.QSize(100, 30))
        self.add_button_sc.clicked.connect(self.PickerCaller)
        self.delete_button_sc = QtWidgets.QPushButton("Delete")
        self.delete_button_sc.setFixedSize(QtCore.QSize(100, 30))
        self.delete_button_sc.clicked.connect(self.list.removerow)
        self.lock_button_sc = QtWidgets.QPushButton("Lock")
        self.lock_button_sc.setFixedSize(QtCore.QSize(100, 30))
        self.lock_button_sc.clicked.connect(self.lock_sc_switch)

        button_layout2 = QtWidgets.QHBoxLayout()
        button_layout2.addWidget(self.add_button_sc)
        button_layout2.addWidget(self.delete_button_sc)
        button_layout2.addWidget(self.lock_button_sc)
        button_layout2.addStretch(1)
        button_box2 = QtWidgets.QGroupBox("Shortcut")
        button_box2.setLayout(button_layout2)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(button_box1,7)
        button_layout.addWidget(button_box2,3)


        tablehbox = QtWidgets.QHBoxLayout()
        #tablehbox.setContentsMargins(10, 10, 10, 10)
        tablehbox.addWidget(self.table,7)
        tablehbox.addWidget(self.list,3)

        self.combox_clk = QtWidgets.QComboBox(self)
        self.combox_clk.addItems(["25", "32", "40", "50", "80", "100", "125", "160", "200", "250", "400", "500", "625", "800", "1000", "1250", "2500", "3125", "4000", "5000", "6250", "10000", "12500", "20000", "25000", "33330", "50000"])
        clockhbox = QtWidgets.QHBoxLayout()
        clockhbox.addWidget(QtWidgets.QLabel("Clock:"))
        clockhbox.addWidget(self.combox_clk)
        clockhbox.addWidget(QtWidgets.QLabel("KHz"))

        self.combox_vol = QtWidgets.QComboBox(self)
        self.combox_vol.addItems(["3.3", "2.5", "1.8", "1.5", "1.2"])
        volhbox = QtWidgets.QHBoxLayout()
        volhbox.addWidget(QtWidgets.QLabel("Voltage:"))
        volhbox.addWidget(self.combox_vol)
        volhbox.addWidget(QtWidgets.QLabel("V"))

        self.button_connect = QtWidgets.QPushButton('Connect')
        self.button_connect.setFixedSize(QtCore.QSize(100, 30))
        self.led = led.MyLed()
        self.button_connect.clicked.connect(self.spi_switch)
        conhbox = QtWidgets.QHBoxLayout()
        conhbox.addWidget(self.button_connect)
        conhbox.addWidget(self.led)

        setupvbox = QtWidgets.QHBoxLayout()
        setupvbox.addLayout(clockhbox)
        setupvbox.addLayout(volhbox)
        setupvbox.addLayout(conhbox)
        setupvbox.addStretch(1)
        setupvbox.addLayout(filehbox)
        setupbox = QtWidgets.QGroupBox("Setup")
        setupbox.setLayout(setupvbox)

        #ctrlbox = QtWidgets.QVBoxLayout()
        #ctrlbox.addWidget(setupbox)
        #ctrlbox.addWidget(filebox)
        #ctrlbox.addLayout(button_layout)
        #ctrlbox.setContentsMargins(10, 200, 10, 200)

        mainlayouot = QtWidgets.QVBoxLayout(self)
        tablehbox.setContentsMargins(10, 10, 10, 10)
        mainlayouot.addWidget(setupbox)
        mainlayouot.addLayout(button_layout)
        #grid = QtWidgets.QGridLayout(self)
        #grid.addLayout(ctrlbox, 0, 1)
        #grid.addLayout(tablehbox, 0, 0)
        mainlayouot.addLayout(tablehbox)

        if ni8452.dll_flag is False:
            self.button_connect.setEnabled(False)
            QtWidgets.QMessageBox.warning(self, "WARNING", "Ni845x.dll NOT FOUND!")

        self.setGeometry(50, 50, 1800, 1000)
        self.setWindowTitle('SPI GUI for NI845x')
        self.setWindowIcon(QtGui.QIcon('tokyotech.ico'))

    @QtCore.pyqtSlot()
    def PickerCaller(self):
        if self.picker is not None:
            self.picker.close()
        self.picker = Picker()
        self.picker.buttonApply.clicked.connect(self.addrow_process)
        self.picker.CloseSignal.connect(self.pickerClose)
        self.table.SelectedTx.connect(self.picker.additem)
        self.picker.show()
        if self.lock_button.text() == "Lock":
            self.lock_switch()
        if self.lock_button_sc.text() == "Lock":
            self.lock_sc_switch()
        self.lock_button.setEnabled(False)
        self.lock_button_sc.setEnabled(False)
        self.picker.deleteAll()

    def addrow_process(self):
        itemBasket = self.picker.itemBasket
        index = self.picker.trueIndex
        name = self.picker.nameInput.text()
        self.picker.close()
        self.picker = None
        if len(itemBasket) is not 0:
            self.list.onLoading = True
            readlist = []
            data = []
            range = ""
            for _ in itemBasket:
                if _[0] is -1:
                    if _ is not itemBasket[-1]:
                        data.append([-1, -1])
                        range = range[:-1] + "."
                else:
                    row = index[_[0]]
                    data.append([row, _[1]])
                    range = range + str(row)+"["+str(_[1])+"],"
                    if row not in readlist:
                        readlist.append(row)
            self.list.ReadData.append(data)
            self.list.ReadList.append(readlist)
            range = range[:-1]

            rowcount = self.list.rowCount()
            self.list.insertRow(rowcount)
            self.list.setItem(rowcount, 0, QtWidgets.QTableWidgetItem(name))
            _temp = QtWidgets.QTableWidgetItem()
            _temp.setData(QtCore.Qt.DisplayRole, range)
            _temp.setFlags(QtCore.Qt.ItemIsEnabled)
            self.list.setItem(rowcount, 1, _temp)

            if [-1,-1] not in data:
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, int(0))
                self.list.setItem(rowcount, 3, _temp)
                _format = "0" + str(len(data)) + "b"
                _bin = format(0, _format)
                self.list.data = self.list.data.append(pd.Series([name, range, _bin, 0], index=["Name","Range","Bin","Dec"]),
                                                       ignore_index=True)
                self.list.setItem(rowcount, 2, QtWidgets.QTableWidgetItem(_bin))
            else:
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, float(0.0))
                self.list.setItem(rowcount, 3, _temp)
                _index = data.index([-1, -1])
                if _index is 0:
                    _format = "01b"
                else:
                    _format = "0" + str(len(data[:_index])) + "b"
                _bin = format(0, _format) + "."
                _format = "0" + str(len(data[_index:])-1) + "b"
                _bin = _bin + format(0, _format)
                self.list.data = self.list.data.append(pd.Series([name, range, _bin, 0.0], index=["Name","Range","Bin","Dec"]),
                                                       ignore_index=True)
                self.list.setItem(rowcount, 2, QtWidgets.QTableWidgetItem(_bin))

            button_read = QtWidgets.QPushButton('Read')
            button_write = QtWidgets.QPushButton('Write')
            button_read.setEnabled(SPIConnFlag)
            button_write.setEnabled(SPIConnFlag)
            button_read.clicked.connect(lambda *args, rowcount=rowcount: self.list.handleReadRunClicked(rowcount))
            button_write.clicked.connect(lambda *args, rowcount=rowcount: self.list.handleWriteRunClicked(rowcount))
            self.list.button_read.append(button_read)
            self.list.button_write.append(button_write)
            self.list.setCellWidget(rowcount, 4, button_read)
            self.list.setCellWidget(rowcount, 5, button_write)
            self.list.onLoading = False

    @QtCore.pyqtSlot()
    def pickerClose(self):
        self.lock_button.setEnabled(True)
        self.lock_button_sc.setEnabled(True)
        self.lock_switch()
        self.lock_sc_switch()

    @QtCore.pyqtSlot(bool,int)
    def handleBackbone(self,ReadWriteFlag,row):
        if row is 0:
            if ReadWriteFlag is True:
                for _ in range(len(self.table.button_read_en)):
                    if self.table.button_read_en[_]:
                        self.table.handleReadClicked(_)
            else:
                for _ in range(len(self.table.button_write_en)):
                    if self.table.button_write_en[_]:
                        self.table.handleWriteClicked(_)
        else:
            row = row - 1
            if ReadWriteFlag is True:
                # Read
                dictRead = {}
                _bin = ""
                for _ in self.list.ReadList[row]:
                    r = _ - 1
                    self.table.handleReadClicked(r)
                    dictRead[r] = str(self.table.data.at[r, "BinR"])
                for _ in self.list.ReadData[row]:
                    if _[0] is not -1:
                        _bin = _bin + dictRead[_[0]-1][::-1][_[1]]
                    else:
                        _bin = _bin + "."
                self.list.setItem(row+1, 2, QtWidgets.QTableWidgetItem(_bin))
            else:
                #Write
                dictWrite = {}
                binWrite = self.list.item(row+1, 2).text()
                for _ in self.list.ReadList[row]:
                    r = _ - 1
                    self.table.handleReadClicked(r)
                    dictWrite[r] = str(self.table.data.at[r, "BinR"])
                _ = self.list.ReadData[row]
                for index in range(len(self.list.ReadData[row])):
                    if _[index][0] is not -1:
                        _index = _[index][0] - 1
                        sel = _[index][1]
                        dictWrite[_index] = dictWrite[_index][::-1][:sel] + binWrite[index] + dictWrite[_index][::-1][sel+1:]
                        dictWrite[_index] = dictWrite[_index][::-1]
                    else:
                        continue
                for _ in self.list.ReadList[row]:
                    r = _ - 1
                    self.table.setItem(r, 12, QtWidgets.QTableWidgetItem(dictWrite[r]))
                    self.table.handleWriteClicked(r)

    @QtCore.pyqtSlot()
    def spi_switch(self):
        global SPIConnFlag
        global ni8452
        if SPIConnFlag is False:
            # SPI config

            resource_name = ni8452.ni845xFindDevice()
            if ni8452.status_code is 0:
                ret = ni8452.ni845xOpen(resource_name)
                print(ret)
                ni8452.ni845xSetIoVoltageLevel(int(float(self.combox_vol.currentText())*10))
                ni8452.ni845xSpiConfigurationOpen()
                ni8452.ni845xSpiConfigurationSetChipSelect(0)
                ni8452.ni845xSpiConfigurationSetClockRate(int(self.combox_clk.currentText()))
                ni8452.ni845xSpiConfigurationSetClockPolarity(0)
                ni8452.ni845xSpiConfigurationSetClockPhase(0)

                self.button_connect.setText("Disconnect")
                SPIConnFlag = True
                self.led.ConnFlag = True
                self.combox_clk.setEnabled(False)
                self.combox_vol.setEnabled(False)
                self.led.update()
                self.table.button_update()
                self.list.button_update()
            else:
                    QtWidgets.QMessageBox.warning(self,"WARNING","Please Check NI Devices.")

        else:
            self.button_connect.setText("Connect")
            SPIConnFlag = False
            self.led.ConnFlag = False
            self.combox_clk.setEnabled(True)
            self.combox_vol.setEnabled(True)
            self.led.update()
            self.table.button_update()
            self.list.button_update()
            ni8452.ni845xSpiConfigurationClose()
            ni8452.ni845xClose()

    def voltageModeSwitch(self):
        if self.table.isColumnHidden(4):
            self.table.setColumnHidden(4, False)
            self.table.setColumnHidden(5, False)
            self.table.setColumnHidden(10, False)
            self.table.setColumnHidden(14, False)
            self.vol_button.setText("Hide Voltage")
        else:
            self.table.setColumnHidden(4, True)
            self.table.setColumnHidden(5, True)
            self.table.setColumnHidden(10, True)
            self.table.setColumnHidden(14, True)
            self.vol_button.setText("Show Voltage")

    def closeEvent(self, event):
        if self.led.ConnFlag is True:
            ni8452.ni845xSpiConfigurationClose()
            ni8452.ni845xClose()

    @QtCore.pyqtSlot()
    def lock_switch(self):
        if self.lock_button.text() == "Lock":
            self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.add_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.lock_button.setText("Unlock")
        else:
            self.table.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
            self.add_button.setEnabled(True)
            self.delete_button.setEnabled(True)
            self.lock_button.setText("Lock")

    @QtCore.pyqtSlot()
    def lock_sc_switch(self):
        if self.lock_button_sc.text() == "Lock":
            self.list.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.add_button_sc.setEnabled(False)
            self.delete_button_sc.setEnabled(False)
            self.lock_button_sc.setText("Unlock")
        else:
            self.list.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
            self.add_button_sc.setEnabled(True)
            self.delete_button_sc.setEnabled(True)
            self.lock_button_sc.setText("Lock")

    def save_data(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save SPI Data", os.getcwd(), "CSV Files (*.csv)")
        if (path):
            FileIO.df2csv(path,self.table.data)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
