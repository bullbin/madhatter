from ..binary import BinaryReader, BinaryWriter
from .generic_dlz import DlzEntryNull, DlzData

# ev_fix.dat
# Used to evaluate whether an event has been completed or not
# Since there is limited space in the save file, only 1024 events can be logged as viewed
# The game uses this file to reference these flags more conservatively
# Most, if not all events are stored here
# EventBaseList

class DlzEntryEvFix(DlzEntryNull):

    LENGTH_ENTRY = 6

    def __init__(self, idEvent, indexPuzzle, indexEventViewedFlag):
        DlzEntryNull.__init__(self)
        self.idEvent                = idEvent
        self.indexPuzzle            = indexPuzzle
        self.indexEventViewedFlag   = indexEventViewedFlag

    @staticmethod
    def fromBytes(data):
        if len(data) == DlzEntryEvFix.LENGTH_ENTRY:
            reader = BinaryReader(data=data)
            return DlzEntryEvFix(reader.readU16(), reader.readS16(), reader.readS16())
        return DlzEntryNull()
    
    def toBytes(self):
        writer = BinaryWriter()
        writer.writeU16(self.idEvent)
        writer.writeS16(self.indexPuzzle)
        writer.writeS16(self.indexEventViewedFlag)
        return writer.data

class EventBaseList(DlzData):
    def __init__(self):
        DlzData.__init__(self)
        self._eventLookup = {}
    
    def addEntryFromData(self, data):
        tempEvent = DlzEntryEvFix.fromBytes(data)
        if type(tempEvent) != DlzEntryNull:
            self._eventLookup[tempEvent.idEvent] = self.getCountEntries()
            self.addEntry(tempEvent)
    
    def removeEntry(self, indexEntry):
        if 0 <= indexEntry < self.getCountEntries():
            for key in self._eventLookup:
                if self._eventLookup[key] > indexEntry:
                    self._eventLookup[key] = self._eventLookup[key] - 1
            del self._eventLookup[key]
            return super().removeEntry(indexEntry)
        return False

    def searchForEntry(self, idEvent):
        if idEvent in self._eventLookup:
            return self._eventLookup[idEvent]
        return None