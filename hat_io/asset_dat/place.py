from typing import Optional
from ..asset import File
from ..binary import BinaryReader, BinaryWriter
from ..const import ENCODING_DEFAULT_STRING

class BoundingBox():
    def __init__(self, x, y, width, height):
        # TODO - Maybe support setting limits to prevent user from tampering out of bounds for writing
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
    
    def toBytes(self, isHd : bool = False) -> bytes:
        writer = BinaryWriter()
        if isHd:
            writer.writeIntList([self.bounding.x, self.bounding.y, self.bounding.width, self.bounding.height], 2)
        else:
            writer.writeIntList([self.bounding.x, self.bounding.y, self.bounding.width, self.bounding.height], 1)
        return writer.data

class Exit():
    def __init__(self):
        self.bounding       = BoundingBox(0,0,0,0)
        self.posTransition  = (0,0)

        self.idImage    = 0
        self.idSound    = 0
        
        # TODO - Abstract!
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

    def toBytes(self, isHd : bool = False) -> bytes:
        if isHd:
            sizePosition = 2
        else:
            sizePosition = 1

        writer = BinaryWriter()
        writer.writeIntList([self.bounding.x, self.bounding.y, self.bounding.width, self.bounding.height], sizePosition)
        writer.writeInt(self.idImage, 1)
        writer.writeInt(self.modeDecoding,1)
        writer.pad(1)
        writer.writeInt(self.idSound, 1)
        writer.writeInt(self.posTransition[0], sizePosition)
        writer.writeInt(self.posTransition[1], sizePosition)
        writer.writeU16(self.spawnData)
        return writer.data

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
    
    def toBytes(self, isHd : bool = False) -> bytes:
        writer = BinaryWriter()
        if isHd:
            writer.writeIntList([self.bounding.x, self.bounding.y, self.bounding.width, self.bounding.height], 2)
        else:
            writer.writeIntList([self.bounding.x, self.bounding.y, self.bounding.width, self.bounding.height], 1)
        writer.writeU16(self.idChar)
        writer.writeU32(self.idTObj)
        return writer.data

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
            sizePosition = 2
        else:
            sizePosition = 1

        reader = BinaryReader(data=data)
        output = BgAni()
        output.pos = (reader.readUInt(sizePosition), reader.readUInt(sizePosition))
        output.name = reader.readPaddedString(30, ENCODING_DEFAULT_STRING)
        return output

    def toBytes(self, isHd : bool = False) -> bytes:
        writer = BinaryWriter()
        if isHd:
            sizePosition = 2
        else:
            sizePosition = 1
        writer.writeInt(self.pos[0], sizePosition)
        writer.writeInt(self.pos[1], sizePosition)
        writer.writePaddedString(self.name, 30, ENCODING_DEFAULT_STRING)
        return writer.data

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

    def toBytes(self, isHd : bool = False) -> bytes:
        if isHd:
            sizePosition = 2
        else:
            sizePosition = 1
        writer = BinaryWriter()

        writer.writeIntList([self.bounding.x, self.bounding.y, self.bounding.width, self.bounding.height], sizePosition)
        writer.writeU16(self.idImage)
        writer.writeU16(self.idEvent)
        return writer.data

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

        # TODO - Research music more, this is referenced against snd_fix to get the BG music ID
        self.idSound : int   = 0
    
    def getCountObjEvents(self) -> int:
        return len(self._objEvents)
    
    def getObjEvent(self, indexObj : int) -> Optional[EventEntry]:
        if 0 <= indexObj < self.getCountObjEvents():
            return self._objEvents[indexObj]
        return None
    
    def getCountObjBgEvent(self) -> int:
        return len(self._objBgAni)
    
    def getObjBgEvent(self, indexObj : int) -> Optional[BgAni]:
        if 0 <= indexObj < self.getCountObjBgEvent():
            return self._objBgAni[indexObj]
        return None
    
    def getCountObjText(self) -> int:
        return len(self._objText)
    
    def getObjText(self, indexObj : int) -> Optional[TObjEntry]:
        if 0 <= indexObj < self.getCountObjText():
            return self._objText[indexObj]
        return None
    
    def getCountHintCoin(self) -> int:
        return len(self._objHints)

    def getObjHintCoin(self, indexObj : int) -> Optional[HintCoin]:
        if 0 <= indexObj < self.getCountHintCoin():
            return self._objHints[indexObj]
        return None
    
    def getCountExits(self) -> int:
        return len(self._exits)

    def getExit(self, indexExit : int) -> Optional[Exit]:
        if 0 <= indexExit < self.getCountExits():
            return self._exits[indexExit]
        return None

    def _load(self, data : bytes, isHd : bool = False):
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
        
        # TODO - HD pad
        reader.seek(48, 1)
        # TODO - Is this signed?
        if isHd:
            self.idSound = reader.readU32()
        else:
            self.idSound = reader.readU16()
        
        self.data = data

    def _loadHd(self, data : bytes):
        self._load(data, True)
    
    def _loadNds(self, data : bytes):
        self._load(data, False)
    
    def _save(self, isHd : bool = False):
        writer = BinaryWriter()
        writer.writeInt(self.idNamePlace, 1)
        writer.pad(23)
        if isHd:
            writer.writeU16(self.posMap[0])
            writer.writeU16(self.posMap[1])
        else:
            writer.writeInt(self.posMap[0], 1)
            writer.writeInt(self.posMap[1], 1)
        
        writer.writeInt(self.bgMainId, 1)
        writer.writeInt(self.bgMapId, 1)

        for indexHintCoin in range(4):
            if (objHintCoin := self.getObjHintCoin(indexHintCoin)) != None:
                writer.write(objHintCoin.toBytes(isHd))
            else:
                writer.pad(HintCoin.getLength(isHd))
            
        for indexTObj in range(16):
            if (objText := self.getObjText(indexTObj)) != None:
                writer.write(objText.toBytes(isHd))
            else:
                writer.pad(TObjEntry.getLength(isHd))
        
        for indexBgAni in range(12):
            if (objBgAni := self.getObjBgEvent(indexBgAni)) != None:
                writer.write(objBgAni.toBytes(isHd))
            else:
                writer.pad(BgAni.getLength(isHd))
        
        for indexEvent in range(16):
            if (objEvent := self.getObjEvent(indexEvent)) != None:
                writer.write(objEvent.toBytes(isHd))
            else:
                writer.pad(EventEntry.getLength(isHd))

        for indexExit in range(12):
            if (objExit := self.getExit(indexExit)) != None:
                writer.write(objExit.toBytes(isHd))
            else:
                writer.pad(Exit.getLength(isHd))
        
        # Game reads into itself
        # TODO - HD pad
        writer.pad(48)

        if isHd:
            writer.writeU32(self.idSound)
        else:
            writer.writeU16(self.idSound)
        self.data = writer.data

    def _saveHd(self):
        self._save(True)

    def _saveNds(self):
        self._save(False)
    
class PlaceDataNds(PlaceData):
    def __init__(self):
        super().__init__()

    def load(self, data : bytes):
        self._loadNds(data)
    
    def save(self):
        self._saveNds()

class PlaceDataHd(PlaceData):
    def __init__(self):
        super().__init__()
    
    def load(self, data : bytes):
        self._loadHd(data)
    
    def save(self):
        self._saveHd()