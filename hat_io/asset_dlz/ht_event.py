# Herbtea Event
# Links event IDs to herbtea IDs for triggering the minigame

from typing import Optional
from ..binary import BinaryReader, BinaryWriter
from .generic_dlz import DlzEntryNull, DlzData

class DlzEntryHerbteaEvent(DlzEntryNull):

    LENGTH_ENTRY = 4

    def __init__(self, idEvent : int, idHerbteaFlag : int):
        DlzEntryNull.__init__(self)
        self.idEvent : int = idEvent
        self.idHerbteaFlag : int = idHerbteaFlag

    @staticmethod
    def fromBytes(data):
        if len(data) == DlzEntryHerbteaEvent.LENGTH_ENTRY:
            reader = BinaryReader(data=data)
            return DlzEntryHerbteaEvent(reader.readU16(), reader.readU16())
        return DlzEntryNull()
    
    def toBytes(self):
        writer = BinaryWriter()
        writer.writeU16(self.idEvent)
        writer.writeU16(self.idHerbteaFlag)
        return writer.data

class HerbteaEvent(DlzData):
    def __init__(self):
        DlzData.__init__(self)
        self._entryType = DlzEntryHerbteaEvent
    
    def searchForEntry(self, idEvent : int) -> Optional[DlzEntryHerbteaEvent]:
        for indexEntry in range(self.getCountEntries()):
            entry = self.getEntry(indexEntry)
            if type(entry) == DlzEntryHerbteaEvent and entry.idEvent == idEvent:
                return entry
        return None