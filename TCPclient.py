import socket
import asyncio
import time
from PyQt5 import QtCore

BROADCAST_IP = "255.255.255.255"
UDP_PORT = 5006
DISCOVERY_MESSAGE = b"DISCOVER_PICO"


class TCPClient(QtCore.QObject):
    tcp_signal = QtCore.pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.connections = {}

    async def connect(self, baudrate):
        udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        udp_client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_client.settimeout(5)
        try:
            udp_client.sendto(DISCOVERY_MESSAGE, (BROADCAST_IP, UDP_PORT))
            raw, addr = udp_client.recvfrom(1024)
            data = raw.decode().rsplit("_", 1)
            name = data[0]
            tcp_port = int(data[1])
            print(f"Discovered device at {addr[0]} {tcp_port} {name}")
        except socket.timeout:
            print("No responses.")
            return
        finally:
            udp_client.close()
        tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_client.settimeout(20)
        tcp_client.connect((addr[0], tcp_port))
        self.connections[name] = tcp_client
        tcp_client.send(baudrate.encode())
        self.tcp_signal.emit(name, "open")

    def tcp_send(self, cs, data, name):
        tbuf = bytes([cs] + data)
        self.connections[name].send(tbuf)
        response = self.connections[name].recv(1024)
        print(list(response))
        return response

    async def tcp_close(self, name):
        data = bytes([])
        self.connections[name].send(data)
        self.connections[name].close()
        del self.connections[name]
        self.tcp_signal.emit(name, "close")

    def spi_read(self, name, cs, add, size):
        if size < 6:
            cmd = 2
            ret = self.tcp_send(cs, [((cmd << 5) + (add >> 3)) % 256, (add << 5) % 256], name)
            print("Addr:" + str(add) + "_Rd:" + str(ret[1] % 32))
            return ret[1] % 32
        else:
            cmd = 1
            ret = self.tcp_send(cs, [((cmd << 5) + (add >> 3)) % 256, (add << 5) % 256, 0], name)
            print("Addr:" + str(add) + "_Rd:" + str((ret[1] % 32) * 256 + ret[2] % 256))
            return (ret[1] % 32) * 256 + ret[2] % 256

    def spi_write(self, name, cs, add, data, size):
        if size < 6:
            cmd = 6
            ret = self.tcp_send(cs, [((cmd << 5) + (add >> 3)) % 256, ((add << 5) + data) % 256], name)
            print('Wr:' + str(data) + "_Rd:" + str(ret[1] % 32))
        else:
            cmd = 5
            ret = self.tcp_send(cs, [((cmd << 5) + (add >> 3)) % 256, ((add << 5) + (data >> 8)) % 256,
                                                 data % 256], name)
            print('Wr:' + str(data) + "_Rd:" + str((ret[1] % 32) * 256 + ret[2] % 256))

    def write_reg(self, name, cs, caddr, addr, data):
        """
        NO OVERFLOW PROTECTION!!!
        caddr: 6 bits chip address, addr: 9 bits address, data: 11 bits data or list[].
        addr is designed to start from "0" in HW, but for consistency with conventional okada lab spi protocol,
        parameter _addr is employed making addr starts from "1".
        table.csv also must start from "1"
        """
        cmd = 2
        write_data = [caddr, (cmd * 2 ** 4) + int(addr / 256), addr % 256]
        if type(data) == list:
            for _ in data:
                write_data = write_data + [int(_ / 128), (_ * 2) % 256]
        else:
            write_data = write_data + [int(data / 128), (data * 2) % 256]
        print(write_data)
        ret = self.tcp_send(cs, write_data, name)

    def read_reg(self, name, cs, caddr, addr, read_num=1):
        """
        NO OVERFLOW PROTECTION!!!
        caddr: 6 bits chip address, addr: 9 bits address, read_num: number of addr to read, return: 11 bits list.
        addr is designed to start from "0" in HW, but for consistency with conventional okada lab spi protocol,
        parameter _addr is employed making addr starts from "1".
        table.csv also must start from "1"
        """
        cmd = 1
        write_data = [caddr, (cmd * 2**4)+int(addr/256), addr%256]
        write_data = write_data + 2*read_num*[0]
        raw_data = self.tcp_send(cs, write_data, name)[3:]
        read_data_list = []
        for _ in range(read_num):
            read_data_list.append((raw_data[2*_]%16)*(2**7) + int(raw_data[2*_+1]/2))
        return read_data_list[0]

    def spi_reset(self, name, cs):
        cmd = 7
        writeline = [(cmd << 5) % 256]
        ret = self.tcp_send(cs, writeline, name)

    def spi_reset_new(self, name, cs, caddr):
        cmd = 7
        write_data = [caddr, (cmd * 2**4), 0, 0, 0]
        ret = self.tcp_send(cs, write_data, name)

if __name__ == '__main__':
    tcp_client = TCPClient()
    asyncio.run(tcp_client.connect("400000"))
    time.sleep(2)
    tcp_client.tcp_send(0, [12, 23, 35, 45], "#0")
    time.sleep(2)
    tcp_client.tcp_send(0, [12, 23, 35, 45], "#0")
    time.sleep(2)
    asyncio.run(tcp_client.tcp_close("#0"))
