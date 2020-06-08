from .common import PuzzleHandler
from ...stringsLt2 import OPCODES_LT2

def HandlerWriteAnswer(PuzzleHandler):
    def __init__(self):
        PuzzleHandler.__init__(self)

        self.bgDrawInputBottomScreen = None
        
        self.lengthSolution = 0
        self.solutions = []
    
    def parseCommandLt2(self, command):
        if command.opcode == OPCODES_LT2.SetDrawInputBG.value:
            self.solutions.append(command.operands[1].value)

    def getScriptLt2(self):
        pass
    
    def getScriptLt1(self):
        pass