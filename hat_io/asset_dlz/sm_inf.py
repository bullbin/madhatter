# Submap Info
# Controls how and when the guiding arrows ("HERE!") on the map are displayed

from typing import Optional, Type
from ..binary import BinaryReader, BinaryWriter
from .generic_dlz import DlzData, DlzEntryNull

class DlzEntrySubmapInfo(DlzEntryNull):
    def __init__(self, requiredViewedEventFlag : int, indexPlace : int, chapter : int, indexImage : int, x : int, y : int):
        DlzEntryNull.__init__(self)
        self.idRequiredViewedEvent : int = requiredViewedEventFlag
        self.indexPlace            : int = indexPlace
        self.chapter               : int = chapter
        self.indexImage            : int = indexImage
        self.pos                   = (x,y)

class DlzEntrySubmapInfoNds(DlzEntrySubmapInfo):

    LENGTH_ENTRY = 8

    def __init__(self, requiredViewedEventFlag : int, indexPlace : int, chapter : int, indexImage : int, x : int, y : int):
        super().__init__(requiredViewedEventFlag, indexPlace, chapter, indexImage, x, y)

    @staticmethod
    def fromBytes(data):
        if len(data) == DlzEntrySubmapInfoNds.LENGTH_ENTRY:
            reader = BinaryReader(data=data)
            return DlzEntrySubmapInfoNds(reader.readUInt(1), reader.readUInt(1), reader.readU16(), reader.readUInt(1), reader.readUInt(1), reader.readUInt(1))
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

class DlzEntrySubmapInfoHd(DlzEntrySubmapInfo):

    LENGTH_ENTRY = 12

    def __init__(self, requiredViewedEventFlag : int, indexPlace : int, chapter : int, indexImage : int, x : int, y : int):
        super().__init__(requiredViewedEventFlag, indexPlace, chapter, indexImage, x, y)

    @staticmethod
    def fromBytes(data):
        if len(data) == DlzEntrySubmapInfoHd.LENGTH_ENTRY:
            reader = BinaryReader(data=data)
            requiredViewedEventFlag = reader.readUInt(1)
            indexPlace = reader.readUInt(1)
            chapter = reader.readU16()
            indexImage = reader.readUInt(1)
            reader.seek(1,1)
            x = reader.readU16()
            y = reader.readU16()
            return DlzEntrySubmapInfoHd(requiredViewedEventFlag, indexPlace, chapter, indexImage, x, y)
        return DlzEntryNull()
    
    def toBytes(self):
        writer = BinaryWriter()
        writer.writeInt(self.idRequiredViewedEvent, 1)
        writer.writeInt(self.indexPlace, 1)
        writer.writeU16(self.chapter)
        writer.writeInt(self.indexImage, 1)
        writer.pad(1)
        writer.writeU16(self.pos[0])
        writer.writeU16(self.pos[1])
        writer.pad(2)
        return writer.data

class SubmapInfo(DlzData):
    def __init__(self):
        DlzData.__init__(self)
    
    def searchForEntry(self, eventViewedFlag : int, indexPlace : int, chapter : int) -> Optional[Type[DlzEntrySubmapInfo]]:
        # TODO - Don't do linear search
        for indexEntry in range(self.getCountEntries()):
            entry = self.getEntry(indexEntry)
            if entry.idRequiredViewedEvent == eventViewedFlag and entry.indexPlace == indexPlace and entry.chapter == chapter:
                return entry
        return None

class SubmapInfoNds(SubmapInfo):
    def __init__(self):
        super().__init__()
       
    def addEntryFromData(self, data : bytes):
        # TODO - Use this expression for all dlz files to eliminate null entry
        if type(submapEntry := DlzEntrySubmapInfoNds.fromBytes(data)) == DlzEntrySubmapInfoNds:
            self.addEntry(submapEntry)

class SubmapInfoHd(SubmapInfo):
    def __init__(self):
        super().__init__()
       
    def addEntryFromData(self, data : bytes):
        if type(submapEntry := DlzEntrySubmapInfoHd.fromBytes(data)) == DlzEntrySubmapInfoHd:
            self.addEntry(submapEntry)