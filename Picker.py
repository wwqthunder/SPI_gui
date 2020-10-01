import sys
from PyQt5 import QtCore, QtGui, QtWidgets, sip


class Picker(QtWidgets.QWidget):
    PickerCall = QtCore.pyqtSignal(int,str,int)
    def __init__(self, parent=None):
        super(Picker, self).__init__(parent)

        self.itemButton = []    # Button Pool handles [[button1,button2,...],[button1,button2,...],...]
        self.itemBasket = []    # Result Index [[item1.bit1],[item2.bit2],...]
        self.resButton = []     # Result Button handles [button1,button2,...]
        self.resetButton = []
        self.deleteButton = []
        self.labelList = []
        self.trueIndex = []
        self.PickerCall.connect(self.additem)

        self.resultbox = QtWidgets.QHBoxLayout()
        self.nameInput = QtWidgets.QLineEdit()
        self.nameInput.setFixedWidth(200)
        self.resultbox.addWidget(self.nameInput)
        self.resultbox.addWidget( QtWidgets.QLabel(":"))

        buttonReset = QtWidgets.QPushButton("Reset")
        self.buttonPoint = QtWidgets.QPushButton(".")
        buttonBackspace = QtWidgets.QPushButton("<-")
        buttonReset.setFixedSize(QtCore.QSize(80, 40))
        self.buttonPoint.setFixedSize(QtCore.QSize(80, 40))
        buttonBackspace.setFixedSize(QtCore.QSize(80, 40))
        buttonReset.clicked.connect(self.resetAll)
        self.buttonPoint.clicked.connect(lambda *args, nitem = -1, nbit = -1: self.handleBitButtonClicked(nitem, nbit))
        buttonBackspace.clicked.connect(self.backspace)

        self.buttonApply = QtWidgets.QPushButton("Apply")
        buttonCancel = QtWidgets.QPushButton("Cancel")
        self.buttonApply.setFixedSize(QtCore.QSize(80, 40))
        buttonCancel.setFixedSize(QtCore.QSize(80, 40))
        self.buttonApply.clicked.connect(self.apply)
        buttonCancel.clicked.connect(self.cancel)
        buttonbox = QtWidgets.QGridLayout()
        #buttonbox.addLayout(self.resultbox)
        buttonbox.addWidget(buttonReset, 2, 1)
        buttonbox.addWidget(self.buttonPoint, 0, 1)
        buttonbox.addWidget(buttonBackspace, 1, 1)
        buttonbox.addWidget(self.buttonApply, 3, 0,QtCore.Qt.AlignBottom)
        buttonbox.addWidget(buttonCancel, 3, 1,QtCore.Qt.AlignBottom)

        self.itemRes = QtWidgets.QHBoxLayout()
        self.itemRes.setSpacing(0)

        self.itemForm = QtWidgets.QFormLayout()

        #self.grid = QtWidgets.QGridLayout()
        #self.grid.addWidget(QtWidgets.QLabel("NAME:"), 0, 0,1,1,QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        #self.grid.addWidget(QtWidgets.QLabel("Select item from Main Table to import."), 0, 1,2,8,QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        #self.grid.addLayout(self.resultbox,1, 0,1,1,QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        #self.grid.addLayout(self.itemRes, 1, 1,1,8,QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        #self.grid.addLayout(self.itemForm, 2, 1, 8, 4, QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        #self.grid.addLayout(buttonbox, 2, 5, 4, 4)

        downbox = QtWidgets.QHBoxLayout()
        downbox.addLayout(self.itemForm,QtCore.Qt.AlignLeft)
        downbox.addStretch(1)
        downbox.addLayout(buttonbox)

        textbox = QtWidgets.QHBoxLayout()
        label1 = QtWidgets.QLabel("Input Name Here:")
        label1.setFont(QtGui .QFont('Arial', 16))
        textbox.addWidget(label1)
        label2 = QtWidgets.QLabel("1) Select item from Main Table to import.\n2) MSB 0 bit numbering for custom line")
        label2.setFont(QtGui.QFont('Arial', 16))
        textbox.addWidget(label2)

        resultbox = QtWidgets.QHBoxLayout()
        resultbox.setAlignment(QtCore.Qt.AlignLeft)
        resultbox.addLayout(self.resultbox)
        resultbox.addLayout(self.itemRes)
        resultbox.addStretch(1)

        self.MainLayout = QtWidgets.QVBoxLayout(self)
        self.MainLayout.addLayout(textbox, 1)
        self.MainLayout.addLayout(resultbox, 1)
        self.MainLayout.addLayout(downbox, 8)

        self.setGeometry(400, 300, 800, 600)
        self.setWindowTitle('Picker')
        self.setWindowIcon(QtGui.QIcon('tokyotech.ico'))


    @QtCore.pyqtSlot(int,str,int)
    def additem(self,index,name,data):
        _itemButton = []
        self.trueIndex.append(index)
        nitem = len(self.itemButton)
        itembox = QtWidgets.QHBoxLayout()
        itembox.setSpacing(0)
        #itembox.addWidget(QtWidgets.QLabel(str(nitem+1) + ". " + name+": "))

        for _ in range(data):
            button = QtWidgets.QPushButton(str(_))
            button.clicked.connect(lambda *args, nitem=nitem, nbit = _: self.handleBitButtonClicked(nitem, nbit))
            button.setFixedSize(QtCore.QSize(40, 40))
            _itemButton.append(button)
        for _ in reversed(_itemButton):
            itembox.addWidget(_,alignment=QtCore.Qt.AlignLeft)

        button_reset = QtWidgets.QPushButton("Reset")
        button_reset.setFixedSize(QtCore.QSize(80, 40))
        button_reset.clicked.connect(lambda *args, nitem=nitem: self.handleBitResetClicked(nitem))
        itembox.addWidget(button_reset,alignment=QtCore.Qt.AlignLeft)
        self.resetButton.append(button_reset)
        button_delete = QtWidgets.QPushButton("Delete")
        button_delete.setFixedSize(QtCore.QSize(80, 40))
        button_delete.clicked.connect(lambda *args, nitem=nitem: self.handleBitDeleteClicked(nitem))
        itembox.addWidget(button_delete, alignment=QtCore.Qt.AlignLeft)
        self.deleteButton.append(button_delete)

        self.itemButton.append(_itemButton)
        #_layout = QtWidgets.QHBoxLayout()
        _label = QtWidgets.QLabel(str(nitem+1) + ". " + str(index+1) + "." + str(name)+": ")
        self.labelList.append(_label)
        #_layout.addWidget(_label)
        #self.nameList.addLayout(_layout)
        #self.itemList.addLayout(itembox)
        self.itemForm.addRow(_label, itembox)

    @QtCore.pyqtSlot(int,int)
    def handleBitButtonClicked(self, nitem, nbit):
        if [nitem,nbit] not in self.itemBasket:
            if nitem is -1 and nbit is -1:
                bit = QtWidgets.QPushButton(".")
                self.buttonPoint.setStyleSheet(
                    "background-color:qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,stop: 0 #dadbde, stop: 1 #f6f7fa);"
                    "color: red; font: bold;")
            else:
                self.itemButton[nitem][nbit].setStyleSheet(
                    "background-color:qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,stop: 0 #dadbde, stop: 1 #f6f7fa);"
                    "color: red; font: bold;")
                if [-1,-1] not  in self.itemBasket:
                    self.itemButton[nitem][nbit].setText(str(len(self.itemBasket)))
                else:
                    index = self.itemBasket.index([-1,-1])
                    self.itemButton[nitem][nbit].setText("."+str(len(self.itemBasket[index:])-1))
                bit = QtWidgets.QPushButton(str(nitem + 1) + "." + str(nbit))

            self.itemBasket.append([nitem,nbit])

            bit.setFixedSize(QtCore.QSize(40, 40))
            bit.setStyleSheet("background-color:qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,stop: 0 #dadbde, stop: 1 #f6f7fa);")
            bit.clicked.connect(lambda *args, nitem=nitem, nbit = nbit: self.handleBitButtonClicked(nitem, nbit))
            self.itemRes.addWidget(bit,alignment=QtCore.Qt.AlignLeft)
            self.resButton.append(bit)
        else:
            if nitem is -1 and nbit is -1:
                self.buttonPoint.setStyleSheet("")
            else:
                self.itemButton[nitem][nbit].setStyleSheet("")
                self.itemButton[nitem][nbit].setText(str(nbit))
            index = self.itemBasket.index([nitem,nbit])
            self.itemBasket.remove([nitem, nbit])
            # ReIndex
            if [-1,-1] not in self.itemBasket:
                for _ in self.itemBasket[index:]:
                    self.itemButton[_[0]][_[1]].setText(str(self.itemBasket.index(_)))
            elif [-1,-1] not in self.itemBasket[index:]:
                _index = self.itemBasket.index([-1,-1])
                for _ in self.itemBasket[index:]:
                    self.itemButton[_[0]][_[1]].setText("."+str(len(self.itemBasket[_index:self.itemBasket.index(_)])-1))
            else:
                _index = self.itemBasket.index([-1, -1])
                for _ in self.itemBasket[index:_index]:
                    self.itemButton[_[0]][_[1]].setText(str(self.itemBasket.index(_)))

            self.itemRes.removeWidget(self.resButton[index])
            sip.delete(self.resButton[index])
            del self.resButton[index]


    @QtCore.pyqtSlot(int)
    def handleBitResetClicked(self,nitem):
        size = len(self.itemButton[nitem])
        for bit in range(len(self.itemButton[nitem])):
            if [nitem,bit] in self.itemBasket:
                self.handleBitButtonClicked(nitem,bit)

    @QtCore.pyqtSlot(int)
    def handleBitDeleteClicked(self,nitem):
        # reset
        self.handleBitResetClicked(nitem)
        # Clear itemForm
        #GarbageBin = self.itemForm.itemAt(nitem, QtWidgets.QFormLayout.FieldRole)
        self.itemForm.removeRow(nitem)

        # Clear itemButton
        del self.itemButton[nitem]
        del self.resetButton[nitem]
        del self.deleteButton[nitem]
        del self.labelList[nitem]
        del self.trueIndex[nitem]
        # Signal reAllocate Index reAllocate

        for itemList in self.itemButton[nitem:]:
            item = self.itemButton.index(itemList)
            self.resetButton[item].clicked.disconnect()
            self.resetButton[item].clicked.connect(lambda *args, nitem=item: self.handleBitResetClicked(nitem))
            self.deleteButton[item].clicked.disconnect()
            self.deleteButton[item].clicked.connect(lambda *args, nitem=item: self.handleBitDeleteClicked(nitem))
            _string = self.labelList[item].text()
            _ = _string.index(".")
            self.labelList[item].setText(str(item+1)+_string[_:])
            for bit in range(len(itemList)):
                itemList[bit].clicked.disconnect()
                itemList[bit].clicked.connect(lambda *args, nitem=item, nbit=bit: self.handleBitButtonClicked(nitem, nbit))
                if [item+1,bit] in self.itemBasket:
                    _ = self.itemBasket.index([item+1,bit])
                    self.itemBasket[_] = [item,bit]
                    self.resButton[_].setText(str(item+1)+"."+str(bit))

    def apply(self):
        #self.PickerCall.emit("FLL_INT[0:5]",10)
        pass

    def cancel(self):
        self.close()

    def resetAll(self):
        _itemBasket = self.itemBasket.copy()
        for _ in _itemBasket:
            self.handleBitButtonClicked(_[0], _[1])


    def backspace(self):
        if len(self.itemBasket) is not 0:
            _ = self.itemBasket[-1]
            self.handleBitButtonClicked(_[0], _[1])


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = Picker()
    w.show()
    sys.exit(app.exec_())



