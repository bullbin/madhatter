# Chapter Info
# Maps chapter to intro event upon loading the save

from ..binary import BinaryReader, BinaryWriter
from .generic_dlz import DlzEntryNull, DlzData

class DlzEntryChapterInfo(DlzEntryNull):

    LENGTH_ENTRY = 8

    def __init__(self, chapter, idEvent, indexEventViewedFlag, idEventAlt):
        DlzEntryNull.__init__(self)
        self.chapter                = chapter
        self.idEvent                = idEvent
        self.indexEventViewedFlag   = indexEventViewedFlag
        self.idEventAlt             = idEventAlt

    @staticmethod
    def fromBytes(data):
        if len(data) == DlzEntryChapterInfo.LENGTH_ENTRY:
            reader = BinaryReader(data=data)
            return DlzEntryChapterInfo(reader.readU16(), reader.readU16(), reader.readU16(), reader.readU16())
        return DlzEntryNull()
    
    def toBytes(self):
        writer = BinaryWriter()
        writer.writeU16(self.chapter)
        writer.writeU16(self.idEvent)
        writer.writeU16(self.indexEventViewedFlag)
        writer.writeU16(self.idEventAlt)
        return writer.data

class ChapterInfo(DlzData):
    def __init__(self):
        DlzData.__init__(self)
    
    def addEntryFromData(self, data):
        self.addEntry(DlzEntryChapterInfo.fromBytes(data))