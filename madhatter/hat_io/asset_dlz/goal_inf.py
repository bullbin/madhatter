# Goal Information
# Seems to be used to trigger goal updates after events
# Some unknown information remaining here, since could not be found through reversing

from ..binary import BinaryReader, BinaryWriter
from .generic_dlz import DlzEntryNull, DlzData

class DlzEntryGoalInfo(DlzEntryNull):

    LENGTH_ENTRY = 6

    def __init__(self, idEvent, type, goal):
        if 0 <= type <= 1:
            self.type       = type
        else:
            self.type = 0
        
        self.goal       = goal
        self.idEvent    = idEvent

    @staticmethod
    def fromBytes(data):
        if len(data) == DlzEntryGoalInfo.LENGTH_ENTRY:
            reader = BinaryReader(data=data)
            return DlzEntryGoalInfo(reader.readU16(), reader.readU16(), reader.readU16())
        return DlzEntryNull()
    
    def toBytes(self):
        writer = BinaryWriter()
        writer.writeU16(self.idEvent)
        writer.writeU16(self.type)
        writer.writeU16(self.goal)
        return writer.data

class GoalInfo(DlzData):
    def __init__(self):
        DlzData.__init__(self)
    
    def addEntryFromData(self, data):
        self.addEntry(DlzEntryGoalInfo.fromBytes(data))