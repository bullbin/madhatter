import ndspy.lz10
from functools import partial
from os import makedirs
from . import binary
from ..common import logSevere
from .const import ENCODING_DEFAULT_STRING

class _HuffmanCompressionNode():
    def __init__(self, parent=None, left=None, right=None, weight=0, data=None):
        self.parent = parent
        self.left = left
        self.right = right
        self.weight = weight
        self.data = data
    
    def getBoolCode(self):
        tempNode = self
        outCode = []
        while tempNode.parent != None:
            tempParentNode = tempNode.parent
            outCode.insert(0, tempNode == tempParentNode.right)
            tempNode = tempParentNode
        return outCode

class _HuffmanDecompressionNode(_HuffmanCompressionNode):
    def __init__(self, reader, relativeOffset, maxTreeLen, isData=False, parent=None, left=None, right=None, weight=0, data=None):
        _HuffmanCompressionNode.__init__(self, parent=parent, left=left, right=right, weight=weight, data=data)
        self.isFilled = False
        if reader.tell() < maxTreeLen:
            self.isFilled = True
            if isData:
                self.data = reader.read(1)
            else:
                tempByte = reader.readUInt(1)
                tempOffset = tempByte & 0x3F
                tempAbsOffset = reader.tell()
                zeroRelOffset = (relativeOffset ^ (relativeOffset & 1)) + tempOffset * 2 + 2
                reader.seek(zeroRelOffset - relativeOffset - 1, 1)
                isLeftData = tempByte & (2 ** 7)
                isRightData = tempByte & (2 ** 6)
                self.left = _HuffmanDecompressionNode(reader, zeroRelOffset, maxTreeLen, isData=isLeftData, parent=self)
                self.right = _HuffmanDecompressionNode(reader, zeroRelOffset + 1, maxTreeLen, isData=isRightData, parent=self)
                reader.seek(tempAbsOffset)

class _HuffmanTree():
    def __init__(self, root):
        self.root = root
    
    @staticmethod
    def decode(reader, offsetIn, maxTreeLen):
        output = _HuffmanTree(None)
        output.root = _HuffmanDecompressionNode(reader, offsetIn + 5, maxTreeLen)
        return output
    
    def encode(self):
        writer = binary.BinaryWriter()
        writer.write(b'\x00')
        breadthQueue = [self.root]      # Ported from DsDecmp
        while len(breadthQueue) > 0:
            node = breadthQueue[0]
            breadthQueue = breadthQueue[1:]
            if node.data != None:
                writer.write(node.data)
            else:
                tempData = (len(breadthQueue) // 2) & 0x3F
                if node.left.data != None:
                    tempData = tempData | 0x80
                if node.right.data != None:
                    tempData = tempData | 0x40
                breadthQueue.extend((node.left, node.right))
                writer.writeInt(tempData, 1)
        writer.insert(((writer.tell() // 2) - 1).to_bytes(1, byteorder = 'little'), 0)
        return writer.data

class File():

    COMP_HUFFMAN_8_BIT      = 0x28
    COMP_HUFFMAN_4_BIT      = 0x24
    COMP_RLE                = 0x30
    COMP_LZ10               = 0x10

    LAYTON_1_COMPRESSION    = {COMP_RLE:b'\x01\x00\x00\x00',
                               COMP_LZ10:b'\x02\x00\x00\x00',
                               COMP_HUFFMAN_4_BIT:b'\x03\x00\x00\x00',
                               COMP_HUFFMAN_8_BIT:b'\x04\x00\x00\x00'}

    def __init__(self, name="", data = b'', extension = ''):
        self.name = name
        self.data = bytearray(data)
        self.extension = extension
    
    def __str__(self):
        return str(len(self.data)) + "\t" + self.name

    def compress(self, addHeader=False): # Get optimal compression
        def copyCompress(compressionMethod):
            uncompressed = self.data
            compressionMethod(addHeader = addHeader)
            compressed = self.data
            self.data = uncompressed
            return compressed

        compList = [copyCompress(self.compressHuffman), copyCompress(partial(self.compressHuffman, True)),
                    copyCompress(self.compressLz10),    self.data]
        compList.sort(key=len)
        self.data = compList[0]

    def detectDecompressionMethod(self, byteMagic, bytesLen, offsetIn=0):
        # TODO - goal_inf.dlz is shorter; there's got to be a better way to detect compressed files
        if int.from_bytes(bytesLen, byteorder = 'little') >= len(self.data) - offsetIn:
            # Pass the sanitisation check
            if byteMagic == File.COMP_HUFFMAN_8_BIT or byteMagic == File.COMP_HUFFMAN_4_BIT:
                return self.decompressHuffman
            elif byteMagic == File.COMP_RLE:
                return self.decompressRle
            elif byteMagic == File.COMP_LZ10:
                return self.decompressLz10
        return None

    def decompress(self, detectTypeHeader=True, forceTypeHeader=False):
        if len(self.data) > 4:
            decompressMethod = self.detectDecompressionMethod(self.data[0], self.data[1:4])
            offsetIn = 0
            if (forceTypeHeader or (detectTypeHeader and decompressMethod == None and len(self.data) >= 8)):
                decompressMethod = self.detectDecompressionMethod(self.data[4], self.data[5:8], offsetIn=4)
                offsetIn = 4
            if decompressMethod != None:
                try:
                    return decompressMethod(offsetIn = offsetIn)
                except:
                    return False
        return False

    def compressHuffman(self, useHalfByteBlocks = False, addHeader=False):
        reader = binary.BinaryReader(data = self.data)
        freqDict = {}
        while reader.hasDataRemaining():    # Build frequency table
            tempByte = [bytes(reader.read(1))]
            if useHalfByteBlocks:
                tempByte[0] = int.from_bytes(tempByte[0], byteorder = 'little')
                tempByte = [(tempByte[0] >> 4).to_bytes(1, byteorder = 'little'), (tempByte[0] & 0x0F).to_bytes(1, byteorder = 'little')]
            for block in tempByte:
                if block not in freqDict.keys():
                    freqDict[block] = _HuffmanCompressionNode(data = block)
                freqDict[block].weight += 1

        nodes = freqDict.values()
        if len(nodes) > 2**9:
            raise Exception("Huffman encode: Tree too long to be encoded!")

        while len(nodes) > 1:   # Build Huffman tree by grouping nodes
            nodes = sorted(nodes, key=lambda huffNode : huffNode.weight)
            newNode = _HuffmanCompressionNode(left = nodes[0], right = nodes[1], weight = nodes[0].weight + nodes[1].weight)
            newNode.left.parent = newNode
            newNode.right.parent = newNode
            nodes = nodes[2:]
            nodes.append(newNode)

        tree = _HuffmanTree(nodes[0])
        
        writer = binary.BinaryWriter()
        if useHalfByteBlocks:
            writer.writeInt(File.COMP_HUFFMAN_4_BIT, 1)
        else:
            writer.writeInt(File.COMP_HUFFMAN_8_BIT, 1)
        writer.writeInt(len(self.data), 3)
        writer.write(tree.encode())
        
        keyDict = {}
        for key in freqDict.keys():
            keyDict[freqDict[key].data] = freqDict[key].getBoolCode()
        
        reader.seek(0)
        compressionBlock = 0
        compressionBlockBitsRemaining = 32
        while reader.hasDataRemaining():    # Ported from DsDecmp
            tempByte = [reader.read(1)]
            if useHalfByteBlocks:
                tempByte[0] = int.from_bytes(tempByte[0], byteorder = 'little')
                tempByte = [(tempByte[0] >> 4).to_bytes(1, byteorder = 'little'), (tempByte[0] & 0x0F).to_bytes(1, byteorder = 'little')]
            for data in tempByte:
                for bit in keyDict[bytes(data)]:
                    if compressionBlockBitsRemaining == 0:
                        writer.writeU32(compressionBlock)
                        compressionBlock = 0
                        compressionBlockBitsRemaining = 32
                    compressionBlockBitsRemaining -= 1
                    if bit:
                        compressionBlock = compressionBlock | (1 << compressionBlockBitsRemaining)
        if compressionBlockBitsRemaining != 32:
            writer.writeU32(compressionBlock)
        writer.dsAlign(4, 4)

        if addHeader:
            if useHalfByteBlocks:
                self.data = File.LAYTON_1_COMPRESSION[File.COMP_HUFFMAN_4_BIT] + writer.data
            else:
                self.data = File.LAYTON_1_COMPRESSION[File.COMP_HUFFMAN_8_BIT] + writer.data
        else:
            self.data = writer.data

    def decompressHuffman(self, offsetIn=0):
        reader = binary.BinaryReader(data = self.data)
        reader.seek(offsetIn)
        magic = reader.readUInt(1)
        if magic & 0xF0 != 0x20:
            return False
        elif magic & 0x0F == 0x04:
            useHalfByteBlocks = True
        else:
            useHalfByteBlocks = False

        tempFilesize = reader.readUInt(3)
        tempTreeLength = (reader.readUInt(1) * 2) + 1
        tree = _HuffmanTree.decode(reader, offsetIn, offsetIn + tempTreeLength + 5)
        reader.seek(offsetIn + tempTreeLength + 5)

        writer = binary.BinaryWriter()
        bitsLeft = 0
        currentNode = tree.root
        isMsbNibble = True
        while writer.tell() < tempFilesize:    # Ported from DsDecmp
            while currentNode.data == None:
                if bitsLeft == 0:
                    data = reader.readU32()
                    bitsLeft = 32
                bitsLeft-=1
                nextIsRight = (data & (1 << bitsLeft)) != 0
                if nextIsRight:
                    currentNode = currentNode.right
                else:
                    currentNode = currentNode.left
            
            if useHalfByteBlocks:
                if isMsbNibble:
                    tempIntData = int.from_bytes(currentNode.data, byteorder = 'little') << 4
                else:
                    tempIntData |= int.from_bytes(currentNode.data, byteorder = 'little')        
                    writer.writeInt(tempIntData, 1)
                isMsbNibble = not(isMsbNibble)
            else:
                writer.write(currentNode.data)
            currentNode = tree.root

        if useHalfByteBlocks and not(isMsbNibble):
            writer.writeInt(tempIntData, 1)
        self.data = writer.data[:tempFilesize]
        return True

    def compressRle(self, addHeader=False):
        writer = binary.BinaryWriter()
        reader = binary.BinaryReader(data = self.data)

        tempCompressedByte = b''
        tempCompressedByteLength = 0
        tempUncompressedSection = bytearray(b'')
        compressRepetition = False

        def getRleFlagByte(isCompressed, length):
            if isCompressed:
                return (0x80 | (length - 3)).to_bytes(1, byteorder = 'little')          # Enable MSB compression flag
            return (length - 1).to_bytes(1, byteorder = 'little')
        
        def writeData():
            if len(tempUncompressedSection) > 0:
                writer.write(getRleFlagByte(False, len(tempUncompressedSection)) + tempUncompressedSection)
            if tempCompressedByteLength > 0:
                writer.write(getRleFlagByte(True, tempCompressedByteLength) + tempCompressedByte)
        
        while reader.hasDataRemaining():
            tempByte = reader.read(1)
            if compressRepetition:
                if tempByte == tempCompressedByte:
                    tempCompressedByteLength += 1
                if tempCompressedByteLength == 130 or tempByte != tempCompressedByte:   # If max size has been reached or there's no more repetition
                    compressRepetition = False
                    if tempCompressedByteLength < 3:                                    # Free data if compression won't do much
                        tempUncompressedSection.extend((tempCompressedByte * tempCompressedByteLength) + tempByte)
                    else:                                                               # Else, write uncompressed section, then compressed data
                        writeData()
                        if tempByte == tempCompressedByte:                              # If the compression ended because the max block size was met,
                            tempUncompressedSection = bytearray(b'')                    #     reinitiate the uncompressed section.
                        else:
                            tempUncompressedSection = bytearray(tempByte)               # Else, continue the uncompressed section as normal.
                    tempCompressedByteLength = 0
            else:
                tempUncompressedSection.extend(tempByte)
                if len(tempUncompressedSection) == 128:                                 # Reinitiate block if max size met
                    writeData()
                    tempUncompressedSection = bytearray(b'')
                elif len(tempUncompressedSection) > 1 and tempUncompressedSection[-2] == tempUncompressedSection[-1]:
                    tempCompressedByte = tempByte
                    tempCompressedByteLength = 2
                    compressRepetition = True
                    tempUncompressedSection = tempUncompressedSection[0:-2]
        # Write anything left, as there may be blocks remaining after the reader ran out of data
        writeData()
        if addHeader:
            self.data = bytearray(File.LAYTON_1_COMPRESSION[File.COMP_RLE] + File.COMP_RLE.to_bytes(1, byteorder='little') + len(self.data).to_bytes(3, byteorder = 'little') + writer.data)
        else:
            self.data = bytearray(File.COMP_RLE + len(self.data).to_bytes(3, byteorder = 'little') + writer.data)
            
    def decompressRle(self, offsetIn=0):
        reader = binary.BinaryReader(data = self.data)
        reader.seek(offsetIn)
        if reader.readUInt(1) != File.COMP_RLE:
            return False
        tempFilesize = reader.readUInt(3)
        writer = binary.BinaryWriter()
        while writer.tell() < tempFilesize:
            flag = int.from_bytes(reader.read(1), byteorder = 'little')
            isCompressed = (flag & 0x80) > 0
            if isCompressed:
                decompressedLength = (flag & 0x7f) + 3
                decompressedData = reader.read(1)
                for _indexByte in range(decompressedLength):
                    writer.write(decompressedData)
            else:
                decompressedLength = (flag & 0x7f) + 1
                writer.write(reader.read(decompressedLength))
        self.data = writer.data
        return True
    
    def compressLz10(self, addHeader=False):
        if addHeader:
            self.data = File.LAYTON_1_COMPRESSION[File.COMP_LZ10] + ndspy.lz10.compress(self.data)
        else:
            self.data = ndspy.lz10.compress(self.data)

    def decompressLz10(self, offsetIn=0):
        try:
            self.data = ndspy.lz10.decompress(self.data[offsetIn:])
            return True
        except:
            return False
    
    def save(self):
        """Converts the object state into its original binary form.
        """
        pass

    def export(self, filepath : str) -> bool:
        """Writes the binary form into new file at the provided filepath. Will overwrite existing contents.

        Args:
            filepath (str): Filepath for output. Can be relative or absolute

        Returns:
            bool: True if operation was successful
        """
        # Add a method to BinaryWriter to do this
        try:
            if self.extension != '':
                extension = '.' + self.extension
            else:
                extension = ''
            with open(filepath + self.name + extension, 'wb') as dataOut:
                dataOut.write(self.data)
            return True
        except IOError:
            logSevere("Error writing file!")
            return False
    
    @staticmethod
    def load(filepath):
        reader = binary.BinaryReader(filename = filepath)
        tempName = filepath.split("//")[-1]
        if tempName == "":
            logSevere("Warning: Invalid filename!")
            tempName = "NULL"
        return File(name=tempName, data=reader.data)

class Archive(File):
    def __init__(self, name=""):
        File.__init__(self, name=name)
        self.files = []

    def extract(self, filepath):
        outputFilepath = "\\".join(filepath.split("\\")) + "\\" + self.name.split("\\")[-1]
        makedirs(outputFilepath, exist_ok=True)
        for fileChunk in self.files:
            with open(outputFilepath + "\\" + fileChunk.name, 'wb') as dataOut:
                dataOut.write(fileChunk.data)
    
    def getFile(self, name):
        # TODO - Optimise with a dictionary
        for file in self.files:
            if file.name == name:
                return file.data
        return None

class LaytonPack(Archive):

    METADATA_BLOCK_SIZE = 16
    MAGIC               = [b'LPCK', b'PCK2']

    def __init__(self, name="", version = 0):
        Archive.__init__(self, name=name)
        self._version = version

    def load(self, data):
        reader = binary.BinaryReader(data = data)
        offsetHeader = reader.readU32()
        lengthArchive = reader.readU32()
        if self._version == 0:
            reader.seek(4,1)    # Skip countFile (v0)
        magic = reader.read(4)
        try:
            # self._version = LaytonPack.MAGIC.index(magic)
            reader.seek(offsetHeader)
            while reader.tell() != lengthArchive:
                metadata = reader.readU32List(4)
                self.files.append(File(name = reader.readPaddedString(metadata[0] - LaytonPack.METADATA_BLOCK_SIZE, encoding = ENCODING_DEFAULT_STRING),
                                       data = reader.read(metadata[3])))
                reader.seek(metadata[1] - (metadata[3] + metadata[0]), 1)
            return True
        except ValueError:
            return False
    
    def save(self):
        # TODO - Support writing LT2 PCK files, which differ only in that they specify the start offset of the file.
        writer = binary.BinaryWriter()
        writer.writeU32(16)
        writer.writeU32(0)
        writer.writeU32(len(self.files))
        writer.write(LaytonPack.MAGIC[self._version])
        for fileChunk in self.files:
            header = binary.BinaryWriter()
            data = binary.BinaryWriter()
            data.writeString(fileChunk.name, ENCODING_DEFAULT_STRING)
            data.align(4)
            header.writeU32(data.tell() + LaytonPack.METADATA_BLOCK_SIZE)
            data.write(fileChunk.data)
            data.dsAlign(4, 4)
            header.writeU32(data.tell() + LaytonPack.METADATA_BLOCK_SIZE)
            header.writeU32(0)
            header.writeU32(len(fileChunk.data))
            writer.write(header.data)
            writer.write(data.data)
        writer.insert(writer.tell().to_bytes(4, byteorder = 'little'), 4)
        self.data = writer.data

class LaytonPack2(Archive):

    HEADER_BLOCK_SIZE = 32

    def __init__(self, name=""):
        Archive.__init__(self, name=name)
    
    def load(self, data):
        reader = binary.BinaryReader(data = data)
        if reader.read(4) == b'LPC2':
            countFile = reader.readU32()
            offsetFile = reader.readU32()
            _lengthArchive = reader.readU32()
            offsetMetadata = reader.readU32()
            offsetName = reader.readU32()
            
            for indexFile in range(countFile):
                reader.seek(offsetMetadata + (12 * indexFile))
                fileOffsetName = reader.readU32()
                fileOffsetData = reader.readU32()
                fileLengthData = reader.readU32()

                reader.seek(offsetName + fileOffsetName)
                tempName = reader.readNullTerminatedString(ENCODING_DEFAULT_STRING)
                reader.seek(offsetFile + fileOffsetData)
                tempData = reader.read(fileLengthData)
                self.files.append(File(tempName, data=tempData))

            return True

        return False
    
    def save(self):
        metadata = binary.BinaryWriter()
        sectionName = binary.BinaryWriter()
        sectionData = binary.BinaryWriter()
        for fileIndex, fileChunk in enumerate(self.files):
            metadata.writeU32(sectionName.tell())
            metadata.writeU32(sectionData.tell())
            metadata.writeU32(len(fileChunk.data))

            sectionName.writeString(fileChunk.name, ENCODING_DEFAULT_STRING)
            if fileIndex < len(self.files):
                sectionName.write(b'\x00')

            sectionData.write(fileChunk.data)
            sectionData.dsAlign(4, 4)

        sectionName.dsAlign(4, 4)
        
        writer = binary.BinaryWriter()
        writer.write(b'LPC2')
        writer.writeU32(len(self.files))
        writer.writeU32(LaytonPack2.HEADER_BLOCK_SIZE + metadata.tell() + sectionName.tell())
        writer.writeU32(0) # EOFC, not written until end
        writer.writeU32(LaytonPack2.HEADER_BLOCK_SIZE)
        writer.writeU32(LaytonPack2.HEADER_BLOCK_SIZE + metadata.tell())
        writer.writeU32(LaytonPack2.HEADER_BLOCK_SIZE + metadata.tell() + sectionName.tell())
        writer.pad(LaytonPack2.HEADER_BLOCK_SIZE - writer.tell())
        writer.write(metadata.data)
        writer.write(sectionName.data)
        writer.write(sectionData.data)
        writer.insert(writer.tell().to_bytes(4, byteorder = 'little'), 12)

        self.data = writer.data