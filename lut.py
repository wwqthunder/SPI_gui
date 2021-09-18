from PyQt5.QtWidgets import QWidget,QApplication,QDialogButtonBox,QVBoxLayout,QPushButton,QHBoxLayout,QGroupBox,\
    QLineEdit,QSlider,QSizePolicy,QLabel,QFileDialog,QMessageBox,QTableWidget,QTableWidgetItem,QComboBox
from PyQt5.QtGui import QIcon,QFont
from PyQt5.QtCore import Qt,QSize
import sys
import os
import pandas as pd
from utilis import intSafe

class LUT(QWidget):
    def __init__(self, parent=None):
        super(LUT, self).__init__(parent)
        # self.setGeometry(400, 300, 800, 600)
        self.NameBox = []
        self.ValueBox = []
        self.SliderBox = []
        self.ComboBox = []
        self.ResultBox = []
        self.LUTData = pd.DataFrame()


        self.setWindowTitle('Look Up Table')
        self.setWindowIcon(QIcon('tokyotech.ico'))
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        self.buttonShow = QPushButton("Show LUT")
        self.buttonShow.clicked.connect(self.TableVisual)
        self.buttonShow.setEnabled(False)
        self.buttonAdd = QPushButton("Add")
        self.buttonAdd.clicked.connect(self.additem)
        self.buttonAdd.setEnabled(False)
        buttonLoad = QPushButton("Load")
        buttonLoad.clicked.connect(self.load)
        self.buttonSave = QPushButton("Save")
        self.buttonSave.clicked.connect(self.save)
        self.buttonSave.setEnabled(False)

        CtrlButtonLayout = QHBoxLayout()
        CtrlButtonLayout.addWidget(self.buttonShow)
        CtrlButtonLayout.addWidget(self.buttonAdd)
        CtrlButtonLayout.addStretch(1)
        self.CtrlLayout = QVBoxLayout()
        self.CtrlLayout.addLayout(CtrlButtonLayout)
        CtrlGroup = QGroupBox("Control Panel")
        CtrlGroup.setLayout(self.CtrlLayout)

        MenuLayout = QHBoxLayout()
        # MenuLayout.addWidget(buttonShow)
        # MenuLayout.addWidget(buttonAdd)
        MenuLayout.addStretch(1)
        MenuLayout.addWidget(buttonLoad)
        MenuLayout.addWidget(self.buttonSave)
        MenuLayout.addWidget(buttonBox)

        _font = QFont()
        #_font = QFont('Arial', 15)
        _font.setBold(True)

        self.NoData = QLabel("No Data")
        self.NoData.setFont(_font)
        self.NoData.setStyleSheet("color: red")

        self.MainLayout = QVBoxLayout(self)
        self.MainLayout.addWidget(self.NoData)
        self.MainLayout.addWidget(CtrlGroup)
        self.MainLayout.addLayout(MenuLayout)

        # self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        # self.setWindowFlags(Qt.Window|Qt.WindowTitleHint)

    def accept(self):
        self.close()
    def reject(self):
        self.close()
    def TableVisual(self):
        # self.LUTTable.show()
        winlut = LUTShow(self.LUTData,self)
        winlut.setWindowFlags(winlut.windowFlags() | Qt.Window)
        width = self.LUTData.shape[1]*80+20
        winlut.setGeometry(self.frameGeometry().x()-width,self.frameGeometry().y(),width,500)
        winlut.show()

    def additem(self):
        itembox = QHBoxLayout()
        # itembox.setSpacing(0)
        nameinput = QLineEdit()
        nameinput.setFixedWidth(60)
        valueinput = QLineEdit()
        valueinput.setFixedWidth(60)
        _label1 = QLabel(":")
        _label2 = QLabel(":")
        _font = QFont('Arial', 15)
        _font.setBold(True)
        _label2.setFont(_font)
        deletebutton = QPushButton("Delete")
        _label1.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
        _label2.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        nameinput.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
        valueinput.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Maximum)
        deletebutton.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
        valueinput.editingFinished.connect(lambda  idx=len(self.ValueBox): self.valueEdit(idx))

        colselect = QComboBox()
        colselect.addItems([_ for _ in self.LUTData.columns.tolist()[1:]])

        slider = QSlider(Qt.Horizontal)
        slider.setFocusPolicy(Qt.StrongFocus)
        slider.setTickPosition(QSlider.TicksBothSides)
        slider.setRange(0, self.LUTData.shape[0]-1)
        slider.setTickInterval(1)
        slider.setPageStep(1)
        slider.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Minimum)
        slider.setMinimumWidth(200+2*self.LUTData.shape[0])
        slider.valueChanged.connect(lambda value, idx=len(self.ValueBox): self.sliderSync(value,idx))

        itembox.addWidget(nameinput)
        itembox.addWidget(_label1)
        itembox.addWidget(slider)
        itembox.addWidget(valueinput)
        itembox.addWidget(colselect)
        itembox.addWidget(_label2)
        itembox.addStretch(1)
        itembox.addWidget(deletebutton)
        itembox.addStretch(1)
        self.CtrlLayout.addLayout(itembox)
        self.NameBox.append(nameinput)
        self.ValueBox.append(valueinput)
        self.SliderBox.append(slider)
        self.ComboBox.append(colselect)
        self.ResultBox.append(_label2)
    def sliderSync(self,value,index):
        self.ValueBox[index].setText(str(self.LUTData.iat[value, 0]))
        self.ResultBox[index].setText(": "+str(self.LUTData[self.ComboBox[index].currentText()][value]))

    def load(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import SPI File", os.getcwd(),
                                                        "Data Files (*.xlsm *.xls *.xlsx *.csv)")
        if (path):
            self.onLoading = True
            try:
                self.LUTData = loadLUT(path)
            except Exception as e:
                QMessageBox.critical(self, "Error", "FAIL TO LOAD!")
                return
            self.NoData.hide()
            self.buttonShow.setEnabled(True)
            self.buttonAdd.setEnabled(True)
            self.buttonSave.setEnabled(True)

    def save(self):
        pass

    def valueEdit(self,index):
        text = self.ValueBox[index].text()
        if text.isdigit() is True:
            self.SliderBox[index].setValue(int(text))


def loadLUT(path):
    raw = pd.read_excel(open(path, 'rb'), header=0,dtype=object,na_filter = False)
    return raw

class LUTShow(QTableWidget):
    def __init__(self,df,parent=None):
        super(LUTShow, self).__init__(df.shape[0],df.shape[1],parent)
        self.data = df
        self.setHorizontalHeaderLabels(df.columns.tolist())
        self.verticalHeader().hide()
        self.horizontalHeader().setHighlightSections(True)
        self.horizontalHeader().setStyleSheet("QHeaderView::section{"
            "border-top:0px solid #D8D8D8;"
            "border-left:0px solid #D8D8D8;"
            "border-right:1px solid #D8D8D8;"
            "border-bottom: 1px solid #D8D8D8;"
            "background-color:white;"
            "padding:4px;"
        "}")
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        for index, row in df.iterrows():
            for _ in range(df.shape[1]):
                _temp = QTableWidgetItem()
                _temp.setData(Qt.EditRole, row[_])
                _temp.setTextAlignment(Qt.AlignCenter)
                self.setItem(index, _, _temp)
        for _ in range(df.shape[1]):
            self.setColumnWidth(_, 80)

class ArrayShow(QTableWidget):
    def __init__(self,arr,parent=None):
        super(ArrayShow, self).__init__(len(arr),1,parent)
        self.data = arr
        self.horizontalHeader().setHighlightSections(True)
        self.horizontalHeader().setStyleSheet("QHeaderView::section{"
            "border-top:0px solid #D8D8D8;"
            "border-left:0px solid #D8D8D8;"
            "border-right:1px solid #D8D8D8;"
            "border-bottom: 1px solid #D8D8D8;"
            "background-color:white;"
            "padding:4px;"
        "}")
        self.resizeColumnsToContents()
        #self.resizeRowsToContents()
        self.setColumnWidth(0, 80)
        for _row in range(len(arr)):
            if len(arr[_row]) > self.columnCount():
                for _ in range(self.columnCount(), len(arr[_row])):
                    self.insertColumn(_)
                    self.setColumnWidth(_, 80)
            for idx in range(len(arr[_row])):
                _temp = QTableWidgetItem()
                _temp.setData(Qt.EditRole, str(arr[_row][idx]))
                _temp.setTextAlignment(Qt.AlignCenter)
                self.setItem(_row, idx, _temp)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = LUT()
    w.show()
    sys.exit(app.exec_())