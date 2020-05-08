from . import binary
from .asset import File

class Boundary():
    def __init__(self, cornerPos, boundarySize):
        self.posCorner = cornerPos
        self.sizeBounding = boundarySize
    
    def wasClicked(self, pos):
        offset = (pos[0] - self.posCorner[0],
                  pos[1] - self.posCorner[1])
        if (offset[0] > 0 and offset[1] > 0) and (offset[0] <= self.sizeBounding[0] and offset[1] <= self.sizeBounding[1]):
            return True
        return False

class TObj():
    def __init__(self, boundary, charId, tObjId):
        self.bounding = boundary
        self.idChar = charId
        self.idTObj = tObjId

class PlaceEvent():
    def __init__(self, boundary, eventObjId, eventId):
        self.bounding = boundary
        self.idEventObj = eventObjId
        self.idEvent = eventId

class ExitRoom():
    def __init__(self, boundary, imageId, roomIndex, roomSubIndex):
        self.bounding = boundary
        self.imageId = imageId
        self.roomIndex = roomIndex
        self.roomSubIndex = roomSubIndex

class ExitEvent():
    def __init__(self, boundary, imageId, eventId):
        self.bounding = boundary
        self.imageId = imageId
        self.eventId = eventId

class LaytonPlaceData(File):

    def __init__(self):
        File.__init__(self)
        
        self.mapPos = (0,0)
        self.roomId = 0
        self.mapTsId = 0
        self.mapBgId = 0
        self.hints = []
        self.tObj = []
        self.objAnim = []
        self.objEvent = []
        self.objTap = []
        self.exits = []

    def load(self, data):
        reader = binary.BinaryReader(data=data)
        self.roomId = reader.readU32()
        reader.seek(20, 1)
        self.mapPos = (reader.readUInt(1), reader.readUInt(1))
        self.mapBgId = reader.readUInt(1)
        self.mapTsId = reader.readUInt(1)

        for _indexHint in range(4):
            tempHint = Boundary((reader.readUInt(1), reader.readUInt(1)),
                                (reader.readUInt(1), reader.readUInt(1)))
            if tempHint.posCorner != (0,0) and tempHint.sizeBounding != (0,0):
                self.hints.append(tempHint)
        
        for _indexTObj in range(16):
            tempBoundary = Boundary((reader.readUInt(1), reader.readUInt(1)),
                                    (reader.readUInt(1), reader.readUInt(1)))
            tempCharId = reader.readUInt(2)
            tempTObjId = reader.readUInt(4)
            if tempBoundary.posCorner != (0,0) and tempBoundary.sizeBounding != (0,0):
                self.tObj.append(TObj(tempBoundary, tempCharId, tempTObjId))

        for _indexAnim in range(12):
            tempPos = ((reader.readUInt(1), reader.readUInt(1)))
            tempAnimName = reader.readPaddedString(30, encoding='shift-jis')
            if tempPos != (0,0) and tempAnimName != "":
                self.objAnim.append((tempPos, tempAnimName))
        
        for _indexEvent in range(16):
            tempBoundary = Boundary((reader.readUInt(1), reader.readUInt(1)),
                                    (reader.readUInt(1), reader.readUInt(1)))
            tempEventObjId = reader.readUInt(2)
            tempEventId = reader.readUInt(2)
            if tempBoundary.posCorner != (0,0) and tempBoundary.sizeBounding != (0,0):
                self.objEvent.append(PlaceEvent(tempBoundary, tempEventObjId, tempEventId))
        
        for _indexExit in range(12):
            tempBoundary = Boundary((reader.readUInt(1), reader.readUInt(1)),
                                    (reader.readUInt(1), reader.readUInt(1)))
            tempImageId = reader.readUInt(1)
            tempExitType = reader.readUInt(1)
            reader.seek(4, 1)
            if tempBoundary.posCorner != (0,0) and tempBoundary.sizeBounding != (0,0):
                if tempExitType < 2:
                    tempRoomIndex = reader.readUInt(1)
                    tempRoomSubIndex = reader.readUInt(1)
                    self.exits.append(ExitRoom(tempBoundary, tempImageId, tempRoomIndex, tempRoomSubIndex))
                else:
                    tempEventId = reader.readUInt(2)
                    self.exits.append(ExitEvent(tempBoundary, tempImageId, tempEventId))

class LaytonEventData(File):

    def __init__(self):
        File.__init__(self)
        self.mapTsId = 0
        self.mapBsId = 0
        self.characters                         = []
        self.charactersPosition                 = []
        self.charactersShown                    = []
        self.charactersInitialAnimationIndex    = []
    
    def load(self, data):
        reader = binary.BinaryReader(data = data)
        self.mapBsId = reader.readU16()
        self.mapTsId = reader.readU16()

        reader.seek(2,1)

        for _indexChar in range(8):
            tempChar = reader.readUInt(1)
            if tempChar != 0:
                self.characters.append(tempChar)
        for _indexChar in range(8):
            self.charactersPosition.append(reader.readUInt(1))
        for _indexChar in range(8):
            if reader.readUInt(1) == 0:
                self.charactersShown.append(False)
            else:
                self.charactersShown.append(True)
        for _indexChar in range(8):
            self.charactersInitialAnimationIndex.append(reader.readUInt(1))

class LaytonPuzzleData(File):

    OFFSET_TEXT_DEFAULT = 112

    def __init__(self):
        File.__init__(self)
        self.idExternal = None
        self.idInternal = None
        self.idLocation = None
        self.idTutorial = None
        self.idHandler = None
        self.idBackgroundBs = None
        self.idBackgroundTs = None
        self.idReward = None

        self.idCharacterJudgeAnim = None

        self.textName = None
        self.textPrompt = None
        self.textPass = None
        self.textFail = None
        self.textHint = [None,None,None]

        self.flagEnableSubmit = False
        self.flagEnableBack = False
        
        self.decayPicarots = [None,None,None]
        self.unks = [None,None,None,None]
    
    def load(self, data):

        def seekAndReadNullTerminatedString(offset, reader):
            prevOffset = reader.tell()
            reader.seek(offset)
            output = reader.readNullTerminatedString('shift-jis')
            reader.seek(prevOffset)
            return output

        reader = binary.BinaryReader(data = data)

        self.idExternal = reader.readU16()
        offsetText = reader.readU16()
        self.textName = reader.readPaddedString(48, 'shift-jis')
        self.idTutorial = reader.readUInt(1)
        self.decayPicarots = [reader.readUInt(1), reader.readUInt(1), reader.readUInt(1)]

        self.idCharacterJudgeAnim = reader.readUInt(1)
        self.unks[0] = self.idCharacterJudgeAnim & 0xf0
        self.idCharacterJudgeAnim = self.idCharacterJudgeAnim & 0x0f
        
        self.idLocation = reader.readUInt(1)
        self.idHandler = reader.readUInt(1)
        self.idBackgroundBs = reader.readUInt(1) 

        tempFlagByte = reader.readUInt(1)
        self.flagEnableBack = (tempFlagByte & 2 ^ 6) > 0
        self.flagEnableSubmit = (tempFlagByte & 2 ^ 4) > 0

        self.unks[1] = tempFlagByte     # Seems to be handler-related, as handlers often share the same unk here
        self.unks[2] = reader.read(1)   # Seems to be background related, as ranges between 1 and 4
        self.idBackgroundTs = reader.readUInt(1)
        self.idReward = reader.readInt(1)
        self.textPrompt = seekAndReadNullTerminatedString(reader.readU32() + offsetText, reader)
        self.textPass = seekAndReadNullTerminatedString(reader.readU32() + offsetText, reader)
        self.textFail = seekAndReadNullTerminatedString(reader.readU32() + offsetText, reader)
        for indexHint in range(3):
            self.textHint[indexHint] = seekAndReadNullTerminatedString(reader.readU32() + offsetText, reader)

    def save(self):
        # TODO - Checks for none

        writer = binary.BinaryWriter()
        writer.writeU16(self.idExternal)
        writer.writeU16(LaytonPuzzleData.OFFSET_TEXT_DEFAULT)
        writer.writePaddedString(self.textName, 48, 'shift-jis')
        writer.writeInt(self.idTutorial, 1)
        writer.writeIntList(self.decayPicarots, 1)
        
        # unk0
        writer.writeInt(self.idCharacterJudgeAnim, 1)  # Missing unk at 0xf0

        writer.writeInt(self.idLocation, 1)
        writer.writeInt(self.idHandler, 1)
        writer.writeInt(self.idBackgroundBs, 1)

        tempFlagByte = 0                # Unk: Suspicion
        if self.flagEnableSubmit:
            tempFlagByte += 2 ** 4
        
        writer.writeInt(tempFlagByte, 1) # Unk: handler

        writer.writeInt(1, 1)  # Unk: BG

        writer.writeInt(self.idBackgroundTs, 1)
        writer.writeInt(self.idReward, 1, signed=True)   # TODO - Abstraction

        textPointerOffset = writer.tell()
        textBankOffset = LaytonPuzzleData.OFFSET_TEXT_DEFAULT
        writer.align(textBankOffset)
        
        for indexText, text in enumerate([self.textPrompt, self.textPass, self.textFail, self.textHint[0], self.textHint[1], self.textHint[2]]):
            writer.insert((textBankOffset - LaytonPuzzleData.OFFSET_TEXT_DEFAULT).to_bytes(4, byteorder = 'little'), textPointerOffset + (indexText * 4))
            tempText = text.encode('shift-jis') + b'\x00'
            writer.write(tempText)
            textBankOffset += len(tempText)
        
        self.data = writer.data