# All little-endian

from struct import unpack, pack
from ..common import logSevere

class BinaryReader():

    # TODO - Validate writing data (min)

    def __init__(self, filename='', data=b''):
        if filename != '':
            try:
                with open(filename, 'rb') as dataIn:
                    self.data = bytearray(dataIn.read())
            except FileNotFoundError:
                logSevere("Path", filename, "doesn't exist!")
                self.data = bytearray(data)
            except IOError:
                self.data = bytearray(data)
        else:
            self.data = bytearray(data)

        self.pos = 0

    def seek(self, newPos, mode=0):
        if mode == 0:
            self.pos = newPos
        elif mode == 1:
            self.pos += newPos
        else:
            self.pos = len(self.data) - newPos - 1

    def hasDataRemaining(self):
        if self.tell() <= len(self.data) - 1:
            return True
        return False

    def tell(self):
        return self.pos

    def read(self, length):
        self.pos += length
        return self.data[self.pos - length:self.pos]

    def readFloat(self, length):
        return unpack("<f", self.read(length))[0]

    def readF32(self):
        return self.readFloat(4)
    
    def readInt(self, length, signed=True):
        return int.from_bytes(self.read(length), byteorder = 'little', signed=signed)
    
    def readUInt(self, length):
        return self.readInt(length, signed=False)

    def readU16(self):
        return self.readUInt(2)

    def readU32(self):
        return self.readUInt(4)
    
    def readU32List(self, length):
        out = []
        for _index in range(length):
            out.append(self.readU32())
        return out

    def readU64(self):
        return self.readUInt(8)
    
    def readS16(self):
        return self.readInt(2)

    def readS32(self):
        return self.readInt(4)
    
    def readS64(self):
        return self.readInt(8)
    
    def readNullTerminatedString(self, encoding):
        out = bytearray(b'')
        while self.data[self.pos] != 0:
            out.extend(self.read(1))
        return out.decode(encoding)
    
    # TODO - Convert all padding characters to actual characters - be weary of encoding though
    def readPaddedString(self, length, encoding, padChar="\0"):
        out = self.read(length).decode(encoding)
        return out.split(padChar)[0]

class BinaryWriter():
    def __init__(self):
        self.data = bytearray(b'')
    
    def clear(self):
        self.data = bytearray(b'')
    
    def tell(self):
        return len(self.data)

    def pad(self, padLength, padChar = b'\x00'):
        for _index in range(padLength):
            self.data.extend(padChar)

    def align(self, alignment, padChar = b'\x00'):
        while self.tell() % alignment > 0:
            self.data.extend(padChar)

    def dsAlign(self, alignment, extraPad, padChar = b'\x00'):
        tempAlignmentLength = self.tell()
        self.align(alignment, padChar = padChar)
        if self.tell() == tempAlignmentLength:
            self.pad(extraPad, padChar = padChar)

    def write(self, data):
        self.data.extend(data)
    
    def writeFloat(self, data):
        self.data.extend(pack("<f", data))

    def writeString(self, data, encoding):
        self.data.extend(data.encode(encoding))
    
    def writePaddedString(self, data, length, encoding, padChar=b'\x00'):
        data = data.encode(encoding)
        if len(data) > length:
            # TODO - Breaks multibyte characters...
            self.data.extend(data[:length])
        else:
            self.data.extend(data + (padChar * (length - len(data))))

    def writeInt(self, data, length, signed = False):
        self.data.extend(data.to_bytes(length, byteorder = 'little', signed = signed))
    
    def writeIntList(self, dataList, length, signed = False):
        for data in dataList:
            self.writeInt(data, length, signed = signed)

    def writeLengthAndString(self, data, encoding, lengthSize=2, extraPadLength=1, padChar=b'\x00'):
        tempString = data.encode(encoding)
        self.writeInt(len(tempString) + extraPadLength, lengthSize)
        self.data.extend(tempString)
        self.pad(extraPadLength, padChar=padChar)

    def writeU16(self, data):
        self.writeInt(data, 2)

    def writeU32(self, data):
        self.writeInt(data, 4)
    
    def writeU64(self, data):
        self.writeInt(data, 8)

    def writeS32(self, data):
        self.writeInt(data, 4, signed=True)
    
    def writeU32L(self, dataList):
        self.writeIntList(dataList, 4)
    
    def insert(self, data, pos):
        insertionPos = pos
        for singleByte in data:
            self.data[insertionPos] = singleByte
            insertionPos += 1