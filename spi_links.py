"""SPI links: the NI USB-8452 adapter, Raspberry Pi Pico W boards over TCP, and a simulator.

Every link reads, writes and resets one chip of a profile (chip select, and the chip
address under the CA protocol).  The frame encoding is the tested code in
ni845x_if.py and TCPclient.py; this module only manages connections.
"""
import socket
import time
from collections import OrderedDict

from spi_model import CA

CLOCKS_KHZ = [25, 32, 40, 50, 80, 100, 125, 160, 200, 250, 400, 500, 625, 800, 1000, 1250, 2500, 3125,
              4000, 5000, 6250, 10000, 12500, 20000, 25000, 33330, 50000]
VOLTAGES = [3.3, 2.5, 1.8, 1.5, 1.2]
DISCOVERY_PORT = 5006
DISCOVERY_MESSAGE = b'DISCOVER_PICO'


class LinkError(Exception):
    pass


class SimBackend:
    """In-memory chips; registers never written read back a fixed pseudo-random value."""

    def __init__(self):
        self.mem = {}

    def open(self):
        pass

    def close(self):
        pass

    def read(self, chip, reg, protocol):
        key = (chip.ss, chip.caddr, reg.addr)
        if key not in self.mem:
            self.mem[key] = (reg.addr * 37 + chip.ss * 11 + 5) % (1 << min(reg.width, 10))
        return self.mem[key]

    def write(self, chip, reg, value, protocol):
        if not reg.ro:
            self.mem[(chip.ss, chip.caddr, reg.addr)] = value & reg.full

    def reset(self, chip, protocol):
        for key in [x for x in self.mem if x[:2] == (chip.ss, chip.caddr)]:
            del self.mem[key]


class NiBackend:
    """NI USB-8452 through ni845x_if (same set-up sequence as the old GUI)."""

    def __init__(self, clock_khz=1000, voltage=2.5):
        self.clock_khz = clock_khz
        self.voltage = voltage
        self.ni = None

    def open(self):
        import ni845x_if
        ni = ni845x_if.ni845x_if()
        if not ni.dll_flag:
            raise LinkError('NI-845x driver not found (Ni845x.dll).')
        name = ni.ni845xFindDevice()
        if ni.status_code != 0:
            raise LinkError('No NI USB-8452 found.')
        ni.ni845xOpen(name)
        ni.ni845xSetIoVoltageLevel(int(round(self.voltage * 10)))
        ni.ni845xSpiConfigurationOpen()
        ni.ni845xSpiConfigurationSetClockRate(int(self.clock_khz))
        ni.ni845xSpiConfigurationSetClockPolarity(0)
        ni.ni845xSpiConfigurationSetClockPhase(0)
        self.ni = ni

    def close(self):
        if self.ni is not None:
            try:
                self.ni.ni845xSpiConfigurationClose()
                self.ni.ni845xClose()
            finally:
                self.ni = None

    def _call(self, fn, *args):
        from ni845x_if import Ni845xError
        try:
            return fn(*args)
        except Ni845xError as e:
            raise LinkError(str(e))

    def read(self, chip, reg, protocol):
        if protocol == CA:
            return self._call(self.ni.read_reg, chip.ss, chip.caddr or 0, reg.addr)
        return self._call(self.ni.spi_read, chip.ss, reg.addr, reg.width)

    def write(self, chip, reg, value, protocol):
        if protocol == CA:
            self._call(self.ni.write_reg, chip.ss, chip.caddr or 0, reg.addr, value)
        else:
            self._call(self.ni.spi_write, chip.ss, reg.addr, value, reg.width)

    def reset(self, chip, protocol):
        if protocol == CA:
            self._call(self.ni.spi_reset_new, chip.ss, chip.caddr or 0)
        else:
            self._call(self.ni.spi_reset, chip.ss)


class PicoBackend:
    """Raspberry Pi Pico W over TCP, frames by TCPclient.TCPClient."""

    def __init__(self, name, ip=None, port=None, clock_khz=1000):
        self.name = name
        self.ip = ip
        self.port = port
        self.clock_khz = clock_khz
        self.client = None

    def open(self):
        if not self.ip:
            raise LinkError('Pico %s has not been discovered yet. Use Discover first.' % self.name)
        from TCPclient import TCPClient
        try:
            sock = socket.create_connection((self.ip, self.port), timeout=5)
            sock.settimeout(5)
            sock.send(str(self.clock_khz).encode())
        except OSError as e:
            raise LinkError('Cannot connect to Pico %s at %s:%s (%s).' % (self.name, self.ip, self.port, e))
        self.client = TCPClient()
        self.client.connections[self.name] = sock

    def close(self):
        if self.client is not None:
            sock = self.client.connections.pop(self.name, None)
            self.client = None
            if sock is not None:
                try:
                    sock.send(b'')
                finally:
                    sock.close()

    def _call(self, fn, *args):
        try:
            return fn(self.name, *args)
        except (OSError, IndexError) as e:
            raise LinkError('Pico %s: transfer failed (%s).' % (self.name, e or 'no reply'))

    def read(self, chip, reg, protocol):
        if protocol == CA:
            return self._call(self.client.read_reg, chip.ss, chip.caddr or 0, reg.addr)
        return self._call(self.client.spi_read, chip.ss, reg.addr, reg.width)

    def write(self, chip, reg, value, protocol):
        if protocol == CA:
            self._call(self.client.write_reg, chip.ss, chip.caddr or 0, reg.addr, value)
        else:
            self._call(self.client.spi_write, chip.ss, reg.addr, value, reg.width)

    def reset(self, chip, protocol):
        if protocol == CA:
            self._call(self.client.spi_reset_new, chip.ss, chip.caddr or 0)
        else:
            self._call(self.client.spi_reset, chip.ss)


class Link:
    def __init__(self, link_id, name, short, kind, backend, addr=''):
        self.id = link_id
        self.name = name
        self.short = short
        self.kind = kind            # 'ni', 'pico' or 'sim'
        self.backend = backend
        self.addr = addr            # shown in the links panel
        self.connected = False

    def connect(self):
        self.backend.open()
        self.connected = True

    def disconnect(self):
        try:
            self.backend.close()
        finally:
            self.connected = False

    def _check(self):
        if not self.connected:
            raise LinkError('%s is not connected.' % self.name)

    def read(self, chip, reg, protocol):
        self._check()
        return self.backend.read(chip, reg, protocol) & reg.full

    def write(self, chip, reg, value, protocol):
        self._check()
        self.backend.write(chip, reg, value & reg.full, protocol)

    def reset(self, chip, protocol):
        self._check()
        self.backend.reset(chip, protocol)


def discover_picos(timeout=1.5):
    """Broadcast DISCOVER_PICO and collect every reply ('name_port') until the timeout."""
    found = OrderedDict()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(0.25)
        s.sendto(DISCOVERY_MESSAGE, ('255.255.255.255', DISCOVERY_PORT))
        end = time.time() + timeout
        while time.time() < end:
            try:
                raw, addr = s.recvfrom(1024)
            except socket.timeout:
                continue
            try:
                name, port = raw.decode(errors='replace').rsplit('_', 1)
                found[name] = (addr[0], int(port))
            except ValueError:
                continue
    finally:
        s.close()
    return [(name, ip, port) for name, (ip, port) in found.items()]


class LinkSet:
    """All links the GUI knows.  With simulate on, every link talks to in-memory chips."""

    def __init__(self, simulate=False, clock_khz=1000, voltage=2.5):
        self.simulate = simulate
        self.clock_khz = clock_khz
        self.voltage = voltage
        self.links = OrderedDict()
        self.found = []             # [(name, ip, port)] from the last discovery, not connected yet
        self.add(Link('ni', 'NI USB-8452', 'NI', 'ni', self._backend('ni')))

    def _backend(self, kind, name=None, ip=None, port=None):
        if self.simulate:
            return SimBackend()
        if kind == 'ni':
            return NiBackend(self.clock_khz, self.voltage)
        return PicoBackend(name, ip, port, self.clock_khz)

    def add(self, link):
        self.links[link.id] = link
        return link

    def get(self, link_id):
        return self.links.get(link_id)

    def all(self):
        return list(self.links.values())

    def ensure(self, link_id):
        """Links named by a profile but unknown so far are added, not connected."""
        if link_id in self.links:
            return self.links[link_id]
        if link_id.startswith('pico:'):
            name = link_id[5:]
            return self.add(Link(link_id, 'Pico ' + name, name, 'pico', self._backend('pico', name)))
        if link_id == 'sim':
            return self.add(Link('sim', 'Simulator', 'Sim', 'sim', SimBackend()))
        return self.add(Link(link_id, link_id, link_id, 'ni', self._backend('ni')))

    def set_simulate(self, on):
        for link in self.links.values():
            if link.connected:
                link.disconnect()
        self.simulate = bool(on)
        for link in self.links.values():
            if link.kind == 'pico':
                b = link.backend
                link.backend = self._backend('pico', link.short, getattr(b, 'ip', None), getattr(b, 'port', None))
            elif link.kind == 'ni':
                link.backend = self._backend('ni')

    def configure_ni(self, clock_khz, voltage):
        self.clock_khz = clock_khz
        self.voltage = voltage
        for link in self.links.values():
            if isinstance(link.backend, NiBackend):
                link.backend.clock_khz = clock_khz
                link.backend.voltage = voltage
            elif isinstance(link.backend, PicoBackend):
                link.backend.clock_khz = clock_khz

    def discover(self, timeout=1.5):
        if self.simulate:
            replies = [('#0', '192.168.1.21', 5000), ('#1', '192.168.1.22', 5000), ('#2', '192.168.1.23', 5000)]
        else:
            replies = discover_picos(timeout)
        self.found = []
        for name, ip, port in replies:
            link = self.links.get('pico:' + name)
            if link is not None and link.connected:
                continue
            self.found.append((name, ip, port))
        return list(self.found)

    def connect_found(self, name):
        for n, ip, port in self.found:
            if n == name:
                link = self.ensure('pico:' + name)
                if isinstance(link.backend, PicoBackend):
                    link.backend.ip, link.backend.port = ip, port
                link.addr = '%s:%d' % (ip, port)
                link.connect()
                self.found = [x for x in self.found if x[0] != name]
                return link
        raise LinkError('Pico %s was not found by the last Discover.' % name)
