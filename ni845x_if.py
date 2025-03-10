import ctypes as c
import time
import sys

DEV_SIZE = 256
MAX_SIZE = 1024

class ni845x_if:
    """
    This class makes Python calls to the C DLL of NI USB 8452 (ni845x.dll)
    """
    def __init__(self):
        self.first_device = None
        self.find_device_handle = None
        self.number_found = None
        self.status_code = c.c_ulong(0)
        self.device_handle = 0
        self.spi_handle = 0
        self.flag64 = sys.maxsize > 2 ** 32
        self.dll_location = "Ni845x.dll"
        self.dll_flag = True
        try:
            if self.flag64:
                self.i2c = c.cdll.LoadLibrary(self.dll_location)
            else:
                self.i2c = c.windll.LoadLibrary(self.dll_location)
        except Exception as e:
            print(e)
            self.dll_flag = False

    def ni845xFindDevice(self):
        """
        Calls NI USB-8452 C API function ni845xFindDevice whose prototype is:
        int32 ni845xFindDevice (char * pFirstDevice, NiHandle * pFindDeviceHandle, uInt32 * pNumberFound);
        :return: name of first device
        """
        self.first_device = c.create_string_buffer(DEV_SIZE)#ctypes.create_string_buffer(DEV_SIZE)
        if self.flag64:
            self.find_device_handle = c.c_uint64(0)
        else:
            self.find_device_handle = c.c_uint32(0)
        number_found = c.c_uint32(0)

        self.status_code = self.i2c.ni845xFindDevice(c.byref(self.first_device), c.byref(self.find_device_handle), c.byref(number_found))
        print("returnValue ni845xFindDevice", self.status_code)
        print("First DeviceName:\n", str(self.first_device.value))
        #print("Number Found: ", number_found[0])
        #self.number_found = number_found[0]
        return self.first_device

    def ni845xOpen(self, resource_name):
        """
        Calls the NI USB-8452 C API function ni845xOpen whose prototype is:
        int32 ni845xOpen (char * pResourceName, NiHandle * pDeviceHandle);
        :param resource_name: name of the resource
        :return:device handle
        """
        if self.flag64:
            self.device_handle = c.c_uint64(0)
        else:
            self.device_handle = c.c_uint32(0)

        returnValue = self.i2c.ni845xOpen(c.byref(self.first_device), c.byref(self.device_handle))
        print("self.device_handle", hex((self.device_handle.value)))
        print("Return values of ni845xOpen: ", hex(returnValue))
        #print("Return values of ni845xOpen: ", returnValue)
        #return self.device_handle

    def ni845xCloseFindDeviceHandle(self):
        """
        Calls NI USB-8452 C API function ni845xCloseFindDeviceHandle whose prototype is:
        int32 ni845xCloseFindDeviceHandle (NiHandle FindDeviceHandle);
        :return: None
        """

        self.status_code = self.i2c.ni845xCloseFindDeviceHandle(self.find_device_handle)
        #print("returnValue", self.status_code)
        #print("Running StatusToString")
        self.ni845xStatusToString(self.status_code)

    def ni845xStatusToString(self, status_code):
        """
        Calls NI USB-8452 C API function ni845xStatusToString whose prototype is:
        void ni845xStatusToString (int32 StatusCode, uInt32 MaxSize, int8 * pStatusString);
        :return:None
        """
        status_string = c.create_string_buffer(b'', MAX_SIZE)
        returnValue = self.i2c.ni845xStatusToString(status_code, MAX_SIZE, status_string)
        #print("Status String:\n", repr(status_string.raw))
        str(status_string)
        print(status_string.value)


    def ni845xClose(self):
        """
        Calls the NI USB-8452 C API function ni845xClose whose prototype is
        :return: None
        """
        print("self.device_handle.value",self.device_handle.value)
        returnValue = self.i2c.ni845xClose(self.device_handle)
        print("Return values of ni845xClose: ", returnValue)

    def  ni845xSetIoVoltageLevel(self, VoltageLevel=25):
        """
        Calls NI USB-8452 C API function ni845xSetIoVoltageLevel whose prototype is:
        void ni845xSetIoVoltageLevel (NiHandle DeviceHandle,uInt8 VoltageLevel);
        :return:None
        """
        outlevel = c.c_uint8(VoltageLevel)
        returnValue = self.i2c.ni845xSetIoVoltageLevel(self.device_handle, outlevel)
        print("self.device_handle", self.device_handle.value)
        print("Return values of ni845xSetIoVoltageLevel: ", returnValue)
        
    def  ni845xSpiConfigurationOpen (self):
        """
        Calls NI USB-8452 C API function ni845xSpiConfigurationOpen  whose prototype is:
        void ni845xSpiConfigurationOpen  (NiHandle DeviceHandle);
        :return:None
        """
        if self.flag64:
            self.spi_handle = c.c_uint64(0)
        else:
            self.spi_handle = c.c_uint32(0)

        returnValue = self.i2c.ni845xSpiConfigurationOpen(c.byref(self.spi_handle))
        print("self.spi_handle", self.spi_handle)
        print("Return values of ni845xSpiConfigurationOpen: ", returnValue)


    def  ni845xSpiConfigurationClose (self):
        """
        Calls NI USB-8452 C API function ni845xSpiConfigurationClose  whose prototype is:
        void ni845xSpiConfigurationClose  (NiHandle DeviceHandle);
        :return:None
        """
        returnValue = self.i2c.ni845xSpiConfigurationClose(self.spi_handle)


    def  ni845xSpiConfigurationSetChipSelect (self, ChipSelect=0):
        """
        Calls NI USB-8452 C API function ni845xSpiConfigurationSetChipSelect  whose prototype is:
        void ni845xSpiConfigurationSetChipSelect  (NiHandle DeviceHandle,uInt16 ChipSelect);
        :return:None
        """
        cs = c.c_uint32(ChipSelect)
        returnValue = self.i2c.ni845xSpiConfigurationSetChipSelect(self.spi_handle, cs)
        print("ChipSelect", cs)
        print("Return values of ni845xSpiConfigurationSetChipSelect: ", returnValue)



    def  ni845xSpiConfigurationSetClockRate(self, ClockRate=40):
        """
        Calls NI USB-8452 C API function ni845xSpiConfigurationSetClockRate whose prototype is:
        void ni845xSpiConfigurationSetClockRate (NiHandle DeviceHandle,uInt16 ClockRate);
        :return:None
        """
        cr = c.c_uint16(ClockRate)
        returnValue = self.i2c.ni845xSpiConfigurationSetClockRate(self.spi_handle, cr)
        print("ClockRate", cr)
        print("Return values of ni845xSpiConfigurationSetClockRate: ", returnValue)

    def  ni845xSpiConfigurationSetNumBitsPerSample(self, NumBitsPerSample=40):
        """
        Calls NI USB-8452 C API function ni845xSpiConfigurationSetNumBitsPerSample whose prototype is:
        void ni845xSpiConfigurationSetNumBitsPerSample (NiHandle DeviceHandle,uInt16 VoltageLevel);
        :return:None
        """
        cr = c.c_uint16(NumBitsPerSample)
        returnValue = self.i2c.ni845xSpiConfigurationSetNumBitsPerSample(self.spi_handle, cr)


    def  ni845xSpiConfigurationSetClockPolarity(self, ClockPolarity):
        """
        Calls NI USB-8452 C API function ni845xSpiConfigurationSetClockPolarity whose prototype is:
        void ni845xSpiConfigurationSetClockPolarity (NiHandle DeviceHandle,Int32 ClockPolarity);
        :return:None
        """
        cp = c.c_int32(ClockPolarity)
        returnValue = self.i2c.ni845xSpiConfigurationSetClockPolarity(self.spi_handle, cp)
        print("ClockPolarity", cp)
        print("Return values of ni845xSpiConfigurationSetClockPolarity: ", returnValue)


    def  ni845xSpiConfigurationSetClockPhase (self, ClockPhase):
        """
        Calls NI USB-8452 C API function ni845xSpiConfigurationSetClockPhase  whose prototype is:
        void ni845xSpiConfigurationSetClockPhase  (NiHandle DeviceHandle,Int32 ClockPhase);
        :return:None
        """
        cp = c.c_int32(ClockPhase)
        returnValue = self.i2c.ni845xSpiConfigurationSetClockPhase(self.spi_handle, cp)
        print("ClockPhase", cp)
        print("Return values of ni845xSpiConfigurationSetClockPhase: ", returnValue)

    def SpiWriteRead(self, cs, WriteData, ReadBytes):
        """
        Calls NI USB-8452 C API function ni845xSpiWriteRead whose prototype is:
        void ni845xSpiWriteRead (NiHandle ScriptHandle, uInt32 WriteSize, uInt8 * pWriteData, uInt32 * pReadSize, uInt8 * pReadData);
        :return:None
        """
        cs = c.c_uint32(cs)
        write_bytes = len(WriteData)
        wsize = c.c_uint32(write_bytes)
        wbuf = (c.c_uint8*write_bytes)(*WriteData)
        rsize = c.c_uint32(ReadBytes)
        rbuf = (c.c_uint8*ReadBytes)(*list())

        ret = self.i2c.ni845xSpiConfigurationSetChipSelect(self.spi_handle, cs)
        ret = self.i2c.ni845xSpiWriteRead(self.device_handle, self.spi_handle, wsize, c.byref(wbuf), c.byref(rsize), c.byref(rbuf))

        read_data = [rbuf[i] for i in range(ReadBytes)]
        return read_data

    def spi_read(self, cs, add, size):
        if size < 6:
            cmd = 2
            ret = self.SpiWriteRead(cs, [((cmd << 5) + (add >> 3)) % 256, (add << 5) % 256], 2)
            print("Addr:" + str(add) + "_Rd:" + str(ret[1] % 32))
            return ret[1] % 32
        else:
            cmd = 1
            ret = self.SpiWriteRead(cs, [((cmd << 5) + (add >> 3)) % 256, (add << 5) % 256, 0], 3)
            print("Addr:" + str(add) + "_Rd:" + str((ret[1] % 32) * 256 + ret[2] % 256))
            return (ret[1] % 32) * 256 + ret[2] % 256

    def spi_write(self, cs, add, data, size):
        if size < 6:
            cmd = 6
            ret = self.SpiWriteRead(cs, [((cmd << 5) + (add >> 3)) % 256, ((add << 5) + data) % 256], 2)
            print('Wr:' + str(data) + "_Rd:" + str(ret[1] % 32))
        else:
            cmd = 5
            ret = self.SpiWriteRead(cs, [((cmd << 5) + (add >> 3)) % 256, ((add << 5) + (data >> 8)) % 256,
                                                 data % 256], 3)
            print('Wr:' + str(data) + "_Rd:" + str((ret[1] % 32) * 256 + ret[2] % 256))

    def write_reg(self, cs, caddr, addr, data):
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
        self.SpiWriteRead(cs, write_data, 5)

    def read_reg(self, cs, caddr, addr, read_num=1):
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
        raw_data = self.SpiWriteRead(cs, write_data, 2*read_num+3)[3:]
        read_data_list = []
        for _ in range(read_num):
            read_data_list.append((raw_data[2*_]%16)*(2**7) + int(raw_data[2*_+1]/2))
        return read_data_list[0]

    def spi_reset(self, cs):
        cmd = 7
        writeline = [(cmd << 5) % 256]
        ret = self.SpiWriteRead(cs, writeline, 3)

    def spi_reset_new(self, cs, caddr):
        cmd = 7
        write_data = [caddr, (cmd * 2**4), 0, 0, 0]
        ret = self.SpiWriteRead(cs, write_data, 5)

    def  ni845xDioSetPortLineDirectionMap(self, DioPort, Map):
        """
        Calls NI USB-8452 C API function ni845xDioSetPortLineDirectionMap  whose prototype is:
        void ni845xDioSetPortLineDirectionMap  (NiHandle DeviceHandle,Int32 DioPort, Map Map);
        :return:None
        """
        dp = c.c_uint8(DioPort)
        mp = c.c_uint8(Map)
        returnValue = self.i2c.ni845xDioSetPortLineDirectionMap(self.device_handle, dp, mp)
        print("Return values of ni845xSpiConfigurationSetClockPhase: ", returnValue)

    def  ni845xDioSetDriverType (self, DioPort, Type):
        """
        Calls NI USB-8452 C API function ni845xDioSetDriverType  whose prototype is:
        void ni845xDioSetDriverType  (NiHandle DeviceHandle,Int32 DioPort, Map Map);
        :return:None
        """
        dp = c.c_uint8(DioPort)
        mp = c.c_uint8(Type)
        returnValue = self.i2c.ni845xDioSetDriverType(self.device_handle, dp, mp)
        print("Return values of ni845xSpiConfigurationSetClockPhase: ", returnValue)

    def  ni845xDioWritePort (self, PortNumber,WriteData):
        """
        Calls NI USB-8452 C API function ni845xDioWritePort  whose prototype is:
        void ni845xDioWritePort  (NiHandle DeviceHandle,Int32 DioPort, Map Map);
        :return:None
        """
        dp = c.c_uint8(PortNumber)
        mp = c.c_uint8(WriteData)
        returnValue = self.i2c.ni845xDioWritePort(self.device_handle, dp, mp)
        print("Return values of ni845xSpiConfigurationSetClockPhase: ", returnValue)


def main():
    """
    Entry point to the script
    :return: None
    """

    ni8452 = ni845x_if()
    resource_name = ni8452.ni845xFindDevice()
    #ni8452.ni845xCloseFindDeviceHandle()

    ret=ni8452.ni845xOpen(resource_name)
    print(ret)
    #ni8452.ni845xStatusToString(ret)

    ni8452.ni845xSetIoVoltageLevel(33)

    ni8452.ni845xSpiConfigurationOpen ()

    #/* configure configuration properties */
    ni8452.ni845xSpiConfigurationSetChipSelect (0)
    ni8452.ni845xSpiConfigurationSetClockRate (4)
    ni8452.ni845xSpiConfigurationSetClockPolarity (0)
    ni8452.ni845xSpiConfigurationSetClockPhase (0)

    #/* write number of pages to the EEPROM Target
    #calculate addressbytes depending on endianness and byte number*/


    #/* Write the write enable (WREN) instruction */

    #/* Write the SPI data */

    ni8452.ni845xDioSetDriverType (0, 1)
    ni8452.ni845xDioSetPortLineDirectionMap (0, 0)

    for k in range(10):
          ni8452.ni845xDioWritePort ( 0, 1)
          time.sleep(1)
          ni8452.ni845xDioWritePort ( 0, 0)
          time.sleep(1)
          ni8452.ni845xSpiWriteRead ([2,255,255])


    # print("Device handle after open: ", ni8452.device_handle[0])
    # print("Device handle after open: ", ni8452.device_handle[1])
    # print("Device handle after open: ", ni8452.device_handle[2])
    ni8452.ni845xSpiConfigurationClose ()

    ni8452.ni845xClose()




if __name__ == '__main__':
    cmd = 2
    caddr = 1
    addr = 2
    data = 512
    write_data = [caddr, (cmd * 2 ** 4) + int(addr / 256), addr % 256]
    if type(data) == list:
        for _ in data:
            write_data = write_data + [int(_ / 128), (_ * 2) % 256]
    else:
        write_data = write_data + [int(data / 128), (data * 2) % 256]
    print(write_data)
