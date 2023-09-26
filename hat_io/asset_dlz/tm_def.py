# Time Definition
# Stores framecounts for certain special animations.
# Can be called for wait periods in scripts.

from typing import Optional
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
        DlzData.__init__(self)
        self._entryType = DlzEntryTimeDefinition
        self._internalLookup = {}

    def _addEntryToDb(self, entry: DlzEntryTimeDefinition):
        self._internalLookup[entry.idTime] = entry
    
    def _removeEntryFromDb(self, entry: DlzEntryTimeDefinition):
        del self._internalLookup[entry.idTime]

    def searchForEntry(self, idTime : int) -> Optional[DlzEntryTimeDefinition]:
        if idTime in self._internalLookup:
            return self._internalLookup[idTime]
        return None