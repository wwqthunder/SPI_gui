import re

def intSafe(num):
    if type(num) is str:
        num = num.replace(" ", "")
    try:
        re = int(float(num))
        return re
    except Exception as e:
        return None

def Float2FixPointBin(float,nint,nfrac):
    _Dec = round(float*(2**nfrac))
    _format = "0" + str(nint + nfrac) + "b"
    _bin = format(_Dec, _format)
    bin = _bin[:nint] + "." + _bin[nint:]
    return bin


def Bin2FixPointFloat(_bin):
    if "." in _bin:
        index = _bin.index(".")
        e = len(_bin) - index - 1
        _bin = _bin.replace(".","")
        _dec = int(_bin, 2)
        dec = float(_dec)/(2**e)
        return dec
    else:
        return float(int(_bin, 2))

def RangeParse(range):
    PickerFlag = True
    if '[' not in range and ']' not in range:
        PickerFlag = False
    range = range.replace(" ", "")
    if range.count('.') == 1:
        range = range.replace(".", ",.,")
    elif range.count('.') > 1:
        return None,None
    bit_list = re.split(r',(?![^[]*\])',range)
    # split with , outside []

    ReadList = []
    ReadData = []
    for _ in bit_list:
        if _.isdigit() is True:
            ReadData.append(int(_))
            if int(_) not in ReadList:
                ReadList.append(int(_))
        elif _ == '.':
            ReadData.append([-1,-1])
        elif _ == '':
            pass
        elif PickerFlag is False:
            rows = BitParse(_)
            if rows is not None:
                for row in rows:
                    if len(row) == 1:
                        if row[0] not in ReadList:
                            ReadList.append(row[0])
                    elif len(row) == 2:
                        for _ in range(row[0],row[1]):
                            if _ not in ReadList:
                                ReadList.append(_)
                    elif len(row) == 3:
                        for _ in range(row[0],row[1],row[2]):
                            if _ not in ReadList:
                                ReadList.append(_)
            else:
                return None,None
        else:
            # Validate
            index = IndexParse(_)
            if index is not None and _[-1] == ']':
                bit = _[len(str(index)) + 1:-1]
                bits = BitParse(bit)
                if bits is not None:
                    if len(bits) != 0:
                        for _bit in bits:
                            _bit.insert(0,index)
                        ReadData = ReadData + bits
                        if index not in ReadList:
                            ReadList.append(index)
                    else:
                        continue
                else:
                    return None,None
            else:
                return None,None
    if PickerFlag is False:
        return None,ReadList
    else:
        return ReadData, ReadList

def IndexParse(string): # "Index[...]"(str) -> Index(int) or None(Not Found)
    res = ''
    for _ in string:
        if _ in '0123456789':
            res = res + _
        elif _ == '[':
            break
        else:
            return None
    if res == '':
        return None
    else:
        return int(res)

def BitParse(string):   # [start stop step],[start stop],[bit]
    bit_list = []
    res = ''
    start = -1
    step = 1
    StepFlag = False
    for _ in string:
        if _ in '0123456789':
            res = res + _
        elif _ == ',':
            if step != 1: # [start stop step]
                if res == '':
                    bit_list.append([start, -1, step])
                else:
                    bit_list.append([start, int(res)+1, step])
                    res = ''
                start = -1
                step = 1
                StepFlag = False
            elif start != -1:  # [start stop]
                if res == '':
                    bit_list.append([start, -1])
                else:
                    if int(res) >= start:
                        bit_list.append([start, int(res)+1])
                    else:
                        bit_list.append([start, int(res)-1,-1])
                    res = ''
                start = -1
                step = 1
                StepFlag = False
            elif res != '': # [bit]
                bit_list.append([int(res)])
                res = ''
        elif _ in ':-':
            if StepFlag is True: # third : Not Supported
                return None
            elif start != -1: # Second : res -> step
                if res != '':
                    step = int(res)
                    res = ''
                StepFlag = True
            elif res != '':
                start = int(res)
                res = ''
            else:
                start = 0
        else:
            return None
    if step != 1:  # [start stop step]
        if res == '':
            bit_list.append([start, -1, step])
        else:
            bit_list.append([start, int(res) + 1, step])
    elif start != -1:  # [start stop]
        if res == '':
            bit_list.append([start, -1])
        else:
            bit_list.append([start, int(res) + 1])
    elif res != '':  # [bit]
        bit_list.append([int(res)])
    return bit_list


if __name__ == '__main__':
    text = "114,51[ 4,] 1,[ :-9 1 ]-.9 , 8 1 0,,"
    bit = '123[.13123]'
    index = IndexParse(bit)
    test = '114,12,112:12:1220,13:10,,12'
    bits = BitParse('213,12-13')
    for _ in bits:
        _.insert(0,1)
    print(bits)
    print(bit[2::1])
    asd = [[1],[1]]
    asd.insert(0, [1])
    qwe = "2[]0],3[0],2[4].12[0:5]"
    ReadData, ReadList = RangeParse(qwe)
    print(ReadData)
    print(ReadList)
    test = "01234"
    string_list = list(test)
    string_list[0:5:2] = '987'
    string_new = "".join(string_list)
    print(string_new)
    print(eval("test"+"[2:5:2]"))
    test = [1,2]
    print(type(test))
    print(type(test) is list)
    test = "123 2 2 "
    test.replace(" ","")
    print(BitParse("1:2:5"))
            #if _[-1] == ']' and
    pass

        # print(intSafe("15 . 2"))
        # print("15 .2 ".replace(" ", ""))
        # print(type("15 . 2"))