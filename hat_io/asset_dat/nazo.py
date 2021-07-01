from typing import List, Tuple
from .const import NAZO_MAX_STRING_BANK_LENGTH_HD, NAZO_MAX_STRING_BANK_LENGTH_NDS, NAZO_SIZE_HD
from ..asset import File
from ..binary import BinaryReader, BinaryWriter

class NazoData(File):
    def __init__(self):
        # TODO - Make init consistent
        super().__init__()
        self.idExternal = None
        self.idTutorial = None
        self.idHandler = None
        self.idReward = -1

        self.picaratDecayStages = [0,0,0]
        
        self.__flagUseLukeAsSolver              = False
        self.__flagUseLukeVoiceLines            = False
        self.__flagPuzzleHasAnswerBackground    = False
        self.__flagUseLanguagePromptBackground  = False
        self.__flagUseLanguageAnswerBackground  = False

        self.indexPlace = None
        
        self.bgMainId = None
        self.bgSubId = None
        
        self.textName = ""
        self.textHint = ["","",""]
        self.textPrompt = ""
        self.textCorrect = ""
        self.textIncorrect = ""

    def _load(self, data : bytes, isHd : bool) -> bool:
        """Load Nazo data block. Abstractions are recommended instead of direct interaction with object.

        Args:
            data (bytes): Bytes-like object containing Nazo data
            isHd (bool): True if file type is from HD ports

        Returns:
            bool: True if loading was successful
        """

        reader = BinaryReader(data=data)

        def seekAndReadNullTerminatedString(offset):
            prevOffset = reader.tell()
            reader.seek(offset)
            output = reader.readNullTerminatedString('shift-jis')
            reader.seek(prevOffset)
            return output

        self.idExternal = reader.readU16()

        if isHd:
            lengthHeader = 112
            reader.seek(2,1)
            self.textName = reader.readPaddedString(72, 'shift-jis')
        else:
            lengthHeader = reader.readU16()
            self.textName = reader.readPaddedString(48, 'shift-jis')

        # TODO - Make enum for tutorial and abstract to ensure validity
        # TODO - Abstract picarat to ensure cannot be out of bounds
        self.idTutorial = reader.readUInt(1)
        self.picaratDecayStages = [reader.readUInt(1), reader.readUInt(1), reader.readUInt(1)]
        
        flags = reader.readUInt(1)
        self.__flagUseLukeAsSolver              = flags & 0x01 == 0
        self.__flagUseLukeVoiceLines            = flags & 0x02 != 0
        self.__flagPuzzleHasAnswerBackground    = flags & 0x10 != 0
        self.__flagUseLanguagePromptBackground  = flags & 0x20 != 0
        self.__flagUseLanguageAnswerBackground  = flags & 0x40 != 0

        self.indexPlace = reader.readUInt(1)
        # TODO - Another enum for handler
        self.idHandler = reader.readUInt(1)
        self.bgMainId = reader.readUInt(1)

        reader.seek(2,1)    # Skip sound mode

        self.bgSubId = reader.readUInt(1)
        self.idReward = reader.readInt(1)

        self.textPrompt = seekAndReadNullTerminatedString(lengthHeader + reader.readU32())
        self.textCorrect = seekAndReadNullTerminatedString(lengthHeader + reader.readU32())
        self.textIncorrect = seekAndReadNullTerminatedString(lengthHeader + reader.readU32())
        for indexHint in range(3):
            self.setHintAtIndex(indexHint, seekAndReadNullTerminatedString(lengthHeader + reader.readU32()))
        
        return True

    def _saveFlags(self, writer : BinaryWriter):
        writer.writeInt(self.idTutorial, 1)
        writer.writeIntList(self.picaratDecayStages, 1)
        flagBit = (self.__flagUseLukeAsSolver | (self.__flagUseLukeVoiceLines << 1)) | (self.__flagPuzzleHasAnswerBackground << 4)
        flagBit = (flagBit | (self.__flagUseLanguagePromptBackground << 5)) | (self.__flagUseLanguagePromptBackground << 6)
        writer.writeInt(flagBit, 1)
        writer.writeInt(self.indexPlace, 1)
        writer.writeInt(self.idHandler, 1)
        writer.writeInt(self.bgMainId, 1)
        
        writer.pad(2)

        writer.writeInt(self.bgSubId, 1)
        writer.writeInt(self.idReward, 1)

    def _saveStrings(self, maxLength : int) -> Tuple[BinaryWriter, List[int]]:
        """Generates the string bank for Nazo data. If a string is too long to fit in the remaining space in the bank,
        it is skipped. If that is not possible, the results of the previous string is referenced instead.

        Args:
            maxLength (int): Maximum size of string partition

        Returns:
            Tuple[BinaryWriter, List[int]]: Writer containing data block and list of relative offsets for use in header
        """
        output = BinaryWriter()
        stringWriter = BinaryWriter()

        outputOffset = []
        for text in [self.textPrompt, self.textCorrect, self.textIncorrect] + self.textHint:
            stringWriter.clear()
            stringWriter.writeString(text, 'shift-jis')
            if output.tell() + stringWriter.tell() <= maxLength:
                outputOffset.append(output.tell())
                output.write(stringWriter.data)
            else:
                if maxLength - output.tell() >= 1:
                    outputOffset.append(output.tell())
                    output.write(b'\x00')
                else:
                    # This is safe because its not possible for it to fail on first time - above fallback will kick in
                    outputOffset.append(outputOffset[-1])
        
        return (output, outputOffset)

    def _saveNds(self):
        writer : BinaryWriter = BinaryWriter()
        writer.writeU16(self.idExternal)
        writer.writeU16(112)
        writer.writePaddedString(self.name, 48, 'shift-jis')
        self._saveFlags(writer)
        bankWriter, bankOffsets = self._saveStrings(NAZO_MAX_STRING_BANK_LENGTH_NDS)
        writer.writeIntList(bankOffsets, 4)
        writer.align(112)
        writer.write(bankWriter.data)

    def _saveHd(self):
        writer : BinaryWriter = BinaryWriter()
        writer.writeU16(self.idExternal)
        writer.pad(2)
        writer.writePaddedString(self.name, 72, 'shift-jis')
        self._saveFlags(writer)
        bankWriter, bankOffsets = self._saveStrings(NAZO_MAX_STRING_BANK_LENGTH_HD)
        writer.writeIntList(bankOffsets, 4)
        writer.align(112)
        writer.write(bankWriter.data)
        writer.align(NAZO_SIZE_HD)

    def setHintAtIndex(self, indexHint, text):
        if 0 <= indexHint < len(self.textHint) and type(text) == str:
            self.textHint[indexHint] = text
            return True
        return False

    def setPrompt(self, text):
        pass

    def setCorrectPrompt(self, text):
        pass

    def setIncorrectPrompt(self, text):
        pass
    
    def getTextName(self):
        return self.textName

    def getTextPrompt(self):
        return self.textPrompt
    
    def getTextCorrect(self):
        return self.textCorrect
    
    def getTextIncorrect(self):
        return self.textIncorrect
    
    def getTextHints(self):
        return (self.textHint[0], self.textHint[1], self.textHint[2])
    
    def getPicaratStage(self, index):
        if 0 <= index < 3:
            return self.picaratDecayStages[index]
        return None

    def isBgPromptLanguageDependent(self):
        return self.__flagUseLanguagePromptBackground
    
    def isBgAnswerLanguageDependent(self):
        return self.__flagUseLanguageAnswerBackground
    
    def hasAnswerBg(self):
        return self.__flagPuzzleHasAnswerBackground
    
    def isAltCharacterUsed(self):
        return self.__flagUseLukeAsSolver
    
    def getBgMainIndex(self):
        return self.bgMainId

    def getBgSubIndex(self):
        return self.bgSubId

class NazoDataNds(NazoData):
    # TODO - Format conversions
    def  __init__(self):
        super().__init__()

    def load(self, data: bytes) -> bool:
        return super()._load(data, False)
    
    def save(self):
        """Overwrites stored byte representation with current NDS state. If string size is too long, it will be skipped.
        """
        self._saveNds()

class NazoDataHd(NazoData):
    def  __init__(self):
        super().__init__()

    def load(self, data: bytes) -> bool:
        return super()._load(data, True)
    
    def save(self):
        """Overwrites stored byte representation with current HD state. If string size is too long, it will be skipped.
        """
        self._saveHd()