# Time Definition
# Stores framecounts for certain special animations.
# Can be called for wait periods in scripts.

from ..binary import BinaryReader, BinaryWriter
from .generic_dlz import DlzEntryNull, DlzData

class DlzEntryTimeDefinition(DlzEntryNull):
    
    LENGTH_ENTRY = 4

    def __init__(self, idTime, countFrames):
        DlzEntryNull.__init__(self)
        self.idTime = idTime
        self.countFrames = countFrames
    
    @staticmethod
    def fromBytes(data):
        if len(data) == DlzEntryTimeDefinition.LENGTH_ENTRY:
            reader = BinaryReader(data=data)
            return DlzEntryTimeDefinition(reader.readU16(), reader.readU16())
        return DlzEntryNull()
    
    def toBytes(self):
        writer = BinaryWriter()
        writer.writeU16(self.idTime)
        writer.writeU16(self.countFrames)
        return writer.data

class TimeDefinitionInfo(DlzData):
    def __init__(self):
        # TODO - Rewrite some dlzs to store data in a dictionary, as each index can only map to one entry
        DlzData.__init__(self)
        self._internalLookup = {}

    def addEntryFromData(self, data):
        tempEntry = DlzEntryTimeDefinition.fromBytes(data)
        if type(tempEntry) != DlzEntryNull:
            self._internalLookup[tempEntry.idTime] = self.getCountEntries()
            self.addEntry(tempEntry)
    
    def removeEntry(self, indexEntry):
        if 0 <= indexEntry < self.getCountEntries():
            for key in self._internalLookup:
                if self._internalLookup[key] > indexEntry:
                    self._internalLookup[key] = self._internalLookup[key] - 1
            del self._internalLookup[key]
            return super().removeEntry(indexEntry)
        return False

    def searchForEntry(self, idTime):
        if idTime in self._internalLookup:
            return self._internalLookup[idTime]
        return None