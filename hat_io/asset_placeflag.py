from typing import Dict, List, Optional
from .asset import File
from .binary import BinaryReader, BinaryWriter

# Used to decide which room state to load based on current chapter and conditional flags

class PlaceFlagRoomEntry():
    def __init__(self, chapterStart, chapterEnd):
        self.chapterStart = chapterStart
        self.chapterEnd = chapterEnd
    
    def toBytes(self) -> bytes:
        writer = BinaryWriter()
        writer.writeU16(self.chapterStart)
        writer.writeU16(self.chapterEnd)
        return writer.data

class PlaceFlagCounterFlagEntry():
    def __init__(self, indexEventCounter, decodeMode, unk1):
        self.indexEventCounter = indexEventCounter
        self.unk1 = unk1
        self.decodeMode = decodeMode
    
    def toBytes(self) -> bytes:
        writer = BinaryWriter()
        writer.writeInt(self.indexEventCounter, 1, False)
        writer.writeInt(self.unk1, 1, False)
        writer.writeInt(self.decodeMode, 1, False)
        return writer.data

class PlaceFlagRoomCollection():
    def __init__(self, roomIndex):
        self.roomIndex = roomIndex
        self.entries = []
        self.counterEntries = []

    def addEntry(self, entry):
        self.entries.append(entry)
    
    def getEntry(self, indexEntry) -> Optional[PlaceFlagRoomEntry]:
        if 0 <= indexEntry < len(self.entries):
            return self.entries[indexEntry]
        return None
    
    def addCounterEntry(self, entry):
        self.counterEntries.append(entry)

    def getCounterEntry(self, indexEntry) -> Optional[PlaceFlagCounterFlagEntry]:
        if 0 <= indexEntry < len(self.counterEntries):
            return self.counterEntries[indexEntry]
        return None

# TODO - Init with correct lengths
# TODO - Add export
# TODO - Improve access

class PlaceFlag(File):
    def __init__(self):
        File.__init__(self)
        self.entries : List[PlaceFlagRoomCollection] = []
    
    def load(self, data):

        reader = BinaryReader(data=data)

        for indexRoom in range(128):
            self.entries.append(PlaceFlagRoomCollection(indexRoom))
            for indexSubRoom in range(16):
                self.entries[indexRoom].addEntry(PlaceFlagRoomEntry(reader.readU16(), reader.readU16()))
        
        for indexRoom in range(128):
            for indexSubRoom in range(16):
                self.entries[indexRoom].addCounterEntry(PlaceFlagCounterFlagEntry(reader.readUInt(1), reader.readUInt(1), reader.readUInt(1)))
        
        self.data = data
    
    def save(self):
        # TODO - Rewrite this library
        mapRoomIndexToCollection : Dict[int, Optional[PlaceFlagRoomCollection]] = {}
        for indexRoom in range(128):
            mapRoomIndexToCollection[indexRoom] = None
        
        for entry in self.entries:
            if entry.roomIndex in mapRoomIndexToCollection:
                mapRoomIndexToCollection[entry.roomIndex] = entry

        blankRoom = PlaceFlagRoomCollection(0)
        blankEntrySubRoom = PlaceFlagRoomEntry(0,0)
        blankEntryCounter = PlaceFlagCounterFlagEntry(0,0,0)

        writer = BinaryWriter()

        for indexRoom in range(128):
            entry = mapRoomIndexToCollection[indexRoom]
            if entry == None:
                entry = blankRoom

            for indexSubRoom in range(16):
                if (entrySubRoom := entry.getEntry(indexSubRoom)) != None:
                    writer.write(entrySubRoom.toBytes())
                else:
                    writer.write(blankEntrySubRoom.toBytes())
            
            for indexSubRoom in range(16):
                if (entrySubRoom := entry.getCounterEntry(indexSubRoom)) != None:
                    writer.write(entrySubRoom.toBytes())
                else:
                    writer.write(blankEntryCounter.toBytes())
        
        self.data = writer.data