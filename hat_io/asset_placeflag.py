from typing import Dict, List, Optional
from .asset import File
from .binary import BinaryReader, BinaryWriter

# Used to decide which room state to load based on current chapter and conditional flags

class PlaceFlagRoomEntry():
    def __init__(self, chapterStart : int = 0, chapterEnd : int = 0):
        self.chapterStart   : int = chapterStart
        self.chapterEnd     : int = chapterEnd
    
    def clear(self):
        self.chapterEnd = 0
        self.chapterStart = 0

    def isEmpty(self) -> bool:
        return self.chapterStart == 0 or self.chapterEnd == 0
    
    def toBytes(self) -> bytes:
        writer = BinaryWriter()
        writer.writeU16(self.chapterStart)
        writer.writeU16(self.chapterEnd)
        return writer.data

class PlaceFlagCounterFlagEntry():
    def __init__(self, indexEventCounter : int = 0, decodeMode : int = 0, unk1 : int = 0):
        self.indexEventCounter  : int = indexEventCounter
        self.unk1               : int = unk1
        self.decodeMode         : int = decodeMode
    
    def clear(self):
        self.indexEventCounter = 0
        self.unk1 = 0
        self.decodeMode = 0

    def isEmpty(self) -> bool:
        return self.indexEventCounter == 0
    
    def toBytes(self) -> bytes:
        writer = BinaryWriter()
        writer.writeInt(self.indexEventCounter, 1, False)
        writer.writeInt(self.unk1, 1, False)
        writer.writeInt(self.decodeMode, 1, False)
        return writer.data

class PlaceFlagRoomCollection():

    MAX_SUBROOM_COUNT = 16

    def __init__(self):
        self.__entriesChapter : Dict[int, PlaceFlagRoomEntry] = {}
        self.__entriesCondition : Dict[int, PlaceFlagCounterFlagEntry] = {}

        for x in range(PlaceFlagRoomCollection.MAX_SUBROOM_COUNT):
            self.__entriesChapter[x] = PlaceFlagRoomEntry(0,0)
            self.__entriesCondition[x] = PlaceFlagCounterFlagEntry(0,0,0)

    def setChapterEntry(self, indexEntry : int, entry : PlaceFlagRoomEntry) -> bool:
        if indexEntry in self.__entriesChapter:
            self.__entriesChapter[indexEntry] = entry
            return True
        return False
    
    def getChapterEntry(self, indexEntry : int) -> Optional[PlaceFlagRoomEntry]:
        if indexEntry in self.__entriesChapter:
            return self.__entriesChapter[indexEntry]
        return None
    
    def setCounterEntry(self, indexEntry : int, entry : PlaceFlagCounterFlagEntry) -> bool:
        if indexEntry in self.__entriesCondition:
            self.__entriesCondition[indexEntry] = entry
            return True
        return False

    def getCounterEntry(self, indexEntry : int) -> Optional[PlaceFlagCounterFlagEntry]:
        if indexEntry in self.__entriesCondition:
            return self.__entriesCondition[indexEntry]
        return None

    def isEmpty(self) -> bool:
        for x in range(16):
            if not(self.__entriesChapter[x].isEmpty()):
                return False
            if not(self.__entriesCondition[x].isEmpty()):
                return False
        return True
    
    def clear(self):
        for x in range(16):
            self.__entriesChapter[x].clear()
            self.__entriesCondition[x].clear()

class PlaceFlag(File):

    MAX_ROOM_COUNT = 128

    def __init__(self):
        File.__init__(self)
        self.__roomToEntryMap : Dict[int, PlaceFlagRoomCollection] = {}
        for x in range(128):
            self.__roomToEntryMap[x] = PlaceFlagRoomCollection()
    
    def load(self, data):
        reader = BinaryReader(data=data)
        for indexRoom in range(PlaceFlag.MAX_ROOM_COUNT):
            self.__roomToEntryMap[indexRoom].clear()
            for indexSubRoom in range(PlaceFlagRoomCollection.MAX_SUBROOM_COUNT):
                self.__roomToEntryMap[indexRoom].setChapterEntry(indexSubRoom, PlaceFlagRoomEntry(reader.readU16(), reader.readU16()))
        
        for indexRoom in range(PlaceFlag.MAX_ROOM_COUNT):
            for indexSubRoom in range(PlaceFlagRoomCollection.MAX_SUBROOM_COUNT):
                self.__roomToEntryMap[indexRoom].setCounterEntry(indexSubRoom, PlaceFlagCounterFlagEntry(reader.readUInt(1), reader.readUInt(1), reader.readUInt(1)))
        
        self.data = data
    
    def save(self):
        writer = BinaryWriter()

        for indexRoom in range(PlaceFlag.MAX_ROOM_COUNT):
            entry = self.__roomToEntryMap[indexRoom]
            for indexSubRoom in range(PlaceFlagRoomCollection.MAX_SUBROOM_COUNT):
                entrySubRoom = entry.getChapterEntry(indexSubRoom)
                writer.write(entrySubRoom.toBytes())
        
        for indexRoom in range(PlaceFlag.MAX_ROOM_COUNT):
            entry = self.__roomToEntryMap[indexRoom]
            for indexSubRoom in range(PlaceFlagRoomCollection.MAX_SUBROOM_COUNT):
                entrySubRoom = entry.getCounterEntry(indexSubRoom)
                writer.write(entrySubRoom.toBytes())
        
        self.data = writer.data
    
    def getEntry(self, indexRoom : int) -> Optional[PlaceFlagRoomCollection]:
        if indexRoom in self.__roomToEntryMap:
            return self.__roomToEntryMap[indexRoom]
        return None

    def swapEntry(self, indexRoomA : int, indexRoomB : int) -> bool:
        if indexRoomA in self.__roomToEntryMap and indexRoomB in self.__roomToEntryMap:
            temp = self.__roomToEntryMap[indexRoomA]
            self.__roomToEntryMap[indexRoomA] = self.__roomToEntryMap[indexRoomB]
            self.__roomToEntryMap[indexRoomB] = temp
            return True
        return False
    
    def getBlankEntries(self) -> List[int]:
        output = []
        for indexRoom in range(PlaceFlag.MAX_ROOM_COUNT):
            if self.__roomToEntryMap[indexRoom].isEmpty():
                output.append(indexRoom)
        return output