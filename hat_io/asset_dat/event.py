from madhatter.hat_io.asset import File
from madhatter.hat_io.binary import BinaryReader

class EventData(File):

    def __init__(self):
        File.__init__(self)
        self.mapTsId = 0
        self.mapBsId = 0
        self.behaviour = 0
        self.characters                         = []
        self.charactersPosition                 = []
        self.charactersShown                    = []
        self.charactersInitialAnimationIndex    = []
    
    def load(self, data):
        reader = BinaryReader(data = data)
        self.mapBsId = reader.readU16()
        self.mapTsId = reader.readU16()
        self.behaviour = reader.readUInt(1)

        reader.seek(6)
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
