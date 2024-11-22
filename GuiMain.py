import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets
import FileIO
import led  
import pandas as pd
import ni845x_if as ni
import numpy as np
import pickle as pkl
from Picker import *
from utilis import *
from TCPclient import *
from lut import LUT, LUTShow, ArrayShow
# NI SPI interface

ni8452 = ni.ni845x_if()
SPIConnFlag = bool(False)
Protocol = "Classic"


# Main Control Table
class LoadTable(QtWidgets.QTableWidget):
    SelectedTx = QtCore.pyqtSignal(int, str, int)
    Table2ListSync = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super(LoadTable, self).__init__(0, 21, parent) # Remember to change when length changed
        self.client = TCPClient()
        self.onLoading = False
        # Store button handle
        self.button_read = []
        self.button_write = []
        self.button_read_en = []
        self.button_write_en = []
        self.button_minus = []
        self.button_plus = []
        self.cols_headers = ["Term", "SS", "CAddr", "Addr", "Pos", "Name", "VolMax", "VolMin", "RegSize", "Size",
                             "BinR", "DecR", "VolR", "Read", "BinW", "DecW", "VolW", "Write", "-", "+", "Unit"]
        self.data_headers = ["Term", "SS", "CAddr", "Addr", "Pos", "Name", "VolMax", "VolMin", "RegSize", "Size",
                             "BinR", "DecR", "VolR", "BinW", "DecW", "VolW", "Unit"]
        self.col_dict = dict(zip(self.cols_headers, range(len(self.cols_headers))))
        '''
         0       1        2      3       4       5         6          7           8        9       10      11      12      13      14      15      16    17   18     19
        "SS", "CAddr", "Addr", "Pos", "Name", "VolMax", "VolMin", "RegSize", "Size", "BinR", "DecR", "VolR", "Read", "BinW", "DecW", "VolW", "Write", "-", "+", "unit"
        '''
        self.forbidden_cols = [self.col_dict["BinR"], self.col_dict["DecR"], self.col_dict["VolR"],
                               self.col_dict["Read"], self.col_dict["Write"], self.col_dict["-"], self.col_dict["+"]]
        self.Filter_cols = ["Term", "SS", "CAddr", "Addr", "Pos", "Name", "VolMax", "VolMin", "RegSize", "Size"]
        self.cols_int = [self.col_dict["SS"], self.col_dict["CAddr"], self.col_dict["Addr"], self.col_dict["Pos"],
                         self.col_dict["RegSize"], self.col_dict["Size"], self.col_dict["DecW"], self.col_dict["Unit"]]

        self.data = pd.DataFrame(columns=self.data_headers)

        self.setHorizontalHeaderLabels(self.cols_headers)
        self.horizontalHeader().setHighlightSections(True)
        self.horizontalHeader().sectionClicked.connect(self.columnfilterclicked)
        self.FilterConfig = [dict([(str(_), True) for _ in self.data.loc[:, idx].drop_duplicates().tolist()]) for idx
                             in self.Filter_cols]
        self.keywords = dict([(i, []) for i in self.Filter_cols])
        self.checkBoxs = []
        self.default_path = ""

        # Draw Borders for Cols' Headers on Win10
        self.horizontalHeader().setStyleSheet("QHeaderView::section{"
                                              "border-top:0px solid #D8D8D8;"
                                              "border-left:0px solid #D8D8D8;"
                                              "border-right:1px solid #D8D8D8;"
                                              "border-bottom: 1px solid #D8D8D8;"
                                              "background-color:white;"
                                              "padding:4px;""}")
        # self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.setColumnHidden(self.col_dict["Term"], True)
        self.setColumnHidden(self.col_dict["CAddr"], True)
        self.setColumnHidden(self.col_dict["VolMax"], True)
        self.setColumnHidden(self.col_dict["VolMin"], True)
        self.setColumnHidden(self.col_dict["VolR"], True)
        self.setColumnHidden(self.col_dict["VolW"], True)
        self.setColumnHidden(self.col_dict["-"], True)
        self.setColumnHidden(self.col_dict["+"], True)
        self.setColumnHidden(self.col_dict["Unit"], True)
        # self.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.setColumnWidth(self.col_dict["Term"], 40)
        self.setColumnWidth(self.col_dict["SS"], 20)
        self.setColumnWidth(self.col_dict["CAddr"], 50)
        self.setColumnWidth(self.col_dict["Addr"], 50)
        self.setColumnWidth(self.col_dict["Pos"], 20)
        self.setColumnWidth(self.col_dict["Name"], 250)
        self.setColumnWidth(self.col_dict["VolMax"], 40)
        self.setColumnWidth(self.col_dict["VolMin"], 40)
        self.setColumnWidth(self.col_dict["RegSize"], 30)
        self.setColumnWidth(self.col_dict["Size"], 20)
        self.setColumnWidth(self.col_dict["BinR"], 90)
        self.setColumnWidth(self.col_dict["DecR"], 60)
        self.setColumnWidth(self.col_dict["VolR"], 70)
        self.setColumnWidth(self.col_dict["Read"], 60)
        self.setColumnWidth(self.col_dict["BinW"], 90)
        self.setColumnWidth(self.col_dict["DecW"], 60)
        self.setColumnWidth(self.col_dict["VolW"], 70)
        self.setColumnWidth(self.col_dict["Write"], 60)
        self.setColumnWidth(self.col_dict["-"], 40)
        self.setColumnWidth(self.col_dict["+"], 40)
        self.setColumnWidth(self.col_dict["Unit"], 40)
        self.cellChanged.connect(self._cellclicked)
        #self.setSelectionMode(QtWidgets.QTableWidget.ContiguousSelection)
        self.itemSelectionChanged.connect(self._itemclicked)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setInputMethodHints(QtCore.Qt.ImhHiddenText)
        self.customContextMenuRequested.connect(self.MenuShow)

    @QtCore.pyqtSlot(QtCore.QPoint)
    def MenuShow(self, pos):
        it = self.itemAt(pos)
        if it is None:
            return
        c = it.column()
        r = it.row()
        text = it.text()

        menu = QtWidgets.QMenu()
        copy_action = QtWidgets.QAction("Copy", self)
        copy_action.setShortcut(QtGui.QKeySequence.Copy)
        copy_action.triggered.connect(self.copy)
        menu.addAction(copy_action)
        paste_action = QtWidgets.QAction("Paste", self)
        paste_action.setShortcut(QtGui.QKeySequence.Paste)
        paste_action.triggered.connect(self.paste)
        menu.addAction(paste_action)
        fill_action = QtWidgets.QAction("Fill Down", self)
        fill_action.setShortcut("Ctrl+D")
        fill_action.triggered.connect(self.fill_down)
        menu.addAction(fill_action)
        menu.addSeparator()
        add_action = menu.addAction("Add Row")
        delete_action = menu.addAction("Delete Row")
        edit_action = menu.addAction("Edit")
        edit_action.setShortcut('F2')
        if c in self.forbidden_cols:
            edit_action.setEnabled(False)
        menu.addSeparator()
        BackgroundColor_action = menu.addAction("Set Background Color")
        FontColor_action = menu.addAction("Set Font Color")
        action = menu.exec_(self.viewport().mapToGlobal(pos))
        if action == add_action:
            self.addrow()
        elif action == edit_action:
            if c in self.cols_int:
                global Protocol
                if Protocol == "CA":
                    _size = 10
                else:
                    _size = self.data.at[r, "Size"]
                if text.isdigit():
                    _init = int(text)
                else:
                    _init = 0
                if c in [self.col_dict["CAddr"], self.col_dict["Addr"]]:
                    _max = 255
                elif c == self.col_dict["DecW"] and str(_size).isdigit():
                    _max = 2**int(_size) - 1
                else:
                    _max = 65535
                res, okPressed = QtWidgets.QInputDialog.getInt(self, self.cols_headers[c], "Set "+self.cols_headers[c]+":", _init, 0, _max, 1)
            elif c in [self.col_dict["Name"], self.col_dict["BinW"]]:
                if c == self.col_dict["Name"]:
                    _suffix = "Name"
                else:
                    _suffix = "Bin"
                res, okPressed = QtWidgets.QInputDialog.getText(self, _suffix, 'Input '+_suffix+':')
            elif c in [self.col_dict["VolMax"], self.col_dict["VolMin"], self.col_dict["VolW"]]:
                try:
                    _init = float(text)
                except Exception as e:
                    _init = 0.0
                _min = -10
                _max = 10
                if c == self.col_dict["VolMax"]:
                    _suffix = ' Max'
                elif c == self.col_dict["VolMin"]:
                    _suffix = ' Min'
                else:
                    _suffix = ''
                    try:
                        _min = float(self.data.at[r, "VolMin"])
                    except Exception as e:
                        pass
                    try:
                        _max = float(self.data.at[r, "VolMax"])
                    except Exception as e:
                        pass
                res, okPressed = QtWidgets.QInputDialog.getDouble(self, 'Set Voltage', 'Voltage'+_suffix+':', _init, _min, _max, 1)
            else:
                return
            if okPressed:
                for _ in self.selectedIndexes():
                    _r = _.row()
                    _temp = QtWidgets.QTableWidgetItem()
                    _temp.setData(QtCore.Qt.EditRole, res)
                    self.setItem(_r, c, _temp)
        elif action == delete_action:
            self.removerow()
        elif action == BackgroundColor_action:
            color = QtWidgets.QColorDialog.getColor()
            if color.isValid():
                for _ in self.selectedIndexes():
                    self.item(_.row(), _.column()).setBackground(color)
        elif action == FontColor_action:
            color = QtWidgets.QColorDialog.getColor()
            if color.isValid():
                for _ in self.selectedIndexes():
                    self.item(_.row(), _.column()).setForeground(color)

    def copy(self):
        selected_ranges = self.selectedRanges()
        if not selected_ranges:
            return

        selected_text = ""
        for r in range(selected_ranges[0].topRow(), selected_ranges[0].bottomRow() + 1):
            row_data = []
            for c in range(selected_ranges[0].leftColumn(), selected_ranges[0].rightColumn() + 1):
                if self.isColumnHidden(c) or self.cols_headers[c].endswith("R") or self.cols_headers[c] in ["Read", "Write", "-", "+"]:
                    continue
                item = self.item(r, c)
                row_data.append(item.text() if item else "")
            selected_text += "\t".join(row_data) + "\n"
        QtWidgets.QApplication.clipboard().setText(selected_text.strip())

    def paste(self):
        clipboard = QtWidgets.QApplication.clipboard().text()
        if not clipboard:
            return
        selected_ranges = self.selectedRanges()
        if not selected_ranges:
            return
        start_row = selected_ranges[0].topRow()
        start_col = selected_ranges[0].leftColumn()
        rows = clipboard.split("\n")
        for r_offset, row_data in enumerate(rows):
            cells = row_data.split("\t")
            c_offset = 0
            _row = start_row + r_offset
            while cells:
                _col = start_col + c_offset
                if _row < self.rowCount() and _col < self.columnCount():
                    if self.isColumnHidden(_col) or self.cols_headers[_col].endswith("R") or self.cols_headers[_col] in ["Read", "Write", "-", "+"]:
                        c_offset += 1
                        continue
                    else:
                        self.setItem(_row, _col, QtWidgets.QTableWidgetItem(cells[0]))
                        cells.pop(0)
                        c_offset += 1
                else:
                    break

    def fill_down(self):
        idx = self.selectedIndexes()
        selected_rows = sorted(set(_.row() for _ in idx))
        selected_columns = sorted(set(_.column() for _ in idx))
        if len(selected_columns) > 1 or len(selected_rows) < 1:
            return
        _col = selected_columns[0]
        _base = self.data.at[selected_rows[-1], self.cols_headers[_col]]
        pointer = selected_rows[-1] + 1
        _step = 0
        _flag = ""
        if self.cols_headers[_col] in ["Read", "Write", "-", "+"] or pointer > self.rowCount():
            return
        elif _col in self.cols_int and str(_base).isdigit():
            _base = int(_base)
            if len(selected_rows) > 1:
                _pre = self.data.at[selected_rows[-2], self.cols_headers[_col]]
                if str(_pre).isdigit():
                    _step = _base - int(_pre)
        elif self.cols_headers[_col].startswith("Vol"):
            try:
                _base = float(_base)
                _flag = "F"
            except Exception as e:
                return
            if len(selected_rows) > 1:
                _pre = self.data.at[selected_rows[-2], self.cols_headers[_col]]
                try:
                    _step = _base - float(_pre)
                except Exception as e:
                    _step = 0
        else:
            _dup = False if len(str(self.data.at[pointer, self.cols_headers[_col]]).replace(" ", "")) > 0 else True
            while pointer < self.rowCount():
                dup = False if len(str(self.data.at[pointer, self.cols_headers[_col]]).replace(" ", "")) > 0 else True
                if dup == _dup:
                    self.setTable(pointer, _col, _base)
                    pointer += 1
                else:
                    return
            return
        _dup = False if len(str(self.data.at[pointer, self.cols_headers[_col]]).replace(" ", "")) > 0 else True
        while pointer < self.rowCount():
            dup = False if len(str(self.data.at[pointer, self.cols_headers[_col]]).replace(" ", "")) > 0 else True
            if dup == _dup:
                _base += _step
                self.setTable(pointer, _col, _base, _flag)
                pointer += 1
            else:
                return

    def keyPressEvent(self, event):
        if event.matches(QtGui.QKeySequence.Copy):
            self.copy()
        elif event.matches(QtGui.QKeySequence.Paste):
            self.paste()
        elif event.key() == QtCore.Qt.Key_D and event.modifiers() & QtCore.Qt.ControlModifier:
            self.fill_down()
        else:
            super().keyPressEvent(event)

     # Synchronize data-> self.item self.data
    @QtCore.pyqtSlot(int, int)
    def _cellclicked(self, r, c):
        self.blockSignals(True)
        self.item(r, c).setTextAlignment(QtCore.Qt.AlignCenter)
        if self.onLoading is False and c not in [self.col_dict["BinR"], self.col_dict["DecR"], self.col_dict["VolR"]]:
            self.onLoading = True
            print(str(r) + ","+str(c))
            text = self.item(r, c).text().replace(" ", "")
            _pre = self.data.at[r, self.cols_headers[c]]
            if c in self.cols_int:
                if text.isdigit():
                    self.setTable(r, c, int(text))
                else:
                    self.item(r, c).setData(QtCore.Qt.EditRole, _pre)
                    self.onLoading = False
                    self.blockSignals(False)
                    return
            elif c == self.col_dict["BinW"]:
                if text == "":
                    self.item(r, c).setData(QtCore.Qt.EditRole, _pre)
                    self.onLoading = False
                    self.blockSignals(False)
                    return
                for _ in text:  # Binary Check
                    if _ not in '01':
                        self.item(r, c).setData(QtCore.Qt.EditRole, _pre)
                        self.onLoading = False
                        self.blockSignals(False)
                        return
            elif c == self.col_dict["VolW"]:
                try:
                    float_data = float(text)
                    self.setTable(r, c, str(float_data), "F")
                except Exception as e:
                    self.item(r, c).setData(QtCore.Qt.EditRole, _pre)
                    self.onLoading = False
                    self.blockSignals(False)
                    return
            self.data.at[r, self.cols_headers[c]] = text # Data type should be int despite name and bin
            if self.cols_headers[c] in self.Filter_cols:  # cols_int c < 9
                if _pre not in self.data[self.data_headers[c]].values.tolist():
                    if str(_pre) in self.FilterConfig[c]:
                        del self.FilterConfig[c][str(_pre)]
                if text not in self.FilterConfig[c]:
                    self.FilterConfig[c][str(text)] = True
            # Bin Dec data sync
            global Protocol
            if Protocol == "CA":
                _size = 10
            else:
                _size = self.data.at[r, "Size"]
            if c == self.col_dict["DecW"] and str(_size).isdigit():
                if int(_size) is not 0:
                    _dec = int(text)
                    self.setbin(r, _dec, _size)
                    _vol = self.dec2voltage(self.data.at[r, "VolMax"], self.data.at[r, "VolMin"], _dec, _size)
                    if _vol is not None:
                        self.data.at[r, "VolW"] = _vol
                        self.setTable(r, self.col_dict["VolW"], _vol, "F")
            elif c == self.col_dict["BinW"]:
                _dec = int(text, 2)
                self.data.at[r, "DecW"] = _dec
                self.setTable(r, self.col_dict["DecW"], _dec)
                if str(_size).isdigit():
                    if int(_size) is not 0:
                        self.setbin(r, _dec, _size)
                _vol = self.dec2voltage(self.data.at[r, "VolMax"], self.data.at[r, "VolMin"], _dec, _size)
                if _vol is not None:
                    self.data.at[r, "VolW"] = _vol
                    self.setTable(r, self.col_dict["VolW"], _vol, "F")
            elif c == self.col_dict["VolW"]:
                _dec = self.voltage2dec(self.data.at[r, "VolMax"], self.data.at[r, "VolMin"], text, _size)
                if _dec is not None:
                    self.data.at[r, "DecW"] = _dec
                    self.setTable(r, self.col_dict["DecW"], _dec)
                    self.setbin(r, _dec, _size)
            else:
                pass
            # Status Update
            if self.cols_headers[c] in ["Term", "SS", "CAddr", "Addr", "Pos", "RegSize", "Size", "BinW", "DecW", "VolW"]:
                self.button_enable_set(r)
            self.onLoading = False
        self.blockSignals(False)

    @QtCore.pyqtSlot()
    def _itemclicked(self):
        for index in self.selectedIndexes():
            r = index.row()
            if self.button_read_en[r] is True:
                global Protocol
                if Protocol == "CA":
                    _size = 10
                else:
                    _size = self.data.at[r, "Size"]
                self.SelectedTx.emit(r+1, self.data.at[r, "Name"], int(_size))

    def setTable(self, r, c, data, flag=""):
        if data is None:
            data = ""
        if "F" in flag:
            try:
                float_data = float(data)
                data = f"{float_data:.4f}"
            except Exception as e:
                data = ""
        _temp = QtWidgets.QTableWidgetItem()
        if "R" in flag:
            _temp.setData(QtCore.Qt.DisplayRole, data)
            _temp.setFlags(QtCore.Qt.ItemIsEnabled)
        else:
            _temp.setData(QtCore.Qt.EditRole, data)
        self.setItem(r, c, _temp)
        self.item(r, c).setTextAlignment(QtCore.Qt.AlignCenter)

    def button_enable_set(self, r):
        global Protocol
        raspi_flag = self.isColumnHidden(self.col_dict["Term"])
        term = ""
        if not raspi_flag:
            term = self.data.at[r, "Term"]
            term = str(term).replace(" ", "")
        if len(term) > 0:
            if term in self.client.connections:
                ConnFlag = True
            else:
                ConnFlag = False
        else:
            ConnFlag = SPIConnFlag
        if Protocol == "CA":
            cols_key = ["SS", "CAddr", "Addr"]
        else:
            cols_key = ["SS", "Addr", "RegSize", "Size", "Pos"]
        _enRead = all(str(self.data.at[r, col]).isdigit() for col in cols_key)

        _enWrite = _enRead and str(self.data.at[r, "DecW"]).isdigit()
        self.button_read_en[r] = _enRead
        self.button_write_en[r] = _enWrite
        self.button_read[r].setEnabled(ConnFlag and _enRead)
        self.button_write[r].setEnabled(ConnFlag and _enWrite)

    def menuClose(self):
        self.keywords[self.col] = []
        for element in self.checkBoxs:
            if element.isChecked():
                self.keywords[self.col].append(element.text())
        self.filterdata()
        self.FilterMenu.close()

    def clearFilter(self):
        if self.rowCount() > 0:
            for i in range(self.rowCount()):
                self.setRowHidden(i, False)

    def filterdata(self):
        columnsShow = dict([(i, True) for i in range(self.rowCount())])

        for i in range(self.rowCount()):
            for j in self.Filter_cols:
                col = self.col_dict[j]
                item = self.item(i, col)
                if self.keywords[col]:
                    if item.text() not in self.keywords[col]:
                        columnsShow[i] = False
        for key in columnsShow:
            self.setRowHidden(key, not columnsShow[key])

    def processtrigger(self, qaction):
        if qaction.text() == "sort from low to high":
            print(True)
        elif qaction.text() == "sort from high to low":
            print(False)
        else:
            print(qaction.text() + " is triggered!")

    def columnfilterclicked(self, index):
        if self.cols_headers[index] not in self.Filter_cols:
            return
        self.FilterMenu = QtWidgets.QMenu()
        self.col = index

        self.checkBoxs = []

        sortLH = QtWidgets.QAction("sort from low to high", self.FilterMenu)
        sortHL = QtWidgets.QAction("sort from high to low", self.FilterMenu)
        #sortLH.setShortcut('Ctrl+S')
        self.FilterMenu.addAction(sortLH)
        self.FilterMenu.addAction(sortHL)
        self.FilterMenu.triggered[QtWidgets.QAction].connect(self.processtrigger)
        self.FilterMenu.addSeparator()

        # Search Edit
        self.searchLine = QtWidgets.QLineEdit()
        self.searchLine.setPlaceholderText("Search")
        EditAction = QtWidgets.QWidgetAction(self.FilterMenu)
        EditAction.setDefaultWidget(self.searchLine)
        self.FilterMenu.addAction(EditAction)
        # List Widget
        self.listWidget = QtWidgets.QListWidget(self.FilterMenu)
        self.listWidget.setStyleSheet("margin-top:5px;margin-bottom:5px")
        ListAction = QtWidgets.QWidgetAction(self.FilterMenu)
        ListAction.setDefaultWidget(self.listWidget)
        self.FilterMenu.addAction(ListAction)

        self.checkBox_all = QtWidgets.QCheckBox("Select all", self.FilterMenu)
        row = QtWidgets.QListWidgetItem()
        self.listWidget.addItem(row)
        self.listWidget.setItemWidget(row, self.checkBox_all)

        self.checkBox_all.stateChanged.connect(self.slotSelect)

        selectAll_check = True
        selectAll_uncheck = False
        for key, value in self.FilterConfig[index].items():
            checkBox = QtWidgets.QCheckBox(key)
            checkBox.setChecked(value)
            checkBox.stateChanged.connect(lambda state, index=index, key=key: self.filterConfigChanged(state,index,key))
            selectAll_check = selectAll_check and value
            selectAll_uncheck = selectAll_uncheck or value
            row = QtWidgets.QListWidgetItem()
            self.listWidget.addItem(row)
            self.listWidget.setItemWidget(row, checkBox)
            self.checkBoxs.append(checkBox)

        if selectAll_check is True:
            self.checkBox_all.setChecked(True)
        elif selectAll_uncheck is False:
            self.checkBox_all.setChecked(False)
        else:
            self.checkBox_all.setCheckState(QtCore.Qt.PartiallyChecked)

        btn = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
                                         QtCore.Qt.Horizontal, self.FilterMenu)
        btn.accepted.connect(lambda *args, index=index: self.filter(index))
        btn.rejected.connect(self.FilterMenu.close)
        checkableAction = QtWidgets.QWidgetAction(self.FilterMenu)
        checkableAction.setDefaultWidget(btn)
        self.FilterMenu.addAction(checkableAction)

        headerPos = self.mapToGlobal(self.horizontalHeader().pos())
        posY = headerPos.y() + self.horizontalHeader().height()
        posX = headerPos.x() + self.horizontalHeader().sectionPosition(index)
        print(posX)
        print(posY)
        self.FilterMenu.exec_(QtCore.QPoint(posX, posY))

    def slotSelect(self, state):
        if state != QtCore.Qt.PartiallyChecked:
            self.checkBox_all.setTristate(False)
            for checkbox in self.checkBoxs:
                checkbox.setChecked(QtCore.Qt.Checked == state)

    def filterConfigChanged(self, state, index, key):
        self.FilterConfig[index][key] = (QtCore.Qt.Checked == state)
        if all(self.FilterConfig[index].values()):
            self.checkBox_all.setChecked(True)
            self.checkBox_all.setTristate(False)
        elif any(self.FilterConfig[index].values()):
            self.checkBox_all.setCheckState(QtCore.Qt.PartiallyChecked)
        else:
            self.checkBox_all.setChecked(False)
            self.checkBox_all.setTristate(False)

    def filter(self, index):
        for idx, value in self.data.iloc[:, index].items():
            if self.FilterConfig[index][str(value)] is False:
                self.setRowHidden(idx, True)
            else:
                self.setRowHidden(idx, False)
        self.FilterMenu.close()

    def dataload(self, load_flag):
        if load_flag is False:
            if not os.path.exists(self.default_path):
                self.default_path = os.getcwd()
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import SPI File", self.default_path,
                                                            "Data Files (*.xlsm *.xls *.xlsx *.csv)")
            if path:
                try:
                    self.default_path = os.path.dirname(path)
                    self.data = FileIO.load(path)
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Error", "FAIL TO LOAD!")
                    return
            else:
                return
        self.FilterConfig = [dict([(str(_), True) for _ in self.data.loc[:, idx].drop_duplicates().tolist()]) for idx
                             in self.Filter_cols]
        self.onLoading = True
        self.setRowCount(0)
        self.setRowCount(self.data.shape[0])
        self.button_read = []
        self.button_write = []
        self.button_minus = []
        self.button_plus = []
        self.button_read_en = []
        self.button_write_en = []

        for index, row in self.data.iterrows():
            for _ in self.cols_headers:
                _flag = ""
                if _.endswith("R"):
                    _flag += "R"
                if _.startswith("Vol"):
                    _flag += "F"
                if self.col_dict[_] in self.cols_int:
                    self.setTable(index, self.col_dict[_], intSafe(row[_]))
                elif _ not in ["Read", "Write", "-", "+"]:
                    self.setTable(index, self.col_dict[_], str(row[_]), _flag)
            if row["DecW"] == "":
                if row["BinW"]:
                    _dec = int(row["BinW"], 2)
                    self.data.at[index, "DecW"] = _dec
                    self.setTable(index, self.col_dict["DecW"], _dec)
                else:
                    _dec = self.voltage2dec(row["VolMax"], row["VolMin"], row["VolW"], row["Size"])
                    if _dec is not None:
                        self.data.at[index, "DecW"] = _dec
                        self.setTable(index, self.col_dict["DecW"], _dec)
            if row["BinW"] == "":
                if str(self.data.at[index, "DecW"]).isdigit() and str(row["Size"]).isdigit() and row["Size"]:
                    self.setbin(index, int(self.data.at[index, "DecW"]), row["Size"])
            if row["VolW"] == "":
                if str(self.data.at[index, "DecW"]).isdigit() and str(row["Size"]).isdigit() and row["Size"]:
                    _vol = self.dec2voltage(row["VolMax"], row["VolMin"], self.data.at[index, "DecW"], row["Size"])
                    if _vol is not None:
                        self.data.at[index, "VolW"] = _vol
                        self.setTable(index, self.col_dict["VolW"], _vol, "F")

            button_read = QtWidgets.QPushButton('Read')
            button_read.clicked.connect(lambda *args, rowcount=index: self.handleReadClicked(rowcount))
            self.button_read.append(button_read)
            self.button_read_en.append(False)
            button_write = QtWidgets.QPushButton('Write')
            button_write.clicked.connect(lambda *args, rowcount=index: self.handleWriteClicked(rowcount))
            self.button_write.append(button_write)
            self.button_write_en.append(False)
            self.setCellWidget(index, self.col_dict["Read"], button_read)
            self.setCellWidget(index, self.col_dict["Write"], button_write)
            self.button_enable_set(index)

            button_minus = QtWidgets.QPushButton('-')
            button_minus.clicked.connect(lambda *args, rowcount=index: self.handleMinusClicked(rowcount))
            self.button_minus.append(button_minus)
            self.setCellWidget(index, self.col_dict["-"], button_minus)

            button_plus = QtWidgets.QPushButton('+')
            button_plus.clicked.connect(lambda *args, rowcount=index: self.handlePlusClicked(rowcount))
            self.button_plus.append(button_plus)
            self.setCellWidget(index, self.col_dict["+"], button_plus)
        self.onLoading = False

    @QtCore.pyqtSlot()
    def addrow(self):
        if len(self.selectedIndexes()) is 0:
            rowcount = self.rowCount()
            if rowcount is 0:
                newRowSeries = pd.Series([None for _ in range(len(self.data_headers))], index=self.data_headers)
                for _ in self.data_headers:
                    if _ in ["SS", "CAddr", "Addr", "Pos"]:
                        newRowSeries.at[_] = 0
                    elif _ == "RegSize":
                        newRowSeries.at[_] = 13
                    elif _ == "Size":
                        newRowSeries.at[_] = 10
                    elif _ == "VolMax":
                        newRowSeries.at[_] = 1.00
                    elif _ == "VolMin":
                        newRowSeries.at[_] = 0.00
                    elif _ == "Unit":
                        newRowSeries.at[_] = 1
                    else:
                        newRowSeries.at[_] = ""
            else:
                newRowSeries = self.data.iloc[-1]
                newRowSeries["Addr"] += 1
        else:
            rowcount = self.selectedIndexes()[-1].row() + 1
            newRowSeries = self.data.iloc[rowcount-1]
            if str(newRowSeries["Addr"]).isdigit():
                newRowSeries["Addr"] = int(newRowSeries["Addr"]) + 1

        self.insertRow(rowcount)
        _data = self.data[0:rowcount]
        self.data = _data.append(newRowSeries, ignore_index=True).append(self.data[rowcount:], ignore_index=True)
        self.data.reset_index(drop=True, inplace=True)

        button_read = QtWidgets.QPushButton('Read')
        button_read.clicked.connect(lambda *args, rowcount=rowcount: self.handleReadClicked(rowcount))
        button_read.setEnabled(False)
        self.button_read.insert(rowcount, button_read)
        self.button_read_en.insert(rowcount, False)
        self.setCellWidget(rowcount, self.col_dict["Read"], button_read)

        button_write = QtWidgets.QPushButton('Write')
        button_write.clicked.connect(lambda *args, rowcount=rowcount: self.handleWriteClicked(rowcount))
        button_write.setEnabled(False)
        self.button_write.insert(rowcount, button_write)
        self.button_write_en.insert(rowcount, False)
        self.setCellWidget(rowcount, self.col_dict["Write"], button_write)

        button_minus = QtWidgets.QPushButton('-')
        button_minus.clicked.connect(lambda *args, rowcount=rowcount: self.handleMinusClicked(rowcount))
        self.button_minus.insert(rowcount, button_minus)
        self.setCellWidget(rowcount, self.col_dict["-"], button_minus)

        button_plus = QtWidgets.QPushButton('+')
        button_plus.clicked.connect(lambda *args, rowcount=rowcount: self.handlePlusClicked(rowcount))
        self.button_plus.insert(rowcount, button_plus)
        self.setCellWidget(rowcount, self.col_dict["+"], button_plus)

        self.onLoading = True
        for _ in self.cols_headers:
            _flag = ""
            if _.endswith("R"):
                _flag += "R"
            if _.startswith("Vol"):
                _flag += "F"
            if self.col_dict[_] in self.cols_int:
                self.setTable(rowcount, self.col_dict[_], intSafe(newRowSeries[_]))
            elif _ not in ["Read", "Write", "-", "+"]:
                self.setTable(rowcount, self.col_dict[_], str(newRowSeries[_]), _flag)
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
                del self.button_minus[row]
                del self.button_plus[row]

            self.data = self.data.drop(index=rows)
            self.data.reset_index(drop=True, inplace=True)
            rows = sorted(rows)

            if rows[0] < len(self.button_read):
                for _ in range(rows[0], len(self.button_read)):
                    self.button_write[_].clicked.disconnect()
                    self.button_write[_].clicked.connect(lambda *args, rowcount=_: self.handleWriteClicked(rowcount))
                    self.button_read[_].clicked.disconnect()
                    self.button_read[_].clicked.connect(lambda *args, rowcount=_: self.handleReadClicked(rowcount))
                    self.button_minus[_].clicked.disconnect()
                    self.button_minus[_].clicked.connect(lambda *args, rowcount=_: self.handleMinusClicked(rowcount))
                    self.button_plus[_].clicked.disconnect()
                    self.button_plus[_].clicked.connect(lambda *args, rowcount=_: self.handlePlusClicked(rowcount))

    @QtCore.pyqtSlot(int)
    def handleReadClicked(self, r):
        global Protocol
        raspi_flag = self.isColumnHidden(self.col_dict["Term"])
        term = ""
        if not raspi_flag:
            term = self.data.at[r, "Term"]
            term = str(term).replace(" ", "")
        cs = int(self.data.at[r, "SS"])
        addr = int(self.data.at[r, "Addr"])

        if Protocol == "CA":
            caddr = int(self.data.at[r, "CAddr"])
            nBits = 10
            if len(term) > 0:
                res = self.client.read_reg(term, cs, caddr, addr)
            else:
                res = ni8452.read_reg(cs, caddr, addr)
            res = res % (2 ** 10)
        else:
            sel = int(self.data.at[r, "Pos"])
            size = int(self.data.at[r, "RegSize"])
            nBits = int(self.data.at[r, "Size"])
            if len(term) > 0:
                res = self.client.spi_read(term, cs, addr, size)
            else:
                res = ni8452.spi_read(cs, addr, size)
            if sel == 0:
                if size is not nBits:
                    res = res % (2 ** nBits)
            else:
                res = (res >> (sel - 1)) % (2 ** nBits)
        self.data.at[r, "DecR"] = res
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.DisplayRole, int(res))
        _temp.setFlags(QtCore.Qt.ItemIsEnabled)
        self.setItem(r, self.col_dict["DecR"], _temp)

        _format = "0" + str(nBits) + "b"
        _bin = format(int(res), _format)
        self.data.at[r, "BinR"] = _bin
        _temp = QtWidgets.QTableWidgetItem()
        _temp.setData(QtCore.Qt.DisplayRole, _bin)
        _temp.setFlags(QtCore.Qt.ItemIsEnabled)
        self.setItem(r, self.col_dict["BinR"], _temp)
        self.Table2ListSync.emit(r)
        _vol = self.dec2voltage(self.data.at[r, "VolMax"], self.data.at[r, "VolMin"], res, nBits)
        if _vol is not None:
            _temp = QtWidgets.QTableWidgetItem()
            _temp.setData(QtCore.Qt.DisplayRole, _vol)
            _temp.setFlags(QtCore.Qt.ItemIsEnabled)
            self.setItem(r, self.col_dict["VolR"], _temp)

    @QtCore.pyqtSlot(int)
    def handleWriteClicked(self, r):
        global Protocol
        raspi_flag = self.isColumnHidden(self.col_dict["Term"])
        term = ""
        if not raspi_flag:
            term = self.data.at[r, "Term"]
            term = str(term).replace(" ", "")

        cs = int(self.data.at[r, "SS"])
        data = int(self.data.at[r, "DecW"])
        addr = int(self.data.at[r, "Addr"])

        if Protocol == "CA":
            caddr = int(self.data.at[r, "CAddr"])
            if len(term) > 0:
                self.client.write_reg(term, cs, caddr, addr, data)
            else:
                ni8452.write_reg(cs, caddr, addr, data)
        else:
            sel = int(self.data.at[r, "Pos"])
            size = int(self.data.at[r, "RegSize"])
            nBits = int(self.data.at[r, "Size"])
            if sel is not 0:
                if len(term) > 0:
                    self.client.spi_read(term, cs, addr, size)
                else:
                    res = ni8452.spi_read(cs, addr, size)
                _format = "0" + str(size) + "b"
                _mask = 2 ** size - 1 - (2 ** nBits - 1) * (2 ** (sel - 1))
                mask = format(_mask, _format)
                data = (res & int(mask, 2)) | (data << (sel - 1))
            if len(term) > 0:
                self.client.spi_write(term, cs, addr, data, size)
            else:
                ni8452.spi_write(cs, addr, data, size)
        self.handleReadClicked(r)

    @QtCore.pyqtSlot(int)
    def handleMinusClicked(self, r):
        if self.button_write_en[r]:
            data = int(self.data.at[r, "DecW"])
            unit = self.item(r, self.col_dict["Unit"]).data(QtCore.Qt.EditRole)
            res = data - unit
            if res < 0:
                return
            _temp = QtWidgets.QTableWidgetItem()
            _temp.setData(QtCore.Qt.EditRole, res)
            self.setItem(r, self.col_dict["DecW"], _temp)
            if SPIConnFlag:
                self.handleWriteClicked(r)

    @QtCore.pyqtSlot(int)
    def handlePlusClicked(self, r):
        if self.button_write_en[r]:
            global Protocol
            if Protocol == "CA":
                _size = 10
            else:
                _size = self.data.at[r, "Size"]
            data = int(self.data.at[r, "DecW"])
            unit = self.item(r, self.col_dict["Unit"]).data(QtCore.Qt.EditRole)
            res = data + unit
            if res > (2**int(_size)-1):
                return
            _temp = QtWidgets.QTableWidgetItem()
            _temp.setData(QtCore.Qt.EditRole, res)
            self.setItem(r, self.col_dict["DecW"], _temp)
            if SPIConnFlag:
                self.handleWriteClicked(r)

    def button_update(self):
        for _ in range(len(self.button_read)):
            self.button_enable_set(_)

    def setbin(self, r, dec, size):
        _format = "0" + str(size) + "b"
        _bin = format(dec, _format)
        self.data.at[r, "BinW"] = _bin
        self.setItem(r, self.col_dict["BinW"], QtWidgets.QTableWidgetItem(_bin))
        self.item(r, self.col_dict["BinW"]).setTextAlignment(QtCore.Qt.AlignCenter)

    def dec2voltage(self, Volmax, Volmin, dec, nbits):
        try:
            Volmax = float(Volmax)
            Volmin = float(Volmin)
            dec = float(dec)
            nbits = float(nbits)
        except Exception as e:
            return None
        if nbits == 0:
            return None
        voltage = (Volmax - Volmin) * dec/(2**nbits-1)
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
    Tx = QtCore.pyqtSignal(bool, int)
    dataset = QtCore.pyqtSignal(list, int)
    def __init__(self,parent=None):
        super(ShortCutList, self).__init__(0, 6, parent)
        self.verticalHeader().hide()
        self.setHorizontalHeaderLabels(["Name", "Range", "Bin", "Dec", "Read", "Write"])
        self.horizontalHeader().setStyleSheet("QHeaderView::section{"
            "border-top:0px solid #D8D8D8;"
            "border-left:0px solid #D8D8D8;"
            "border-right:1px solid #D8D8D8;"
            "border-bottom: 1px solid #D8D8D8;"
            "background-color:white;"
            "padding:4px;"
        "}")
        self.button_read = []
        self.button_write = []
        self.button_read_en = []
        self.button_write_en = []
        self.ReadData = []
        self.ReadList = []
        self.data = pd.DataFrame(columns=["Name", "Range", "Bin", "Dec", "Length"])
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
        button_read.setEnabled(True)
        button_write.setEnabled(True)
        button_read.clicked.connect(lambda *args, rowcount=0: self.handleReadRunClicked(rowcount))
        button_write.clicked.connect(lambda *args, rowcount=0: self.handleWriteRunClicked(rowcount))
        self.button_read.append(button_read)
        self.button_write.append(button_write)
        self.button_read_en.append(True)
        self.button_write_en.append(True)
        self.setCellWidget(0, 4, button_read)
        self.setCellWidget(0, 5, button_write)
        self.cellChanged.connect(self._cellchanged)

    @QtCore.pyqtSlot(int, int)
    def _cellchanged(self, r, c):
        self.blockSignals(True)
        self.item(r, c).setTextAlignment(QtCore.Qt.AlignCenter)
        if self.onLoading is False:
            self.onLoading = True
            row = r - 1
            text = self.item(r, c).text()
            if c is 0:
                self.data.at[row, "Name"] = text
            elif c is 1:
                _text = text.replace(" ", "")
                _temp = QtWidgets.QTableWidgetItem()
                _temp.setData(QtCore.Qt.EditRole, _text)
                _ReadData, _ReadList = RangeParse(_text)
                print(_ReadData)
                print(_ReadList)
                self.data.at[row, "Range"] = _text
                self.ReadData[row] = _ReadData
                self.ReadList[row] = _ReadList
                if _ReadList is not None:
                    self.button_read_en[r] = True
                    self.button_write_en[r] = True
                    self.setItem(r, c, _temp)
                    if _ReadData is None:
                        _temp = QtWidgets.QTableWidgetItem()
                        _temp.setData(QtCore.Qt.DisplayRole, "")
                        _temp.setFlags(QtCore.Qt.ItemIsEnabled)
                        self.setItem(r, 2, _temp)
                        _temp = QtWidgets.QTableWidgetItem()
                        _temp.setData(QtCore.Qt.DisplayRole, "")
                        _temp.setFlags(QtCore.Qt.ItemIsEnabled)
                        self.setItem(r, 3, _temp)
                    else:
                        self.blockSignals(False)
                        print(row)
                        self.dataset.emit(_ReadData,row)
                        self.blockSignals(True)
                else:
                    self.button_read_en[r] = False
                    self.button_write_en[r] = False
                    _temp.setForeground(QtGui.QColor(255, 0, 0))
                    self.setItem(r, c, _temp)
                self.item(r, c).setTextAlignment(QtCore.Qt.AlignCenter)
                self.button_read[r].setEnabled(self.button_read_en[r])
                self.button_write[r].setEnabled(self.button_write_en[r])

            elif c is 2:
                if self.ReadData[row] is None:
                    self.onLoading = False
                    return
                if (text.count(".") > 1 and [-1, -1] in self.ReadData[row]) or (text.count(".") > 0 and [-1, -1] not in self.ReadData[row]):
                    self.item(r, c).setData(QtCore.Qt.EditRole, self.data.at[row, "Bin"])
                    self.onLoading = False
                    return
                for _ in text:
                    if _ not in '.01':
                        self.item(r, c).setData(QtCore.Qt.EditRole, self.data.at[row, "Bin"])
                        self.onLoading = False
                        return

                self.data.at[row, "Bin"] = text
                _dec = Bin2FixPointFloat(text)
                self.data.at[row, "Dec"] = _dec
                self.item(r, 3).setData(QtCore.Qt.EditRole, _dec)
                if [-1, -1] not in self.ReadData[row]:
                    print(self.data.at[row, "Length"])
                    _format = "0" + str(int(self.data.at[row, "Length"])) + "b"
                    _bin = format(int(_dec), _format)
                else:
                    _index = self.ReadData[row].index([-1, -1])
                    if _index is 0:
                        nint = 1
                    else:
                        nint = _index
                    _bin = Float2FixPointBin(_dec, nint, self.data.at[row, "Length"] - _index - 1)
                self.data.at[row, "Bin"] = _bin
                self.item(r, 2).setData(QtCore.Qt.EditRole, _bin)
            elif c is 3:
                if self.ReadData[row] is None:
                    self.onLoading = False
                    return
                if float(text) < 0:
                    if [-1, -1] not in self.ReadData[row]:
                        self.item(r, c).setData(QtCore.Qt.EditRole, int(self.data.at[row, "Dec"]))
                    else:
                        self.item(r, c).setData(QtCore.Qt.EditRole, float(self.data.at[row, "Dec"]))
                    self.onLoading = False
                    return

                if [-1, -1] not in self.ReadData[row]:
                    _format = "0" + str(int(self.data.at[row, "Length"])) + "b"
                    self.data.at[row, "Dec"] = int(text)
                    _bin = format(int(text), _format)
                else:
                    _index = self.ReadData[row].index([-1, -1])
                    if _index is 0:
                        nint = 1
                    else:
                        nint = _index
                    self.data.at[row, "Dec"] = float(text)
                    _bin = Float2FixPointBin(float(text), nint, self.data.at[row, "Length"] - _index - 1)
                self.data.at[row, "Bin"] = _bin
                self.item(r, 2).setData(QtCore.Qt.EditRole, _bin)
            else:
                pass
            self.onLoading = False
        self.blockSignals(False)

    def dataload(self):
        self.onLoading = True
        self.setRowCount(self.data.shape[0]+1)
        self.button_read = [self.button_read[0]]
        self.button_write = [self.button_write[0]]
        self.button_read_en = [self.button_read_en[0]]
        self.button_write_en = [self.button_write_en[0]]
        self.ReadData = []
        self.ReadList = []
        for _index, row in self.data.iterrows():
            self.setItem(_index+1, 0, QtWidgets.QTableWidgetItem(row["Name"]))
            _temp = QtWidgets.QTableWidgetItem()
            _temp.setData(QtCore.Qt.DisplayRole, row["Range"])
            self.setItem(_index+1, 1, _temp)
            _ReadData, _ReadList = RangeParse(row['Range'])
            self.ReadList.append(_ReadList)
            self.ReadData.append(_ReadData)
            self.setItem(_index+1, 2, QtWidgets.QTableWidgetItem(row["Bin"]))
            _temp = QtWidgets.QTableWidgetItem()
            if [-1,-1] not in _ReadData:
                _temp.setData(QtCore.Qt.EditRole, intSafe(row["Dec"]))
            else:
                _temp.setData(QtCore.Qt.EditRole, float(row["Dec"]))
            self.setItem(_index+1, 3, _temp)

            button_read = QtWidgets.QPushButton('Read')
            button_write = QtWidgets.QPushButton('Write')
            button_read.setEnabled(True)
            button_write.setEnabled(True)
            button_read.clicked.connect(lambda *args, rowcount=_index+1: self.handleReadRunClicked(rowcount))
            button_write.clicked.connect(lambda *args, rowcount=_index+1: self.handleWriteRunClicked(rowcount))
            self.button_read.append(button_read)
            self.button_write.append(button_write)
            self.button_read_en.append(True)
            self.button_write_en.append(True)
            self.setCellWidget(_index+1, 4, button_read)
            self.setCellWidget(_index+1, 5, button_write)
        self.onLoading = False

    @QtCore.pyqtSlot()
    def addrow(self):
        rowcount = self.rowCount()
        newRowSeries = pd.Series(["", "", "", "",0], index=["Name", "Range", "Bin", "Dec","Length"])
        self.insertRow(rowcount)

        self.data = self.data.append(newRowSeries, ignore_index=True)
        self.ReadList.append([])
        self.ReadData.append([])
        button_read = QtWidgets.QPushButton('Read')
        button_write = QtWidgets.QPushButton('Write')
        button_read.setEnabled(False)
        button_write.setEnabled(False)
        button_read.clicked.connect(lambda *args, rowcount=rowcount:self.handleReadRunClicked(rowcount))
        button_write.clicked.connect(lambda *args, rowcount=rowcount: self.handleWriteRunClicked(rowcount))
        self.button_read.append(button_read)
        self.button_write.append(button_write)
        self.button_read_en.append(False)
        self.button_write_en.append(False)

        self.onLoading = True
        self.setCellWidget(rowcount, 4, button_read)
        self.setCellWidget(rowcount, 5, button_write)
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
                del self.button_read_en[row + 1]
                del self.button_write_en[row + 1]
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
    def handleReadRunClicked(self, r):
        self.Tx.emit(True, r)

    @QtCore.pyqtSlot(int)
    def handleWriteRunClicked(self, r):
        self.Tx.emit(False, r)

    def button_update(self):
        for _ in range(len(self.button_read)):
            self.button_read[_].setEnabled(self.button_read_en[_])
        for _ in range(len(self.button_write)):
            self.button_write[_].setEnabled(self.button_write_en[_])


class VarTable(QtWidgets.QTableWidget):
    def __init__(self,parent=None):
        super(VarTable, self).__init__(0, 4, parent)
        self.setHorizontalHeaderLabels(["Name", "Expression", "Value", "Description"])
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
        self.setColumnWidth(0, 100)
        self.setColumnWidth(1, 200)
        self.setColumnWidth(2, 100)
        self.setColumnWidth(3, 100)

        self.data = pd.DataFrame(["Name", "Expression", "Value", "Description"])
        self.VarTree = {}   # {"Name":["sin(x)*cos(x)"(str->equation, if int/float->var),[children(str->Var,)]],....}

    @QtCore.pyqtSlot()
    def addrow(self):
        rowcount = self.rowCount()
        newRowSeries = pd.Series(["", "", "", ""], index=["Name", "Expression", "Value", "Description"])
        self.insertRow(rowcount)
        self.data = self.data.append(newRowSeries, ignore_index=True)

    @QtCore.pyqtSlot()
    def removerow(self):
        rows = set()
        for index in self.selectedIndexes():
            rows.add(index.row())
        if len(rows) > 0:
            for row in sorted(rows, reverse=True):
                self.removeRow(row)
            self.data = self.data.drop(index=rows)
            self.data.reset_index(drop=True, inplace=True)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.picker = None
        self.table = LoadTable()
        self.list = ShortCutList()
        self.var = VarTable()
        self.table.Table2ListSync.connect(self.pickersync)
        self.table.client.tcp_signal.connect(self.tcp_panel)
        self.list.Tx.connect(self.handleBackbone)
        self.list.dataset.connect(self.length_data)

        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('File')
        fileMenu.addAction("New")
        editMenu = mainMenu.addMenu('Edit')
        viewMenu = mainMenu.addMenu('View')
        modeMenu = mainMenu.addMenu('Mode')

        self.classic_action = QtWidgets.QAction("Classic", self)
        self.classic_action.setStatusTip("Standard SPI protocol")
        self.classic_action.setCheckable(True)
        self.classic_action.setChecked(True)
        self.classic_action.triggered.connect(self.mode_toggle_classic)
        modeMenu.addAction(self.classic_action)
        self.cs_action = QtWidgets.QAction("Chip Address", self)
        self.cs_action.setStatusTip("New SPI protocol with chip selected address")
        self.cs_action.setCheckable(True)
        self.cs_action.triggered.connect(self.mode_toggle_cs)
        modeMenu.addAction(self.cs_action)
        modeMenu.addSeparator()
        self.raspi_action = QtWidgets.QAction("Via Raspberry Pi", self)
        self.raspi_action.setStatusTip("Remote SPI with Raspberry Pi Pico W")
        self.raspi_action.setCheckable(True)
        self.raspi_action.triggered.connect(self.raspi_switch)
        modeMenu.addAction(self.raspi_action)

        toolsMenu = mainMenu.addMenu('Tools')
        RawDataView = toolsMenu.addMenu("Raw Data")
        action_view1 = QtWidgets.QAction("Main Table", self)
        action_view2 = QtWidgets.QAction("Shortcut List", self)
        action_view3 = QtWidgets.QAction("List Index Array", self)
        action_view4 = QtWidgets.QAction("List Data Array", self)
        action_view1.triggered.connect(lambda *args, idx=int(1): self.TableVisual(idx))
        action_view2.triggered.connect(lambda *args, idx=int(2): self.TableVisual(idx))
        action_view3.triggered.connect(lambda *args, idx=int(3): self.TableVisual(idx))
        action_view4.triggered.connect(lambda *args, idx=int(4): self.TableVisual(idx))
        RawDataView.addAction(action_view1)
        RawDataView.addAction(action_view2)
        RawDataView.addAction(action_view3)
        RawDataView.addAction(action_view4)
        helpMenu = mainMenu.addMenu('Help')

        #self.statusBar().showMessage("Ready")

        load_button = QtWidgets.QPushButton("Load")
        load_button.setFixedSize(QtCore.QSize(100, 30))
        load_button.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        load_button.clicked.connect(self.table.dataload)
        save_button = QtWidgets.QPushButton("Save")
        save_button.setFixedSize(QtCore.QSize(100, 30))
        save_button.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        save_button.clicked.connect(self.save_data)

        filehbox = QtWidgets.QHBoxLayout()
        filehbox.addWidget(load_button)
        filehbox.addWidget(save_button)
        #filebox = QtWidgets.QGroupBox()
        #filebox.setLayout(filehbox)

        self.add_button = QtWidgets.QPushButton("Add")
        self.add_button.setFixedSize(QtCore.QSize(100, 30))
        self.add_button.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.add_button.clicked.connect(self.table.addrow)
        self.delete_button = QtWidgets.QPushButton("Delete")
        self.delete_button.setFixedSize(QtCore.QSize(100, 30))
        self.delete_button.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.delete_button.clicked.connect(self.table.removerow)
        self.lock_button = QtWidgets.QPushButton("Lock")
        self.lock_button.setFixedSize(QtCore.QSize(100, 30))
        self.lock_button.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.lock_button.clicked.connect(self.lock_switch)
        self.vol_button = QtWidgets.QPushButton("Show Voltage")
        self.vol_button.setFixedSize(QtCore.QSize(120, 30))
        self.vol_button.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.vol_button.clicked.connect(self.voltageModeSwitch)
        self.instant_button = QtWidgets.QPushButton("Show Inst.W")
        self.instant_button.setFixedSize(QtCore.QSize(120, 30))
        self.instant_button.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.instant_button.clicked.connect(self.instantswitch)

        button_layout1 = QtWidgets.QHBoxLayout()
        button_layout1.addWidget(self.add_button)
        button_layout1.addWidget(self.delete_button)
        button_layout1.addWidget(self.lock_button)
        button_layout1.addWidget(self.vol_button)
        button_layout1.addWidget(self.instant_button)
        button_layout1.addStretch(1)
        button_box1 = QtWidgets.QGroupBox("Main Table")
        button_box1.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        button_box1.setLayout(button_layout1)

        self.add_button_sc = QtWidgets.QPushButton("Add")
        self.add_button_sc.setFixedSize(QtCore.QSize(70, 30))
        self.add_button_sc.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.add_button_sc.clicked.connect(self.list.addrow)
        self.edit_button_sc = QtWidgets.QPushButton("Edit")
        self.edit_button_sc.setFixedSize(QtCore.QSize(70, 30))
        self.edit_button_sc.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.edit_button_sc.clicked.connect(self.EditCaller)
        self.picker_button_sc = QtWidgets.QPushButton("Picker")
        self.picker_button_sc.setFixedSize(QtCore.QSize(70, 30))
        self.picker_button_sc.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.picker_button_sc.clicked.connect(self.PickerCaller)
        self.delete_button_sc = QtWidgets.QPushButton("Delete")
        self.delete_button_sc.setFixedSize(QtCore.QSize(70, 30))
        self.delete_button_sc.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.delete_button_sc.clicked.connect(self.list.removerow)
        self.lock_button_sc = QtWidgets.QPushButton("Lock")
        self.lock_button_sc.setFixedSize(QtCore.QSize(70, 30))
        self.lock_button_sc.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.lock_button_sc.clicked.connect(self.lock_sc_switch)
        self.autogen_button = QtWidgets.QPushButton("Auto Gen.")
        self.autogen_button.setFixedSize(QtCore.QSize(90, 30))
        self.autogen_button.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.autogen_button.clicked.connect(self.auto_picker)

        button_layout2 = QtWidgets.QHBoxLayout()
        button_layout2.addWidget(self.add_button_sc)
        button_layout2.addWidget(self.edit_button_sc)
        button_layout2.addWidget(self.picker_button_sc)
        button_layout2.addWidget(self.delete_button_sc)
        button_layout2.addWidget(self.lock_button_sc)
        #button_layout2.addWidget(self.autogen_button)
        button_layout2.addStretch(1)
        button_box2 = QtWidgets.QGroupBox("Shortcut")
        button_box2.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        button_box2.setLayout(button_layout2)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(button_box1,7)
        button_layout.addWidget(button_box2,3)


        self.add_button_var = QtWidgets.QPushButton("Add")
        self.add_button_var.setFixedSize(QtCore.QSize(100, 30))
        self.add_button_var.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.add_button_var.clicked.connect(self.var.addrow)
        self.delete_button_var = QtWidgets.QPushButton("Delete")
        self.delete_button_var.setFixedSize(QtCore.QSize(100, 30))
        self.delete_button_var.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.delete_button_var.clicked.connect(self.var.removerow)

        button_layout3 = QtWidgets.QHBoxLayout()
        button_layout3.addWidget(self.add_button_var)
        button_layout3.addWidget(self.delete_button_var)
        button_layout3.addStretch(1)
        button_box3 = QtWidgets.QGroupBox("Variables")
        button_box3.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        button_box3.setLayout(button_layout3)

        tablespliter = QtWidgets.QSplitter()
        tablespliter.addWidget(self.table)
        tablespliter.addWidget(self.list)
        tablespliter.setStretchFactor(0, 7)
        tablespliter.setStretchFactor(1, 3)
        tablespliter.setSizePolicy(QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)

        self.combox_clk = QtWidgets.QComboBox(self)
        self.combox_clk.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.combox_clk.addItems(["25", "32", "40", "50", "80", "100", "125", "160", "200", "250", "400", "500", "625", "800", "1000", "1250", "2500", "3125", "4000", "5000", "6250", "10000", "12500", "20000", "25000", "33330", "50000"])
        clockhbox = QtWidgets.QHBoxLayout()
        _label = QtWidgets.QLabel("Clock:")
        _label.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        clockhbox.addWidget(_label)
        clockhbox.addWidget(self.combox_clk)
        _label = QtWidgets.QLabel("kHz")
        _label.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        clockhbox.addWidget(_label)

        self.combox_vol = QtWidgets.QComboBox(self)
        self.combox_vol.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.combox_vol.addItems(["3.3", "2.5", "1.8", "1.5", "1.2"])
        volhbox = QtWidgets.QHBoxLayout()
        _label = QtWidgets.QLabel("Voltage:")
        _label.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        volhbox.addWidget(_label)
        volhbox.addWidget(self.combox_vol)
        _label = QtWidgets.QLabel("V")
        _label.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        volhbox.addWidget(_label)

        self.button_connect = QtWidgets.QPushButton('Connect')
        self.button_connect.setFixedSize(QtCore.QSize(100, 30))
        self.button_connect.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.led = led.MyLed()
        self.button_connect.clicked.connect(self.spi_switch)
        conhbox = QtWidgets.QHBoxLayout()
        conhbox.addWidget(self.button_connect)
        conhbox.addWidget(self.led)

        reset_button = QtWidgets.QPushButton("Reset")
        reset_button.setFixedSize(QtCore.QSize(75, 30))
        reset_button.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        reset_button.clicked.connect(self.reset_spi)
        self.resetInput = QtWidgets.QSpinBox()
        self.resetInput.setFixedWidth(40)
        self.resetInput.setMinimum(0)
        self.resetInput.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))

        setupvbox = QtWidgets.QHBoxLayout()
        setupvbox.addLayout(clockhbox)
        setupvbox.addLayout(volhbox)
        setupvbox.addLayout(conhbox)
        setupvbox.addWidget(reset_button)
        setupvbox.addWidget(self.resetInput)
        setupvbox.addStretch(1)
        setupvbox.addLayout(filehbox)
        setupbox = QtWidgets.QGroupBox("Setup")
        setupbox.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        setupbox.setLayout(setupvbox)

        self.combox_clk_raspi = QtWidgets.QComboBox()
        self.combox_clk_raspi.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.combox_clk_raspi.addItems(
            ["25", "32", "40", "50", "80", "100", "125", "160", "200", "250", "400", "500", "625", "800", "1000",
             "1250", "2500", "3125", "4000", "5000", "6250", "10000", "12500", "20000", "25000", "33330", "50000"])
        clockhbox = QtWidgets.QHBoxLayout()
        _label = QtWidgets.QLabel("Clock:")
        _label.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        clockhbox.addWidget(_label)
        clockhbox.addWidget(self.combox_clk_raspi)
        _label = QtWidgets.QLabel("kHz")
        _label.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        clockhbox.addWidget(_label)

        combox_vol = QtWidgets.QComboBox()
        combox_vol.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        combox_vol.addItems(["3.3", "2.5", "1.8", "1.5", "1.2"])
        combox_vol.setCurrentText("3.3")
        combox_vol.setEnabled(False)
        volhbox = QtWidgets.QHBoxLayout()
        _label = QtWidgets.QLabel("Voltage:")
        _label.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        volhbox.addWidget(_label)
        volhbox.addWidget(combox_vol)
        _label = QtWidgets.QLabel("V")
        _label.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        volhbox.addWidget(_label)

        self.button_discover = QtWidgets.QPushButton('Discover')
        self.button_discover.setFixedSize(QtCore.QSize(100, 30))
        self.button_discover.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.button_discover.clicked.connect(self.tcp_discover)

        self.raspihbox = QtWidgets.QHBoxLayout()
        self.raspihbox.addLayout(clockhbox)
        self.raspihbox.addLayout(volhbox)
        self.raspihbox.addWidget(self.button_discover)
        self.raspihbox.addStretch(1)

        self.raspibox = QtWidgets.QGroupBox("Raspberry Pi")
        self.raspibox.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.raspibox.setLayout(self.raspihbox)
        self.raspibox.hide()
        self.raspi_layout = {}
        mainlayout = QtWidgets.QVBoxLayout()
        #tablehbox.setContentsMargins(10, 10, 10, 10)
        mainlayout.addWidget(setupbox)
        mainlayout.addWidget(self.raspibox)
        mainlayout.addLayout(button_layout)
        #grid = QtWidgets.QGridLayout(self)
        #grid.addLayout(ctrlbox, 0, 1)
        #grid.addLayout(tablehbox, 0, 0)
        #mainlayout.addLayout(tablehbox)
        mainlayout.addWidget(tablespliter)
        qWidget = QtWidgets.QWidget()
        qWidget.setLayout(mainlayout)
        self.setCentralWidget(qWidget)
        if ni8452.dll_flag is False:
            self.button_connect.setEnabled(False)
            QtWidgets.QMessageBox.warning(self, "Warning", "Ni845x.dll NOT FOUND!")
        self.setGeometry(50, 50, 1800, 1000)
        self.setWindowTitle('SPI GUI for NI845x')
        self.setWindowIcon(QtGui.QIcon('tokyotech.ico'))
        self.showMaximized()

        if os.path.exists("config.spi") is True:
            try:
                f = open('config.spi', 'rb')
                table_data, self.list.data, self.list.ReadData, self.list.ReadList, self.table.default_path = pkl.load(f)
                for col in self.table.data.columns:
                    if col in table_data.columns:
                        self.table.data[col] = table_data[col]
                    elif col == "Pos" and "Sel" in table_data.columns:
                        self.table.data[col] = table_data["Sel"]
                    elif col == "RegSize" and "DataSize" in table_data.columns:
                        self.table.data[col] = table_data["DataSize"]
                    elif col == "Size" and "EnbBits" in table_data.columns:
                        self.table.data[col] = table_data["EnbBits"]
                    else:
                        self.table.data[col] = ""
                f.close()
                self.table.dataload(True)
                self.list.dataload()
            except Exception as e:
                pass

    @QtCore.pyqtSlot()
    def PickerCaller(self):
        if self.picker is not None:
            self.picker.close()
        self.picker = Picker()
        self.picker.buttonApply.clicked.connect(lambda *args, row=None: self.addrow_process(row))
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

    @QtCore.pyqtSlot()
    def EditCaller(self):
        if len(self.list.selectedIndexes()) is 0:
            return
        if self.picker is not None:
            self.picker.close()
        self.picker = Picker()
        row = self.list.selectedIndexes()[0].row() -1
        self.picker.buttonApply.clicked.connect(lambda *args, row=row: self.addrow_process(row+1))
        self.picker.CloseSignal.connect(self.pickerClose)
        self.table.SelectedTx.connect(self.picker.additem)
        self.picker.nameInput.setText(self.list.data.at[row, "Name"])
        if self.lock_button.text() == "Lock":
            self.lock_switch()
        if self.lock_button_sc.text() == "Lock":
            self.lock_sc_switch()
        self.lock_button.setEnabled(False)
        self.lock_button_sc.setEnabled(False)
        self.picker.deleteAll()
        for _index in self.list.ReadList[row]:
            r = _index - 1
            global Protocol
            if Protocol == "CA":
                _size = 10
            else:
                _size = self.data.at[r, "Size"]
            self.picker.additem(_index, self.table.data.at[r, "Name"], int(_size))
        for _index, _bit in self.list.ReadData[row]:
            if _index == -1:
                self.picker.buttonPoint.click()
            else:
                _item = self.list.ReadList[row].index(_index)
                if _bit < len(self.picker.itemButton[_item]):
                    self.picker.itemButton[_item][_bit].click()
        self.picker.show()

    def addrow_process(self, rowcount):      # picker itemBasket parse
        itemBasket = self.picker.itemBasket  # itemBasket: [[0,bit],[1,bit],...]
        index = self.picker.trueIndex        # True Index: [index_1,index_2，index_3,...]
        name = self.picker.nameInput.text()
        self.picker.close()
        self.picker = None
        if len(itemBasket) is not 0:
            self.list.onLoading = True
            readlist = []
            data = []
            range = ""
            for _ in itemBasket:
                if _[0] is -1: # floating point .
                    if _ is not itemBasket[-1]:
                        data.append([-1, -1])
                        range = range[:-1] + "."
                else:
                    row = index[_[0]]
                    data.append([row, _[1]])
                    range = range + str(row)+"["+str(_[1])+"],"
                    if row not in readlist:
                        readlist.append(row)
            if rowcount is None:
                self.list.ReadData.append(data)
                self.list.ReadList.append(readlist)
            else:
                self.list.ReadData[rowcount-1] = data
                self.list.ReadList[rowcount-1] = readlist
            range = range[:-1]

            if rowcount is None:
                rowcount = self.list.rowCount()
                self.list.insertRow(rowcount)
                self.list.setItem(rowcount, 0, QtWidgets.QTableWidgetItem(name))
                button_read = QtWidgets.QPushButton('Read')
                button_write = QtWidgets.QPushButton('Write')
                button_read.setEnabled(SPIConnFlag)
                button_write.setEnabled(SPIConnFlag)
                button_read.clicked.connect(lambda *args, rowcount=rowcount: self.list.handleReadRunClicked(rowcount))
                button_write.clicked.connect(lambda *args, rowcount=rowcount: self.list.handleWriteRunClicked(rowcount))
                self.list.button_read.append(button_read)
                self.list.button_write.append(button_write)
                self.list.button_read_en.append(True)
                self.list.button_write_en.append(True)
                self.list.setCellWidget(rowcount, 4, button_read)
                self.list.setCellWidget(rowcount, 5, button_write)
            else:
                pass

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
                self.list.data = self.list.data.append(pd.Series([name, range, _bin, 0, len(data)], index=["Name", "Range", "Bin", "Dec", "Length"]),
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
                self.list.data = self.list.data.append(pd.Series([name, range, _bin, 0.0, len(data)], index=["Name", "Range", "Bin", "Dec", "Length"]),
                                                       ignore_index=True)
                self.list.setItem(rowcount, 2, QtWidgets.QTableWidgetItem(_bin))

            self.list.onLoading = False

    @QtCore.pyqtSlot()
    def pickerClose(self):
        self.lock_button.setEnabled(True)
        self.lock_button_sc.setEnabled(True)
        self.lock_switch()
        self.lock_sc_switch()

    @QtCore.pyqtSlot(int)
    def pickersync(self, index):
        for row in range(len(self.list.ReadList)):
            if len(self.list.ReadData[row]) == 0:
                continue
            else:
                for _ in self.list.ReadList[row]:
                    if _ == index+1:
                        r = _ - 1
                        read_data = str(self.table.data.at[r, "BinR"][::-1])
                        list_data = list(self.list.data.at[row, "Bin"])
                        count = 0
                        for _idx, bit in self.list.ReadData[row]:
                            if _idx == index+1:
                                list_data[count] = read_data[bit]
                            count = count + 1
                        _bin = "".join(list_data)
                        self.list.setItem(row+1, 2, QtWidgets.QTableWidgetItem(_bin))

    @QtCore.pyqtSlot(bool, int)
    def handleBackbone(self, ReadWriteFlag, row):  # Shortcut list control
        print(row)
        if row is 0:
            if ReadWriteFlag is True:
                for _ in range(len(self.table.button_read_en)):
                    if self.table.button_read[_].isEnabled():
                        self.table.handleReadClicked(_)
            else:
                for _ in range(len(self.table.button_write_en)):
                    if self.table.button_write[_].isEnabled():
                        self.table.handleWriteClicked(_)
        else:
            row = row - 1
            if len(self.list.ReadData[row]) == 0:  # index group read and write
                if ReadWriteFlag is True:
                    for _ in self.list.ReadList[row]:
                        r = _ - 1
                        if self.table.button_read[r].isEnabled():
                            self.table.handleReadClicked(r)
                else:
                    for _ in self.list.ReadList[row]:
                        r = _ - 1
                        if self.table.button_write[r].isEnabled():
                            self.table.handleWriteClicked(r)

            elif ReadWriteFlag is True:
                # Read
                dictRead = {}
                _bin = ""
                for _ in self.list.ReadList[row]:
                    r = _ - 1
                    if not self.table.button_read[r].isEnabled():
                        return
                for _ in self.list.ReadList[row]:
                    r = _ - 1
                    self.table.handleReadClicked(r)
                    dictRead[r] = str(self.table.data.at[r, "BinR"])
                for _ in self.list.ReadData[row]:
                    if _[0] is not -1:
                        if len(_) == 2:
                            _bin = _bin + dictRead[_[0]-1][::-1][_[1]]  # [::-1] string flip
                        elif len(_) == 3:
                            if _[2] == -1:
                                _bin = _bin + dictRead[_[0]-1][::-1][_[1]:]
                            else:
                                _bin = _bin + dictRead[_[0]-1][::-1][_[1]:_[2]]
                        elif len(_) == 4:
                            if _[2] == -1:
                                _bin = _bin + dictRead[_[0]-1][::-1][_[1]::_[3]]
                            else:
                                _bin = _bin + dictRead[_[0]-1][::-1][_[1]:_[2]:_[3]]
                    else:
                        _bin = _bin + "."
                self.list.setItem(row+1, 2, QtWidgets.QTableWidgetItem(_bin))
            else:
                # Write
                dictWrite = {}
                binWrite = self.list.item(row+1, 2).text()
                for _ in self.list.ReadList[row]:
                    r = _ - 1
                    if not self.table.button_write[r].isEnabled():
                        return
                for _ in self.list.ReadList[row]:
                    r = _ - 1
                    self.table.handleReadClicked(r)
                    dictWrite[r] = str(self.table.data.at[r, "BinR"])

                for _ in self.list.ReadData[row]:
                    if _[0] is not -1:
                        _index = _[0] - 1
                        string_list = list(dictWrite[_index][::-1])
                        if len(_) == 2: # 1 bit
                            string_list[_[1]] = binWrite[0]
                            binWrite = binWrite[1:]
                        elif len(_) == 3:
                            string_list[_[1]:_[2]] = binWrite[0:_[2]-_[1]]
                            binWrite = binWrite[_[2]-_[1]:]
                        elif len(_) == 4:
                            length = round((_[2]-_[1])/_[3])
                            string_list[_[1]:_[2]:_[3]] = binWrite[0:length]
                            binWrite = binWrite[length:]
                        string_new = "".join(string_list)
                        dictWrite[_index] = string_new[::-1]
                    else:
                        binWrite = binWrite[1:]

                for _ in self.list.ReadList[row]:
                    r = _ - 1
                    self.table.setItem(r, self.table.col_dict["BinW"], QtWidgets.QTableWidgetItem(dictWrite[r]))
                    self.table.handleWriteClicked(r)

    @QtCore.pyqtSlot()
    def reset_spi(self):
        global Protocol
        if Protocol == "CA":
            caddr = int(self.resetInput.value())
            ni8452.spi_reset_new(0, caddr)
            for _ in self.table.client.connections:
                self.table.client.spi_reset_new(_, 0, caddr)
        else:
            cs = int(self.resetInput.value())
            ni8452.spi_reset(cs)
            for _ in self.table.client.connections:
                self.table.client.spi_reset(_, cs)

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
                QtWidgets.QMessageBox.warning(self, "Warning", "No NI Devices detected!")

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

    @QtCore.pyqtSlot()
    def raspi_switch(self):
        if self.raspi_action.isChecked():
            self.raspibox.show()
            self.table.setColumnHidden(self.table.col_dict["Term"], False)
            self.table.button_update()
            self.list.button_update()
        else:
            self.raspibox.hide()
            self.table.setColumnHidden(self.table.col_dict["Term"], True)
            self.table.button_update()
            self.list.button_update()

    @QtCore.pyqtSlot()
    def tcp_discover(self):
        asyncio.run(self.table.client.connect(self.combox_clk_raspi.currentText()))

    @QtCore.pyqtSlot(str, str)
    def tcp_panel(self, name, cmd):
        if cmd == "open":
            _label_temp = QtWidgets.QLabel()
            _ico = QtGui.QPixmap('chip.png')
            _ico = _ico.scaled(32, 32)
            _label_temp.setPixmap(_ico)
            _label_name = QtWidgets.QLabel(name)
            _label_name.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
            _button = QtWidgets.QPushButton('Disconnect')
            _button.setFixedSize(QtCore.QSize(100, 30))
            _button.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
            _button.clicked.connect(lambda *args, _name=name: self.raspi_delete(_name))
            _led = led.MyLed()
            _led.ConnFlag = True
            _led.update()
            conhbox = QtWidgets.QHBoxLayout()
            conhbox.addWidget(_label_temp)
            conhbox.addWidget(_label_name)
            conhbox.addWidget(_button)
            conhbox.addWidget(_led)
            _strech = self.raspihbox.itemAt(self.raspihbox.count() - 1)
            self.raspihbox.removeItem(_strech)
            self.raspihbox.addLayout(conhbox)
            self.raspihbox.addStretch(1)
            self.raspi_layout[name] = conhbox
        else:
            for i in range(self.raspi_layout[name].count()):
                item = self.raspi_layout[name].itemAt(i)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            self.raspi_layout[name].deleteLater()
            self.raspi_layout[name] = None
            del self.raspi_layout[name]
        self.table.button_update()
        self.list.button_update()

    @QtCore.pyqtSlot(str)
    def raspi_delete(self, name):
        asyncio.run(self.table.client.tcp_close(name))

    @QtCore.pyqtSlot()
    def mode_toggle_classic(self):
        global Protocol
        Protocol = "Classic"
        self.classic_action.setChecked(True)
        self.cs_action.setChecked(False)
        self.table.setColumnHidden(self.table.col_dict["CAddr"], True)
        self.table.setColumnHidden(self.table.col_dict["Pos"], False)
        self.table.setColumnHidden(self.table.col_dict["RegSize"], False)
        self.table.setColumnHidden(self.table.col_dict["Size"], False)
        self.table.button_update()

    @QtCore.pyqtSlot()
    def mode_toggle_cs(self):
        global Protocol
        Protocol = "CA"
        self.classic_action.setChecked(False)
        self.cs_action.setChecked(True)
        self.table.setColumnHidden(self.table.col_dict["CAddr"], False)
        self.table.setColumnHidden(self.table.col_dict["Pos"], True)
        self.table.setColumnHidden(self.table.col_dict["RegSize"], True)
        self.table.setColumnHidden(self.table.col_dict["Size"], True)
        self.table.button_update()


    def voltageModeSwitch(self):
        if self.table.isColumnHidden(self.table.col_dict["VolMax"]):
            self.table.setColumnHidden(self.table.col_dict["VolMax"], False)
            self.table.setColumnHidden(self.table.col_dict["VolMin"], False)
            self.table.setColumnHidden(self.table.col_dict["VolR"], False)
            self.table.setColumnHidden(self.table.col_dict["VolW"], False)
            self.vol_button.setText("Hide Voltage")
        else:
            self.table.setColumnHidden(self.table.col_dict["VolMax"], True)
            self.table.setColumnHidden(self.table.col_dict["VolMin"], True)
            self.table.setColumnHidden(self.table.col_dict["VolR"], True)
            self.table.setColumnHidden(self.table.col_dict["VolW"], True)
            self.vol_button.setText("Show Voltage")

    def instantswitch(self):
        if self.table.isColumnHidden(self.table.col_dict["-"]):
            self.table.setColumnHidden(self.table.col_dict["-"], False)
            self.table.setColumnHidden(self.table.col_dict["+"], False)
            self.table.setColumnHidden(self.table.col_dict["Unit"], False)
            self.instant_button.setText("Hide Inst.W")
        else:
            self.table.setColumnHidden(self.table.col_dict["-"], True)
            self.table.setColumnHidden(self.table.col_dict["+"], True)
            self.table.setColumnHidden(self.table.col_dict["Unit"], True)
            self.instant_button.setText("Show Inst.W")

    def closeEvent(self, event):
        for _ in self.table.client.connections:
            asyncio.run(self.table.client.tcp_close(_))
        f = open('config.spi', 'wb')
        pkl.dump((self.table.data, self.list.data, self.list.ReadData, self.list.ReadList, self.table.default_path), f)
        f.close()
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
            self.edit_button_sc.setEnabled(False)
            self.delete_button_sc.setEnabled(False)
            self.lock_button_sc.setText("Unlock")
        else:
            self.list.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
            self.add_button_sc.setEnabled(True)
            self.edit_button_sc.setEnabled(True)
            self.delete_button_sc.setEnabled(True)
            self.lock_button_sc.setText("Lock")

    def save_data(self):
        f = open('config.spi', 'wb')
        pkl.dump((self.table.data, self.list.data, self.list.ReadData, self.list.ReadList, self.table.default_path), f)
        f.close()
        if not os.path.exists(self.table.default_path):
            self.table.default_path = os.getcwd()
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save SPI Data", self.table.default_path, "CSV Files (*.csv)")
        if path:
            self.table.default_path = os.path.dirname(path)
            FileIO.df2csv(path, self.table.data)

    @QtCore.pyqtSlot(list, int)
    def length_data(self, ReadData, row):
        count = 0
        for _ in ReadData:
            if type(_) is int:
                global Protocol
                if Protocol == "CA":
                    _length = 10
                else:
                    _length = intSafe(self.table.data.at[_-1, "Size"])
                if _length is not None:
                    count = count + _length
            elif len(_) == 2:
                if _[0] != -1:
                    count = count + 1
            elif len(_) == 3:
                count = count + _[2] - _[1]
            elif len(_) == 4:
                count = count + round((_[2] - _[1])/_[3])
            else:
                pass
        self.list.data.at[row, "Length"] = int(count)

    @QtCore.pyqtSlot(int)
    def TableVisual(self, index):
        if index == 1:
            df = self.table.data
        elif index == 2:
            df = self.list.data
        elif index == 3:
            df = self.list.ReadList
        else:
            df = self.list.ReadData

        if index in [1, 2]:
            winlut = LUTShow(df, self)
            width = df.shape[1] * 80 + 20
        else:
            winlut = ArrayShow(df, self)
            width = winlut.columnCount() * 80 + 20
        winlut.setWindowFlags(winlut.windowFlags() | QtCore.Qt.Window)
        #winlut.setFixedSize(width,self.height())
        winlut.setGeometry(100,50,width,self.height())
        winlut.show()

    def auto_picker(self):
        pre_dict = {}
        name_list = self.table.data["Name"].tolist()
        for _ in name_list:
            if '<' in _ and '>' in _:
                _temp = _.split(",")
                print(_temp)

    def exc_handle(self):
        for _ in self.table.client.connections:
            asyncio.run(self.table.client.tcp_close(_))


def exception_hook(exc_type, exc_value, traceback):
    global main_window
    main_window.exc_handle()
    print(f"Unhandled exception: {exc_value}")
    sys.__excepthook__(exc_type, exc_value, traceback)
    sys.exit(1)


if __name__ == '__main__':
    global main_window
    sys.excepthook = exception_hook
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
