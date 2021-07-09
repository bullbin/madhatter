# Nazo List
# Used to store basic information about puzzles.
# The in-game puzzle list will retain the order of this file.

from __future__ import annotations
from typing import Optional, Type, Union
from ..binary import BinaryReader, BinaryWriter
from .generic_dlz import DlzEntryNull, DlzData
from ..const import ENCODING_DEFAULT_STRING

class DlzEntryNzLst(DlzEntryNull):
    def __init__(self, idInternal : int, idExternal : int, name : str, idGroup : int):
        DlzEntryNull.__init__(self)

        self.idInternal : int   = idInternal
        self.idExternal : int   = idExternal
        self.name       : str   = name
        self.idGroup    : int   = idGroup

class DlzEntryNzLstNds(DlzEntryNzLst):

    LENGTH_ENTRY = 0x36

    def __init__(self, idInternal : int, idExternal : int, name : str, idGroup : int):
        super().__init__(idInternal, idExternal, name, idGroup)
    
    @staticmethod
    def fromBytes(data) -> Union[DlzEntryNull, DlzEntryNzLstNds]:
        if len(data) == DlzEntryNzLstNds.LENGTH_ENTRY:
            reader = BinaryReader(data=data)
            return DlzEntryNzLstNds(reader.readU16(), reader.readU16(), reader.readPaddedString(48, ENCODING_DEFAULT_STRING), reader.readS16())
        return DlzEntryNull()
    
    def toBytes(self) -> bytes:
        writer = BinaryWriter()
        writer.writeU16(self.idInternal)
        writer.writeU16(self.idExternal)
        writer.writePaddedString(self.name, 48, ENCODING_DEFAULT_STRING)
        writer.writeS16(self.idGroup)
        return writer.data

class DlzEntryNzLstHd(DlzEntryNzLst):

    LENGTH_ENTRY = 0x56

    def __init__(self, idInternal : int, idExternal : int, name : str, idGroup : int):
        super().__init__(idInternal, idExternal, name, idGroup)
    
    @staticmethod
    def fromBytes(data) -> Union[DlzEntryNull, DlzEntryNzLstHd]:
        if len(data) == DlzEntryNzLstHd.LENGTH_ENTRY:
            reader = BinaryReader(data=data)
            return DlzEntryNzLstHd(reader.readU16(), reader.readU16(), reader.readPaddedString(80, ENCODING_DEFAULT_STRING), reader.readS16())
        return DlzEntryNull()
    
    def toBytes(self) -> bytes:
        writer = BinaryWriter()
        writer.writeU16(self.idInternal)
        writer.writeU16(self.idExternal)
        writer.writePaddedString(self.name, 80, ENCODING_DEFAULT_STRING)
        writer.writeS16(self.idGroup)
        return writer.data

class NazoList(DlzData):
    def __init__(self):
        DlzData.__init__(self)
        self._internalLookup = {}

    def _addEntryToDb(self, entry: Type[DlzEntryNzLst]):
        self._internalLookup[entry.idInternal] = entry
    
    def _removeEntryFromDb(self, entry: Type[DlzEntryNzLst]):
        del self._internalLookup[entry.idInternal]

    def searchForEntry(self, idInteral : int) -> Optional[Type[DlzEntryNzLst]]:
        if idInteral in self._internalLookup:
            return self._internalLookup[idInteral]
        return None

class NazoListNds(NazoList):
    def __init__(self):
        super().__init__()
        self._entryType = DlzEntryNzLstNds

class NazoListHd(NazoList):
    def __init__(self):
        super().__init__()
        self._entryType = DlzEntryNzLstHd