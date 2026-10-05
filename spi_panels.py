"""Side panels of the register-array GUI: profile rail, inspectors, bit picking and links."""
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

import spi_model as m
from spi_links import CLOCKS_KHZ, VOLTAGES
from spi_widgets import (ACCENT, ACCENT_SOFT, INK, INK3, LINE2, ORANGE, ORANGE_SOFT, ORANGE_TEXT,
                         BitStrip, Combo, FlowLayout, Stepper, Switch, dot_icon, mono, sans, set_prop)


# ---------------------------------------------------------------- small helpers

def label(text='', name=None, wrap=False, mono_pt=None, selectable=False):
    w = QtWidgets.QLabel(text)
    if name:
        w.setObjectName(name)
    if wrap:
        w.setWordWrap(True)
    if mono_pt:
        w.setFont(mono(mono_pt))
    if selectable:
        w.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return w


def button(text, slot=None, primary=False, danger=False, flat=False, checkable=False, tip=None):
    b = QtWidgets.QPushButton(text)
    for prop, on in (('primary', primary), ('danger', danger), ('flat', flat)):
        if on:
            b.setProperty(prop, True)
    b.setCheckable(checkable)
    b.setCursor(Qt.PointingHandCursor)
    if tip:
        b.setToolTip(tip)
    if slot is not None:
        b.clicked.connect(lambda _checked=False: slot())
    return b


def hbox(*items, spacing=6):
    w = QtWidgets.QWidget()
    lay = QtWidgets.QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    for it in items:
        if it is None:
            lay.addStretch(1)
        elif isinstance(it, int):
            lay.addSpacing(it)
        else:
            lay.addWidget(it)
    return w


def set_idle(edit, text):
    """Update a line edit unless the user is typing in it."""
    if not edit.hasFocus() and edit.text() != text:
        edit.setText(text)


def style_pill(lbl, kind, accent=ACCENT):
    colors = {'pending': (ORANGE_SOFT, ORANGE_TEXT), 'ok': (ACCENT_SOFT, accent), 'idle': ('#EFEDE7', '#4F5257')}
    bg, fg = colors[kind]
    lbl.setStyleSheet('background:%s; color:%s; border-radius:6px; padding:7px 12px; font-weight:500;' % (bg, fg))


def clear_layout(lay):
    while lay.count():
        item = lay.takeAt(0)
        if item.widget() is not None:
            item.widget().deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


# ---------------------------------------------------------------- left rail

class Rail(QtWidgets.QWidget):
    def __init__(self, session, win):
        super().__init__()
        self.setObjectName('Rail')
        self.s = session
        self.win = win
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(14, 16, 14, 16)
        lay.setSpacing(8)

        lay.addWidget(hbox(label('PROFILE', 'Eyebrow'), None, label('all you define', 'Muted')))
        card = QtWidgets.QFrame()
        card.setObjectName('Card')
        cl = QtWidgets.QVBoxLayout(card)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(2)
        self.pf = {}
        for key, title, mono_pt in (('proto', 'Protocol', None), ('chips', 'Chips and links', 8.5),
                                    ('regs', 'Registers', 8.5), ('names', 'Names', None)):
            cl.addWidget(label(title, 'Muted'))
            self.pf[key] = label('', wrap=True, mono_pt=mono_pt)
            cl.addWidget(self.pf[key])
            cl.addSpacing(4)
        lay.addWidget(card)
        lay.addSpacing(10)

        self.w_title = label('WATCHES', 'Eyebrow')
        lay.addWidget(hbox(self.w_title, None, button('+ Pick bits', lambda: self.s.start_pick(),
                                                      tip='Build a value from bits of any registers (the old Picker)')))
        self.w_note = label('', 'Muted', wrap=True)
        lay.addWidget(self.w_note)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setFont(mono(8.5))
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.tree.itemClicked.connect(lambda item, _col: self.s.select_watch(self.tree.indexOfTopLevelItem(item)))
        lay.addWidget(self.tree, 3)
        lay.addSpacing(10)

        lay.addWidget(label('SNAPSHOTS', 'Eyebrow'))
        self.snaps = QtWidgets.QListWidget()
        self.snaps.setMaximumHeight(110)
        self.snaps.itemDoubleClicked.connect(lambda _item: self.restore())
        lay.addWidget(self.snaps, 1)
        lay.addWidget(hbox(button('Save snapshot', lambda: self.s.take_snapshot()),
                           button('Restore', self.restore, tip='Load the selected snapshot as unsent changes')))

    def restore(self):
        row = self.snaps.currentRow()
        if row >= 0:
            self.s.restore_snapshot(row)

    def refresh(self, kinds):
        s = self.s
        p = s.profile
        if kinds & {'profile', 'links', 'names', 'layout'}:
            self.pf['proto'].setText('Classic, chip select' if p.protocol == m.CLASSIC else 'Chip address (CA)')
            groups = []
            for chip in p.chips:
                link = s.links.get(chip.link)
                name = link.name if link else chip.link
                if groups and groups[-1][0] == name:
                    groups[-1][1].append(chip.label)
                else:
                    groups.append((name, [chip.label]))
            self.pf['chips'].setText('\n'.join('%s → %s' % (' '.join(c), n) for n, c in groups))
            self.pf['regs'].setText('\n'.join(m.register_summary(p.registers)))
            nf = sum(len(r.fields) for r in p.registers)
            named = sum(1 for r in p.registers if r.name)
            self.pf['names'].setText('%d field names%s' % (nf, ', %d register names' % named if named else '')
                                     if nf or named else 'none yet — name registers as you learn them')
        if kinds & {'profile', 'watches'}:
            self.tree.clear()
            for w in p.watches:
                QtWidgets.QTreeWidgetItem(self.tree, [w.name + w.width_label(), ''])
            n_auto = sum(1 for w in p.watches if w.src == 'names')
            if n_auto:
                note = '%d found in field names like FLL_KP<0>…<3>.' % n_auto
                if p.skipped:
                    note += ' %d more names share a field with other signals or have gaps; pick those by hand.' % len(p.skipped)
                self.w_note.setToolTip('Not detected: ' + ', '.join(p.skipped) if p.skipped else '')
            elif p.watches:
                note = 'Picked by hand. Name bits like NAME<0>, NAME<1> and buses are found automatically.'
            else:
                note = 'None yet. A watch joins bits from any registers into one value.'
            self.w_note.setText(note)
            self.w_title.setText('WATCHES · %d' % len(p.watches) if p.watches else 'WATCHES')
        if kinds & {'profile', 'watches', 'values', 'chip', 'select'}:
            for n, w in enumerate(p.watches):
                item = self.tree.topLevelItem(n)
                if item is not None:
                    item.setText(1, w.fmt(s.watch_raw(w)))
                    item.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
            if s.sel[0] == 'watch' and s.sel[1] < self.tree.topLevelItemCount():
                self.tree.setCurrentItem(self.tree.topLevelItem(s.sel[1]))
            else:
                self.tree.clearSelection()
        if kinds & {'profile', 'snapshots'}:
            self.snaps.clear()
            for snap in s.snapshots:
                self.snaps.addItem(snap['name'])


# ---------------------------------------------------------------- register inspector

class RegisterInspector(QtWidgets.QWidget):
    def __init__(self, session, run):
        super().__init__()
        self.s = session
        self.run = run
        self.i = None
        self.key = None
        self._busy = False
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self.eyebrow = label('', 'Eyebrow')
        lay.addWidget(self.eyebrow)
        lay.addWidget(label('Name', 'Muted'))
        self.name = QtWidgets.QLineEdit()
        self.name.setFont(mono(10, True))
        self.name.editingFinished.connect(self._rename)
        lay.addWidget(self.name)

        self.big = label('', 'Big')
        self.big.setFont(mono(22))
        self.read_btn = button('Read', lambda: self.run(self.s.read_one, self.i))
        self.write_btn = button('Write', lambda: self.run(self.s.write_one, self.i), primary=True)
        lay.addWidget(hbox(self.big, None, self.read_btn, self.write_btn))
        self.valline = label('', 'Muted', mono_pt=8.5, selectable=True)
        lay.addWidget(self.valline)
        self.status = label('', wrap=True)
        lay.addWidget(self.status)

        self.bits_title = label('', 'Muted')
        self.bits_hint = label('', 'Muted')
        lay.addWidget(hbox(self.bits_title, None, self.bits_hint))
        self.bits = BitStrip()
        self.bits.clicked.connect(self._bit)
        lay.addWidget(self.bits)

        # a DAC-style field shown as a voltage
        self.scaled = QtWidgets.QFrame()
        self.scaled.setObjectName('Soft')
        sl = QtWidgets.QVBoxLayout(self.scaled)
        sl.setContentsMargins(12, 10, 12, 12)
        self.s_name = label('', mono_pt=9)
        self.s_range = label('', 'Muted', mono_pt=8)
        sl.addWidget(hbox(self.s_name, None, self.s_range))
        self.s_volts = label('')
        self.s_volts.setFont(sans(17))
        self.s_vedit = QtWidgets.QLineEdit()
        self.s_vedit.setPlaceholderText('type volts')
        self.s_vedit.setMaximumWidth(96)
        self.s_vedit.editingFinished.connect(self._volts_typed)
        sl.addWidget(hbox(self.s_volts, None, self.s_vedit))
        self.s_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.s_slider.setTracking(False)            # one write per release, not per pixel
        self.s_slider.valueChanged.connect(self._slide)
        sl.addWidget(self.s_slider)
        steps = []
        for d in (-10, -1, 1, 10):
            steps.append(button(('%+d' % d).replace('-', '−'), lambda d=d: self._step(d)))
        sl.addWidget(hbox(*steps))
        lay.addWidget(self.scaled)

        # named fields: switches for single bits, spin boxes for multi-bit fields
        self.fields = QtWidgets.QWidget()
        fl = QtWidgets.QVBoxLayout(self.fields)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.addWidget(label('Fields in this register', 'Muted'))
        self.fields_grid = QtWidgets.QGridLayout()
        self.fields_grid.setHorizontalSpacing(8)
        self.fields_grid.setVerticalSpacing(2)
        fl.addLayout(self.fields_grid)
        self.field_ctl = []
        lay.addWidget(self.fields)

        # register without fields: the width can still be changed
        self.width_box = QtWidgets.QWidget()
        wl = QtWidgets.QVBoxLayout(self.width_box)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.addWidget(label('Register width', 'Muted'))
        self.w5 = button('5-bit', lambda: self.s.set_width(self.i, 5), checkable=True)
        self.w13 = button('13-bit', lambda: self.s.set_width(self.i, 13), checkable=True)
        wl.addWidget(hbox(self.w5, self.w13))
        lay.addWidget(self.width_box)

        # the same address on every chip
        self.chips = QtWidgets.QWidget()
        cl = QtWidgets.QVBoxLayout(self.chips)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(label('Same address on every chip', 'Muted'))
        self.chips_grid = QtWidgets.QGridLayout()
        self.chips_grid.setVerticalSpacing(2)
        cl.addLayout(self.chips_grid)
        self.chip_rows = []
        self.copy_btn = button('', lambda: self.run(self.s.copy_to_all, self.i))
        cl.addWidget(self.copy_btn)
        lay.addWidget(self.chips)
        lay.addStretch(1)

    # -- structure
    def show_reg(self, i):
        s = self.s
        reg = s.reg(i)
        key = (id(s.profile), i, reg.width, len(reg.fields), len(s.profile.chips))
        self.i = i
        if key != self.key:
            self.key = key
            self._build_fields(reg)
            self._build_chips()
        self.update_values()

    def _build_fields(self, reg):
        clear_layout(self.fields_grid)
        self.field_ctl = []
        if reg.scaled_field() is not None or not reg.fields:
            return
        for row, f in enumerate(reversed(reg.fields)):
            name = label(f.name, mono_pt=8.5)
            name.setToolTip(f.name)
            name.setMinimumWidth(40)
            name.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
            loc = label('[%d]' % f.lo if f.width == 1 else '[%d:%d]' % (f.hi, f.lo), 'Muted', mono_pt=8)
            if f.width == 1:
                ctl = Switch()
                ctl.setToolTip(f.name)
                ctl.toggled.connect(lambda on, f=f: self._field(f, 1 if on else 0))
            else:
                ctl = Stepper(f.full)
                ctl.valueChanged.connect(lambda v, f=f: self._field(f, v))
            self.fields_grid.addWidget(name, row, 0)
            self.fields_grid.addWidget(loc, row, 1)
            self.fields_grid.addWidget(ctl, row, 2)
            self.field_ctl.append((f, ctl))
        self.fields_grid.setColumnStretch(0, 1)

    def _build_chips(self):
        clear_layout(self.chips_grid)
        self.chip_rows = []
        s = self.s
        if len(s.profile.chips) < 2:
            return
        for k, chip in enumerate(s.profile.chips):
            b = button(chip.label, lambda k=k: s.set_chip(k), flat=True)
            b.setFont(mono(9, True))
            edit = QtWidgets.QLineEdit()
            edit.setFont(mono(9))
            edit.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            edit.setMaximumWidth(72)
            edit.editingFinished.connect(lambda k=k, e=edit: self._chip_typed(k, e))
            extra = label('', 'Muted', mono_pt=8)
            diff = label('')
            diff.setFont(sans(10, QtGui.QFont.Bold))
            for col, w in enumerate((b, edit, extra, diff)):
                self.chips_grid.addWidget(w, k, col)
            self.chip_rows.append((b, edit, extra, diff))
        self.chips_grid.setColumnStretch(2, 1)

    # -- values
    def update_values(self):
        s = self.s
        if self.i is None or s.profile is None or self.i >= len(s.profile.registers):
            return
        self._busy = True
        try:
            self._update()
        finally:
            self._busy = False

    def _update(self):
        s, i, k = self.s, self.i, self.s.chip
        reg = s.reg(i)
        v, cv = s.val[k][i], s.chipv[k][i]
        unknown = v is None
        pend = s.pending(k, i)
        online = s.online(k)
        link = s.chip_link(k)
        chip = s.profile.chips[k]
        self.eyebrow.setText('%s · A%d · %d-BIT%s' % (chip.label, reg.addr, reg.width, ' · READ-ONLY' if reg.ro else ''))
        self.name.setPlaceholderText(reg.title() or 'Name this register')
        set_idle(self.name, reg.name)
        self.big.setText('—' if unknown else str(v))
        self.valline.setText('not read yet' if unknown else '0x%0*X · 0b%s' % ((reg.width + 3) // 4, v, format(v, '0%db' % reg.width)))
        if not online:
            text = ('Unsent — %s is offline' % link.name) if pend else ('Offline — not read yet' if unknown else
                                                                          'Offline — last value read over %s' % link.name)
            style_pill(self.status, 'pending' if pend else 'idle')
        elif pend:
            text = 'Unsent — chip holds %s' % ('an unread value' if cv is None else cv)
            style_pill(self.status, 'pending')
        else:
            text = 'Not read yet' if unknown else 'Read-only readout' if reg.ro else (
                'Written — auto-write is on' if s.auto else 'In sync with chip')
            style_pill(self.status, 'ok' if not unknown else 'idle')
        self.status.setText(text)
        self.read_btn.setEnabled(online)
        self.write_btn.setEnabled(online and pend)

        # bits, most significant first; while picking they show their position in the new watch
        pos = {x: lab for lab, x in s.pick_labels() if x is not None}
        wide = reg.width > 5
        items = []
        for b in range(reg.width - 1, -1, -1):
            used = reg.used(b)
            on = not unknown and (v >> b) & 1
            lab = pos.get((reg.addr, b))
            if lab is not None:
                bg, fg, bd, text = ORANGE_SOFT, ORANGE_TEXT, ORANGE, lab
            elif on:
                bg, fg, bd, text = ACCENT, '#FFFFFF', ACCENT, '1'
            else:
                bg, fg, bd = ('#FFFFFF', INK, LINE2) if used else ('#EFEDE7', INK3, LINE2)
                text = '·' if unknown else '0'
            nxt = b - 1
            gap = 2 if wide else (8 if nxt >= 0 and reg.fields and reg.field_at(b) is not reg.field_at(nxt) else 4)
            tip = 'A%d bit %d%s' % (reg.addr, b, (' · ' + reg.bit_name(b)) if reg.bit_name(b) else '')
            items.append({'kind': 'bit', 'text': text, 'sub': str(b), 'bg': bg, 'fg': fg, 'bd': bd, 'tip': tip,
                          'gap': gap, 'enabled': s.pick is not None or not reg.ro})
        self.bits.set_items(items, 20 if wide else 46)
        unused = sum(1 for b in range(reg.width) if not reg.used(b))
        self.bits_title.setText('All %d bits%s' % (reg.width, ', unused ones too' if unused else ''))
        self.bits_hint.setText('click to pick' if s.pick is not None else ('' if reg.ro else 'click to flip'))

        sf = reg.scaled_field()
        self.scaled.setVisible(sf is not None)
        if sf is not None:
            code = 0 if unknown else (v >> sf.lo) & sf.full
            self.s_name.setText(sf.name)
            self.s_range.setText('field [%d:%d] · %g–%g V' % (sf.hi, sf.lo, sf.vmin, sf.vmax))
            self.s_volts.setText('—' if unknown else '%.3f V' % sf.volts(code))
            self.s_slider.setRange(0, sf.full)
            self.s_slider.setValue(code)
            self.s_slider.setEnabled(not reg.ro)

        self.fields.setVisible(bool(self.field_ctl))
        for f, ctl in self.field_ctl:
            fv = 0 if unknown else (v >> f.lo) & f.full
            ctl.setEnabled(not reg.ro)
            if isinstance(ctl, Switch):
                ctl.setChecked(bool(fv))
            else:
                ctl.setValue(fv)

        self.width_box.setVisible(not reg.fields)
        self.w5.setChecked(reg.width == 5)
        self.w13.setChecked(reg.width == 13)

        self.chips.setVisible(bool(self.chip_rows))
        for kk, (b, edit, extra, diff) in enumerate(self.chip_rows):
            kv = s.val[kk][i]
            lnk = s.chip_link(kk)
            b.setText('%s  %s' % (s.profile.chips[kk].label, lnk.short if lnk else '?'))
            b.setIcon(dot_icon(s.online(kk)))
            b.setStyleSheet('background:%s;' % ACCENT_SOFT if kk == k else '')
            set_idle(edit, '' if kv is None else str(kv))
            edit.setEnabled(not reg.ro)
            set_prop(edit, 'bad', False)
            edit.setStyleSheet('border-color:%s;' % ORANGE if s.pending(kk, i) else '')
            txt = 'not read' if kv is None else ('%.3f V' % sf.volts((kv >> sf.lo) & sf.full) if sf else '0x%X' % kv)
            extra.setText(txt + ('' if s.online(kk) else ' · offline'))
            diff.setText('≠' if kv != s.val[0][i] else '')
        self.copy_btn.setText('Copy %s value to all chips' % chip.label)
        self.copy_btn.setEnabled(not unknown and not reg.ro)

    # -- slots
    def _rename(self):
        if self.i is not None and self.name.text().strip() != self.s.reg(self.i).name:
            self.s.rename(self.i, self.name.text())

    def _bit(self, n):
        s = self.s
        reg = s.reg(self.i)
        b = reg.width - 1 - n
        if s.pick is not None:
            s.pick_bit(reg.addr, b)
        else:
            self.run(s.toggle_bit, self.i, b)

    def _field(self, f, code):
        if not self._busy:
            self.run(self.s.set_field, self.i, f, code)

    def _slide(self, code):
        sf = self.s.reg(self.i).scaled_field()
        if not self._busy and sf is not None:
            self.run(self.s.set_field, self.i, sf, code)

    def _step(self, d):
        sf = self.s.reg(self.i).scaled_field()
        v = self.s.val[self.s.chip][self.i]
        if sf is not None:
            code = 0 if v is None else (v >> sf.lo) & sf.full
            self.run(self.s.set_field, self.i, sf, code + d)

    def _volts_typed(self):
        sf = self.s.reg(self.i).scaled_field()
        text = self.s_vedit.text().strip().lower().rstrip('v').strip()
        if sf is None or not text:
            return
        try:
            volts = float(text)
        except ValueError:
            self.s.say('Type a voltage such as 0.5')
            return
        self.s_vedit.clear()
        self.run(self.s.set_field, self.i, sf, sf.code(volts))

    def _chip_typed(self, k, edit):
        if self._busy:
            return
        v = self.s.val[k][self.i]
        if edit.text().strip() == ('' if v is None else str(v)):
            return
        err = self.run(self.s.type_value, self.i, edit.text(), k)
        set_prop(edit, 'bad', bool(err))


# ---------------------------------------------------------------- watch inspector

class WatchInspector(QtWidgets.QWidget):
    def __init__(self, session, run):
        super().__init__()
        self.s = session
        self.run = run
        self.wi = None
        self.key = None
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.eyebrow = label('', 'Eyebrow')
        lay.addWidget(self.eyebrow)
        self.name = label('', mono_pt=13)
        self.name.setFont(mono(13, True))
        self.range = label('', 'Muted', mono_pt=10)
        lay.addWidget(hbox(self.name, self.range, None))
        self.big = label('')
        self.big.setFont(mono(22))
        self.read_btn = button('Read', lambda: self.run(self.s.read_watch, self.wi))
        self.write_btn = button('Write', lambda: self.run(self.s.write_watch, self.wi), primary=True)
        lay.addWidget(hbox(self.big, None, self.read_btn, self.write_btn))
        self.valline = label('', 'Muted', mono_pt=8.5, wrap=True, selectable=True)
        lay.addWidget(self.valline)
        self.status = label('', wrap=True)
        lay.addWidget(self.status)
        self.edit = QtWidgets.QLineEdit()
        self.edit.setFont(mono(11))
        self.edit.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.edit.editingFinished.connect(self._typed)
        dec = button('−', lambda: self._step(-1))
        inc = button('+', lambda: self._step(1))
        for b in (dec, inc):
            b.setFixedWidth(48)
        lay.addWidget(hbox(dec, self.edit, inc))
        lay.addWidget(label('Bits · most significant first · click to toggle', 'Muted'))
        self.bits = BitStrip()
        self.bits.clicked.connect(self._bit)
        lay.addWidget(self.bits)
        lay.addWidget(label('Range, most significant first', 'Muted'))
        self.range_text = label('', mono_pt=9, wrap=True, selectable=True)
        self.range_text.setStyleSheet('background:#FAF9F6; border:1px solid #DAD7CE; border-radius:6px; padding:8px 10px;')
        lay.addWidget(self.range_text)
        lay.addWidget(label('Registers it writes', 'Muted'))
        self.regs_box = QtWidgets.QVBoxLayout()
        self.regs_box.setSpacing(2)
        lay.addLayout(self.regs_box)
        self.reg_rows = []
        lay.addWidget(hbox(button('Edit bits', lambda: self.s.start_pick(edit=self.wi)), None,
                           button('Delete watch', self._delete, danger=True)))
        lay.addStretch(1)

    def show_watch(self, wi):
        s = self.s
        w = s.profile.watches[wi]
        key = (id(s.profile), wi, id(w))
        self.wi = wi
        if key != self.key:
            self.key = key
            clear_layout(self.regs_box)
            self.reg_rows = []
            for i in s.watch_regs(w):
                b = button('', lambda i=i: s.select_reg(i), flat=True)
                b.setFont(mono(9))
                self.regs_box.addWidget(b)
                self.reg_rows.append((i, b))
        self.update_values()

    def update_values(self):
        s = self.s
        if self.wi is None or self.wi >= len(s.profile.watches):
            return
        w = s.profile.watches[self.wi]
        k = s.chip
        raw = s.watch_raw(w)
        n, frac = w.width, w.frac
        online = s.online(k)
        pend = [i for i, _b in self.reg_rows if s.pending(k, i)]
        self.eyebrow.setText('WATCH · %s · %s' % ('%d+%d-BIT FIXED POINT' % (n - frac, frac) if frac else '%d-BIT' % n,
                                                 'FOUND IN FIELD NAMES' if w.src == 'names' else 'PICKED BY HAND'))
        self.name.setText(w.name)
        self.range.setText(w.width_label())
        self.big.setText(w.fmt(raw))
        b = format(raw, '0%db' % n)
        bpt = (b[:n - frac] or '0') + '.' + b[n - frac:] if frac else b
        self.valline.setText('%s0x%X · 0b%s' % ('raw ' if frac else '', raw, bpt))
        if pend:
            text = 'Unsent — %d register%s%s' % (len(pend), '' if len(pend) == 1 else 's',
                                                ' to write' if online else ', %s is offline' % s.chip_link(k).name)
            style_pill(self.status, 'pending')
        else:
            text = 'In sync with chip' if online else 'Offline — last values read over %s' % s.chip_link(k).name
            style_pill(self.status, 'ok' if online else 'idle')
        self.status.setText(text)
        self.read_btn.setEnabled(online)
        self.write_btn.setEnabled(online and bool(pend))
        set_idle(self.edit, w.fmt(raw))
        items = []
        if frac == n:
            items.append({'kind': 'point', 'gap': 8})
        for kbit in range(n - 1, -1, -1):
            a, bit = w.bits[kbit]
            on = (raw >> kbit) & 1
            nxt = w.bits[kbit - 1][0] if kbit > 0 else a
            gap = 2 if (frac and kbit == frac) else (10 if nxt != a else 2)
            items.append({'kind': 'bit', 'text': '1' if on else '0', 'sub': '%d.%d' % (a, bit),
                          'bg': ACCENT if on else '#FFFFFF', 'fg': '#FFFFFF' if on else INK,
                          'bd': ACCENT if on else LINE2, 'gap': gap,
                          'tip': '%s bit %d = A%d bit %d' % (w.name, kbit - frac, a, bit)})
            if frac and kbit == frac:
                items.append({'kind': 'point', 'gap': 8})
        self.bits.set_items(items, 24)
        self.range_text.setText(w.range_text())
        for i, btn in self.reg_rows:
            v = s.val[k][i]
            reg = s.reg(i)
            btn.setText('A%-4d %s   %s' % (reg.addr, '—' if v is None else '0b' + format(v, '0%db' % reg.width),
                                           'unsent' if s.pending(k, i) else 'in sync'))
            btn.setStyleSheet('color:%s;' % ORANGE_TEXT if s.pending(k, i) else '')

    def _typed(self):
        w = self.s.profile.watches[self.wi]
        if self.edit.text().strip() == w.fmt(self.s.watch_raw(w)):
            return
        err = self.run(self.s.type_watch, self.wi, self.edit.text())
        set_prop(self.edit, 'bad', bool(err))

    def _step(self, d):
        w = self.s.profile.watches[self.wi]
        self.run(self.s.set_watch, self.wi, self.s.watch_raw(w) + d)

    def _bit(self, n):
        w = self.s.profile.watches[self.wi]
        items = [x for x in self.bits.items]
        kbits = [x for x in items if x['kind'] == 'bit']
        pos = kbits.index(items[n])
        kbit = w.width - 1 - pos
        self.run(self.s.set_watch, self.wi, self.s.watch_raw(w) ^ (1 << kbit))

    def _delete(self):
        w = self.s.profile.watches[self.wi]
        if QtWidgets.QMessageBox.question(self, 'Delete watch', 'Delete watch %s?' % w.name) == QtWidgets.QMessageBox.Yes:
            self.s.delete_watch(self.wi)


# ---------------------------------------------------------------- picking bits

class PickPanel(QtWidgets.QFrame):
    """The old Picker window, now a panel: bits are clicked right on the tiles."""

    def __init__(self, session):
        super().__init__()
        self.setObjectName('Pick')
        self.s = session
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)
        self.title = label('')
        self.title.setStyleSheet('color:%s; font-weight:600;' % ORANGE_TEXT)
        lay.addWidget(self.title)
        lay.addWidget(label('Click bits in the tiles, most significant first. Click a picked bit again to drop it.',
                            wrap=True))
        lay.addWidget(label('Name', 'Muted'))
        self.name = QtWidgets.QLineEdit()
        self.name.setFont(mono(9.5))
        self.name.setPlaceholderText('e.g. FLL_KP')
        self.name.textEdited.connect(lambda t: self.s.pick_rename(t))
        lay.addWidget(self.name)
        lay.addWidget(label('Order, most significant first', 'Muted'))
        self.chips = QtWidgets.QWidget()
        self.flow = FlowLayout(self.chips, 4)
        lay.addWidget(self.chips)
        self.empty = label('No bits picked yet', 'Muted')
        lay.addWidget(self.empty)
        self.summary = label('', 'Muted', wrap=True)
        lay.addWidget(self.summary)
        self.point_btn = button('Add point', lambda: self.s.pick_point(),
                                tip='Bits after the point are the fraction part (fixed point)')
        lay.addWidget(hbox(self.point_btn, button('Undo last', lambda: self.s.pick_undo()),
                           button('Clear', lambda: self.s.pick_clear())))
        self.save_btn = button('Save watch', self._save, primary=True)
        lay.addWidget(hbox(self.save_btn, button('Cancel', lambda: self.s.cancel_pick())))

    def _save(self):
        self.s.pick_rename(self.name.text())
        self.s.save_pick()

    def refresh(self):
        s = self.s
        self.setVisible(s.pick is not None)
        if s.pick is None:
            return
        edit = s.pick['edit']
        self.title.setText('Editing watch %s' % s.profile.watches[edit].name if edit is not None else 'New watch')
        set_idle(self.name, s.pick['name'])
        self.flow.clear()
        labels = s.pick_labels()
        for n, (lab, x) in enumerate(labels):
            text = '.' if x is None else '%s  A%d[%d]' % (lab, x[0], x[1])
            b = QtWidgets.QPushButton(text)
            b.setFont(mono(8.5, True) if x is None else mono(8.5))
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip('Remove the point' if x is None else 'Drop A%d bit %d' % x)
            b.setStyleSheet('QPushButton { background:#FFFFFF; border:1px solid %s; border-radius:11px;'
                            ' padding:0 8px; min-height:22px; }' % (ORANGE_TEXT if x is None else ORANGE))
            b.clicked.connect(lambda _c=False, n=n: self.s.pick_drop(n))
            self.flow.addWidget(b)
        w = s.pick_watch()
        self.empty.setVisible(not w.bits)
        if w.bits:
            self.summary.setText('%d bit%s · %s · %s' % (w.width, '' if w.width == 1 else 's',
                                                        '%d integer + %d fraction' % (w.width - w.frac, w.frac)
                                                        if w.frac else 'integer', w.range_text()))
        else:
            self.summary.setText('Use Add point where the fraction starts, if the value has one.')
        has_point = None in s.pick['seq']
        self.point_btn.setText('Remove point' if has_point else 'Add point')
        self.save_btn.setText('Save changes' if edit is not None else 'Save watch')
        self.save_btn.setEnabled(bool(w.bits))
        self.chips.updateGeometry()


# ---------------------------------------------------------------- links

class LinksPanel(QtWidgets.QFrame):
    """Popup under the header's links chip: connect the NI adapter and Pico W boards."""
    closed = QtCore.pyqtSignal()

    def __init__(self, win):
        super().__init__(None, Qt.Popup)
        self.win = win
        self.setObjectName('Card')
        self.setStyleSheet('QFrame#Card { background:#FFFFFF; border:1px solid #CFCBC1; border-radius:8px; }')
        self.setFixedWidth(560)
        self.lay = QtWidgets.QVBoxLayout(self)
        self.lay.setContentsMargins(16, 14, 16, 16)
        self.lay.setSpacing(6)

    def hideEvent(self, e):
        super().hideEvent(e)
        self.closed.emit()

    def rebuild(self):
        clear_layout(self.lay)
        win, links, s = self.win, self.win.links, self.win.s
        title = label('Links')
        title.setFont(sans(11, QtGui.QFont.DemiBold))
        self.lay.addWidget(title)
        self.lay.addWidget(label('Each chip in the profile names its link and chip select, like the old '
                                 'Term and SS columns.', 'Muted', wrap=True))
        for link in links.all():
            used = [c.label for c in s.profile.chips if c.link == link.id]
            dot = QtWidgets.QLabel()
            dot.setPixmap(dot_icon(link.connected).pixmap(10, 10))
            name = label(link.name)
            name.setFont(sans(9.5, QtGui.QFont.DemiBold))
            addr = link.addr or ('USB' if link.kind == 'ni' else 'not discovered yet')
            if links.simulate and link.kind != 'sim':
                addr += ' · simulated'
            info = label('%s · %s' % ('Connected' if link.connected else 'Not connected',
                                      'this profile: ' + ', '.join(used) if used else 'not used by this profile'),
                         'Muted')
            col = QtWidgets.QWidget()
            cl = QtWidgets.QVBoxLayout(col)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setSpacing(0)
            cl.addWidget(hbox(name, label(addr, 'Muted', mono_pt=8), None))
            cl.addWidget(info)
            row = [dot, col, None]
            if link.kind in ('ni', 'pico') and not link.connected:
                clock = Combo()
                clock.addItems(['%d kHz' % c for c in CLOCKS_KHZ])
                clock.setCurrentIndex(CLOCKS_KHZ.index(links.clock_khz) if links.clock_khz in CLOCKS_KHZ else 14)
                clock.currentIndexChanged.connect(lambda n: win.configure_links(clock_khz=CLOCKS_KHZ[n]))
                row.append(clock)
                if link.kind == 'ni':
                    volt = Combo()
                    volt.addItems(['%.1f V' % v for v in VOLTAGES])
                    volt.setCurrentIndex(VOLTAGES.index(links.voltage) if links.voltage in VOLTAGES else 1)
                    volt.currentIndexChanged.connect(lambda n: win.configure_links(voltage=VOLTAGES[n]))
                    row.append(volt)
            btn = button('Disconnect' if link.connected else 'Connect',
                         lambda l=link: win.toggle_link(l), primary=not link.connected)
            btn.setMinimumWidth(100)
            row.append(btn)
            self.lay.addWidget(hbox(*row, spacing=8))
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet('color:#E6E3DB;')
        self.lay.addWidget(line)
        note = ('%d board%s answered. Connect the ones you need.' % (len(links.found), '' if len(links.found) == 1 else 's')
                if links.found else 'Broadcasts DISCOVER_PICO on UDP 5006.')
        self.lay.addWidget(hbox(button('Discover Pico', win.discover), label(note, 'Muted', wrap=True), None,
                                button('Reset chips', lambda: win.run(s.reset_chips), danger=True,
                                       tip='Reset command (cmd 7) to every chip on a connected link')))
        for name, ip, port in links.found:
            dot = QtWidgets.QLabel()
            dot.setPixmap(dot_icon(False).pixmap(10, 10))
            self.lay.addWidget(hbox(dot, label('Pico ' + name), label('%s:%d' % (ip, port), 'Muted', mono_pt=8), None,
                                    button('Connect', lambda n=name: win.connect_found(n), primary=True), spacing=8))
        sim = Switch('Simulate hardware (every link talks to in-memory chips)')
        sim.setChecked(links.simulate)
        sim.toggled.connect(win.set_simulate)
        self.lay.addWidget(sim)
        self.adjustSize()
