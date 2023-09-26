from typing import Dict, List, Optional
from .asset import File
from .binary import BinaryReader, BinaryWriter

# Controls which events are shown when visiting an area.
# These events will have an eventViewed flag to prevent them from being
# shown twice, so remember to cross reference ev_fix

# TODO - Normalise maximum amount of rooms (used also in PlaceFlag for example)

class AutoEventSubPlaceEntry():
    def __init__(self, idEvent : int, chapterStart : int, chapterEnd : int):
        self.idEvent : int = idEvent
        self.chapterStart : int = chapterStart
        self.chapterEnd : int = chapterEnd
    
    def clear(self):
        self.idEvent = 0
        self.chapterEnd = 0
        self.chapterStart = 0
    
    def isEmpty(self):
        return self.chapterStart == 0 and self.chapterEnd == 0

class AutoEventPlaceCollection():

    MAX_SUBROOM_COUNT = 8

    def __init__(self):
        self.__subEntries : Dict[int, AutoEventSubPlaceEntry] = {}
        for indexEntry in range(AutoEventPlaceCollection.MAX_SUBROOM_COUNT):
            self.__subEntries[indexEntry] = AutoEventSubPlaceEntry(0,0,0)

    def getSubPlaceEntry(self, indexSubPlace : int) -> Optional[AutoEventSubPlaceEntry]:
        if indexSubPlace in self.__subEntries:
            return self.__subEntries[indexSubPlace]
        return None

    def clear(self):
        for indexEntry in range(AutoEventPlaceCollection.MAX_SUBROOM_COUNT):
            self.__subEntries[indexEntry].clear()

    def setSubPlaceEntry(self, indexSubPlace : int, entry : Optional[AutoEventSubPlaceEntry]) -> bool:
        if indexSubPlace in self.__subEntries and (type(entry) == AutoEventSubPlaceEntry or type(entry) == None):
            if type(entry) == None:
                self.__subEntries[indexSubPlace].clear()
            else:
                self.__subEntries[indexSubPlace] = entry
            return True
        return False

class AutoEvent(File):

    MAX_ROOM_COUNT = 128

    def __init__(self):
        File.__init__(self)
        # TODO : Fix naming
        self.__entries : List[AutoEventPlaceCollection] = []
        for indexRoom in range(AutoEvent.MAX_ROOM_COUNT):
            self.__entries.append(AutoEventPlaceCollection())

    def getEntry(self, indexRoom : int) -> Optional[AutoEventPlaceCollection]:
        if 0 <= indexRoom < len(self.__entries):
            return self.__entries[indexRoom]
        return None
    
    def removeEntry(self, indexRoom : int) -> bool:
        if 0 <= indexRoom < len(self.__entries):
            for indexSubRoom in range(AutoEventPlaceCollection.MAX_SUBROOM_COUNT):
                self.__entries[indexRoom].getSubPlaceEntry(indexSubRoom).clear()
            return True
        return False

    def swapEntry(self, indexRoomA : int, indexRoomB : int) -> bool:
        if 0 <= indexRoomA < len(self.__entries) and 0 <= indexRoomB < len(self.__entries):
            self.__entries[indexRoomA], self.__entries[indexRoomB] = self.__entries[indexRoomB], self.__entries[indexRoomA]
            return True
        return False

    def load(self, data):

        reader = BinaryReader(data=data)
        self.__entries = []

        for indexRoom in range(AutoEvent.MAX_ROOM_COUNT):
            self.__entries.append(AutoEventPlaceCollection())
            for indexSubRoom in range(AutoEventPlaceCollection.MAX_SUBROOM_COUNT):
                idEvent = reader.readU16()
                chapterStart = reader.readU16()
                chapterEnd = reader.readU16()
                reader.seek(2,1)

                if chapterStart != 0 or chapterEnd != 0:
                    self.__entries[indexRoom].setSubPlaceEntry(indexSubRoom, AutoEventSubPlaceEntry(idEvent, chapterStart, chapterEnd))
        
        self.data = data
    
    def save(self):
        writer = BinaryWriter()

        for entry in self.__entries:
            for indexSubPlace in range(AutoEventPlaceCollection.MAX_SUBROOM_COUNT):
                subPlace = entry.getSubPlaceEntry(indexSubPlace)
                writer.writeU16(subPlace.idEvent)
                writer.writeU16(subPlace.chapterStart)
                writer.writeU16(subPlace.chapterEnd)
                writer.pad(2)
        
        self.data = writer.data