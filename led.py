import sys
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import QtWidgets

allAttributes =   [  'colorOnBegin', 'colorOnEnd', 'colorOffBegin', 'colorOffEnd', 'colorBorderIn', 'colorBorderOut',
                     'radiusBorderOut', 'radiusBorderIn', 'radiusCircle']
allDefaultVal =   [ QColor(0, 240, 0), QColor(0, 160, 0), QColor(0, 68, 0), QColor(0, 28, 0), QColor(140, 140, 140), QColor(100, 100, 100),
                    500, 450, 400]

class MyLed(QtWidgets.QAbstractButton):
    def __init__(self, parent=None):
        super(MyLed, self).__init__(parent)
        self.initUI()

    def initUI(self):
        self.setMinimumSize(24, 24)
        self.setCheckable(True)
        self.scaledSize = 1000.0    #为方便计算，将窗口短边值映射为1000
        self.setLedDefaultOption()
        self.ConnFlag = False

    def setLedDefaultOption(self):
        for attr, val in zip(allAttributes, allDefaultVal):
            setattr(self, attr, val)
        self.update()

    def setLedOption(self, opt='colorOnBegin', val=QColor(0,240,0)):
        if hasattr(self, opt):
            setattr(self, opt, val)
            self.update()

    def resizeEvent(self, evt):
        self.update()

    def paintEvent(self, evt):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(Qt.black, 1))

        realSize = min(self.width(), self.height())                         #窗口的短边
        painter.translate(self.width()/2.0, self.height()/2.0)              #原点平移到窗口中心
        painter.scale(realSize/self.scaledSize, realSize/self.scaledSize)   #缩放，窗口的短边值映射为self.scaledSize
        gradient = QRadialGradient(QPointF(0, 0), self.scaledSize/2.0, QPointF(0, 0))

        for color, radius in [(self.colorBorderOut, self.radiusBorderOut),
                               (self.colorBorderIn, self.radiusBorderIn)]:
            gradient.setColorAt(1, color)
            painter.setBrush(QBrush(gradient))
            painter.drawEllipse(QPointF(0, 0), radius, radius)

        gradient.setColorAt(0, self.colorOnBegin if self.ConnFlag else self.colorOffBegin)
        gradient.setColorAt(1, self.colorOnEnd if self.ConnFlag else self.colorOffEnd)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(QPointF(0, 0), self.radiusCircle, self.radiusCircle)

