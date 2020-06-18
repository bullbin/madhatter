from .asset import File
from .binary import BinaryReader, BinaryWriter

# Controls which events are shown when visiting an area.
# These events will have an eventViewed flag to prevent them from being
# shown twice, so remember to cross reference ev_fix

# TODO - Normalise maximum amount of rooms (used also in PlaceFlag for example)

class AutoEventSubPlaceEntry():
    def __init__(self, idEvent, chapterStart, chapterEnd):
        self.idEvent = idEvent
        self.chapterStart = chapterStart
        self.chapterEnd = chapterEnd

class AutoEventPlaceCollection():

    MAX_SUBROOM_COUNT = 8

    def __init__(self, indexRoom):
        self.indexRoom = indexRoom
        self.subEntries = {}
        for indexEntry in range(AutoEventPlaceCollection.MAX_SUBROOM_COUNT):
            self.subEntries[indexEntry] = None

    def getSubPlaceEntry(self, indexSubPlace):
        if indexSubPlace in self.subEntries:
            return self.subEntries[indexSubPlace]
        return None
    
    def setSubPlaceEntry(self, indexSubPlace, entry):
        if indexSubPlace in self.subEntries and (type(entry) == AutoEventSubPlaceEntry or type(entry) == None):
            self.subEntries[indexSubPlace] = entry
            return True
        return False

class AutoEvent(File):

    MAX_ROOM_COUNT = 128

    def __init__(self):
        File.__init__(self)
        # TODO : Fix naming
        self.entries = []

    def load(self, data):

        reader = BinaryReader(data=data)

        for indexRoom in range(AutoEvent.MAX_ROOM_COUNT):
            self.entries.append(AutoEventPlaceCollection(indexRoom))
            for indexSubRoom in range(AutoEventPlaceCollection.MAX_SUBROOM_COUNT):
                idEvent = reader.readU16()
                chapterStart = reader.readU16()
                chapterEnd = reader.readU16()
                reader.seek(2,1)

                if chapterStart != 0 or chapterEnd != 0:
                    self.entries[indexRoom].setSubPlaceEntry(indexSubRoom, AutoEventSubPlaceEntry(idEvent, chapterStart, chapterEnd))
    
    def save(self):
        writer = BinaryWriter()

        for entry in self.entries:
            for indexSubPlace in range(AutoEventPlaceCollection.MAX_SUBROOM_COUNT):
                subPlace = entry.getSubPlaceEntry(indexSubPlace)
                if subPlace == None:
                    writer.pad(8)
                else:
                    writer.writeU16(subPlace.idEvent)
                    writer.writeU16(subPlace.chapterStart)
                    writer.writeU16(subPlace.chapterEnd)
                    writer.pad(2)
        
        self.data = writer.data