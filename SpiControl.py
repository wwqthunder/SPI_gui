"""SPI Control: a register-array GUI for Okada Lab's SPI chips (NI USB-8452 and Pico W links).

    python SpiControl.py [profile.json | old table .csv/.xlsx/.xlsm]

Layers: spi_model (profiles, values, operations; no Qt), spi_links (NI / Pico / simulator),
spi_widgets + spi_panels (GUI).  The old GuiMain.py is untouched.
"""
import os
import sys
import traceback

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

import spi_model as m
from spi_links import LinkError, LinkSet
from spi_panels import LinksPanel, PickPanel, RegisterInspector, Rail, WatchInspector, button, hbox, label
from spi_widgets import QSS, AutoWriteButton, BitsMap, LinksButton, TileGrid, dot_icon

HERE = os.path.dirname(os.path.abspath(__file__))
FILE_FILTER = 'Profiles and old tables (*.json *.csv *.xlsx *.xls *.xlsm);;All files (*)'


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, path=None):
        super().__init__()
        ini = os.environ.get('SPICONTROL_INI')          # tests keep their settings out of the registry
        self.settings = (QtCore.QSettings(ini, QtCore.QSettings.IniFormat) if ini
                         else QtCore.QSettings('OkadaLab', 'SPIControl'))
        self.links = LinkSet(simulate=self.settings.value('simulate', False, type=bool),
                             clock_khz=self.settings.value('clock_khz', 1000, type=int),
                             voltage=float(self.settings.value('voltage', 2.5)))
        self.s = m.Session(self.links)
        self._insp_key = None
        self._build()
        self.s.subscribe(self.on_change)
        start = path or self.settings.value('last_path', '', type=str)
        if not (start and os.path.exists(start) and self.open_path(start, quiet=not path)):
            self.s.load(m.blank_profile(), status='New profile · 64 registers · connect a link and press Read all')

    # ------------------------------------------------------------ layout
    def _build(self):
        self.setWindowTitle('SPI Control')
        central = QtWidgets.QWidget()
        central.setObjectName('Body')
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(central)

        # header: links, auto-write, read / write everything
        header = QtWidgets.QFrame()
        header.setObjectName('Header')
        header.setFixedHeight(56)
        hl = QtWidgets.QHBoxLayout(header)
        hl.setContentsMargins(18, 0, 18, 0)
        hl.setSpacing(10)
        title = label('SPI Control')
        title.setStyleSheet('font-size:12pt; font-weight:600;')
        hl.addWidget(title)
        hl.addSpacing(12)
        self.links_btn = LinksButton(self.links)
        self.links_btn.setToolTip('Links: connect the NI adapter or Pico W boards')
        self.links_btn.clicked.connect(self.show_links)
        hl.addWidget(self.links_btn)
        hl.addStretch(1)
        self.auto_btn = AutoWriteButton()
        self.auto_btn.clicked.connect(lambda: self.s.set_auto(self.auto_btn.isChecked()))
        self.read_all_btn = button('Read all', lambda: self.run(self.s.read_all))
        self.discard_btn = button('Discard', lambda: self.s.discard(), tip='Drop unsent changes')
        self.write_btn = button('Write', lambda: self.run(self.s.write_all))
        self.write_btn.setObjectName('WriteBtn')
        for b in (self.auto_btn, self.read_all_btn, self.discard_btn, self.write_btn):
            hl.addWidget(b)
        root.addWidget(header)

        # sub bar: profile, chip tabs, view toggle
        sub = QtWidgets.QFrame()
        sub.setObjectName('SubBar')
        sub.setFixedHeight(50)
        sl = QtWidgets.QHBoxLayout(sub)
        sl.setContentsMargins(16, 0, 16, 0)
        sl.setSpacing(8)
        sl.addWidget(label('Chip profile', 'Muted'))
        self.prof_label = label('')
        self.prof_label.setStyleSheet('font-weight:600;')
        sl.addWidget(self.prof_label)
        open_btn = QtWidgets.QToolButton()
        open_btn.setObjectName('FileBtn')
        open_btn.setText('File  ▾')
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        open_btn.setMenu(self._file_menu(QtWidgets.QMenu(self)))
        sl.addWidget(open_btn)
        sl.addStretch(1)
        self.chip_bar = QtWidgets.QWidget()
        self.chip_lay = QtWidgets.QHBoxLayout(self.chip_bar)
        self.chip_lay.setContentsMargins(0, 0, 0, 0)
        self.chip_lay.setSpacing(4)
        self.chip_group = QtWidgets.QButtonGroup(self)
        self.chip_group.setExclusive(True)
        sl.addWidget(self.chip_bar)
        sl.addSpacing(10)
        self.tiles_btn = button('Tiles', lambda: self.set_view(0), checkable=True)
        self.bits_btn = button('Bits', lambda: self.set_view(1), checkable=True)
        view_group = QtWidgets.QButtonGroup(self)
        view_group.addButton(self.tiles_btn)
        view_group.addButton(self.bits_btn)
        self.tiles_btn.setChecked(True)
        sl.addWidget(hbox(self.tiles_btn, self.bits_btn, spacing=0))
        root.addWidget(sub)

        body = QtWidgets.QWidget()
        bl = QtWidgets.QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self.rail = Rail(self.s, self)
        rail_scroll = QtWidgets.QScrollArea()
        rail_scroll.setWidgetResizable(True)
        rail_scroll.setWidget(self.rail)
        rail_scroll.setFixedWidth(248)
        rail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        rail_scroll.setStyleSheet('QScrollArea { border-right:1px solid #D8D5CC; }')
        bl.addWidget(rail_scroll)

        center = QtWidgets.QWidget()
        center.setObjectName('Center')
        cl = QtWidgets.QVBoxLayout(center)
        cl.setContentsMargins(18, 12, 12, 8)
        cl.setSpacing(8)
        heading = label('Register array', 'Title')
        self.meta = label('', 'Muted')
        legend = label('<span style="color:#1D4E89">■</span> 1 &nbsp; <span style="color:#D3CFC5">■</span> 0 &nbsp; '
                       '<span style="color:#C8671F">●</span> unsent &nbsp; <b>≠</b> chips differ &nbsp; '
                       '<span style="color:#BDB8AC">- - -</span> click to type', 'Muted')
        self.tiles = TileGrid(self.s, self.run, scale=self.settings.value('tile_scale', 1.0, type=float))
        self.zoom_label = label('', 'Muted', mono_pt=8.5)
        self.zoom_label.setFixedWidth(40)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        zoom_out = button('−', lambda: self.tiles.set_scale(self.tiles.k - 0.1), tip='Smaller tiles (Ctrl + wheel, Ctrl+−)')
        zoom_in = button('+', lambda: self.tiles.set_scale(self.tiles.k + 0.1), tip='Larger tiles (Ctrl + wheel, Ctrl+=)')
        for b in (zoom_out, zoom_in):
            b.setProperty('step', True)
            b.setFixedSize(26, 26)
        self.tiles.scaleChanged.connect(self._scale_changed)
        self._scale_changed(self.tiles.k, save=False)
        cl.addWidget(hbox(heading, 10, self.meta, None, legend, 12, zoom_out, self.zoom_label, zoom_in, spacing=6))
        self.banner = QtWidgets.QFrame()
        self.banner.setObjectName('Banner')
        bnl = QtWidgets.QHBoxLayout(self.banner)
        bnl.setContentsMargins(12, 6, 8, 6)
        self.banner_text = label('', wrap=True)
        bnl.addWidget(self.banner_text, 1)
        bnl.addWidget(button('Reconnect', self.reconnect_current))
        cl.addWidget(self.banner)
        self.stack = QtWidgets.QStackedWidget()
        self.tiles_scroll = QtWidgets.QScrollArea()
        self.tiles_scroll.setWidgetResizable(True)
        self.tiles_scroll.setWidget(self.tiles)
        self.tiles_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.stack.addWidget(self.tiles_scroll)
        self.bitsmap = BitsMap(self.s)
        bits_scroll = QtWidgets.QScrollArea()
        bits_scroll.setWidgetResizable(True)
        bits_scroll.setWidget(self.bitsmap)
        self.stack.addWidget(bits_scroll)
        cl.addWidget(self.stack, 1)
        bl.addWidget(center, 1)

        insp = QtWidgets.QWidget()
        insp.setObjectName('Inspector')
        il = QtWidgets.QVBoxLayout(insp)
        il.setContentsMargins(18, 16, 18, 16)
        il.setSpacing(12)
        self.pick_panel = PickPanel(self.s)
        il.addWidget(self.pick_panel)
        self.insp_stack = QtWidgets.QStackedWidget()
        self.reg_insp = RegisterInspector(self.s, self.run)
        self.watch_insp = WatchInspector(self.s, self.run)
        self.insp_stack.addWidget(self.reg_insp)
        self.insp_stack.addWidget(self.watch_insp)
        il.addWidget(self.insp_stack)
        il.addStretch(1)
        insp_scroll = QtWidgets.QScrollArea()
        insp_scroll.setWidgetResizable(True)
        insp_scroll.setWidget(insp)
        insp_scroll.setFixedWidth(356)
        insp_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        insp_scroll.setStyleSheet('QScrollArea { border-left:1px solid #D8D5CC; background:#FFFFFF; }')
        bl.addWidget(insp_scroll)
        root.addWidget(body, 1)

        self.status_text = label('', mono_pt=8.5)
        last = label('Last')
        last.setStyleSheet('font-weight:600; padding-left:8px;')
        self.statusBar().addWidget(last)
        self.statusBar().addWidget(self.status_text, 1)
        self.statusBar().setSizeGripEnabled(False)

        self.links_panel = LinksPanel(self)
        self.links_panel.closed.connect(lambda: self.links_btn.setChecked(False))

        # No menu bar: File lives in the sub bar, links in the header.  Keys still work window-wide.
        for keys, slot in (('Ctrl+L', self.show_links), ('Ctrl+1', lambda: self.set_view(0)),
                           ('Ctrl+2', lambda: self.set_view(1)),
                           ('Ctrl+=', lambda: self.tiles.set_scale(self.tiles.k + 0.1)),
                           ('Ctrl++', lambda: self.tiles.set_scale(self.tiles.k + 0.1)),
                           ('Ctrl+-', lambda: self.tiles.set_scale(self.tiles.k - 0.1)),
                           ('Ctrl+0', lambda: self.tiles.set_scale(1.0))):
            QtWidgets.QShortcut(QtGui.QKeySequence(keys), self, activated=slot)

    def _scale_changed(self, k, save=True):
        self.zoom_label.setText('%d%%' % round(k * 100))
        if save:
            self.settings.setValue('tile_scale', k)

    def _file_menu(self, menu):
        for item in (('Open profile or old table…', self.open_dialog, 'Ctrl+O'),
                     ('Save profile as…', self.save_profile_dialog, 'Ctrl+S'), None,
                     ('Save values…', self.save_values_dialog, None),
                     ('Load values…', self.load_values_dialog, None), None,
                     ('New chip (A1–A64, 5-bit)', lambda: self.s.load(m.blank_profile()), None), None,
                     ('Quit', self.close, 'Ctrl+Q')):
            if item is None:
                menu.addSeparator()
                continue
            text, slot, keys = item
            act = menu.addAction(text, slot)
            if keys:
                act.setShortcut(QtGui.QKeySequence(keys))
                self.addAction(act)             # the shortcut works while the menu is closed
        return menu

    # ------------------------------------------------------------ refresh
    def on_change(self, kinds):
        s = self.s
        if s.profile is None:
            return
        if 'profile' in kinds:
            self.prof_label.setText(s.profile.name)
            self.setWindowTitle('SPI Control — %s' % s.profile.name)
            self._insp_key = None
            kinds = kinds | {'links', 'watches', 'snapshots', 'layout'}
        if 'layout' in kinds:
            self.tiles.relayout()
            self.bitsmap.relayout()
        if kinds & {'profile', 'links', 'chip'}:
            self._build_chip_tabs()
        self.tiles.update()
        self.bitsmap.update()
        self.links_btn.updateGeometry()
        self.links_btn.update()
        self._refresh_header()
        k = s.chip
        link = s.chip_link(k)
        self.meta.setText('%d registers · %s via %s' % (len(s.profile.registers), s.profile.chips[k].label,
                                                          link.short if link else '?'))
        self.banner.setVisible(not s.online(k))
        if not s.online(k):
            self.banner_text.setText('%s hangs on %s, which is not connected. You can still edit; changes wait '
                                     'until it is back.' % (s.profile.chips[k].label, link.name if link else s.profile.chips[k].link))
        self.rail.refresh(kinds | {'values'})
        self.pick_panel.refresh()
        self._refresh_inspector(kinds)
        self.status_text.setText(s.status)
        if 'links' in kinds and self.links_panel.isVisible():
            self.links_panel.rebuild()

    def _refresh_header(self):
        s = self.s
        on = s.pending_count(online_only=True)
        allp = s.pending_count()
        self.write_btn.setText('Write %d register%s' % (on, '' if on == 1 else 's') if on else
                               ('%d waiting for a link' % allp if allp else 'Write'))
        self.write_btn.setEnabled(on > 0)
        self.discard_btn.setVisible(allp > 0)
        self.auto_btn.setChecked(s.auto)
        self.auto_btn.update()

    def _build_chip_tabs(self):
        s = self.s
        for b in self.chip_group.buttons():
            self.chip_group.removeButton(b)
            b.deleteLater()
        self.chip_bar.setVisible(len(s.profile.chips) > 1)
        if len(s.profile.chips) < 2:
            return
        for k, chip in enumerate(s.profile.chips):
            link = s.chip_link(k)
            b = QtWidgets.QPushButton('%s  %s' % (chip.label, link.short if link else '?'))
            b.setProperty('chipTab', True)
            b.setCheckable(True)
            b.setChecked(k == s.chip)
            b.setIcon(dot_icon(s.online(k), '#FFFFFF' if k == s.chip else '#1D4E89'))
            b.setToolTip('%s on %s%s' % (chip.label, link.name if link else chip.link, '' if s.online(k) else ' · offline'))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _c=False, k=k: self.s.set_chip(k))
            self.chip_group.addButton(b)
            self.chip_lay.addWidget(b)

    def _refresh_inspector(self, kinds):
        s = self.s
        kind, n = s.sel
        if kind == 'watch' and n < len(s.profile.watches):
            self.insp_stack.setCurrentWidget(self.watch_insp)
            key = ('w', n, id(s.profile.watches[n]))
            if key != self._insp_key or kinds & {'profile', 'watches'}:
                self._insp_key = key
                self.watch_insp.key = None if kinds & {'profile', 'watches'} else self.watch_insp.key
                self.watch_insp.show_watch(n)
            else:
                self.watch_insp.update_values()
        else:
            self.insp_stack.setCurrentWidget(self.reg_insp)
            i = n if kind == 'reg' and n < len(s.profile.registers) else 0
            if ('r', i) != self._insp_key or kinds & {'profile', 'layout'}:
                self._insp_key = ('r', i)
                if kinds & {'profile', 'layout'}:
                    self.reg_insp.key = None
                self.reg_insp.show_reg(i)
            else:
                self.reg_insp.update_values()

    # ------------------------------------------------------------ actions
    def run(self, fn, *args):
        """Call a session or link operation; show link errors instead of crashing."""
        try:
            return fn(*args)
        except LinkError as e:
            self.s.say('Error: %s' % e)
            QtWidgets.QMessageBox.critical(self, 'SPI Error', str(e))
        except Exception as e:
            traceback.print_exc()
            self.s.say('Error: %s' % e)
            QtWidgets.QMessageBox.critical(self, 'Error', '%s: %s' % (type(e).__name__, e))
        return None

    def set_view(self, n):
        self.stack.setCurrentIndex(n)
        (self.tiles_btn if n == 0 else self.bits_btn).setChecked(True)
        if n == 1:
            self.bitsmap.relayout()

    def show_links(self):
        self.links_panel.rebuild()
        pos = self.links_btn.mapToGlobal(QtCore.QPoint(0, self.links_btn.height() + 6))
        self.links_panel.move(pos)
        self.links_btn.setChecked(True)
        self.links_panel.show()

    def toggle_link(self, link):
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.run(link.disconnect if link.connected else link.connect)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        chips = [c.label for c in self.s.profile.chips if c.link == link.id]
        self.s.say('%s %s%s' % (link.name, 'connected' if link.connected else 'disconnected',
                                ' · %s %s' % (', '.join(chips), 'online' if link.connected else 'offline') if chips else ''))
        self.s.emit('links')

    def reconnect_current(self):
        link = self.s.chip_link(self.s.chip)
        if link is not None and not link.connected:
            self.toggle_link(link)

    def discover(self):
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            found = self.run(self.links.discover)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        if found is not None:
            self.s.say('Discover on UDP 5006 · %d board%s answered' % (len(found), '' if len(found) == 1 else 's'))
        self.s.emit('links')
        self.show_links()

    def connect_found(self, name):
        link = self.run(self.links.connect_found, name)
        if link is not None:
            self.s.say('%s connected at %s' % (link.name, link.addr))
        self.s.emit('links')

    def set_simulate(self, on):
        if on == self.links.simulate:
            return
        self.links.set_simulate(on)
        self.settings.setValue('simulate', bool(on))
        self.s.say('Simulated hardware %s · connect a link to use it' % ('on' if on else 'off'))
        self.s.emit('links')

    def configure_links(self, clock_khz=None, voltage=None):
        self.links.configure_ni(clock_khz or self.links.clock_khz, voltage or self.links.voltage)
        self.settings.setValue('clock_khz', self.links.clock_khz)
        self.settings.setValue('voltage', self.links.voltage)

    # ------------------------------------------------------------ files
    def _dir(self):
        return self.settings.value('last_dir', HERE, type=str)

    def open_dialog(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open profile or old table', self._dir(), FILE_FILTER)
        if path:
            self.open_path(path)

    def open_path(self, path, quiet=False):
        try:
            if path.lower().endswith('.json'):
                profile, values = m.load_profile(path), None
            else:
                import FileIO
                data, shortcut = FileIO.load(path)
                rows = data.to_dict('records')
                name = os.path.splitext(os.path.basename(path))[0]
                profile, values = m.profile_from_table(rows, name, path)
                if shortcut is not None:
                    profile.watches += m.watches_from_shortcuts(rows, shortcut.to_dict('records'))
        except Exception as e:
            traceback.print_exc()
            if not quiet:
                QtWidgets.QMessageBox.critical(self, 'Open failed', '%s\n\n%s: %s' % (path, type(e).__name__, e))
            return False
        self.settings.setValue('last_path', path)
        self.settings.setValue('last_dir', os.path.dirname(path))
        self.s.load(profile, values)
        return True

    def save_profile_dialog(self):
        p = self.s.profile
        start = p.path if p.path.lower().endswith('.json') else os.path.join(self._dir(), p.name + '.profile.json')
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save profile', start, 'Profile (*.json)')
        if path:
            self.run(m.save_profile, p, path)
            self.settings.setValue('last_path', path)
            self.s.say('Saved profile %s' % os.path.basename(path))

    def save_values_dialog(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save values', os.path.join(
            self._dir(), self.s.profile.name + '.values.json'), 'Values (*.json)')
        if path:
            self.run(m.save_values, self.s, path)
            self.s.say('Saved values to %s' % os.path.basename(path))

    def load_values_dialog(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Load values', self._dir(), 'Values (*.json)')
        if path:
            values = self.run(m.load_values, path)
            if values is not None:
                self.s.apply_values(values)
                self.s.say('Loaded %s as unsent changes' % os.path.basename(path))
                self.s.emit('values')

    # ------------------------------------------------------------ shutdown
    def closeEvent(self, e):
        for link in self.links.all():
            if link.connected:
                try:
                    link.disconnect()
                except Exception:
                    traceback.print_exc()
        super().closeEvent(e)

    def excepthook(self, etype, value, tb):
        """Show unexpected errors instead of letting PyQt abort the process."""
        traceback.print_exception(etype, value, tb)
        try:
            QtWidgets.QMessageBox.critical(self, 'Unexpected error', '%s: %s' % (etype.__name__, value))
        except Exception:
            pass


def main():
    QtWidgets.QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(QtGui.QFont('Segoe UI', 9))
    app.setStyleSheet(QSS)
    app.setWindowIcon(QtGui.QIcon(os.path.join(HERE, 'tokyotech.ico')))
    win = MainWindow(sys.argv[1] if len(sys.argv) > 1 else None)
    sys.excepthook = win.excepthook
    win.resize(1440, 900)
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
