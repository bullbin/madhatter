from ..asset import File
from ..binary import BinaryReader, BinaryWriter

# TODO - Some dlzs probably require sorting of values
# TODO - Encoding mismatch, ev_str still requires cp932 support

class DlzEntryNull():
    @staticmethod
    def fromBytes(data):
        return DlzEntryNull()
    
    def toBytes(self):
        return b''

class DlzEntry(DlzEntryNull):
    def __init__(self, data):
        self.data = data
    
    @staticmethod
    def fromBytes(data):
        return DlzEntry(data)

    def toBytes(self):
        return self.data

class DlzData(File):

    ENTRY_OFFSET = 8

    def __init__(self):
        File.__init__(self)
        self._entries = []
        self.lengthEntry = 0
    
    def load(self, data):
        reader = BinaryReader(data=data)
        countEntries = reader.readU16()
        if reader.readU16() == DlzData.ENTRY_OFFSET:
            self.lengthEntry = reader.readU32()
            reader.seek(DlzData.ENTRY_OFFSET)
            for indexEntry in range(countEntries):
                self.addEntryFromData(reader.read(self.lengthEntry))
    
    def save(self):
        writerHeader = BinaryWriter()
        writerData = BinaryWriter()

        countEntry = 0
        for indexEntry in range(self.getCountEntries()):
            workingEntryBytes = self.getEntry(indexEntry).toBytes()
            if len(workingEntryBytes) == self.lengthEntry:
                writerData.write(workingEntryBytes)
                countEntry += 1
        
        writerHeader.writeU16(countEntry)
        writerHeader.writeU16(DlzData.MAGIC_VERSION)
        writerHeader.writeU32(self.lengthEntry)
        writerHeader.write(writerData.data)
        return writerHeader.data

    def addEntry(self, entry):
        self._entries.append(entry)

    def addEntryFromData(self, data):
        self.addEntry(DlzEntry.fromBytes(data))

    def getCountEntries(self):
        return len(self._entries)

    def getEntry(self, indexEntry):
        if 0 <= indexEntry < self.getCountEntries():
            return self._entries[indexEntry]
        return None
    
    def removeEntry(self, indexEntry):
        if 0 <= indexEntry < self.getCountEntries():
            del self._entries[indexEntry]
            return True
        return False
    
    def searchForEntry(self, key):
        return None