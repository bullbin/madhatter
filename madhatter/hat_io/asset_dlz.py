import math
from PIL import Image
from os import path

from . import binary
from .asset import File

class EntryUnknown():
    def __init__(self, data=None):
        if data == None:
            self.isValidEntry = False
        else:
            self.isValidEntry = True

        self.data = data

class EntryGoalPointer(EntryUnknown):
    def __init__(self, data=None):
        EntryUnknown.__init__(self, data=data)

        if data != None:
            self.idEvent = int.from_bytes(data[:2], byteorder = 'little')
            self.triggerType = int.from_bytes(data[2:4], byteorder = 'little')
            self.idGoal = int.from_bytes(data[4:], byteorder = 'little')
        else:
            self.idEvent = 0
            self.triggerType = 0
            self.idGoal = 0

class LaytonDlz(File):

    DATA_MAP = {"goal_inf":EntryGoalPointer}

    def __init__(self):
        File.__init__(self)
        self.entries = []
    
    def load(self, data, entryObject=EntryUnknown):
        if data != None:
            reader = binary.BinaryReader(data=data)
            countEntry = reader.readU16()
            reader.seek(2,1)    # Always 8
            sizeEntry = reader.readU32()
            try:
                for _indexEntry in range(countEntry):
                    self.entries.append(entryObject(data=reader.read(sizeEntry)))
            except IndexError:
                pass

    def loadWithName(self, data, name):
        name = name.split(".")[0]
        if name in LaytonDlz.DATA_MAP:
            self.load(data, entryObject=LaytonDlz.DATA_MAP[name])
        else:
            self.load(data)

    def save(self):
        pass