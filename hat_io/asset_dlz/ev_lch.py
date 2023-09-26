# Event Descriptor Bank
# Not used nor loaded in-game. Seems to be relic from development

from __future__ import annotations
from typing import Optional, Type, Union
from ..binary import BinaryReader, BinaryWriter
from .generic_dlz import DlzEntryNull, DlzData

class DlzEntryEventDescriptorBank(DlzEntryNull):

    def __init__(self, idEvent : int, description : str):
        DlzEntryNull.__init__(self)
        self.idEvent : int      = idEvent
        self.description : str  = description

class DlzEntryEventDescriptorBankNds(DlzEntryEventDescriptorBank):

    LENGTH_ENTRY = 0x34

    def __init__(self, idEvent : int, description : str):
        super().__init__(idEvent, description)

    @staticmethod
    def fromBytes(data : bytes) -> Union[DlzEntryEventDescriptorBankNds, DlzEntryNull]:
        if len(data) == DlzEntryEventDescriptorBankNds.LENGTH_ENTRY:
            reader = BinaryReader(data=data)
            # TODO - What encoding? DEFAULT const?
            return DlzEntryEventDescriptorBankNds(reader.readU32(), reader.readPaddedString(48, 'shift-jis'))
        return DlzEntryNull()
    
    def toBytes(self):
        writer = BinaryWriter()
        writer.writeU32(self.idEvent)
        writer.writePaddedString(self.description, 48, 'shift-jis')
        return writer.data

class DlzEntryEventDescriptorBankHd(DlzEntryEventDescriptorBank):

    LENGTH_ENTRY = 0x44

    def __init__(self, idEvent : int, description : str):
        super().__init__(idEvent, description)

    @staticmethod
    def fromBytes(data : bytes) -> Union[DlzEntryEventDescriptorBankHd, DlzEntryNull]:
        if len(data) == DlzEntryEventDescriptorBankHd.LENGTH_ENTRY:
            reader = BinaryReader(data=data)
            return DlzEntryEventDescriptorBankHd(reader.readU32(), reader.readPaddedString(64, 'shift-jis'))
        return DlzEntryNull()
    
    def toBytes(self):
        writer = BinaryWriter()
        writer.writeU32(self.idEvent)
        writer.writePaddedString(self.description, 64, 'shift-jis')
        return writer.data

class EventDescriptorBank(DlzData):
    def __init__(self):
        DlzData.__init__(self)
    
    # TODO - Lookup table
    def _searchForEntry(self, idEvent : int) -> Optional[Type[DlzEntryEventDescriptorBank]]:
        for indexEntry in range(self.getCountEntries()):
            entry = self.getEntry(indexEntry)
            if isinstance(entry, DlzEntryEventDescriptorBank) and entry.idEvent == idEvent:
                return entry
        return None

# TODO - Conversion
class EventDescriptorBankNds(EventDescriptorBank):
    def __init__(self):
        super().__init__()
        self._entryType = DlzEntryEventDescriptorBankNds
    
    def searchForEntry(self, idEvent : int) -> Optional[DlzEntryEventDescriptorBankNds]:
        return super()._searchForEntry(idEvent)

class EventDescriptorBankHd(EventDescriptorBank):
    def __init__(self):
        super().__init__()
        self._entryType = DlzEntryEventDescriptorBankHd
    
    def searchForEntry(self, idEvent : int) -> Optional[DlzEntryEventDescriptorBankHd]:
        return super()._searchForEntry(idEvent)