from ..asset import File
from ..binary import BinaryReader, BinaryWriter
from ..const import ENCODING_DEFAULT_STRING

class BoundingBox():
    def __init__(self, x, y, width, height):
        self.x      = x
        self.y      = y
        self.width  = width
        self.height = height
    
    def isEmpty(self):
        return self.x == 0 and self.y == 0 and self.width == 0 and self.height == 0

class HintCoin():
    def __init__(self):
        self.bounding = BoundingBox(0,0,0,0)
    
    @staticmethod
    def fromBytes(data):
        reader = BinaryReader(data=data)
        output = HintCoin()
        output.bounding = BoundingBox(reader.readUInt(1), reader.readUInt(1), reader.readUInt(1), reader.readUInt(1))
        return output

class Exit():
    def __init__(self):
        self.bounding       = BoundingBox(0,0,0,0)
        self.posTransition  = (0,0)

        self.idImage    = 0
        self.idSound    = 0
        
        self.modeDecoding   = 0
        self.spawnData      = 0
    
    @staticmethod
    def fromBytes(data):
        reader = BinaryReader(data=data)
        output = Exit()
        output.bounding = BoundingBox(reader.readUInt(1), reader.readUInt(1), reader.readUInt(1), reader.readUInt(1))
        output.idImage = reader.readUInt(1)
        output.modeDecoding = reader.readUInt(1)
        reader.seek(1,1)
        output.idSound = reader.readUInt(1)
        output.posTransition = (reader.readUInt(1), reader.readUInt(1))
        output.spawnData = reader.readU16()
        return output

    def canSpawnEvent(self):
        return self.modeDecoding >= 2

    def canTriggerExclamationPopup(self):
        return self.modeDecoding == 3
    
    def canBePressedImmediately(self):
        return (self.modeDecoding | 2) == 3

class TObjEntry():
    def __init__(self):
        self.bounding = BoundingBox(0,0,0,0)
        self.idChar = 0
        self.idTObj = 0
    
    @staticmethod
    def fromBytes(data):
        reader = BinaryReader(data=data)
        output = TObjEntry()
        output.bounding = BoundingBox(reader.readUInt(1), reader.readUInt(1), reader.readUInt(1), reader.readUInt(1))
        output.idChar = reader.readU16()
        output.idTObj = reader.readU32()
        return output

class BgAni():
    def __init__(self):
        self.pos = (0,0)
        self.name = ""
    
    @staticmethod
    def fromBytes(data):
        reader = BinaryReader(data=data)
        output = BgAni()
        output.pos = (reader.readUInt(1), reader.readUInt(1))
        output.name = reader.readPaddedString(30, ENCODING_DEFAULT_STRING)
        return output

class EventEntry():
    def __init__(self):
        self.bounding = (0,0,0,0)
        self.idImage = 0
        self.idEvent = 0
    
    @staticmethod
    def fromBytes(data):
        reader = BinaryReader(data=data)
        output = EventEntry()
        output.bounding = BoundingBox(reader.readUInt(1), reader.readUInt(1), reader.readUInt(1), reader.readUInt(1))
        output.idImage = reader.readU16()
        output.idEvent = reader.readU16()
        return output

class PlaceData(File):
    # Used to access room data, which includes animation positions, room connections and event objects.
    # Only the NDS variant of place data is supported. Android versions follow similar suit, but
    # field lengths are changed to adjust for larger screen resolution.

    def __init__(self):
        File.__init__(self)
        self.indexPlace    = 0
        self.bgMainId       = 0
        self.bgMapId        = 0

        self.posMap         = (0,0)
        self._objEvents      = []
        self._objBgAni       = []
        self._objText        = []
        self._objHints       = []
        self._exits          = []
    
    def getCountObjEvents(self):
        return len(self._objEvents)
    
    def getObjEvent(self, indexObj):
        if 0 <= indexObj < self.getCountObjEvents():
            return self._objEvents[indexObj]
        return None
    
    def getCountObjBgEvent(self):
        return len(self._objBgAni)
    
    def getObjBgEvent(self, indexObj):
        if 0 <= indexObj < self.getCountObjBgEvent():
            return self._objBgAni[indexObj]
        return None
    
    def getCountObjText(self):
        return len(self._objText)
    
    def getObjText(self, indexObj):
        if 0 <= indexObj < self.getCountObjText():
            return self._objText[indexObj]
        return None
    
    def getCountHintCoin(self):
        return len(self._objHints)

    def getObjHintCoin(self, indexObj):
        if 0 <= indexObj < self.getCountHintCoin():
            return self._objHints[indexObj]
        return None
    
    def getCountExits(self):
        return len(self._exits)

    def getExit(self, indexExit):
        if 0 <= indexExit < self.getCountExits():
            return self._exits[indexExit]
        return None

    def load(self, data):
        reader = BinaryReader(data=data)
        placeIndex = reader.readU32()
        reader.seek(24)
        self.posMap = (reader.readUInt(1), reader.readUInt(1))
        self.bgMainId = reader.readUInt(1)
        self.bgMapId = reader.readUInt(1)

        for hintCoinIndex in range(4):
            self._objHints.append(HintCoin.fromBytes(reader.read(4)))
            if self._objHints[-1].bounding.isEmpty():
                self._objHints.pop()
                break

        reader.seek(44)
        for tObjIndex in range(16):
            self._objText.append(TObjEntry.fromBytes(reader.read(10)))
            if self._objText[-1].bounding.isEmpty():
                self._objText.pop()
                break
        
        reader.seek(204)
        for bgIndex in range(12):
            # TODO - Verification is actually on no path for anim
            self._objBgAni.append(BgAni.fromBytes(reader.read(32)))
            if self._objBgAni[-1].pos == (0,0):
                self._objBgAni.pop()
                break
        
        reader.seek(588)
        for eventIndex in range(16):
            self._objEvents.append(EventEntry.fromBytes(reader.read(8)))
            if self._objEvents[-1].bounding.isEmpty():
                self._objEvents.pop()
                break

        reader.seek(716)
        for exitIndex in range(12):
            self._exits.append(Exit.fromBytes(reader.read(12)))
            if self._exits[-1].bounding.isEmpty():
                self._exits.pop()
                break
