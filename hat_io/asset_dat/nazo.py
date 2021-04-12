from ..asset import File
from ..binary import BinaryReader

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

    def load(self, data):

        reader = BinaryReader(data=data)

        def seekAndReadNullTerminatedString(offset):
            prevOffset = reader.tell()
            reader.seek(offset)
            output = reader.readNullTerminatedString('shift-jis')
            reader.seek(prevOffset)
            return output

        self.idExternal = reader.readU16()
        lengthHeader = reader.readU16()
        self.textName = reader.readPaddedString(48, 'shift-jis')
        self.idTutorial = reader.readUInt(1)
        self.picaratDecayStages = [reader.readUInt(1), reader.readUInt(1), reader.readUInt(1)]
        
        flags = reader.readUInt(1)
        self.__flagUseLukeAsSolver              = flags & 0x01 == 0
        self.__flagUseLukeVoiceLines            = flags & 0x02 != 0
        self.__flagPuzzleHasAnswerBackground    = flags & 0x10 != 0
        self.__flagUseLanguagePromptBackground  = flags & 0x20 != 0
        self.__flagUseLanguageAnswerBackground  = flags & 0x40 != 0

        self.indexPlace = reader.readUInt(1)
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