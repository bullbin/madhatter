from ..binary import BinaryReader, BinaryWriter
from .generic_dlz import DlzEntryNull, DlzData

# ev_fix.dat

class DlzEntryEvFix(DlzEntryNull):

    LENGTH_ENTRY = 6

    def __init__(self, idEvent, indexPuzzle, unk):
        self.idEvent        = idEvent
        self.indexPuzzle    = indexPuzzle
        self.unk = unk

    @staticmethod
    def fromBytes(data):
        if len(data) == DlzEntryEvFix.LENGTH_ENTRY:
            reader = BinaryReader(data=data)
            return DlzEntryEvFix(reader.readU16(), reader.readS16(), reader.readS16())
        return DlzEntryNull()
    
    def toBytes(self):
        writer = BinaryWriter()
        writer.writeU16(self.idEvent)
        writer.writeS16(self.indexPuzzle)
        writer.writeS16(self.unk)
        return writer.data

class EventBaseList(DlzData):
    def __init__(self):
        DlzData.__init__(self)
    
    def addEntryFromData(self, data):
        self.addEntry(DlzEntryEvFix.fromBytes(data))