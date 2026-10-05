"""Core model of the register-array SPI GUI (no Qt here, so it tests with plain Python).

A *profile* is the only chip-specific input: the protocol, the chips (the link and
chip select each one hangs on), the register addresses and widths, and optional
field names.  Everything the GUI shows is derived from it.
"""
import json
import math
import os
import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field as dc_field
from typing import List, Optional, Tuple

CLASSIC = 'classic'
CA = 'ca'

BUS_ONE = re.compile(r'^([A-Za-z_]\w*)<(\d+)(?::(\d+))?>$')      # FLL_KP<3> or FCW_IN<5:9>
BUS_ANY = re.compile(r'([A-Za-z_]\w*)<\d+(?::\d+)?>')
RANGE_ITEM = re.compile(r'^A?(\d+)\[(\d+)(?::(\d+))?\]$')        # A30[2:0] or A28[4]


# ---------------------------------------------------------------- data classes

@dataclass
class Field:
    name: str
    lo: int
    width: int = 1
    vmin: float = 0.0
    vmax: Optional[float] = None        # set: the field is a DAC code shown as a voltage

    @property
    def hi(self):
        return self.lo + self.width - 1

    @property
    def mask(self):
        return ((1 << self.width) - 1) << self.lo

    @property
    def full(self):
        return (1 << self.width) - 1

    def volts(self, code):
        return self.vmin + (self.vmax - self.vmin) * code / self.full

    def code(self, volts):
        span = self.vmax - self.vmin
        return int(math.floor((volts - self.vmin) / span * self.full + 0.5)) if span else 0


@dataclass
class Register:
    addr: int
    width: int
    name: str = ''
    ro: bool = False
    fields: List[Field] = dc_field(default_factory=list)

    @property
    def full(self):
        return (1 << self.width) - 1

    def field_at(self, bit):
        for f in self.fields:
            if f.lo <= bit <= f.hi:
                return f
        return None

    def used(self, bit):
        """A register without fields uses every bit."""
        return not self.fields or self.field_at(bit) is not None

    def shown_bits(self):
        """Bits drawn on a tile, most significant first."""
        return [b for b in range(self.width - 1, -1, -1) if self.used(b)]

    def title(self):
        """Explicit name, else the distinct field names with bus indices stripped."""
        if self.name:
            return self.name
        seen = []
        for f in self.fields:
            base = re.sub(r'<[^>]*>', '', f.name)
            if base not in seen:
                seen.append(base)
        return ' '.join(seen)

    def bit_name(self, bit):
        """FLL_en, div_ratio_spi<5>, V45 [7] or 'unused'."""
        f = self.field_at(bit)
        if f is None:
            return 'unused' if self.fields else ''
        if f.width == 1:
            return f.name
        m = BUS_ONE.match(f.name)
        if m and m.group(3) is not None and int(m.group(3)) - int(m.group(2)) == f.width - 1:
            return '%s<%d>' % (m.group(1), int(m.group(2)) + bit - f.lo)
        return '%s [%d]' % (f.name, bit - f.lo)

    def scaled_field(self):
        if len(self.fields) == 1 and self.fields[0].vmax is not None:
            return self.fields[0]
        return None


@dataclass
class Chip:
    label: str
    link: str = 'ni'                    # link id: 'ni', 'sim' or 'pico:<name>'
    ss: int = 0
    caddr: Optional[int] = None         # chip address, CA protocol only


@dataclass
class Watch:
    """A value made of bits from any registers (the old shortcut / Picker result)."""
    name: str
    bits: List[Tuple[int, int]]         # (register address, bit), least significant first
    frac: int = 0                       # bits after the binary point
    src: str = 'picked'                 # 'names': found automatically in field names

    @property
    def width(self):
        return len(self.bits)

    @property
    def full(self):
        return (1 << len(self.bits)) - 1

    def fmt(self, raw):
        return '%.*f' % (self.frac, raw / (1 << self.frac)) if self.frac else str(raw)

    def width_label(self):
        n = len(self.bits)
        return '[%d:-%d]' % (n - self.frac - 1, self.frac) if self.frac else '[%d:0]' % (n - 1)

    def range_text(self):
        """Compact, most significant first: A30[2:0], A29[4:0].A28[4:3]"""
        msb = list(reversed(self.bits))
        int_n = len(msb) - self.frac
        runs = []
        for n, (a, b) in enumerate(msb):
            last = runs[-1] if runs else None
            if last and last['a'] == a and last['lo'] - 1 == b and n != int_n:
                last['lo'] = b
                last['end'] = n
            else:
                runs.append({'a': a, 'hi': b, 'lo': b, 'end': n})
        text = '.' if int_n == 0 and msb else ''
        for m, r in enumerate(runs):
            text += 'A%d[%d]' % (r['a'], r['hi']) if r['hi'] == r['lo'] else 'A%d[%d:%d]' % (r['a'], r['hi'], r['lo'])
            if m < len(runs) - 1:
                text += '.' if r['end'] == int_n - 1 else ', '
        return text


@dataclass
class Profile:
    name: str
    protocol: str = CLASSIC
    chips: List[Chip] = dc_field(default_factory=list)
    registers: List[Register] = dc_field(default_factory=list)
    watches: List[Watch] = dc_field(default_factory=list)
    skipped: List[str] = dc_field(default_factory=list)      # names auto-detection left out
    path: str = ''
    _idx: Optional[dict] = dc_field(default=None, repr=False, compare=False)

    def index(self, addr):
        if self._idx is None:
            self._idx = {r.addr: i for i, r in enumerate(self.registers)}
        return self._idx.get(addr, -1)

    def reindex(self):
        self._idx = None


# ---------------------------------------------------------------- helpers

def parse_addr_list(spec):
    """'1-4, 8-60' or 13 -> [1, 2, 3, 4, 8, ...]"""
    if isinstance(spec, int):
        return [spec]
    out = []
    for part in str(spec).replace(' ', '').split(','):
        if not part:
            continue
        if '-' in part:
            a, b = part.split('-', 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def seq_to_bits(seq):
    """Most-significant-first sequence, None marking the point -> (bits LSB first, frac)."""
    bits = [x for x in seq if x is not None]
    frac = 0
    if None in seq:
        frac = len([x for x in seq[seq.index(None) + 1:] if x is not None])
    return list(reversed(bits)), frac


def parse_range(text):
    """'A30[2:0], A29[4:0].A28[4:3]' -> (bits LSB first, frac)."""
    seq = []
    for part in re.split(r'([,.])', text.replace(' ', '')):
        if part == '.':
            seq.append(None)
            continue
        if part in (',', ''):
            continue
        m = RANGE_ITEM.match(part)
        if not m:
            raise ValueError('Bad range item: %s' % part)
        a, hi = int(m.group(1)), int(m.group(2))
        lo = int(m.group(3)) if m.group(3) is not None else hi
        step = -1 if hi >= lo else 1
        seq.extend((a, b) for b in range(hi, lo + step, step))
    return seq_to_bits(seq)


def parse_value(text, max_value):
    """Decimal, 0x… or 0b… -> (value, error).  Empty text gives (None, None)."""
    t = str(text).strip().lower().replace('_', '')
    if t == '':
        return None, None
    try:
        if t.startswith('0x'):
            v = int(t[2:], 16)
        elif t.startswith('0b'):
            v = int(t[2:], 2)
        elif re.match(r'^\d+$', t):
            v = int(t)
        else:
            raise ValueError
    except ValueError:
        return None, 'Enter a number: decimal, 0x… or 0b…'
    if v > max_value:
        return None, 'Out of range: 0–%d' % max_value
    return v, None


def parse_watch_value(text, watch):
    """Like parse_value; fixed-point watches also take decimals such as 12.25."""
    t = str(text).strip()
    if watch.frac and re.match(r'^(\d+\.?\d*|\.\d+)$', t):
        raw = int(math.floor(float(t) * (1 << watch.frac) + 0.5))
        if raw > watch.full:
            return None, 'Out of range: 0–%s in steps of %s' % (watch.fmt(watch.full), 1.0 / (1 << watch.frac))
        return raw, None
    return parse_value(t, watch.full)


def register_summary(regs):
    """['A1–A4, A8–A60 · 5-bit', 'A111–A116 · 13-bit, read-only', …]"""
    runs = []
    for r in regs:
        last = runs[-1] if runs else None
        if last and last['w'] == r.width and last['ro'] == r.ro and r.addr == last['end'] + 1:
            last['end'] = r.addr
        else:
            runs.append({'start': r.addr, 'end': r.addr, 'w': r.width, 'ro': r.ro})
    groups = OrderedDict()
    for run in runs:
        groups.setdefault((run['w'], run['ro']), []).append(run)
    lines = []
    for (w, ro), rs in groups.items():
        spans = ', '.join('A%d' % x['start'] if x['start'] == x['end'] else 'A%d–A%d' % (x['start'], x['end'])
                          for x in rs)
        lines.append('%s · %d-bit%s' % (spans, w, ', read-only' if ro else ''))
    return lines


def detect_watches(registers):
    """Buses from field names such as FLL_KP<0> or FCW_IN<5:9>.

    A name is trusted only when every index 0..n-1 is present, it spans more than one
    field, and it never shares a field with other signals.  Returns (watches, skipped).
    """
    found = OrderedDict()
    mixed = OrderedDict()
    for r in registers:
        for f in r.fields:
            m = BUS_ONE.match(f.name)
            lo = int(m.group(2)) if m else 0
            hi = (int(m.group(3)) if m.group(3) is not None else lo) if m else -1
            if m and hi - lo + 1 == f.width:
                key = m.group(1).lower()
                g = found.setdefault(key, {'name': m.group(1), 'bits': {}, 'fields': 0})
                for k in range(f.width):
                    g['bits'][lo + k] = (r.addr, f.lo + k)
                g['fields'] += 1
            else:
                for nm in BUS_ANY.findall(f.name):
                    mixed.setdefault(nm.lower(), nm)
    watches, skipped = [], []
    for key, g in found.items():
        idx = sorted(g['bits'])
        n = len(idx)
        complete = idx[0] == 0 and idx[-1] == n - 1
        if key in mixed or (n >= 2 and not complete):
            skipped.append(g['name'])
            continue
        if n < 2 or g['fields'] < 2:
            continue
        watches.append(Watch(g['name'], [g['bits'][k] for k in idx], 0, 'names'))
    for key, nm in mixed.items():
        if key not in found:
            skipped.append(nm)
    return watches, skipped


# ---------------------------------------------------------------- profile files

def profile_from_dict(d, path=''):
    protocol = d.get('protocol', CLASSIC)
    default_w = int(d.get('width', 10 if protocol == CA else 13))
    regs = OrderedDict()
    for entry in d.get('registers', []):
        for addr in parse_addr_list(entry['addr']):
            reg = regs.get(addr)
            if reg is None:
                reg = regs[addr] = Register(addr, int(entry.get('width', default_w)))
            elif 'width' in entry:
                reg.width = int(entry['width'])
            reg.ro = bool(entry.get('ro', reg.ro))
            reg.name = entry.get('name', reg.name)
            for fd in entry.get('fields', []):
                reg.fields.append(Field(fd['name'], int(fd.get('lo', 0)), int(fd.get('width', 1)),
                                        float(fd.get('vmin', 0.0)),
                                        None if fd.get('vmax') is None else float(fd['vmax'])))
    registers = sorted(regs.values(), key=lambda r: r.addr)
    for r in registers:
        r.fields.sort(key=lambda f: f.lo)
    chips = [Chip(c.get('label', 'SS%d' % c.get('ss', 0)), c.get('link', 'ni'), int(c.get('ss', 0)),
                  None if c.get('caddr') is None else int(c['caddr']))
             for c in d.get('chips', [{'label': 'SS0'}])]
    auto, skipped = detect_watches(registers)
    watches = list(auto)
    for wd in d.get('watches', []):
        bits, frac = parse_range(wd['range'])
        watches.append(Watch(wd['name'], bits, frac, 'picked'))
    name = d.get('name') or os.path.splitext(os.path.basename(path))[0] or 'Profile'
    return Profile(name, protocol, chips, registers, watches, skipped, path)


def profile_to_dict(p):
    regs = []
    for r in p.registers:
        e = OrderedDict([('addr', r.addr), ('width', r.width)])
        if r.name:
            e['name'] = r.name
        if r.ro:
            e['ro'] = True
        if r.fields:
            fl = []
            for f in r.fields:
                fd = OrderedDict([('name', f.name), ('lo', f.lo)])
                if f.width != 1:
                    fd['width'] = f.width
                if f.vmax is not None:
                    fd['vmin'] = f.vmin
                    fd['vmax'] = f.vmax
                fl.append(fd)
            e['fields'] = fl
        regs.append(e)
    chips = []
    for c in p.chips:
        cd = OrderedDict([('label', c.label), ('link', c.link), ('ss', c.ss)])
        if c.caddr is not None:
            cd['caddr'] = c.caddr
        chips.append(cd)
    watches = [OrderedDict([('name', w.name), ('range', w.range_text())]) for w in p.watches if w.src != 'names']
    return OrderedDict([('format', 'spi-profile/1'), ('name', p.name), ('protocol', p.protocol),
                        ('chips', chips), ('registers', regs), ('watches', watches)])


def load_profile(path):
    with open(path, 'r', encoding='utf-8') as f:
        return profile_from_dict(json.load(f), path)


def save_profile(p, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(profile_to_dict(p), f, indent=1, ensure_ascii=False)
    p.path = path


def _int(x):
    try:
        return int(float(str(x).strip()))
    except (TypeError, ValueError):
        return None


def _float(x):
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return None


def profile_from_table(rows, name, path=''):
    """Import the old SPIgui table (rows = field records with FileIO.data_headers keys).

    Returns (profile, values) where values = {chip label: {addr: (value, mask)}} holds
    the table's write values (DecW); only the bits of fields that had one are set.
    """
    ca = any(_int(r.get('CAddr')) is not None for r in rows)
    protocol = CA if ca else CLASSIC
    chip_keys = OrderedDict()
    regs = OrderedDict()
    raw_values = {}
    for r in rows:
        addr = _int(r.get('Addr'))
        if addr is None:
            continue
        term = str(r.get('Term', '') or '').strip()
        ss = _int(r.get('SS')) or 0
        caddr = _int(r.get('CAddr')) if ca else None
        key = (term, ss, caddr)
        chip_keys.setdefault(key, None)
        regsize = _int(r.get('RegSize'))
        width = 10 if ca else (regsize or 13)
        reg = regs.get(addr)
        if reg is None:
            reg = regs[addr] = Register(addr, width)
        reg.width = max(reg.width, width)
        pos = _int(r.get('Pos')) or 0
        size = _int(r.get('Size')) or width
        lo = pos - 1 if pos >= 1 else 0
        fname = str(r.get('Name', '') or '').strip()
        if fname and not any(f.name == fname and f.lo == lo and f.width == size for f in reg.fields):
            vmax = _float(r.get('VolMax'))
            vmin = _float(r.get('VolMin')) or 0.0
            scaled = size >= 8 and vmax is not None and vmax != vmin
            reg.fields.append(Field(fname, lo, size, vmin, vmax if scaled else None))
        dec = _int(r.get('DecW'))
        if dec is not None:
            fm = ((1 << size) - 1) << lo
            v, m = raw_values.setdefault(key, {}).get(addr, (0, 0))
            raw_values[key][addr] = ((v & ~fm) | ((dec << lo) & fm), m | fm)
    terms = {k[0] for k in chip_keys}
    chips, values = [], {}
    for key in chip_keys:
        term, ss, caddr = key
        label = 'SS%d' % ss
        if caddr is not None:
            label += '·C%d' % caddr
        if len(terms) > 1 and term:
            label = '%s·%s' % (term, label)
        chips.append(Chip(label, 'pico:' + term if term else 'ni', ss, caddr))
        values[label] = raw_values.get(key, {})
    if not chips:
        chips = [Chip('SS0')]
    registers = sorted(regs.values(), key=lambda x: x.addr)
    for reg in registers:
        reg.fields.sort(key=lambda f: f.lo)
    watches, skipped = detect_watches(registers)
    return Profile(name, protocol, chips, registers, watches, skipped, path), values


def watches_from_shortcuts(rows, shortcuts):
    """Old ShortCutList rows: Range such as '12[3],12[4].13[0]' = table row, bit of that row's field."""
    out = []
    for sc in shortcuts:
        name = str(sc.get('Name', '') or '').strip()
        rng = str(sc.get('Range', '') or '').replace(' ', '')
        if not name or '[' not in rng:
            continue
        seq, ok = [], True
        for part in re.split(r'([,.])', rng):
            if part == '.':
                seq.append(None)
                continue
            if part in (',', ''):
                continue
            mm = re.match(r'^(\d+)\[(\d+)\]$', part)
            r = int(mm.group(1)) - 1 if mm else -1
            addr = _int(rows[r].get('Addr')) if 0 <= r < len(rows) else None
            if addr is None:
                ok = False
                break
            pos = _int(rows[r].get('Pos')) or 0
            seq.append((addr, (pos - 1 if pos >= 1 else 0) + int(mm.group(2))))
        if ok and any(x is not None for x in seq):
            bits, frac = seq_to_bits(seq)
            out.append(Watch(name, bits, frac, 'picked'))
    return out


def blank_profile(count=64, width=5):
    return Profile('New chip', CLASSIC, [Chip('SS0', 'ni', 0)],
                   [Register(a, width) for a in range(1, count + 1)])


# ---------------------------------------------------------------- session

class Session:
    """Values and editing state of one profile, and every operation the GUI offers.

    val[k][i]      value shown for register i of chip k (None: never read nor set)
    chipv[k][i]    value the chip is known to hold (None: unknown)
    touched[k][i]  bits edited since chipv was last known.  Writing a register whose
                   chip value is unknown reads it first and replaces only these bits,
                   like the old table's read-modify-write for fields with Pos != 0.
    Link errors propagate to the caller; the GUI shows them.
    """

    def __init__(self, links):
        self.links = links
        self.profile = None
        self.val, self.chipv, self.touched = [], [], []
        self.chip = 0
        self.sel = ('reg', 0)
        self.auto = False
        self.pick = None            # {'seq': [(addr, bit) or None], 'name': str, 'edit': index or None}
        self.snapshots = []         # [{'name': str, 'values': {...}}]
        self.status = ''
        self._subs = []

    # -- notification
    def subscribe(self, fn):
        self._subs.append(fn)

    def emit(self, *kinds):
        for fn in list(self._subs):
            fn(set(kinds))

    def say(self, text, stamp=False):
        self.status = (time.strftime('%H:%M:%S') + '  ' + text) if stamp else text
        self.emit('status')

    # -- profile
    def load(self, profile, values=None, status=''):
        self.profile = profile
        n, c = len(profile.registers), len(profile.chips)
        self.val = [[None] * n for _ in range(c)]
        self.chipv = [[None] * n for _ in range(c)]
        self.touched = [[0] * n for _ in range(c)]
        self.chip = 0
        self.pick = None
        self.snapshots = []
        for chip in profile.chips:
            self.links.ensure(chip.link)
        if values:
            self.apply_values(values)
        self.sel = ('reg', 0)
        self.emit('profile')
        self.say(status or 'Loaded %s · %d registers on %d chip%s' % (
            profile.name, n, c, '' if c == 1 else 's'))

    def apply_values(self, values):
        """values: {chip label: {addr: value or (value, mask)}}; they become unsent edits."""
        for k, chip in enumerate(self.profile.chips):
            for addr, v in values.get(chip.label, {}).items():
                i = self.profile.index(int(addr))
                if i < 0:
                    continue
                reg = self.profile.registers[i]
                m = reg.full
                if isinstance(v, (list, tuple)):
                    v, m = v
                m &= reg.full
                cur = self.val[k][i] or 0
                self.val[k][i] = (cur & ~m) | (int(v) & m)
                self.touched[k][i] |= m

    def values_dict(self, only_known=True):
        out = OrderedDict()
        for k, chip in enumerate(self.profile.chips):
            out[chip.label] = OrderedDict((str(r.addr), self.val[k][i]) for i, r in enumerate(self.profile.registers)
                                          if not (only_known and self.val[k][i] is None))
        return out

    # -- queries
    def reg(self, i):
        return self.profile.registers[i]

    def chip_link(self, k):
        return self.links.get(self.profile.chips[k].link)

    def online(self, k):
        link = self.chip_link(k)
        return link is not None and link.connected

    def pending(self, k, i):
        v = self.val[k][i]
        return v is not None and not self.reg(i).ro and v != self.chipv[k][i]

    def pending_count(self, online_only=False):
        n = 0
        for k in range(len(self.profile.chips)):
            if online_only and not self.online(k):
                continue
            n += sum(1 for i in range(len(self.profile.registers)) if self.pending(k, i))
        return n

    def differs(self, i):
        if len(self.val) < 2:
            return False
        first = self.val[0][i]
        return any(row[i] != first for row in self.val[1:])

    # -- selection
    def select_reg(self, i):
        if 0 <= i < len(self.profile.registers) and self.sel != ('reg', i):
            self.sel = ('reg', i)
            self.emit('select')

    def select_watch(self, wi):
        if 0 <= wi < len(self.profile.watches):
            self.sel = ('watch', wi)
            self.emit('select')

    def set_chip(self, k):
        if 0 <= k < len(self.profile.chips) and k != self.chip:
            self.chip = k
            self.emit('chip')

    def set_auto(self, on):
        self.auto = bool(on)
        self.emit('values')

    # -- editing (chip k defaults to the current chip)
    def _edit(self, k, i, v, mask):
        reg = self.reg(i)
        if reg.ro:
            return
        m = mask & reg.full
        cur = self.val[k][i] or 0
        self.val[k][i] = (cur & ~m) | (int(v) & m)
        self.touched[k][i] |= m
        if self.auto:
            if self.online(k):
                self.write_reg(k, i)
                self.say('W  %s  A%d %s  0x%X  ok' % (self.profile.chips[k].label, reg.addr, reg.title(), self.val[k][i]), True)
            else:
                self.say('%s A%d kept unsent · %s is offline' % (self.profile.chips[k].label, reg.addr,
                                                                  self.chip_link(k).name if self.chip_link(k) else 'no link'))

    def set_value(self, i, v, k=None, mask=None):
        k = self.chip if k is None else k
        reg = self.reg(i)
        try:
            self._edit(k, i, max(0, min(reg.full, int(v))), reg.full if mask is None else mask)
        finally:
            self.emit('values')

    def toggle_bit(self, i, b, k=None):
        k = self.chip if k is None else k
        cur = self.val[k][i] or 0
        self.set_value(i, cur ^ (1 << b), k, 1 << b)

    def set_field(self, i, f, code, k=None):
        code = max(0, min(f.full, int(code)))
        self.set_value(i, code << f.lo, k, f.mask)

    def type_value(self, i, text, k=None):
        """Returns an error message, or None when the value was taken (or nothing typed)."""
        reg = self.reg(i)
        v, err = parse_value(text, reg.full)
        if err:
            self.say('A%d: %s' % (reg.addr, err))
            return err
        if v is not None:
            self.set_value(i, v, k)
        return None

    def copy_to_all(self, i):
        v = self.val[self.chip][i]
        if v is None:
            return
        try:
            for k in range(len(self.profile.chips)):
                if k != self.chip:
                    self._edit(k, i, v, self.reg(i).full)
            self.say('Copied %s A%d to all chips%s' % (self.profile.chips[self.chip].label, self.reg(i).addr,
                                                      '' if self.auto else ' · not sent yet'))
        finally:
            self.emit('values')

    def rename(self, i, name):
        self.reg(i).name = name.strip()
        self.emit('names')

    def set_width(self, i, w):
        reg = self.reg(i)
        if reg.fields or w == reg.width:
            return
        reg.width = w
        for rows in (self.val, self.chipv):
            for row in rows:
                if row[i] is not None:
                    row[i] &= reg.full
        for row in self.touched:
            row[i] &= reg.full
        self.emit('layout')

    def discard(self):
        self.val = [list(row) for row in self.chipv]
        self.touched = [[0] * len(row) for row in self.chipv]
        self.say('Unsent changes discarded')
        self.emit('values')

    # -- I/O (link errors propagate)
    def _got(self, k, i, v):
        v &= self.reg(i).full
        self.chipv[k][i] = v
        t = self.touched[k][i]
        cur = self.val[k][i]
        if cur is None or not t:
            self.val[k][i] = v
            self.touched[k][i] = 0
        else:
            self.val[k][i] = (v & ~t) | (cur & t)       # keep the unsent bits
            if self.val[k][i] == v:
                self.touched[k][i] = 0

    def read_reg(self, k, i):
        chip, reg = self.profile.chips[k], self.reg(i)
        self._got(k, i, self.chip_link(k).read(chip, reg, self.profile.protocol))

    def write_reg(self, k, i):
        chip, reg = self.profile.chips[k], self.reg(i)
        v = self.val[k][i]
        if reg.ro or v is None:
            return False
        link = self.chip_link(k)
        t = self.touched[k][i] & reg.full
        if self.chipv[k][i] is None and t != reg.full:
            cur = link.read(chip, reg, self.profile.protocol) & reg.full     # read-modify-write
            v = (cur & ~t) | (v & t)
            self.val[k][i] = v
        link.write(chip, reg, v, self.profile.protocol)
        self.chipv[k][i] = v
        self.touched[k][i] = 0
        return True

    def _offline_msg(self, k):
        link = self.chip_link(k)
        return '%s is offline · %s is not connected' % (self.profile.chips[k].label, link.name if link else 'its link')

    def read_one(self, i):
        k = self.chip
        if not self.online(k):
            return self.say(self._offline_msg(k))
        try:
            self.read_reg(k, i)
            self.say('R  %s  A%d %s  0x%X' % (self.profile.chips[k].label, self.reg(i).addr, self.reg(i).title(),
                                               self.chipv[k][i]), True)
        finally:
            self.emit('values')

    def write_one(self, i):
        k = self.chip
        if not self.online(k):
            return self.say(self._offline_msg(k))
        try:
            if self.write_reg(k, i):
                self.say('W  %s  A%d %s  0x%X  ok' % (self.profile.chips[k].label, self.reg(i).addr,
                                                       self.reg(i).title(), self.chipv[k][i]), True)
        finally:
            self.emit('values')

    def write_all(self):
        n, waiting, idle = 0, 0, []
        try:
            for k in range(len(self.profile.chips)):
                for i in range(len(self.profile.registers)):
                    if not self.pending(k, i):
                        continue
                    if not self.online(k):
                        waiting += 1
                        name = self.chip_link(k).name if self.chip_link(k) else self.profile.chips[k].link
                        if name not in idle:
                            idle.append(name)
                        continue
                    self.write_reg(k, i)
                    n += 1
            self.say('W  %d register%s written, one frame each  ok%s' % (
                n, '' if n == 1 else 's', ' · %d waiting for %s' % (waiting, ', '.join(idle)) if waiting else ''), True)
        except Exception:
            self.say('W  stopped after %d register%s' % (n, '' if n == 1 else 's'), True)
            raise
        finally:
            self.emit('values')

    def read_all(self):
        n, skipped = 0, []
        try:
            for k in range(len(self.profile.chips)):
                if not self.online(k):
                    skipped.append(self.profile.chips[k].label)
                    continue
                for i in range(len(self.profile.registers)):
                    self.read_reg(k, i)
                    n += 1
            self.say('R  %d register%s%s' % (n, '' if n == 1 else 's',
                                            ' · %s skipped, offline' % ', '.join(skipped) if skipped else ''), True)
        except Exception:
            self.say('R  stopped after %d register%s' % (n, '' if n == 1 else 's'), True)
            raise
        finally:
            self.emit('values')

    def reset_chips(self):
        done = []
        for k, chip in enumerate(self.profile.chips):
            if self.online(k):
                self.chip_link(k).reset(chip, self.profile.protocol)
                done.append(chip.label)
        self.chipv = [[None] * len(row) for row in self.chipv]
        self.touched = [[(r.full if v is not None else 0) for r, v in zip(self.profile.registers, row)]
                        for row in self.val]
        self.say('RST  cmd 7 sent to %s' % (', '.join(done) or 'no chip (nothing connected)'), True)
        self.emit('values')

    # -- watches
    def watch_raw(self, w, k=None):
        k = self.chip if k is None else k
        raw = 0
        for n, (a, b) in enumerate(w.bits):
            i = self.profile.index(a)
            v = self.val[k][i] if i >= 0 else None
            if v is not None and (v >> b) & 1:
                raw |= 1 << n
        return raw

    def watch_regs(self, w):
        """Register indices a watch touches, most significant first."""
        out = []
        for a, _b in reversed(w.bits):
            i = self.profile.index(a)
            if i >= 0 and i not in out:
                out.append(i)
        return out

    def set_watch(self, wi, raw, k=None):
        k = self.chip if k is None else k
        w = self.profile.watches[wi]
        raw = max(0, min(w.full, int(raw)))
        per = OrderedDict()
        for n, (a, b) in enumerate(w.bits):
            i = self.profile.index(a)
            if i < 0 or self.reg(i).ro:
                continue
            v, m = per.get(i, (0, 0))
            per[i] = (v | (((raw >> n) & 1) << b), m | (1 << b))
        auto = self.auto
        try:
            self.auto = False
            for i, (v, m) in per.items():
                self._edit(k, i, v, m)
            if auto and self.online(k):
                for i in per:
                    if self.pending(k, i):
                        self.write_reg(k, i)
                self.say('W  %s  %s = %s  (%d register%s)  ok' % (self.profile.chips[k].label, w.name, w.fmt(raw),
                                                                   len(per), '' if len(per) == 1 else 's'), True)
            elif auto:
                self.say('%s kept unsent · %s' % (w.name, self._offline_msg(k)))
        finally:
            self.auto = auto
            self.emit('values')

    def type_watch(self, wi, text):
        w = self.profile.watches[wi]
        raw, err = parse_watch_value(text, w)
        if err:
            self.say('%s: %s' % (w.name, err))
            return err
        if raw is not None:
            self.set_watch(wi, raw)
        return None

    def read_watch(self, wi):
        k = self.chip
        if not self.online(k):
            return self.say(self._offline_msg(k))
        w = self.profile.watches[wi]
        try:
            for i in self.watch_regs(w):
                self.read_reg(k, i)
            self.say('R  %s  %s = %s' % (self.profile.chips[k].label, w.name, w.fmt(self.watch_raw(w))), True)
        finally:
            self.emit('values')

    def write_watch(self, wi):
        k = self.chip
        if not self.online(k):
            return self.say(self._offline_msg(k))
        w = self.profile.watches[wi]
        try:
            n = sum(1 for i in self.watch_regs(w) if self.pending(k, i) and self.write_reg(k, i))
            self.say('W  %s  %s = %s  (%d register%s)  ok' % (self.profile.chips[k].label, w.name,
                                                               w.fmt(self.watch_raw(w)), n, '' if n == 1 else 's'), True)
        finally:
            self.emit('values')

    def delete_watch(self, wi):
        w = self.profile.watches.pop(wi)
        regs = self.watch_regs(w)
        self.pick = None
        self.sel = ('reg', regs[0] if regs else 0)
        self.say('Deleted watch %s' % w.name)
        self.emit('watches', 'select', 'pick')

    # -- picking bits (the old Picker window, now done on the tiles)
    def start_pick(self, edit=None):
        if edit is None:
            self.pick = {'seq': [], 'name': '', 'edit': None}
        else:
            w = self.profile.watches[edit]
            seq = list(reversed(w.bits))
            if w.frac:
                seq.insert(len(seq) - w.frac, None)
            self.pick = {'seq': seq, 'name': w.name, 'edit': edit}
            self.sel = ('watch', edit)
        self.emit('pick', 'select')

    def cancel_pick(self):
        self.pick = None
        self.emit('pick')

    def _set_seq(self, seq):
        self.pick['seq'] = seq
        self.emit('pick')

    def pick_bit(self, a, b):
        if self.pick is None:
            return
        seq = self.pick['seq']
        self._set_seq([x for x in seq if x != (a, b)] if (a, b) in seq else seq + [(a, b)])

    def pick_point(self):
        if self.pick is not None:
            seq = self.pick['seq']
            self._set_seq([x for x in seq if x is not None] if None in seq else seq + [None])

    def pick_undo(self):
        if self.pick and self.pick['seq']:
            self._set_seq(self.pick['seq'][:-1])

    def pick_clear(self):
        if self.pick is not None:
            self._set_seq([])

    def pick_drop(self, n):
        if self.pick is not None:
            self._set_seq([x for m, x in enumerate(self.pick['seq']) if m != n])

    def pick_rename(self, name):
        if self.pick is not None:
            self.pick['name'] = name

    def pick_labels(self):
        """[(position label, (addr, bit) or None)] in order, e.g. ('0', (13, 4)), ('', None), ('.0', …)."""
        out, ip, fp, after = [], 0, 0, False
        for x in (self.pick['seq'] if self.pick else []):
            if x is None:
                after = True
                out.append(('', None))
            elif after:
                out.append(('.%d' % fp, x))
                fp += 1
            else:
                out.append((str(ip), x))
                ip += 1
        return out

    def pick_watch(self):
        bits, frac = seq_to_bits(self.pick['seq'] if self.pick else [])
        return Watch(self.pick['name'].strip() if self.pick else '', bits, frac)

    def save_pick(self):
        if not self.pick:
            return False
        w = self.pick_watch()
        if not w.bits:
            return False
        edit = self.pick['edit']
        idx = edit if edit is not None else len(self.profile.watches)
        w.name = w.name or 'watch_%d' % (idx + 1)
        if edit is not None:
            self.profile.watches[edit] = w
        else:
            self.profile.watches.append(w)
        self.pick = None
        self.sel = ('watch', idx)
        self.say('%s watch %s · %s' % ('Updated' if edit is not None else 'Added', w.name, w.range_text()))
        self.emit('watches', 'select', 'pick')
        return True

    # -- snapshots (replace the old preset files)
    def take_snapshot(self, name=None):
        snap = {'name': name or 'Snapshot %d · %s' % (len(self.snapshots) + 1, time.strftime('%H:%M')),
                'values': self.values_dict()}
        self.snapshots.append(snap)
        self.say('Saved %s' % snap['name'])
        self.emit('snapshots')
        return snap

    def restore_snapshot(self, n):
        snap = self.snapshots[n]
        self.apply_values(snap['values'])
        self.say('Restored %s as unsent changes' % snap['name'])
        self.emit('values')


def save_values(session, path):
    data = OrderedDict([('format', 'spi-values/1'), ('profile', session.profile.name),
                        ('saved', time.strftime('%Y-%m-%d %H:%M:%S')), ('chips', session.values_dict())])
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


def load_values(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {label: {int(a): v for a, v in regs.items() if v is not None}
            for label, regs in data.get('chips', {}).items()}
