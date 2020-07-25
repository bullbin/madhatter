# Nazo List
# Used to store basic information about puzzles.
# The in-game puzzle list will retain the order of this file.

from ..binary import BinaryReader, BinaryWriter
from .generic_dlz import DlzEntryNull, DlzData
from ..const import ENCODING_DEFAULT_STRING

class DlzEntryNzLst(DlzEntryNull):

    LENGTH_ENTRY = 0x36

    def __init__(self, idInternal, idExternal, name, idReward):
        DlzEntryNull.__init__(self)

        self.idInternal = idInternal
        self.idExternal = idExternal
        self.name       = name
        self.idReward   = idReward

    @staticmethod
    def fromBytes(data):
        if len(data) == DlzEntryNzLst.LENGTH_ENTRY:
            reader = BinaryReader(data=data)
            return DlzEntryNzLst(reader.readU16(), reader.readU16(), reader.readPaddedString(48, ENCODING_DEFAULT_STRING), reader.readS16())
        return DlzEntryNull()
    
    def toBytes(self):
        writer = BinaryWriter()
        writer.writeU16(self.idInternal)
        writer.writeU16(self.idExternal)
        writer.writePaddedString(self.name, 48, ENCODING_DEFAULT_STRING)
        writer.writeS16(self.idReward)
        return writer.data

class NazoList(DlzData):
    def __init__(self):
        DlzData.__init__(self)
        self._internalLookup = {}
    
    def addEntryFromData(self, data):
        tempEntry = DlzEntryNzLst.fromBytes(data)
        if type(tempEntry) != DlzEntryNull:
            self._internalLookup[tempEntry.idInternal] = self.getCountEntries()
            self.addEntry(tempEntry)
    
    def removeEntry(self, indexEntry):
        if 0 <= indexEntry < self.getCountEntries():
            for key in self._internalLookup:
                if self._internalLookup[key] > indexEntry:
                    self._internalLookup[key] = self._internalLookup[key] - 1
            del self._internalLookup[key]
            return super().removeEntry(indexEntry)
        return False

    def searchForEntry(self, idInteral):
        if idInteral in self._internalLookup:
            return self._internalLookup[idInteral]
        return None