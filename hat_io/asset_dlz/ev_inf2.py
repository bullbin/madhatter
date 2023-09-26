# Event Information
# Used to set event branching behaviour prior to executing an event

from typing import Optional
from ..binary import BinaryReader, BinaryWriter
from .generic_dlz import DlzEntryNull, DlzData

class DlzEntryEvInf2(DlzEntryNull):

    LENGTH_ENTRY = 12

    def __init__(self, idEvent : Optional[int], typeEvent : Optional[int], dataSoundSet : Optional[int],
                 dataPuzzle : Optional[int], indexEventViewedFlag : Optional[int], indexStoryFlag : Optional[int]):
        DlzEntryNull.__init__(self)
        self.idEvent                = idEvent
        self.typeEvent              = typeEvent
        self.dataSoundSet           = dataSoundSet
        self.dataPuzzle             = dataPuzzle
        self.indexEventViewedFlag   = indexEventViewedFlag
        self.indexStoryFlag         = indexStoryFlag

    @staticmethod
    def fromBytes(data):

        def readMaskedU16(reader):
            value = reader.readU16()
            if value == 0xffff:
                return None
            return value

        if len(data) == DlzEntryEvInf2.LENGTH_ENTRY:
            reader = BinaryReader(data=data)
            return DlzEntryEvInf2(readMaskedU16(reader), readMaskedU16(reader), readMaskedU16(reader),
                                  readMaskedU16(reader), readMaskedU16(reader), readMaskedU16(reader))
        return DlzEntryNull()
    
    def toBytes(self):

        def writeMaskedU16(writer, value):
            if value == None:
                writer.writeU16(0xffff)
            else:
                writer.writeU16(value)

        writer = BinaryWriter()
        writeMaskedU16(writer, self.idEvent)
        writeMaskedU16(writer, self.typeEvent)
        writeMaskedU16(writer, self.dataSoundSet)
        writeMaskedU16(writer, self.dataPuzzle)
        writeMaskedU16(writer, self.indexEventViewedFlag)
        writeMaskedU16(writer, self.indexStoryFlag)
        return writer.data

class EventInfoList(DlzData):
    def __init__(self):
        DlzData.__init__(self)
        self._entryType = DlzEntryEvInf2
        self._eventLookup = {}

    def save(self):
        self._entries.sort(key=lambda x: x.idEvent)
        return super().save()
    
    def getEntry(self, indexEntry: int) -> Optional[DlzEntryEvInf2]:
        return super().getEntry(indexEntry)

    def _addEntryToDb(self, entry: DlzEntryEvInf2):
        self._eventLookup[entry.idEvent] = entry
    
    def _removeEntryFromDb(self, entry: DlzEntryEvInf2):
        del self._eventLookup[entry.idEvent]

    def searchForEntry(self, idEvent : int) -> Optional[DlzEntryEvInf2]:
        if idEvent in self._eventLookup:
            return self._eventLookup[idEvent]
        return None