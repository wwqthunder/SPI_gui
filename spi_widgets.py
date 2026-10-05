"""Painted widgets of the register-array GUI: the tile grid, the bit map and bit strips.

Tiles are painted, not built from child widgets, so a chip with hundreds of
registers stays light.  Bits are clicked in place; a value is typed into a
single line edit that is placed over the clicked tile.
"""
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QPoint, QRect, QRectF, QSize, Qt

ACCENT = '#1D4E89'
ACCENT_SOFT = '#E3EAF4'
ORANGE = '#C8671F'
ORANGE_TEXT = '#A8480A'
ORANGE_SOFT = '#FAEBDD'
INK = '#1B1C1E'
INK2 = '#4F5257'
INK3 = '#5F6268'
LINE = '#DAD7CE'
LINE2 = '#CFCBC1'
CARD = '#FFFFFF'
RO_BG = '#F2F1EC'
ZERO = '#D3CFC5'
UNKNOWN = '#F7F6F2'
UNKNOWN_EDGE = '#C9C5BA'
DIFF = '#2E3A4A'
MONO = 'Consolas'
SANS = 'Segoe UI'

# Fonts come from QApplication.setFont / QWidget.setFont; a font rule on QWidget here would
# override every per-widget font (mono values, big numbers).
QSS = """
QWidget { color: #1B1C1E; }
QMainWindow, QWidget#Body { background: #ECEAE4; }
QFrame#Header { background: #1B1C1E; }
QFrame#Header QLabel { color: #F2F1EC; }
QFrame#Header QPushButton { color: #F2F1EC; background: transparent; border: 1px solid #55585E;
    border-radius: 6px; padding: 0 14px; min-height: 34px; }
QFrame#Header QPushButton:hover { background: #2E3035; }
QFrame#Header QPushButton:checked { background: #2E3035; border-color: #7FB2EC; }
QFrame#Header QPushButton#WriteBtn { background: #1D4E89; border: 0; font-weight: 600; min-width: 160px; }
QFrame#Header QPushButton#WriteBtn:disabled { background: #3A3D42; color: #9A9892; }
QFrame#SubBar { background: #F4F3EF; border-bottom: 1px solid #D8D5CC; }
QWidget#Rail { background: #F4F3EF; }
QWidget#Center { background: #FAF9F6; }
QWidget#Inspector { background: #FFFFFF; }
QFrame#Card { background: #FFFFFF; border: 1px solid #D8D5CC; border-radius: 6px; }
QFrame#Soft { background: #FAF9F6; border: 1px solid #DAD7CE; border-radius: 8px; }
QFrame#Pick { background: #FDF4EC; border: 1px solid #C8671F; border-radius: 8px; }
QFrame#Banner { background: #FAEBDD; border: 1px solid #E2B48F; border-radius: 6px; }
QFrame#Banner QLabel { color: #7A3A0C; }
QPushButton { background: #FFFFFF; border: 1px solid #CFCBC1; border-radius: 6px; padding: 0 12px; min-height: 30px; }
QPushButton:hover { border-color: #A9A59A; }
QPushButton:pressed { background: #ECEAE4; }
QPushButton:checked { background: #1D4E89; color: #FFFFFF; border-color: #1D4E89; }
QPushButton:disabled { color: #9A9892; background: #F4F3EF; border-color: #DAD7CE; }
QPushButton[primary="true"] { background: #1D4E89; color: #FFFFFF; border-color: #1D4E89; font-weight: 600; }
QPushButton[primary="true"]:disabled { background: #E6E3DB; color: #5F6268; border-color: #E6E3DB; }
QPushButton[danger="true"] { color: #A8480A; }
QPushButton[flat="true"] { border: 0; background: transparent; text-align: left; padding: 0 6px; }
QPushButton[flat="true"]:hover { background: #ECEAE4; }
QPushButton[chipTab="true"] { font-family: Consolas; font-weight: 600; min-width: 64px; }
QPushButton[step="true"] { padding: 0; min-height: 0; font-size: 11pt; }
QLineEdit { background: #FFFFFF; border: 1px solid #CFCBC1; border-radius: 6px; padding: 2px 8px; min-height: 24px;
    selection-background-color: #1D4E89; }
QLineEdit:hover { border-color: #A9A59A; }
QLineEdit:focus { border-color: #1D4E89; }
QLineEdit:disabled { background: #F4F3EF; color: #9A9892; border-color: #DAD7CE; }
QLineEdit[bad="true"] { border-color: #A8480A; color: #A8480A; }
QLineEdit[mono="true"] { font-family: Consolas; }

QComboBox { background: #FFFFFF; border: 1px solid #CFCBC1; border-radius: 6px; padding: 3px 26px 3px 10px;
    min-height: 24px; }
QComboBox:hover { border-color: #A9A59A; }
QComboBox:focus, QComboBox:on { border-color: #1D4E89; }
QComboBox:disabled { background: #F4F3EF; color: #9A9892; border-color: #DAD7CE; }
QComboBox::drop-down { border: 0; width: 24px; subcontrol-origin: padding; subcontrol-position: center right; }
QComboBox::down-arrow { image: none; width: 0; height: 0; }
QComboBox QAbstractItemView { background: #FFFFFF; border: 1px solid #CFCBC1; padding: 4px; outline: 0;
    selection-background-color: #E3EAF4; selection-color: #1D4E89; }
QComboBox QAbstractItemView::item { min-height: 26px; padding: 0 8px; border-radius: 4px; }
QComboBox QAbstractItemView::item:hover { background: #ECEAE4; }

QSlider { min-height: 26px; }
QSlider::groove:horizontal { height: 6px; background: #E6E3DB; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #1D4E89; border-radius: 3px; }
QSlider::add-page:horizontal { background: #E6E3DB; border-radius: 3px; }
QSlider::handle:horizontal { background: #FFFFFF; border: 2px solid #1D4E89; width: 16px; height: 16px;
    margin: -7px 0; border-radius: 10px; }
QSlider::handle:horizontal:hover { background: #E3EAF4; }
QSlider::sub-page:horizontal:disabled { background: #B9B7B0; }
QSlider::handle:horizontal:disabled { border-color: #B9B7B0; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #CFCBC1; border-radius: 3px; min-height: 32px; margin: 2px; }
QScrollBar::handle:horizontal { background: #CFCBC1; border-radius: 3px; min-width: 32px; margin: 2px; }
QScrollBar::handle:hover { background: #A9A59A; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; border: 0; background: none; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }

QMenu { background: #FFFFFF; border: 1px solid #CFCBC1; padding: 4px; }
QMenu::item { padding: 6px 28px 6px 12px; border-radius: 4px; }
QMenu::item:selected { background: #E3EAF4; color: #1D4E89; }
QMenu::item:disabled { color: #9A9892; }
QMenu::separator { height: 1px; background: #E6E3DB; margin: 4px 6px; }
QToolButton#FileBtn { background: #FFFFFF; border: 1px solid #CFCBC1; border-radius: 6px; padding: 4px 12px; }
QToolButton#FileBtn:hover { border-color: #A9A59A; }
QToolButton#FileBtn::menu-indicator { image: none; width: 0; }

QLabel#Eyebrow { font-size: 8pt; font-weight: 600; color: #4F5257; }
QLabel#Muted { color: #5F6268; }
QLabel#Title { font-size: 15pt; font-weight: 600; }
QTreeWidget, QListWidget { background: transparent; border: 0; outline: 0; }
QTreeWidget::item, QListWidget::item { padding: 4px 2px; border-radius: 4px; }
QTreeWidget::item:hover, QListWidget::item:hover { background: #ECEAE4; }
QTreeWidget::item:selected, QListWidget::item:selected,
QTreeWidget::item:selected:!active, QListWidget::item:selected:!active { background: #E3EAF4; color: #1D4E89; }
QScrollArea { border: 0; background: transparent; }
QStatusBar { background: #F4F3EF; border-top: 1px solid #D8D5CC; }
QToolTip { background: #1B1C1E; color: #F2F1EC; border: 0; padding: 4px 6px; }
QMessageBox { background: #FFFFFF; }
"""


def mono(pt, bold=False):
    f = QtGui.QFont(MONO)
    f.setPointSizeF(pt)
    f.setBold(bold)
    return f


def sans(pt, weight=QtGui.QFont.Normal):
    f = QtGui.QFont(SANS)
    f.setPointSizeF(pt)
    f.setWeight(weight)
    return f


def set_prop(widget, name, value):
    """Change a dynamic property used by the style sheet and re-apply the style."""
    if widget.property(name) != value:
        widget.setProperty(name, value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)


def dot_icon(on, color=ACCENT, size=10):
    pm = QtGui.QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    p.setPen(QtGui.QPen(QtGui.QColor(color if on else '#8A8C90'), 1.5))
    p.setBrush(QtGui.QColor(color) if on else Qt.NoBrush)
    p.drawEllipse(QRectF(1, 1, size - 2, size - 2))
    p.end()
    return QtGui.QIcon(pm)


class FlowLayout(QtWidgets.QLayout):
    """Lays child widgets out left to right, wrapping at the right edge."""

    def __init__(self, parent=None, spacing=4):
        super().__init__(parent)
        self._items = []
        self.setSpacing(spacing)
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _do_layout(self, rect, test):
        x, y, line_h = rect.x(), rect.y(), 0
        sp = self.spacing()
        for item in self._items:
            hint = item.sizeHint()
            if x + hint.width() > rect.right() + 1 and line_h > 0:
                x, y, line_h = rect.x(), y + line_h + sp, 0
            if not test:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + sp
            line_h = max(line_h, hint.height())
        return y + line_h - rect.y()

    def clear(self):
        while self._items:
            item = self._items.pop()
            if item.widget() is not None:
                item.widget().deleteLater()


def _bit_gaps(reg, shown, small, big):
    """Gap after each shown bit: wider where one field ends and the next begins."""
    gaps = []
    for n, b in enumerate(shown):
        if n == len(shown) - 1:
            gaps.append(0)
        else:
            nxt = shown[n + 1]
            gaps.append(big if reg.fields and reg.field_at(b) is not reg.field_at(nxt) else small)
    return gaps


class TileGrid(QtWidgets.QWidget):
    """Every register of the current chip as a tile; click a bit to flip it, click the value to type.

    Sizes scale with self.k (Ctrl + wheel, or the zoom buttons above the grid).
    """
    MIN_K, MAX_K = 0.6, 1.8
    scaleChanged = QtCore.pyqtSignal(float)

    def __init__(self, session, run, scale=1.0, parent=None):
        super().__init__(parent)
        self.s = session
        self.run = run
        self.geo = []
        self.hover = None
        self.edit_i = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.editor = QtWidgets.QLineEdit(self)
        self.editor.setProperty('mono', True)
        self.editor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.editor.setToolTip('Decimal, 0x… or 0b… · Enter to apply, Esc to cancel')
        self.editor.hide()
        self.editor.installEventFilter(self)
        self._committing = False
        self.k = max(self.MIN_K, min(self.MAX_K, float(scale)))
        self._size()

    # -- size
    def _size(self):
        k = self.k
        px = lambda v, lo=1: max(lo, int(round(v * k)))
        self.pad, self.gap = px(5), px(6)
        self.head_h, self.name_h, self.bits_h = px(18), px(15), px(16)
        self.sp1, self.sp2 = px(3), px(5)
        self.tile_h = 2 * self.pad + self.head_h + self.sp1 + self.name_h + self.sp2 + self.bits_h
        self.cell_wide, self.cell_narrow = px(12, 3), px(18, 4)
        self.gap_in, self.gap_field = px(2), px(4, 2)
        self.inner_wide = 10 * self.cell_wide + 9 * self.gap_in          # a 10-bit DAC field fits exactly
        self.inner_narrow = 5 * self.cell_narrow + 4 * self.gap_field    # so do five 1-bit fields
        self.val_wide, self.val_narrow = px(48), px(36)
        self.f_addr = mono(8 * k)
        self.f_val = mono(10.5 * k, True)
        self.f_name = mono(8.5 * k)
        self.f_mark = sans(9 * k, QtGui.QFont.Bold)
        self.editor.setFont(mono(10 * k))

    def set_scale(self, k):
        k = max(self.MIN_K, min(self.MAX_K, round(k, 2)))
        if abs(k - self.k) < 1e-6:
            return
        self.k = k
        self._size()
        self.relayout()
        if self.s.sel[0] == 'reg':
            self.ensure_visible(self.s.sel[1])
        self.scaleChanged.emit(k)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            self.set_scale(self.k + (0.1 if e.angleDelta().y() > 0 else -0.1))
            e.accept()
        else:
            super().wheelEvent(e)

    # -- layout
    def relayout(self):
        self.close_editor()
        regs = self.s.profile.registers if self.s.profile else []
        width = max(self.width(), self.inner_wide + 2 * self.pad)
        x = y = 0
        self.geo = []
        for reg in regs:
            tw = (self.inner_wide if reg.width > 5 else self.inner_narrow) + 2 * self.pad
            if x and x + tw > width:
                x, y = 0, y + self.tile_h + self.gap
            self.geo.append(self._tile_geo(QRect(x, y, tw, self.tile_h), reg))
            x += tw + self.gap
        h = y + self.tile_h if regs else 0
        if self.minimumHeight() != h:
            self.setMinimumHeight(h)
        self.update()

    def _tile_geo(self, rect, reg):
        wide = reg.width > 5
        inner = rect.adjusted(self.pad, self.pad, -self.pad, -self.pad)
        val_w = self.val_wide if wide else self.val_narrow
        top = inner.top()
        value = QRect(inner.right() - val_w + 1, top, val_w, self.head_h)
        head = QRect(inner.left(), top, inner.width() - val_w - 2, self.head_h)
        name_top = top + self.head_h + self.sp1
        name = QRect(inner.left(), name_top, inner.width(), self.name_h)
        bits_top = name_top + self.name_h + self.sp2
        shown = reg.shown_bits()
        gaps = _bit_gaps(reg, shown, self.gap_in, self.gap_field)
        room = inner.width() - sum(gaps)
        cw = max(3, min(self.cell_wide if wide else self.cell_narrow, room // max(1, len(shown))))
        bits, x = [], inner.left()
        for b, gap in zip(shown, gaps):
            bits.append((b, QRect(x, bits_top, cw, self.bits_h)))
            x += cw + gap
        return {'rect': rect, 'value': value, 'head': head, 'name': name, 'bits': bits}

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if e.oldSize().width() != e.size().width():
            self.relayout()

    # -- painting
    def paintEvent(self, ev):
        s = self.s
        if not s.profile:
            return
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        k = s.chip
        online = s.online(k)
        sel_i = s.sel[1] if s.sel[0] == 'reg' else None
        hl = set()
        if s.sel[0] == 'watch' and s.sel[1] < len(s.profile.watches):
            hl = {a for a, _b in s.profile.watches[s.sel[1]].bits}
        picked = {x: lab for lab, x in s.pick_labels() if x is not None}
        clip = ev.rect()
        for i, g in enumerate(self.geo):
            if g['rect'].intersects(clip):
                self._paint_tile(p, i, g, k, online, i == sel_i, s.reg(i).addr in hl, picked)
        p.end()

    def _paint_tile(self, p, i, g, k, online, sel, hil, picked):
        s = self.s
        reg = s.reg(i)
        v = s.val[k][i]
        unknown = v is None
        pend = s.pending(k, i)
        bg = ACCENT_SOFT if sel else ORANGE_SOFT if pend else RO_BG if (reg.ro or not online) else CARD
        border = ACCENT if (sel or hil) else ORANGE if pend else LINE
        r = QRectF(g['rect']).adjusted(1, 1, -1, -1)
        p.setPen(QtGui.QPen(QtGui.QColor(border), 2 if sel else 1))
        p.setBrush(QtGui.QColor(bg))
        p.drawRoundedRect(r, 6, 6)
        # address and markers
        z = self.k
        head = g['head']
        p.setFont(self.f_addr)
        p.setPen(QtGui.QColor(INK3))
        text = 'A%d' % reg.addr
        p.drawText(head, Qt.AlignLeft | Qt.AlignVCenter, text)
        x = head.left() + QtGui.QFontMetrics(self.f_addr).horizontalAdvance(text) + 5 * z
        cy = head.center().y() + 1
        if s.differs(i):
            p.setFont(self.f_mark)
            p.setPen(QtGui.QColor(DIFF))
            p.drawText(QRectF(x, head.top(), 12 * z, head.height()), Qt.AlignLeft | Qt.AlignVCenter, '≠')
            x += 12 * z
        if pend:
            p.setPen(Qt.NoPen)
            p.setBrush(QtGui.QColor(ORANGE))
            p.drawEllipse(QRectF(x, cy - 3.5 * z, 7 * z, 7 * z))
            x += 11 * z
        if reg.ro:
            p.setPen(QtGui.QPen(QtGui.QColor(INK2), 1.2))
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(x + 0.5, cy - 1 * z, 8 * z, 6 * z))
            p.drawArc(QRectF(x + 1.5 * z, cy - 6 * z, 6 * z, 7 * z), 0, 180 * 16)
        # value, with a dashed underline that says "type here"
        value = g['value']
        text = '—' if unknown else str(v)
        p.setFont(self.f_val)
        p.setPen(QtGui.QColor(INK3 if unknown else INK))
        p.drawText(value, Qt.AlignRight | Qt.AlignVCenter, text)
        if not reg.ro:
            tw = QtGui.QFontMetrics(self.f_val).horizontalAdvance(text)
            pen = QtGui.QPen(QtGui.QColor(ORANGE if pend else '#BDB8AC'), 1, Qt.DashLine)
            p.setPen(pen)
            p.drawLine(value.right() - tw, value.bottom(), value.right(), value.bottom())
        # name
        nm = reg.title()
        p.setFont(self.f_name)
        p.setPen(QtGui.QColor(INK if nm else INK3))
        fm = QtGui.QFontMetrics(self.f_name)
        p.drawText(g['name'], Qt.AlignLeft | Qt.AlignVCenter, fm.elidedText(nm or '—', Qt.ElideRight, g['name'].width()))
        # bits
        for b, br in g['bits']:
            on = not unknown and (v >> b) & 1
            rf = QRectF(br)
            if (reg.addr, b) in picked:
                p.setPen(Qt.NoPen)
                p.setBrush(QtGui.QColor(ORANGE))
            elif unknown:
                p.setPen(QtGui.QPen(QtGui.QColor(UNKNOWN_EDGE), 1))
                p.setBrush(QtGui.QColor(UNKNOWN))
                rf = rf.adjusted(0.5, 0.5, -0.5, -0.5)
            else:
                p.setPen(Qt.NoPen)
                p.setBrush(QtGui.QColor(ACCENT if on else ZERO))
            p.drawRoundedRect(rf, 2 * z, 2 * z)
            if self.hover == (i, b):
                p.setPen(QtGui.QPen(QtGui.QColor(INK), 1.2))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(QRectF(br).adjusted(-1.5, -1.5, 1.5, 1.5), 3 * z, 3 * z)

    # -- interaction
    def hit(self, pos):
        for i, g in enumerate(self.geo):
            if g['rect'].contains(pos):
                for b, br in g['bits']:
                    if br.adjusted(-1, -3, 1, 3).contains(pos):
                        return i, 'bit', b
                if g['value'].adjusted(-6, -2, 2, 3).contains(pos):
                    return i, 'value', None
                return i, 'tile', None
        return None, None, None

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        i, part, b = self.hit(e.pos())
        if i is None:
            return
        self.setFocus()
        s = self.s
        reg = s.reg(i)
        if part == 'bit':
            if s.pick is not None:
                s.pick_bit(reg.addr, b)
            elif not reg.ro:
                self.run(s.toggle_bit, i, b)
            s.select_reg(i)
        else:
            s.select_reg(i)
            if part == 'value' and not reg.ro:
                self.open_editor(i)

    def mouseDoubleClickEvent(self, e):
        i, part, _b = self.hit(e.pos())
        if i is not None and part == 'tile' and not self.s.reg(i).ro:
            self.open_editor(i)

    def mouseMoveEvent(self, e):
        i, part, b = self.hit(e.pos())
        new = (i, b) if part == 'bit' else None
        if new != self.hover:
            self.hover = new
            self.update()
        self.setCursor(Qt.PointingHandCursor if part in ('bit', 'value') else Qt.ArrowCursor)

    def leaveEvent(self, e):
        if self.hover is not None:
            self.hover = None
            self.update()

    def event(self, e):
        if e.type() == QtCore.QEvent.ToolTip:
            text = self.tip(e.pos())
            if text:
                QtWidgets.QToolTip.showText(e.globalPos(), text, self)
            else:
                QtWidgets.QToolTip.hideText()
                e.ignore()
            return True
        return super().event(e)

    def tip(self, pos):
        i, part, b = self.hit(pos)
        if i is None:
            return ''
        s = self.s
        reg = s.reg(i)
        v = s.val[s.chip][i]
        if part == 'bit':
            text = 'A%d bit %d' % (reg.addr, b)
            if reg.bit_name(b):
                text += ' · ' + reg.bit_name(b)
            if v is not None:
                text += ' = %d' % ((v >> b) & 1)
            lab = dict((x, l) for l, x in s.pick_labels()).get((reg.addr, b))
            return text + (' · picked as %s' % lab if lab is not None else '')
        text = 'A%d %s' % (reg.addr, reg.title())
        if v is None:
            return text + ' · not read yet'
        text += ' · %d · 0x%X' % (v, v)
        sf = reg.scaled_field()
        if sf is not None:
            text += ' · %.3f V' % sf.volts((v >> sf.lo) & sf.full)
        if part == 'value' and not reg.ro:
            text += '\nClick to type a value'
        return text

    def keyPressEvent(self, e):
        s = self.s
        if not self.geo:
            return super().keyPressEvent(e)
        i = s.sel[1] if s.sel[0] == 'reg' else 0
        key = e.key()
        if key in (Qt.Key_Left, Qt.Key_Right):
            s.select_reg(max(0, min(len(self.geo) - 1, i + (1 if key == Qt.Key_Right else -1))))
        elif key in (Qt.Key_Up, Qt.Key_Down):
            here = self.geo[i]['rect']
            want = here.top() + (self.tile_h + self.gap) * (1 if key == Qt.Key_Down else -1)
            row = [(abs(g['rect'].center().x() - here.center().x()), n) for n, g in enumerate(self.geo)
                   if g['rect'].top() == want]
            if row:
                s.select_reg(min(row)[1])
        elif key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_F2) and not s.reg(i).ro:
            self.open_editor(i)
        else:
            return super().keyPressEvent(e)
        self.ensure_visible(s.sel[1] if s.sel[0] == 'reg' else 0)

    def ensure_visible(self, i):
        area = self.parent().parent() if self.parent() else None
        if isinstance(area, QtWidgets.QScrollArea) and 0 <= i < len(self.geo):
            r = self.geo[i]['rect']
            area.ensureVisible(r.center().x(), r.center().y(), r.width() // 2 + 8, r.height() // 2 + 8)

    # -- value editor
    def open_editor(self, i):
        g = self.geo[i]
        r = g['value'].adjusted(-6, -2, 3, 3)
        min_w = int(64 * self.k)
        if r.width() < min_w:
            r.setLeft(r.right() - min_w)
        v = self.s.val[self.s.chip][i]
        self.edit_i = i
        set_prop(self.editor, 'bad', False)
        self.editor.setGeometry(r)
        self.editor.setText('' if v is None else str(v))
        self.editor.show()
        self.editor.raise_()
        self.editor.setFocus()
        self.editor.selectAll()

    def close_editor(self):
        self.edit_i = None
        if self.editor.isVisible():
            self.editor.hide()

    def _commit(self, focus_out=False):
        i = self.edit_i
        if i is None or self._committing:
            return
        self._committing = True             # an error dialog takes focus; don't commit twice
        try:
            err = self.run(self.s.type_value, i, self.editor.text())
        finally:
            self._committing = False
        if err and not focus_out:
            set_prop(self.editor, 'bad', True)          # stay open until fixed or Esc
            return
        self.close_editor()
        if not focus_out:
            self.setFocus()

    def eventFilter(self, obj, e):
        if obj is self.editor:
            if e.type() == QtCore.QEvent.KeyPress:
                if e.key() in (Qt.Key_Return, Qt.Key_Enter):
                    self._commit()
                    return True             # keep Return from reaching the grid and reopening
                if e.key() == Qt.Key_Escape:
                    self.close_editor()
                    self.setFocus()
                    return True
            elif e.type() == QtCore.QEvent.FocusOut and self.edit_i is not None:
                self._commit(focus_out=True)
        return super().eventFilter(obj, e)


class BitsMap(QtWidgets.QWidget):
    """Every register of every chip side by side, one square per bit (overview)."""
    ROW, CELL, CHIP_GAP, LABEL_W, HEAD_H, JUMP = 7, 6, 16, 44, 34, 6

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.s = session
        self.rows = []              # (i, y)
        self.setMouseTracking(True)
        self.f_head = mono(8, True)
        self.f_note = sans(7.5)
        self.f_lab = mono(6.5)

    def relayout(self):
        self.rows = []
        y = self.HEAD_H
        regs = self.s.profile.registers if self.s.profile else []
        for i, reg in enumerate(regs):
            if i and reg.addr - regs[i - 1].addr > 1:
                y += self.JUMP
            self.rows.append((i, y))
            y += self.ROW
        self.setMinimumHeight(y + 36)
        chips = len(self.s.profile.chips) if self.s.profile else 1
        self.setMinimumWidth(self.LABEL_W + chips * (13 * self.ROW + self.CHIP_GAP) + 40)
        self.update()

    def _chip_x(self, k):
        return self.LABEL_W + k * (13 * self.ROW - 1 + self.CHIP_GAP)

    def paintEvent(self, ev):
        s = self.s
        if not s.profile:
            return
        p = QtGui.QPainter(self)
        sel_i = s.sel[1] if s.sel[0] == 'reg' else None
        hl = set()
        if s.sel[0] == 'watch' and s.sel[1] < len(s.profile.watches):
            hl = {a for a, _b in s.profile.watches[s.sel[1]].bits}
        for k, chip in enumerate(s.profile.chips):
            x = self._chip_x(k)
            link = s.chip_link(k)
            p.setFont(self.f_head)
            p.setPen(QtGui.QColor(INK))
            p.drawText(QRect(x, 2, 110, 14), Qt.AlignLeft | Qt.AlignVCenter,
                       '%s · %s' % (chip.label, link.short if link else '?'))
            p.setFont(self.f_note)
            p.setPen(QtGui.QColor(INK3 if s.online(k) else ORANGE_TEXT))
            p.drawText(QRect(x, 16, 110, 12), Qt.AlignLeft | Qt.AlignVCenter, 'online' if s.online(k) else 'offline')
        regs = s.profile.registers
        for n, (i, y) in enumerate(self.rows):
            reg = regs[i]
            if i == sel_i or reg.addr in hl:
                p.fillRect(QRect(0, y - 1, self.width(), self.ROW), QtGui.QColor('#CCDAEC' if i == sel_i else ACCENT_SOFT))
            jump = n and reg.addr - regs[self.rows[n - 1][0]].addr > 1
            if n == 0 or jump or reg.addr % 8 == 0:
                p.setFont(self.f_lab)
                p.setPen(QtGui.QColor(INK2))
                p.drawText(QRect(0, y - 3, self.LABEL_W - 4, 12), Qt.AlignRight | Qt.AlignVCenter, 'A%d' % reg.addr)
            for k in range(len(s.profile.chips)):
                v = s.val[k][i]
                dim = not s.online(k)
                x0 = self._chip_x(k)
                for b in range(12, -1, -1):
                    if b >= reg.width:
                        continue
                    x = x0 + (12 - b) * self.ROW
                    if not reg.used(b):
                        color = '#E9E7E1'
                    elif v is None:
                        color = '#F1EFEA'
                    elif (v >> b) & 1:
                        color = '#A9BCD6' if dim else ACCENT
                    else:
                        color = '#E4E1D9' if dim else ZERO
                    p.fillRect(QRect(x, y, self.CELL, self.CELL), QtGui.QColor(color))
            if s.differs(i):
                p.setFont(self.f_head)
                p.setPen(QtGui.QColor(DIFF))
                p.drawText(QRect(self._chip_x(len(s.profile.chips)) - 8, y - 4, 14, 14), Qt.AlignCenter, '≠')
        p.setFont(self.f_note)
        p.setPen(QtGui.QColor(INK2))
        y = (self.rows[-1][1] + 20) if self.rows else self.HEAD_H
        p.drawText(QRect(0, y, self.width(), 16), Qt.AlignLeft | Qt.AlignVCenter,
                   'One row per register, one square per bit, most significant bit on the left. '
                   'Click a row to open it; edit in Tiles.')
        p.end()

    def row_at(self, pos):
        for i, y in self.rows:
            if y - 1 <= pos.y() < y + self.ROW:
                return i
        return None

    def mousePressEvent(self, e):
        i = self.row_at(e.pos())
        if i is not None:
            self.s.select_reg(i)

    def event(self, e):
        if e.type() == QtCore.QEvent.ToolTip:
            i = self.row_at(e.pos())
            if i is None:
                QtWidgets.QToolTip.hideText()
                return True
            s = self.s
            reg = s.reg(i)
            parts = ['A%d %s' % (reg.addr, reg.title())]
            for k, chip in enumerate(s.profile.chips):
                v = s.val[k][i]
                parts.append('%s %s' % (chip.label, '—' if v is None else v))
            QtWidgets.QToolTip.showText(e.globalPos(), ' · '.join(parts), self)
            return True
        return super().event(e)


class BitStrip(QtWidgets.QWidget):
    """A row of large bit buttons with a small label under each; wraps when narrow.

    items: dicts with kind 'bit' or 'point', text, sub, bg, fg, bd, tip, gap, enabled.
    """
    clicked = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.box_w, self.box_h = 20, 30
        self.rects = []
        sp = self.sizePolicy()
        sp.setHeightForWidth(True)
        self.setSizePolicy(sp)
        self.setMouseTracking(True)
        self.f_bit = mono(8.5, True)
        self.f_small = mono(7.5, True)
        self.f_sub = mono(6.5)

    def set_items(self, items, box_w):
        self.items, self.box_w = items, box_w
        self._place(self.width())
        self.updateGeometry()
        self.update()

    def _place(self, width):
        self.rects = []
        x, y = 0, 0
        line = self.box_h + 16
        width = max(width, self.box_w + 4)
        for it in self.items:
            w = 10 if it['kind'] == 'point' else self.box_w
            if x and x + w > width:
                x, y = 0, y + line
            self.rects.append(QRect(x, y, w, self.box_h))
            x += w + it.get('gap', 2)
        return (y + line) if self.items else 0

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        return self._place(w)

    def sizeHint(self):
        return QSize(280, self._place(self.width() if self.width() > 50 else 280))

    def resizeEvent(self, e):
        self._place(self.width())
        super().resizeEvent(e)

    def paintEvent(self, ev):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        for it, r in zip(self.items, self.rects):
            if it['kind'] == 'point':
                p.setFont(sans(16, QtGui.QFont.Bold))
                p.setPen(QtGui.QColor(ORANGE_TEXT))
                p.drawText(r.adjusted(0, 4, 0, 4), Qt.AlignCenter, '.')
                continue
            p.setPen(QtGui.QPen(QtGui.QColor(it['bd']), 1))
            p.setBrush(QtGui.QColor(it['bg']))
            p.drawRoundedRect(QRectF(r).adjusted(0.5, 0.5, -0.5, -0.5), 4, 4)
            p.setFont(self.f_small if len(it['text']) > 2 else self.f_bit)
            p.setPen(QtGui.QColor(it['fg']))
            p.drawText(r, Qt.AlignCenter, it['text'])
            if it.get('sub'):
                p.setFont(self.f_sub)
                p.setPen(QtGui.QColor(INK3))
                p.drawText(QRect(r.left() - 6, r.bottom() + 2, r.width() + 12, 12), Qt.AlignHCenter | Qt.AlignTop, it['sub'])
        p.end()

    def _at(self, pos):
        for n, r in enumerate(self.rects):
            if r.contains(pos) and self.items[n]['kind'] == 'bit':
                return n
        return None

    def mousePressEvent(self, e):
        n = self._at(e.pos())
        if n is not None and self.items[n].get('enabled', True):
            self.clicked.emit(n)

    def mouseMoveEvent(self, e):
        n = self._at(e.pos())
        ok = n is not None and self.items[n].get('enabled', True)
        self.setCursor(Qt.PointingHandCursor if ok else Qt.ArrowCursor)

    def event(self, e):
        if e.type() == QtCore.QEvent.ToolTip:
            n = self._at(e.pos())
            if n is not None and self.items[n].get('tip'):
                QtWidgets.QToolTip.showText(e.globalPos(), self.items[n]['tip'], self)
            else:
                QtWidgets.QToolTip.hideText()
            return True
        return super().event(e)


class LinksButton(QtWidgets.QAbstractButton):
    """Header chip listing every link with a connection dot."""

    def __init__(self, links, parent=None):
        super().__init__(parent)
        self.links = links
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.f = sans(9, QtGui.QFont.DemiBold)

    def sizeHint(self):
        fm = QtGui.QFontMetrics(self.f)
        w = 24 + sum(14 + fm.horizontalAdvance(l.name) + 14 for l in self.links.all()) + 14
        return QSize(w, 36)

    def paintEvent(self, ev):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QtGui.QPen(QtGui.QColor('#7FB2EC' if self.isChecked() else '#55585E'), 1))
        p.setBrush(QtGui.QColor('#2E3035' if (self.isChecked() or self.underMouse()) else '#1B1C1E'))
        p.drawRoundedRect(r, 6, 6)
        p.setFont(self.f)
        fm = QtGui.QFontMetrics(self.f)
        x = 12
        cy = self.height() / 2.0
        for link in self.links.all():
            on = link.connected
            p.setPen(QtGui.QPen(QtGui.QColor('#7FB2EC' if on else '#8A8C90'), 1.5))
            p.setBrush(QtGui.QColor('#7FB2EC') if on else Qt.NoBrush)
            p.drawEllipse(QRectF(x, cy - 4, 8, 8))
            x += 14
            p.setPen(QtGui.QColor('#F2F1EC' if on else '#9A9892'))
            tw = fm.horizontalAdvance(link.name)
            p.drawText(QRect(int(x), 0, tw + 2, self.height()), Qt.AlignLeft | Qt.AlignVCenter, link.name)
            x += tw + 14
        p.setPen(QtGui.QPen(QtGui.QColor('#B9B7B0'), 1.5))
        p.drawPolyline(QtGui.QPolygonF([QtCore.QPointF(x, cy - 2), QtCore.QPointF(x + 4, cy + 2),
                                        QtCore.QPointF(x + 8, cy - 2)]))
        p.end()

    def enterEvent(self, e):
        self.update()

    def leaveEvent(self, e):
        self.update()


# ---------------------------------------------------------------- controls in the app's style

def _chevron(p, cx, cy, color, size=4.0):
    p.setPen(QtGui.QPen(QtGui.QColor(color), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawPolyline(QtGui.QPolygonF([QtCore.QPointF(cx - size, cy - size / 2), QtCore.QPointF(cx, cy + size / 2),
                                    QtCore.QPointF(cx + size, cy - size / 2)]))


class Combo(QtWidgets.QComboBox):
    """Combo box in the app's style: frame and popup from the style sheet, arrow painted here."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setItemDelegate(QtWidgets.QStyledItemDelegate(self))    # lets the style sheet size popup rows

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        _chevron(p, self.width() - 14, self.height() / 2.0, INK2 if self.isEnabled() else '#B9B7B0')
        p.end()


class Switch(QtWidgets.QAbstractButton):
    """Toggle switch in place of a check box; optional text on the right."""
    TW, TH = 36, 20

    def __init__(self, text='', parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setText(text)
        self.setCursor(Qt.PointingHandCursor)
        self.f = sans(9)

    def sizeHint(self):
        tw = QtGui.QFontMetrics(self.f).horizontalAdvance(self.text()) + 10 if self.text() else 0
        return QSize(self.TW + 2 + tw, max(self.TH + 4, 24))

    def minimumSizeHint(self):
        return self.sizeHint()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        on, en = self.isChecked(), self.isEnabled()
        top = (self.height() - self.TH) / 2.0
        track = QRectF(1, top, self.TW, self.TH)
        if en:
            color = ACCENT if on else '#A9A59A'
        else:
            color = '#A9BCD6' if on else '#DAD7CE'
        p.setPen(Qt.NoPen)
        p.setBrush(QtGui.QColor(color))
        p.drawRoundedRect(track, self.TH / 2.0, self.TH / 2.0)
        d = self.TH - 4
        p.setBrush(QtGui.QColor('#FFFFFF'))
        p.drawEllipse(QRectF(track.right() - d - 2 if on else track.left() + 2, top + 2, d, d))
        if self.hasFocus():
            p.setPen(QtGui.QPen(QtGui.QColor(ACCENT), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(track.adjusted(-1, -1, 1, 1), self.TH / 2.0 + 1, self.TH / 2.0 + 1)
        if self.text():
            p.setFont(self.f)
            p.setPen(QtGui.QColor(INK if en else '#9A9892'))
            p.drawText(QRect(self.TW + 10, 0, self.width() - self.TW - 10, self.height()),
                       Qt.AlignLeft | Qt.AlignVCenter, self.text())
        p.end()


class Stepper(QtWidgets.QWidget):
    """[−] value [+] in place of a spin box; the value can also be typed (decimal, 0x…, 0b…)."""
    valueChanged = QtCore.pyqtSignal(int)

    def __init__(self, maximum=255, parent=None):
        super().__init__(parent)
        self._max = maximum
        self._value = 0
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.minus = QtWidgets.QPushButton('−')
        self.plus = QtWidgets.QPushButton('+')
        for b, d in ((self.minus, -1), (self.plus, 1)):
            b.setProperty('step', True)
            b.setFixedSize(28, 28)
            b.setAutoRepeat(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _c=False, d=d: self._set(self._value + d))
        self.edit = QtWidgets.QLineEdit('0')
        self.edit.setFont(mono(9))
        self.edit.setAlignment(Qt.AlignCenter)
        self.edit.setFixedWidth(56)
        self.edit.editingFinished.connect(self._typed)
        lay.addWidget(self.minus)
        lay.addWidget(self.edit)
        lay.addWidget(self.plus)

    def setMaximum(self, maximum):
        self._max = maximum

    def value(self):
        return self._value

    def setValue(self, v):
        """Show a value without emitting valueChanged."""
        self._value = max(0, min(self._max, int(v)))
        if not self.edit.hasFocus():
            self.edit.setText(str(self._value))

    def _set(self, v):
        v = max(0, min(self._max, int(v)))
        if v != self._value:
            self._value = v
            self.edit.setText(str(v))
            self.valueChanged.emit(v)

    def _typed(self):
        from spi_model import parse_value
        v, err = parse_value(self.edit.text(), self._max)
        if v is None:
            set_prop(self.edit, 'bad', bool(err))
            if not err:
                self.edit.setText(str(self._value))
            return
        set_prop(self.edit, 'bad', False)
        self._set(v)


class AutoWriteButton(QtWidgets.QAbstractButton):
    """Header toggle: a switch, 'Auto-write' and the current state."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip('Write every change immediately')
        self.f = sans(9, QtGui.QFont.DemiBold)
        self.f_state = mono(8.5)

    def sizeHint(self):
        fm = QtGui.QFontMetrics(self.f)
        return QSize(12 + 36 + 10 + fm.horizontalAdvance('Auto-write') + 8 + 26 + 12, 36)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        on = self.isChecked()
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QtGui.QPen(QtGui.QColor('#55585E'), 1))
        p.setBrush(QtGui.QColor('#2E3035' if self.underMouse() else '#1B1C1E'))
        p.drawRoundedRect(r, 6, 6)
        cy = self.height() / 2.0
        track = QRectF(12, cy - 10, 36, 20)
        p.setPen(Qt.NoPen)
        p.setBrush(QtGui.QColor(ACCENT if on else '#55585E'))
        p.drawRoundedRect(track, 10, 10)
        p.setBrush(QtGui.QColor('#FFFFFF'))
        p.drawEllipse(QRectF(track.right() - 18 if on else track.left() + 2, cy - 8, 16, 16))
        p.setFont(self.f)
        p.setPen(QtGui.QColor('#F2F1EC'))
        fm = QtGui.QFontMetrics(self.f)
        x = int(track.right()) + 10
        p.drawText(QRect(x, 0, fm.horizontalAdvance('Auto-write') + 2, self.height()), Qt.AlignLeft | Qt.AlignVCenter,
                   'Auto-write')
        p.setFont(self.f_state)
        p.setPen(QtGui.QColor('#B9B7B0'))
        p.drawText(QRect(x + fm.horizontalAdvance('Auto-write') + 8, 0, 30, self.height()),
                   Qt.AlignLeft | Qt.AlignVCenter, 'On' if on else 'Off')
        p.end()

    def enterEvent(self, e):
        self.update()

    def leaveEvent(self, e):
        self.update()
