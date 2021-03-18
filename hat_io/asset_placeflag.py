from .asset import File
from .binary import BinaryReader, BinaryWriter

# Used to decide which room state to load based on current chapter and conditional flags

class PlaceFlagRoomEntry():
    def __init__(self, chapterStart, chapterEnd):
        self.chapterStart = chapterStart
        self.chapterEnd = chapterEnd

class PlaceFlagRoomCollection():
    def __init__(self, roomIndex):
        self.roomIndex = roomIndex
        self.entries = []
        self.counterEntries = []
    
    def addEntry(self, entry):
        self.entries.append(entry)
    
    def getEntry(self, indexEntry):
        if 0 <= indexEntry < len(self.entries):
            return self.entries[indexEntry]
        return None
    
    def addCounterEntry(self, entry):
        self.counterEntries.append(entry)

    def getCounterEntry(self, indexEntry):
        if 0 <= indexEntry < len(self.counterEntries):
            return self.counterEntries[indexEntry]
        return None

class PlaceFlagCounterFlagEntry():
    def __init__(self, indexEventCounter, decodeMode, unk1):
        self.indexEventCounter = indexEventCounter
        self.unk1 = unk1
        self.decodeMode = decodeMode

# TODO - Init with correct lengths
# TODO - Add export
# TODO - Improve access

class PlaceFlag(File):
    def __init__(self):
        File.__init__(self)
        self.entries = []
    
    def load(self, data):

        reader = BinaryReader(data=data)

        for indexRoom in range(128):
            self.entries.append(PlaceFlagRoomCollection(indexRoom))
            for indexSubRoom in range(16):
                self.entries[indexRoom].addEntry(PlaceFlagRoomEntry(reader.readU16(), reader.readU16()))
        
        for indexRoom in range(128):
            for indexSubRoom in range(16):
                self.entries[indexRoom].addCounterEntry(PlaceFlagCounterFlagEntry(reader.readUInt(1), reader.readUInt(1), reader.readUInt(1)))