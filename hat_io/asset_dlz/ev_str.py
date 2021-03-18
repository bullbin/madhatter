# ev_str
# This is used to update active goal, viewed events, story flags, puzzle states and the event counter during events
# Though there is a limit to the amount of data each entry can store, the update function is recursive so
# entries can be chained together during an update.

from .generic_dlz import DlzEntryNull, DlzData
from ..binary import BinaryReader, BinaryWriter

# TODO - Only here to test loading support. Needs rewrite to better support
# Switch recursive test to keys so objects can be faster loaded.

class DlzEntryStorySelectList(DlzEntryNull):

    LENGTH_ENTRY = 90

    def __init__(self):
        DlzEntryNull.__init__(self)
        self.idEntry        = 1
        self.name           = ""
        self.goal           = 999
        self.indexPlace     = 127
        self.idEvent        = -1
        self.idConnected    = -1

        self.eventViewedFlags   = []
        self.storyFlags         = []
        self.puzzleStates       = []
        self.eventCounterFlags  = []

    @staticmethod
    def fromBytes(data):
        if len(data) == DlzEntryStorySelectList.LENGTH_ENTRY:
            reader = BinaryReader(data=data)
            output              = DlzEntryStorySelectList()
            output.name         = reader.readPaddedString(32, 'cp932')
            output.idEntry      = reader.readU16()
            output.goal         = reader.readU16()
            output.indexPlace   = reader.readU16()
            output.idEvent      = reader.readS16()
            output.idConnected  = reader.readS16()

            for indexFlag in range(4):
                indexFlag = reader.readS16()
                if indexFlag != -1:
                    output.eventViewedFlags.append(indexFlag)
                else:
                    break
            
            reader.seek(50)
            for indexFlag in range(4):
                indexFlag = reader.readS16()
                if indexFlag != -1:
                    output.storyFlags.append(indexFlag)
                else:
                    break
            
            reader.seek(58)
            for indexPuzzle in range(4):
                indexPuzzle = reader.readS16()      # Internal or external?
                tempState = reader.readS16()
                if indexPuzzle != -1:
                    packedState = None
                    if tempState == 1:
                        packedState = 2
                    elif tempState == 0:
                        packedState = 1

                    if packedState != None:
                        output.puzzleStates.append((indexPuzzle, packedState))
                else:
                    break
            
            reader.seek(74)
            for indexEventCounter in range(4):
                indexEventCounter = reader.readS16()
                valueEventCounter = reader.readU16()
                if indexEventCounter != -1 and 0 <= indexEventCounter < 128:
                    output.eventCounterFlags.append((indexEventCounter, valueEventCounter))
                else:
                    break

            return output
        return DlzEntryNull()
    
    def toBytes(self):
        writer = BinaryWriter()
        writer.writeU16(self.idEvent)
        writer.writeU16(self.type)
        writer.writeU16(self.goal)
        return writer.data

class StorySelectList(DlzData):
    def __init__(self):
        DlzData.__init__(self)
        self._entryLookup = {}
    
    def addEntryFromData(self, data):
        tempEvent = DlzEntryStorySelectList.fromBytes(data)
        if type(tempEvent) == DlzEntryStorySelectList:
            self._entryLookup[tempEvent.idEntry] = self.getCountEntries()
            self.addEntry(tempEvent)
    
    def searchForEntry(self, idEntry):
        if idEntry in self._entryLookup:
            return self._entryLookup[idEntry]
        return None