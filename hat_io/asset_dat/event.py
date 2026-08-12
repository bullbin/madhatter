from typing import List
from ..asset import File
from ..binary import BinaryReader, BinaryWriter

# TODO - Getters and setters and output, plus replace the implementation in the room handler

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
        self.envId = 0  # TODO - check null value
        self.behaviourSound = 0

    def load(self, data):
        reader = BinaryReader(data = data)
        self.mapBsId = reader.readU16()
        self.mapTsId = reader.readU16()
        self.behaviour = reader.readUInt(1)
        self.behaviourSound = reader.readUInt(1)

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
        self.envId = reader.readS16()
            
        self.data = data

    def save(self):
        writer = BinaryWriter()

        def padListToEight(inList : List[int]):
            for x in range(8):
                if x < len(inList):
                    writer.writeInt(inList[x], 1, signed=False)
                else:
                    writer.writeInt(0, 1)

        writer.writeU16(self.mapBsId)
        writer.writeU16(self.mapTsId)
        writer.writeInt(self.behaviour, 1, signed=False)
        writer.writeInt(self.behaviourSound, 1, signed=False)
        
        padListToEight(self.characters)
        padListToEight(self.charactersPosition)
        padListToEight(self.charactersShown)
        padListToEight(self.charactersInitialAnimationIndex)

        # This isn't actually read in-game
        writer.writeS16(self.envId)
        self.data = writer.data