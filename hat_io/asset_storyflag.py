from typing import List, Optional
from .asset import File
from .binary import BinaryReader, BinaryWriter

# Used to update current chapter by checking if puzzle was solved or flag was set

class Flag():
    def __init__(self, type = 0, param = 0):
        if type == 1 or type == 2:
            self.type = type
            self.param = param
        else:
            self.type = 0
            self.param = 0

class FlagGroup():

    COUNT_FLAGS_PER_GROUP = 8

    def __init__(self, chapter=0):
        self.chapter = chapter
        self.flags = []
        for _nullFlag in range(FlagGroup.COUNT_FLAGS_PER_GROUP):
            self.flags.append(Flag())
    
    def setChapter(self, chapter):
        self.chapter = chapter

    def getChapter(self) -> int:
        return self.chapter

    def setFlag(self, index, flag) -> bool:
        if 0 <= index < FlagGroup.COUNT_FLAGS_PER_GROUP:
            self.flags[index] = flag
            return True
        return False
    
    def getFlag(self, index) -> Optional[Flag]:
        if 0 <= index < FlagGroup.COUNT_FLAGS_PER_GROUP:
            return self.flags[index]
        return None

class StoryFlag(File):

    COUNT_FLAGS = 256

    def __init__(self):
        File.__init__(self)
        self.flagGroups : List[FlagGroup] = []
        for _nullGroup in range(StoryFlag.COUNT_FLAGS):
            self.flagGroups.append(FlagGroup())

    def load(self, data):
        reader = BinaryReader(data=data)

        for indexFlagGroup in range(StoryFlag.COUNT_FLAGS):
            self.flagGroups[indexFlagGroup].setChapter(reader.readU16())
            for subIndex in range(FlagGroup.COUNT_FLAGS_PER_GROUP):
                typeFlag = reader.readUInt(1)
                reader.seek(1,1)
                param = reader.readU16()
                self.flagGroups[indexFlagGroup].setFlag(subIndex, Flag(type=typeFlag, param=param))
    
    def save(self):
        writer = BinaryWriter()
        for flagGroup in self.flagGroups:
            writer.writeU16(flagGroup.getChapter())
            for subIndex in range(FlagGroup.COUNT_FLAGS_PER_GROUP):
                flag = flagGroup.getFlag(subIndex)
                writer.writeInt(flag.type, 1)
                writer.pad(1)
                writer.writeU16(flag.param)
    
    def getIndexFromChapter(self, chapter : int) -> Optional[int]:
        """Returns the index for the flag group corresponding to this chapter.

        Args:
            chapter (int): Chapter value.

        Returns:
            Optional[int]: Index of flag group. None if no group is found.
        """
        for indexFlagGroup, flagGroup in enumerate(self.flagGroups):
            if flagGroup.getChapter() == chapter:
                return indexFlagGroup
        return None
    
    def getGroupAtIndex(self, index : int) -> Optional[FlagGroup]:
        """Returns the flag group stored at the given index.

        Args:
            index (int): Flag group index.

        Returns:
            Optional[FlagGroup]: Flag group. None if index out of bounds.
        """
        if 0 <= index < StoryFlag.COUNT_FLAGS:
            return self.flagGroups[index]
        return None