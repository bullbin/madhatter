from math import ceil
from io import StringIO

class NamedLogger():

    _logLength : bool = 12

    SHOW_UNIMPORTANT    : bool = False
    SHOW_IMPORTANT      : bool = False
    SHOW_CRITICAL       : bool = True

    @staticmethod
    def _internalLog(*args, name : str = "Unnamed", prefix="U"):
        name = "%s - %s" % (prefix, name)
        if len(name) > (NamedLogger._logLength - 3):
            NamedLogger._logLength = int((ceil((len(name)  + 3) / 4)) * 4)
        
        targetStringLength = NamedLogger._logLength - 3

        buffer = StringIO()
        name = "[" + name + (" " * (targetStringLength - len(name))) + "]"
        print(*args, file=buffer, end='')

        lines = buffer.getvalue().split("\n")
        for indexLine, line in enumerate(lines):
            if indexLine == 0:
                print(name + " " + line)
            else:
                print(((NamedLogger._logLength) * " ") + line)

    @staticmethod
    def logPrint(*args, name : str = "Unnamed"):
        if NamedLogger.SHOW_IMPORTANT:
            NamedLogger._internalLog(*args, name=name, prefix="I")
    
    @staticmethod
    def logVerbose(*args, name : str = "Unnamed"):
        if NamedLogger.SHOW_UNIMPORTANT:
            NamedLogger._internalLog(*args, name=name, prefix="V")
    
    @staticmethod
    def logSevere(*args, name : str = "Unnamed"):
        if NamedLogger.SHOW_CRITICAL:
            NamedLogger._internalLog(*args, name=name, prefix="C")

def log(*args, name : str = "MissImp"):
    NamedLogger.logPrint(*args, name=name)

def logVerbose(*args, name : str = "MissVerb"):
    NamedLogger.logVerbose(*args, name=name)
        
def logSevere(*args, name : str = "MissCrit"):
    NamedLogger.logSevere(*args, name=name)

class Rect():
    def __init__(self,x,y,width,height):
        self.pos = (x,y)
        self.dimensions = (width,height)