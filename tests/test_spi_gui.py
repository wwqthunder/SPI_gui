"""Headless smoke test of the SpiControl window: offscreen Qt, simulated links, real clicks."""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ['SPICONTROL_INI'] = os.path.join(tempfile.mkdtemp(), 'settings.ini')

from PyQt5 import QtCore, QtTest, QtWidgets   # noqa: E402
from PyQt5.QtCore import Qt                    # noqa: E402

APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

import SpiControl                               # noqa: E402
from spi_widgets import QSS                     # noqa: E402

ERRORS = []


def pump(n=3):
    for _ in range(n):
        APP.processEvents()


def click(widget, rect):
    QtTest.QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, rect.center())
    pump()


class GuiSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        APP.setStyleSheet(QSS)
        sys.excepthook = lambda t, v, tb: ERRORS.append('%s: %s' % (t.__name__, v))
        QtWidgets.QMessageBox.critical = staticmethod(lambda *a, **k: ERRORS.append('dialog: %s' % (a[2],)))
        QtWidgets.QMessageBox.question = staticmethod(lambda *a, **k: QtWidgets.QMessageBox.Yes)
        cls.win = SpiControl.MainWindow(os.path.join(ROOT, '1020.csv'))
        cls.win.resize(1440, 900)
        cls.win.show()
        cls.win.set_simulate(True)
        cls.win.toggle_link(cls.win.links.get('ni'))
        pump(5)

    @classmethod
    def tearDownClass(cls):
        cls.win.close()
        pump()

    def setUp(self):
        del ERRORS[:]

    def tearDown(self):
        self.assertEqual(ERRORS, [])

    def test_1_tiles_click_and_type(self):
        win, s = self.win, self.win.s
        grid = win.tiles
        self.assertEqual(len(grid.geo), 64)
        i13 = s.profile.index(13)
        g = grid.geo[i13]
        before = s.val[0][i13]
        bit, rect = g['bits'][2]                     # FLL_en
        click(grid, rect)
        self.assertEqual(s.val[0][i13], before ^ (1 << bit))
        self.assertTrue(s.pending(0, i13))
        self.assertEqual(s.sel, ('reg', i13))
        self.assertIn('FLL_en', win.reg_insp.bits.items[2]['tip'])
        self.assertTrue(win.write_btn.isEnabled())
        click(grid, g['value'])                      # opens the in-place editor
        self.assertTrue(grid.editor.isVisible())
        grid.editor.setText('0x1f')
        QtTest.QTest.keyClick(grid.editor, Qt.Key_Return)
        pump()
        self.assertEqual(s.val[0][i13], 31)
        self.assertFalse(grid.editor.isVisible())
        click(grid, g['value'])
        grid.editor.setText('99')                    # too big for 5 bits: stays open, marked bad
        QtTest.QTest.keyClick(grid.editor, Qt.Key_Return)
        pump()
        self.assertTrue(grid.editor.isVisible())
        self.assertTrue(grid.editor.property('bad'))
        QtTest.QTest.keyClick(grid.editor, Qt.Key_Escape)
        pump()
        self.assertFalse(grid.editor.isVisible())
        self.assertEqual(s.val[0][i13], 31)
        win.write_btn.click()
        pump()
        self.assertEqual(s.pending_count(), 0)
        win.read_all_btn.click()
        pump()
        self.assertIn('R  64 registers', s.status)

    def test_2_watch_and_pick(self):
        win, s = self.win, self.win.s
        names = [w.name for w in s.profile.watches]
        wi = names.index('div_ratio_spi')
        item = win.rail.tree.topLevelItem(wi)
        win.rail.tree.itemClicked.emit(item, 0)
        pump()
        self.assertIs(win.insp_stack.currentWidget(), win.watch_insp)
        win.watch_insp.edit.setText('300')
        win.watch_insp.edit.editingFinished.emit()
        pump()
        self.assertEqual(s.watch_raw(s.profile.watches[wi]), 300)
        # the Picker, on the tiles
        s.start_pick()
        pump()
        self.assertTrue(win.pick_panel.isVisible())
        grid = win.tiles
        g = grid.geo[s.profile.index(14)]
        click(grid, g['bits'][0][1])
        click(grid, g['bits'][1][1])
        win.pick_panel.point_btn.click()
        click(grid, g['bits'][2][1])
        pump()
        self.assertEqual(win.pick_panel.flow.count(), 4)
        win.pick_panel.name.setText('MY_FIX')
        win.pick_panel.save_btn.click()
        pump()
        w = s.profile.watches[-1]
        self.assertEqual((w.name, w.frac, w.width), ('MY_FIX', 1, 3))
        self.assertIs(win.insp_stack.currentWidget(), win.watch_insp)
        self.assertEqual(win.watch_insp.range.text(), '[1:-1]')

    def test_3_bits_view_and_files(self):
        win, s = self.win, self.win.s
        win.set_view(1)
        pump()
        i, y = win.bitsmap.rows[5]
        QtTest.QTest.mouseClick(win.bitsmap, Qt.LeftButton, Qt.NoModifier, QtCore.QPoint(60, y + 2))
        pump()
        self.assertEqual(s.sel, ('reg', i))
        win.set_view(0)
        path = os.path.join(tempfile.mkdtemp(), 'p.profile.json')
        import spi_model as m
        m.save_profile(s.profile, path)
        self.assertTrue(win.open_path(path))
        pump()
        self.assertEqual(s.profile.watches[-1].name, 'MY_FIX')

    def test_4_fband_links_offline(self):
        win, s = self.win, self.win.s
        self.assertTrue(win.open_path(os.path.join(ROOT, '202105TO_Fband_WB_TX_only_v1_TX1_TX2_TX3_TX4_0deg.csv')))
        pump()
        self.assertEqual(len(win.chip_group.buttons()), 4)
        self.assertEqual(len(win.tiles.geo), 87)
        self.assertEqual(win.write_btn.text(), 'Write 336 registers')      # A17–A19 have no value in the file
        i31 = s.profile.index(31)
        s.select_reg(i31)
        pump()
        self.assertTrue(win.reg_insp.scaled.isVisible())
        self.assertEqual(len(win.reg_insp.chip_rows), 4)
        win.reg_insp._step(-10)
        pump()
        self.assertEqual(s.val[0][i31], 1013)
        win.toggle_link(win.links.get('ni'))          # disconnect: every chip goes offline
        pump()
        self.assertTrue(win.banner.isVisible())
        self.assertIn('waiting for a link', win.write_btn.text())
        win.show_links()
        pump()
        win.discover()
        pump()
        self.assertEqual(len(win.links.found), 3)
        win.connect_found('#1')
        pump()
        self.assertTrue(win.links.get('pico:#1').connected)
        win.links_panel.hide()
        win.reconnect_current()
        pump()
        self.assertFalse(win.banner.isVisible())

    def test_6_tile_size(self):
        win, s = self.win, self.win.s
        self.assertTrue(win.open_path(os.path.join(ROOT, '202105TO_Fband_WB_TX_only_v1_TX1_TX2_TX3_TX4_0deg.csv')))
        pump()
        grid = win.tiles
        grid.set_scale(1.0)
        g = grid.geo[s.profile.index(31)]
        self.assertEqual([r.width() for _b, r in g['bits']], [12] * 10)       # V45: ten 12 x 16 px cells
        self.assertEqual(g['bits'][0][1].height(), 16)
        self.assertEqual(g['rect'].size(), QtCore.QSize(148, 67))
        QtTest.QTest.keyClick(win, Qt.Key_Minus, Qt.ControlModifier)
        pump()
        self.assertAlmostEqual(grid.k, 0.9)
        self.assertEqual(win.zoom_label.text(), '90%')
        grid.set_scale(1.4)
        pump()
        g = grid.geo[s.profile.index(31)]
        self.assertEqual(g['bits'][0][1].width(), 17)
        i31 = s.profile.index(31)
        before = s.val[0][i31]
        click(grid, g['bits'][0][1])                                         # hit testing follows the scale
        self.assertEqual(s.val[0][i31], before ^ (1 << 9))
        self.assertFalse(win.grab().isNull())
        grid.set_scale(1.0)
        self.assertEqual(float(win.settings.value('tile_scale')), 1.0)

    def test_5_styled_controls(self):
        from spi_widgets import Combo, Stepper, Switch
        win, s = self.win, self.win.s
        self.assertTrue(win.open_path(os.path.join(ROOT, '1020.csv')))
        ni = win.links.get('ni')
        if not ni.connected:
            win.toggle_link(ni)
        pump()
        self.assertEqual(win.findChildren(QtWidgets.QMenuBar), [])          # no default-styled menu bar
        i13 = s.profile.index(13)
        s.select_reg(i13)
        pump()
        switches = [c for _f, c in win.reg_insp.field_ctl]
        self.assertTrue(all(isinstance(c, Switch) for c in switches))
        before = s.val[0][i13]
        QtTest.QTest.mouseClick(switches[0], Qt.LeftButton)          # MSB field first: FLL_dsm_frozen
        pump()
        self.assertEqual(s.val[0][i13], before ^ (1 << 4))
        i29 = s.profile.index(29)
        s.select_reg(i29)
        pump()
        (_f, stepper), = win.reg_insp.field_ctl
        self.assertIsInstance(stepper, Stepper)
        v = s.val[0][i29]
        stepper.plus.click()
        pump()
        self.assertEqual(s.val[0][i29], v + 1)
        stepper.edit.setText('0b111')
        stepper.edit.editingFinished.emit()
        pump()
        self.assertEqual(s.val[0][i29], 7)
        win.auto_btn.click()
        pump()
        self.assertTrue(s.auto)
        win.auto_btn.click()
        pump()
        win.toggle_link(ni)                                           # combos appear for a disconnected link
        self.assertFalse(ni.connected)
        win.show_links()
        pump()
        combos = win.links_panel.findChildren(Combo)
        self.assertEqual(len(combos), 2)
        combos[0].setCurrentIndex(3)
        self.assertEqual(win.links.clock_khz, 50)
        for state in (win, win.links_panel):                          # paint every widget once
            self.assertFalse(state.grab().isNull())
        win.links_panel.hide()
        win.set_view(1)
        self.assertFalse(win.grab().isNull())
        win.set_view(0)
        s.start_pick()
        pump()
        self.assertFalse(win.grab().isNull())
        s.cancel_pick()


if __name__ == '__main__':
    unittest.main()
