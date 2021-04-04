# Submap Info
# Controls how and when the guiding arrows ("HERE!") on the map are displayed

from typing import Optional
from ..binary import BinaryReader, BinaryWriter
from .generic_dlz import DlzData, DlzEntryNull

class DlzEntrySubmapInfo(DlzEntryNull):

    LENGTH_ENTRY = 8

    def __init__(self, requiredViewedEventFlag : int, indexPlace, chapter, indexImage, x, y):
        DlzEntryNull.__init__(self)
        self.idRequiredViewedEvent : int = requiredViewedEventFlag
        self.indexPlace            : int = indexPlace
        self.chapter               : int = chapter
        self.indexImage            : int = indexImage
        self.pos                   = (x,y)

    @staticmethod
    def fromBytes(data):
        if len(data) == DlzEntrySubmapInfo.LENGTH_ENTRY:
            reader = BinaryReader(data=data)
            return DlzEntrySubmapInfo(reader.readUInt(1), reader.readUInt(1), reader.readU16(), reader.readUInt(1), reader.readUInt(1), reader.readUInt(1))
        return DlzEntryNull()
    
    def toBytes(self):
        writer = BinaryWriter()
        writer.writeInt(self.idRequiredViewedEvent, 1)
        writer.writeInt(self.indexPlace, 1)
        writer.writeU16(self.chapter)
        writer.writeInt(self.indexImage, 1)
        writer.writeInt(self.pos[0], 1)
        writer.writeInt(self.pos[1], 1)
        writer.pad(1)
        return writer.data

class SubmapInfo(DlzData):
    def __init__(self):
        DlzData.__init__(self)
    
    def addEntryFromData(self, data):
        if type(submapEntry := DlzEntrySubmapInfo.fromBytes(data)) == DlzEntrySubmapInfo:
            self.addEntry(submapEntry)
    
    def searchForEntry(self, eventViewedFlag : int, indexPlace : int, chapter : int) -> Optional[DlzEntrySubmapInfo]:
        # TODO - Don't do linear search
        for indexEntry in range(self.getCountEntries()):
            entry = self.getEntry(indexEntry)
            entry : DlzEntrySubmapInfo
            if entry.idRequiredViewedEvent == eventViewedFlag and entry.indexPlace == indexPlace and entry.chapter == chapter:
                return entry
        return None