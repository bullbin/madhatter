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
    def getLength(isHd : bool):
        if isHd:
            return 8
        else:
            return 4
    
    @staticmethod
    def fromBytes(data, isHd : bool = False):
        reader = BinaryReader(data=data)
        output = HintCoin()
        if isHd:
            output.bounding = BoundingBox(reader.readUInt(2), reader.readUInt(2), reader.readUInt(2), reader.readUInt(2))
        else:
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
    def getLength(isHd : bool):
        if isHd:
            return 18
        else:
            return 12
    
    @staticmethod
    def fromBytes(data, isHd : bool = False):
        # TODO - Separate NDS and HD into own items from this so scaling behaviour can be handled.
        if isHd:
            sizePosition = 2
        else:
            sizePosition = 1

        reader = BinaryReader(data=data)
        output = Exit()
        output.bounding = BoundingBox(reader.readUInt(sizePosition), reader.readUInt(sizePosition), reader.readUInt(sizePosition), reader.readUInt(sizePosition))
        output.idImage = reader.readUInt(1)
        output.modeDecoding = reader.readUInt(1)
        reader.seek(1,1)
        output.idSound = reader.readUInt(1)
        output.posTransition = (reader.readUInt(sizePosition), reader.readUInt(sizePosition))
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
    def getLength(isHd : bool):
        if isHd:
            return 14
        else:
            return 10
    
    @staticmethod
    def fromBytes(data, isHd : bool = False):
        if isHd:
            sizePosition = 2
        else:
            sizePosition = 1

        reader = BinaryReader(data=data)
        output = TObjEntry()
        output.bounding = BoundingBox(reader.readUInt(sizePosition), reader.readUInt(sizePosition), reader.readUInt(sizePosition), reader.readUInt(sizePosition))
        output.idChar = reader.readU16()
        output.idTObj = reader.readU32()
        return output

class BgAni():
    def __init__(self):
        self.pos = (0,0)
        self.name = ""
    
    @staticmethod
    def getLength(isHd : bool):
        if isHd:
            return 34
        else:
            return 32

    @staticmethod
    def fromBytes(data, isHd : bool = False):
        if isHd:
            sizePosition = 34
        else:
            sizePosition = 32

        reader = BinaryReader(data=data)
        output = BgAni()
        output.pos = (reader.readUInt(sizePosition), reader.readUInt(sizePosition))
        output.name = reader.readPaddedString(30, ENCODING_DEFAULT_STRING)
        return output

class EventEntry():
    def __init__(self):
        self.bounding = BoundingBox(0,0,0,0)
        self.idImage = 0
        self.idEvent = 0
    
    @staticmethod
    def getLength(isHd : bool):
        if isHd:
            return 12
        else:
            return 8

    @staticmethod
    def fromBytes(data, isHd : bool = False):
        if isHd:
            sizePosition = 2
        else:
            sizePosition = 1

        reader = BinaryReader(data=data)
        output = EventEntry()
        output.bounding = BoundingBox(reader.readUInt(sizePosition), reader.readUInt(sizePosition), reader.readUInt(sizePosition), reader.readUInt(sizePosition))
        output.idImage = reader.readU16()
        output.idEvent = reader.readU16()
        return output

class PlaceData(File):
    # Used to access room data, which includes animation positions, room connections and event objects.
    
    # TODO - Test HD version. NDS and HD should now both be supported

    def __init__(self):
        File.__init__(self)
        self.idNamePlace    = 0
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
    
    def _load(self, data, isHd : bool = False):
        reader = BinaryReader(data=data)
        self.idNamePlace = reader.readUInt(1)
        reader.seek(24)
        if isHd:
            self.posMap = (reader.readUInt(2), reader.readUInt(2))
        else:
            self.posMap = (reader.readUInt(1), reader.readUInt(1))

        self.bgMainId = reader.readUInt(1)
        self.bgMapId = reader.readUInt(1)

        for hintCoinIndex in range(4):
            self._objHints.append(HintCoin.fromBytes(reader.read(HintCoin.getLength(isHd)), isHd))
            if self._objHints[-1].bounding.isEmpty():
                self._objHints.pop()
                reader.seek(reader.tell() + (HintCoin.getLength(isHd) * (3 - hintCoinIndex)))
                break

        for tObjIndex in range(16):
            self._objText.append(TObjEntry.fromBytes(reader.read(TObjEntry.getLength(isHd)), isHd))
            if self._objText[-1].bounding.isEmpty():
                self._objText.pop()
                reader.seek(reader.tell() + (TObjEntry.getLength(isHd) * (15 - tObjIndex)))
                break
        
        for bgIndex in range(12):
            # TODO - Verification is actually on no path for anim
            self._objBgAni.append(BgAni.fromBytes(reader.read(BgAni.getLength(isHd)), isHd))
            if self._objBgAni[-1].pos == (0,0):
                self._objBgAni.pop()
                reader.seek(reader.tell() + (BgAni.getLength(isHd) * (11 - bgIndex)))
                break
        
        for eventIndex in range(16):
            self._objEvents.append(EventEntry.fromBytes(reader.read(EventEntry.getLength(isHd)), isHd))
            if self._objEvents[-1].bounding.isEmpty():
                self._objEvents.pop()
                reader.seek(reader.tell() + (EventEntry.getLength(isHd) * (15 - eventIndex)))
                break

        for exitIndex in range(12):
            self._exits.append(Exit.fromBytes(reader.read(Exit.getLength(isHd)), isHd))
            if self._exits[-1].bounding.isEmpty():
                self._exits.pop()
                reader.seek(reader.tell() + (Exit.getLength(isHd) * (11 - exitIndex)))
                break

    def _loadHd(self, data):
        self._load(data, True)
    
    def _loadNds(self, data):
        self._load(data, False)

class PlaceDataNds(PlaceData):
    def __init__(self):
        super().__init__()

    def load(self, data):
        self._loadNds(data)

class PlaceDataHd(PlaceData):
    def __init__(self):
        super().__init__()
    
    def load(self, data):
        self._loadHd(data)