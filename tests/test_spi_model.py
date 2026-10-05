"""Tests for spi_model / spi_links (no Qt, no hardware: every link is simulated)."""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import spi_model as m                   # noqa: E402
from spi_links import LinkSet, LinkError  # noqa: E402


def table_rows(name):
    import FileIO
    data, _ = FileIO.load(os.path.join(ROOT, name))
    return data.to_dict('records')


def session_for(profile, values=None, connect=True):
    links = LinkSet(simulate=True)
    s = m.Session(links)
    s.load(profile, values)
    if connect:
        for chip in profile.chips:
            links.get(chip.link).connect()
    return s


class ParseTests(unittest.TestCase):
    def test_parse_value(self):
        self.assertEqual(m.parse_value('0x3ff', 1023), (1023, None))
        self.assertEqual(m.parse_value('0b101', 31), (5, None))
        self.assertEqual(m.parse_value('  12 ', 31), (12, None))
        self.assertEqual(m.parse_value('', 31), (None, None))
        self.assertIsNotNone(m.parse_value('32', 31)[1])
        self.assertIsNotNone(m.parse_value('0x', 31)[1])
        self.assertIsNotNone(m.parse_value('abc', 31)[1])

    def test_range_round_trip(self):
        w = m.Watch('div', [(28, 3), (28, 4), (29, 0), (29, 1), (29, 2), (29, 3), (29, 4), (30, 0), (30, 1), (30, 2)])
        self.assertEqual(w.range_text(), 'A30[2:0], A29[4:0], A28[4:3]')
        w.frac = 2
        self.assertEqual(w.range_text(), 'A30[2:0], A29[4:0].A28[4:3]')
        self.assertEqual(w.width_label(), '[7:-2]')
        self.assertEqual(m.parse_range(w.range_text()), (w.bits, 2))
        self.assertEqual(m.parse_range('A13[4:3].A14[0]'), ([(14, 0), (13, 3), (13, 4)], 1))

    def test_fixed_point_input(self):
        w = m.Watch('fx', [(14, 0), (13, 3), (13, 4)], frac=1)
        self.assertEqual(m.parse_watch_value('1.5', w), (3, None))
        self.assertEqual(m.parse_watch_value('0b111', w), (7, None))
        self.assertIsNotNone(m.parse_watch_value('9', w)[1])
        self.assertEqual(w.fmt(3), '1.5')


class ImportTests(unittest.TestCase):
    def test_1020(self):
        p, values = m.profile_from_table(table_rows('1020.csv'), '1020')
        self.assertEqual(p.protocol, m.CLASSIC)
        self.assertEqual([c.label for c in p.chips], ['SS0'])
        self.assertEqual(len(p.registers), 64)
        a13 = p.registers[p.index(13)]
        self.assertEqual([f.name for f in a13.fields], ['reset', 'clk_enable', 'FLL_en', 'FLL_frozen', 'FLL_dsm_frozen'])
        self.assertEqual(p.registers[p.index(111)].width, 13)
        self.assertEqual(len(p.registers[p.index(111)].fields), 1)        # duplicate rows merged
        names = [w.name for w in p.watches]
        self.assertIn('div_ratio_spi', names)
        self.assertIn('FCW_IN', names)
        self.assertIn('PLL_LF_overide', p.skipped)
        s = session_for(p, values)
        w = p.watches[names.index('div_ratio_spi')]
        self.assertEqual(s.watch_raw(w), 292)
        self.assertEqual(s.val[0][p.index(131)], 900)

    def test_fband(self):
        p, values = m.profile_from_table(table_rows('202105TO_Fband_WB_TX_only_v1_TX1_TX2_TX3_TX4_0deg.csv'), 'fband')
        self.assertEqual(len(p.chips), 4)
        self.assertEqual(len(p.registers), 87)
        v45 = p.registers[p.index(31)]
        self.assertEqual(v45.title(), 'V45')
        self.assertEqual(v45.shown_bits(), list(range(9, -1, -1)))
        self.assertIsNotNone(v45.scaled_field())
        s = session_for(p, values)
        self.assertTrue(s.pending(0, p.index(31)))       # preset values are unsent until written


class SessionTests(unittest.TestCase):
    def setUp(self):
        p = m.Profile('t', m.CLASSIC, [m.Chip('SS0', 'ni', 0), m.Chip('SS1', 'pico:#1', 1)],
                      [m.Register(1, 5, fields=[m.Field('a', 0, 2), m.Field('b', 2, 3)]),
                       m.Register(2, 13, fields=[m.Field('dac', 0, 10, 0.0, 1.0)]),
                       m.Register(3, 13, ro=True)])
        self.s = session_for(p, connect=False)
        self.s.links.get('ni').connect()

    def test_read_modify_write_keeps_unknown_bits(self):
        s = self.s
        sim = s.links.get('ni').backend
        sim.mem[(0, None, 1)] = 0b10110
        s.set_field(0, s.reg(0).fields[0], 0b01)      # only field a is known
        self.assertEqual(s.val[0][0], 0b01)
        s.write_one(0)
        self.assertEqual(sim.mem[(0, None, 1)], 0b10101)
        self.assertEqual(s.val[0][0], 0b10101)
        self.assertFalse(s.pending(0, 0))

    def test_offline_chip_waits(self):
        s = self.s
        s.set_chip(1)
        s.toggle_bit(1, 3)
        self.assertEqual(s.pending_count(online_only=True), 0)
        s.write_all()
        self.assertIn('waiting for Pico #1', s.status)
        s.links.get('pico:#1').connect()
        s.write_all()
        self.assertEqual(s.pending_count(), 0)

    def test_auto_write_and_readonly(self):
        s = self.s
        s.set_auto(True)
        s.type_value(1, '0x200')
        self.assertEqual(s.chipv[0][1], 0x200)
        s.set_value(2, 5)
        self.assertIsNone(s.val[0][2])                  # read-only register ignores edits
        s.set_chip(1)
        s.toggle_bit(0, 1)
        self.assertIn('kept unsent', s.status)

    def test_pick_and_fixed_point_watch(self):
        s = self.s
        s.start_pick()
        s.pick_bit(1, 4)
        s.pick_bit(1, 3)
        s.pick_point()
        s.pick_bit(2, 0)
        self.assertEqual([lab for lab, _ in s.pick_labels()], ['0', '1', '', '.0'])
        s.pick_rename('FX')
        self.assertTrue(s.save_pick())
        w = s.profile.watches[-1]
        self.assertEqual((w.width_label(), w.frac), ('[1:-1]', 1))
        s.type_watch(len(s.profile.watches) - 1, '2.5')
        self.assertEqual(s.watch_raw(w), 5)
        self.assertEqual(s.val[0][0] >> 3, 0b10)
        s.start_pick(edit=len(s.profile.watches) - 1)
        self.assertEqual(len(s.pick['seq']), 4)
        s.pick_drop(2)
        s.save_pick()
        self.assertEqual(s.profile.watches[-1].frac, 0)

    def test_link_errors_propagate(self):
        s = self.s
        s.set_chip(1)
        with self.assertRaises(LinkError):
            s.read_reg(1, 0)

    def test_profile_json_round_trip(self):
        s = self.s
        s.start_pick()
        s.pick_bit(1, 4)
        s.pick_bit(2, 9)
        s.save_pick()
        path = os.path.join(tempfile.mkdtemp(), 'p.json')
        m.save_profile(s.profile, path)
        p2 = m.load_profile(path)
        self.assertEqual([c.link for c in p2.chips], ['ni', 'pico:#1'])
        self.assertEqual(p2.registers[1].fields[0].vmax, 1.0)
        self.assertTrue(p2.registers[2].ro)
        self.assertEqual(p2.watches[-1].bits, s.profile.watches[-1].bits)


if __name__ == '__main__':
    unittest.main()
