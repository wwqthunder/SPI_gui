import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets
import FileIO
import test
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
        print("Addr:" + str(add) + "_Rd:" + str((ret[1] % 32) * 256 + ret[2]))
        return ((ret[1] % 32) * 256 + ret[2])

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
        print('Wr:' + str(data) + "_Rd:" + str((ret[1] % 32) * 256 + ret[2]))


# Main Control Table
class LoadTable(QtWidgets.QTableWidget):
    def __init__(self,parent=None):
        super(LoadTable, self).__init__(0,17,parent)
        self.data = pd.DataFrame()
        self.onLoading = False
        # Store button handle
        self.button_read = []
        self.button_write = []
        self.button_read_en = []
        self.button_write_en = []
        self.cols_headers = ["SS", "Addr", "Sel", "Name", "Vol_Max", "Vol_Min", "DataSize", "EnbBits", "BinR",
                        "DecR", "VolR", "Read", "BinW", "DecW", "VolW", "Write", "Steps"]
        self.data_headers = ["SS","Addr","Sel","Name","Vol_Max","Vol_Min","DataSize","EnbBits","BinR","DecR","VolR","BinW","DecW","VolW","Steps"]
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
        self.setColumnWidth(16, 30)
        self.cellChanged.connect(self._cellclicked)

    @QtCore.pyqtSlot(int, int)
    def _cellclicked(self, r, c):
        it = self.item(r, c)
        it.setTextAlignment(QtCore.Qt.AlignCenter)
        if self.onLoading is False:
            self.onLoading = True
            self.data.at[r,self.cols_headers[c]] = it.text()
            if c in [9,13]:
                _format = "0"+ str(self.data.at[r,"EnbBits"]) + "b"
                _bin = format(int(it.text()), _format)
                self.data.at[r, self.cols_headers[c-1]] = _bin
                self.setItem(r, c - 1, QtWidgets.QTableWidgetItem(_bin))
            elif c in [8,12]:
                _dec = int(it.text(),2)
                self.data.at[r, self.cols_headers[c + 1]] = _dec
                self.setItem(r, c + 1, QtWidgets.QTableWidgetItem(str(_dec)))
            else:
                pass
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
    def dataload(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import SPI File", os.getcwd(),"Excel Files (*.xlsm)")
        if (path):
            self.onLoading = True
            self.data = FileIO.loadxlsm(path)
            self.setRowCount(0)
            self.setRowCount(self.data.shape[0])
            self.button_read = []
            self.button_write = []
            self.button_read_en = []
            self.button_write_en = []

            for index, row in self.data.iterrows():
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, row["SS"])
                self.setItem(index, 0, _temp)
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, row["Addr"])
                self.setItem(index, 1, _temp)
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, row["Sel"])
                self.setItem(index, 2, _temp)
                self.setItem(index, 3, QtWidgets.QTableWidgetItem(str(row["Name"])))
                self.setItem(index, 4, QtWidgets.QTableWidgetItem(str(row["Vol_Max"])))
                self.setItem(index, 5, QtWidgets.QTableWidgetItem(str(row["Vol_Min"])))
                self.setItem(index, 6, QtWidgets.QTableWidgetItem(str(row["DataSize"])))
                self.setItem(index, 7, QtWidgets.QTableWidgetItem(str(row["EnbBits"])))
                self.setItem(index, 8, QtWidgets.QTableWidgetItem(str(row["BinR"])))
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, row["DecR"])
                self.setItem(index, 9, _temp)
                self.setItem(index, 10, QtWidgets.QTableWidgetItem(str(row["VolR"])))
                self.setItem(index, 12, QtWidgets.QTableWidgetItem(str(row["BinW"])))
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, row["DecW"])
                self.setItem(index, 13, _temp)
                self.setItem(index, 14, QtWidgets.QTableWidgetItem(str(row["VolW"])))
                self.setItem(index, 16, QtWidgets.QTableWidgetItem(str(row["Steps"])))

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
        else:
            rowcount = self.selectedIndexes()[-1].row() + 1
        self.insertRow(rowcount)

        _data = self.data[0:rowcount]
        self.data = _data.append(pd.Series(), ignore_index=True).append(self.data[rowcount:], ignore_index=True)
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


    @QtCore.pyqtSlot()
    def removerow(self):
        rows = set()
        for index in self.selectedIndexes():
            rows.add(index.row())
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
        if rows[0] > len(self.button_read):
            for _ in range(rows[0],len(self.button_read)):
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
        self.setItem(r, 9, QtWidgets.QTableWidgetItem(str(res)))

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

    @QtCore.pyqtSlot(int)
    def handleCMD(self,cmd):
        if cmd ==0:
            rowcount = self.rowCount()
            for r in range(rowcount):
                self.handleReadClicked(r)
        elif cmd == 1:
            rowcount = self.rowCount()
            for r in range(rowcount):
                self.handleWriteClicked(r)


    def button_update(self):
        for _ in range(len(self.button_read)):
            self.button_read[_].setEnabled(SPIConnFlag and self.button_read_en[_])
        for _ in range(len(self.button_write)):
            self.button_write[_].setEnabled(SPIConnFlag and self.button_write_en[_])


class ShortCutList(QtWidgets.QTableWidget):
    Tx = QtCore.pyqtSignal(int)
    def __init__(self,parent=None):
        super(ShortCutList, self).__init__(0,6,parent)
        self.verticalHeader().hide()
        self.setHorizontalHeaderLabels(["Name","Range","Bin","Dec","Read","Write"])
        self.button_read = []
        self.button_write = []
        self.data = []
        self.ReadList = []
        self.picker = None
        self.setColumnWidth(0, 100)
        self.setColumnWidth(1, 60)
        self.setColumnWidth(2, 60)
        self.setColumnWidth(3, 60)
        self.setColumnWidth(4, 60)
        self.setColumnWidth(5, 60)

        self.setRowCount(1)
        self.setItem(0, 0, QtWidgets.QTableWidgetItem("All"))
        self.setItem(0, 1, QtWidgets.QTableWidgetItem("All"))
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

    @QtCore.pyqtSlot()
    def addrow(self):
        if self.picker is not None:
            self.picker.close()
        self.picker = Picker()
        self.picker.buttonApply.clicked.connect(self.addrow_process)
        self.picker.PickerCall.emit(114,"FLL_INT[0:5]",10)
        self.picker.PickerCall.emit(115,"FLL[0:5]", 10)
        self.picker.show()

    def addrow_process(self):
        itemBasket = self.picker.itemBasket
        index = self.picker.trueIndex
        name = self.picker.nameInput.text()
        self.picker.close()
        self.picker = None
        if len(itemBasket) is not 0:
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
            self.data.append(data)
            self.ReadList.append(readlist)
            range = range[:-1]

            rowcount = self.rowCount()
            self.insertRow(rowcount)
            self.setItem(rowcount, 0, QtWidgets.QTableWidgetItem(name))
            self.setItem(rowcount, 1, QtWidgets.QTableWidgetItem(range))

            if [-1,-1] not in data:
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, int(0))
                self.setItem(rowcount, 3, _temp)
                _format = "0" + str(len(data)) + "b"
                _bin = format(0, _format)
                self.setItem(rowcount, 2, QtWidgets.QTableWidgetItem(_bin))
            else:
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, float(0.0))
                self.setItem(rowcount, 3, _temp)
                _index = data.index([-1, -1])
                _format = "0" + str(len(data[:_index])) + "b"
                _bin = format(0, _format) + "."
                _format = "0" + str(len(data[_index:])-1) + "b"
                _bin = _bin + format(0, _format)
                self.setItem(rowcount, 2, QtWidgets.QTableWidgetItem(_bin))

            button_read = QtWidgets.QPushButton('Read')
            button_write = QtWidgets.QPushButton('Write')
            button_read.setEnabled(SPIConnFlag)
            button_write.setEnabled(SPIConnFlag)
            button_read.clicked.connect(lambda *args, rowcount=rowcount: self.handleReadRunClicked(rowcount))
            button_write.clicked.connect(lambda *args, rowcount=rowcount: self.handleWriteRunClicked(rowcount))
            self.button_read.append(button_read)
            self.button_write.append(button_write)
            self.setCellWidget(rowcount, 4, button_read)
            self.setCellWidget(rowcount, 5, button_write)


    @QtCore.pyqtSlot()
    def removerow(self):
        if self.rowCount() > 2:
            self.removeRow(self.rowCount()-1)
            del self.button[-1]

    @QtCore.pyqtSlot(int)
    def handleReadRunClicked(self,r):
        self.Tx.emit(r)

    @QtCore.pyqtSlot(int)
    def handleWriteRunClicked(self,r):
        self.Tx.emit(r)

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
            index = _bin.index(".",beg=1)
            e = len(_bin)-index
            _bin = _bin.replace(".","")
            _dec = int(_bin, 2)
            dec = float(_dec)/(2**e)
            return dec
        else:
            return





class MainWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.table = LoadTable()
        self.list = ShortCutList()

        self.list.Tx.connect(self.table.handleCMD)

        load_button = QtWidgets.QPushButton("Load")
        load_button.clicked.connect(self.table.dataload)
        save_button = QtWidgets.QPushButton("Save")
        save_button.clicked.connect(self.table.dataload)

        filehbox = QtWidgets.QHBoxLayout()
        filehbox.addWidget(load_button)
        filehbox.addWidget(save_button)
        filebox = QtWidgets.QGroupBox()
        filebox.setLayout(filehbox)

        self.add_button = QtWidgets.QPushButton("Add")
        self.add_button.clicked.connect(self.table.addrow)
        self.delete_button = QtWidgets.QPushButton("Delete")
        self.delete_button.clicked.connect(self.table.removerow)
        self.lock_button = QtWidgets.QPushButton("Lock")
        self.lock_button.clicked.connect(self.lock_switch)

        button_layout1 = QtWidgets.QVBoxLayout()
        button_layout1.addWidget(self.add_button)
        button_layout1.addWidget(self.delete_button)
        button_layout1.addWidget(self.lock_button)
        button_box1 = QtWidgets.QGroupBox("Main Table")
        button_box1.setLayout(button_layout1)

        self.add_button_sc = QtWidgets.QPushButton("Add")
        self.add_button_sc.clicked.connect(self.list.addrow)
        self.delete_button_sc = QtWidgets.QPushButton("Delete")
        self.delete_button_sc.clicked.connect(self.list.removerow)
        self.lock_button_sc = QtWidgets.QPushButton("Lock")
        self.lock_button_sc.clicked.connect(self.lock_sc_switch)

        button_layout2 = QtWidgets.QVBoxLayout()
        button_layout2.addWidget(self.add_button_sc)
        button_layout2.addWidget(self.delete_button_sc)
        button_layout2.addWidget(self.lock_button_sc)
        button_box2 = QtWidgets.QGroupBox("Shortcut")
        button_box2.setLayout(button_layout2)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(button_box1)
        button_layout.addWidget(button_box2)


        tablehbox = QtWidgets.QHBoxLayout(self)
        tablehbox.setContentsMargins(10, 10, 10, 10)
        tablehbox.addWidget(self.table,20)
        tablehbox.addWidget(self.list,5)

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
        self.led = test.MyLed()
        self.button_connect.clicked.connect(self.spi_switch)
        conhbox = QtWidgets.QHBoxLayout()
        conhbox.addWidget(self.button_connect)
        conhbox.addWidget(self.led)

        setupvbox = QtWidgets.QVBoxLayout()
        setupvbox.addLayout(clockhbox)
        setupvbox.addLayout(volhbox)
        setupvbox.addLayout(conhbox)
        setupbox = QtWidgets.QGroupBox("Setup")
        setupbox.setLayout(setupvbox)

        ctrlbox = QtWidgets.QVBoxLayout()
        ctrlbox.addWidget(setupbox)
        ctrlbox.addWidget(filebox)
        ctrlbox.addLayout(button_layout)
        ctrlbox.setContentsMargins(10, 200, 10, 200)

        #grid = QtWidgets.QGridLayout(self)
        #grid.addLayout(ctrlbox, 0, 1)
        #grid.addLayout(tablehbox, 0, 0)
        tablehbox.addLayout(ctrlbox, 1)

        self.setGeometry(50, 50, 1800, 1000)

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

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())