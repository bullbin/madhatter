# Event Information
# Used to set event branching behaviour prior to executing an event

from ..binary import BinaryReader, BinaryWriter
from .generic_dlz import DlzEntryNull, DlzData

class DlzEntryEvInf2(DlzEntryNull):

    LENGTH_ENTRY = 12

    def __init__(self, idEvent, typeEvent, dataSoundSet, dataPuzzle, indexEventViewedFlag, indexStoryFlag):
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
        self._eventLookup = {}
    
    def addEntryFromData(self, data):
        tempEvent = DlzEntryEvInf2.fromBytes(data)
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