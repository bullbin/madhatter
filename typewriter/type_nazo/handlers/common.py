from .const import SOLVED_BY_LAYTON, SOLVED_BY_LUKE
from ....hat_io.asset_script import GdScript, Instruction, Operand
from ...stringsLt1 import OPCODES_LT1
from ...stringsLt2 import OPCODES_LT2
from ....hat_io.const import TYPE_OPERANDS

class PuzzleHandler():

    LAYTON_1_COMMAND_STRING = ""

    def __init__(self):
        self.usesCustomTopScreenBg      = False
        self.usesCustomBottomScreenBg   = False

        self.bgTopScreen    = None
        self.bgBottomScreen = None
        self.bgEndScreen    = None

        self.textTitle      = ""
        self.textPrompt     = ""
        self.textHint       = ["","",""]
        self.textPass       = ""
        self.textFail       = ""

        self.idSolvedBy     = SOLVED_BY_LAYTON

        self.picaratsDecay  = [0,0,0]
    
    # TODO - Sort out returns

    def parseUnifiedCommand(self, command, referenceOpcode):
        pass

    def parseCommandLt1(self, command):
        if command.opcode == OPCODES_LT1.PuzzleSolverLayton:
            self.idSolvedBy = SOLVED_BY_LAYTON
        elif command.opcode == OPCODES_LT1.PuzzleSolverLuke:
            self.idSolvedBy = SOLVED_BY_LUKE
        else:
            return False

    def parseCommandLt2(self, command):
        pass

    def parseCommandLt3(self, command):
        pass

    def loadScriptLt1(self, script):
        pass

    def loadScriptLt2(self, script):
        pass

    def loadScriptLt3(self, script):
        pass

    def extendUnifiedScript(self, script, referenceOpcode):
        pass

    def getScriptLt1(self):
        output = GdScript()

        namePuzzle          = Operand(TYPE_OPERANDS.STRING.value, self.LAYTON_1_COMMAND_STRING)
        nameCommand         = Instruction()
        nameCommand.opcode  = OPCODES_LT1.CreateQuestion.value
        nameCommand.operands.append(namePuzzle)

        hintCount           = Operand(TYPE_OPERANDS.INT_SIGNED.value, len(self.textHint))
        hintCommand         = Instruction()
        hintCommand.opcode  = OPCODES_LT1.AddHints.value
        hintCommand.operands.append(hintCount)

        solveCommand = Instruction()
        if self.idSolvedBy == SOLVED_BY_LUKE:
            solveCommand.opcode = OPCODES_LT1.PuzzleSolverLuke.value
        else:
            solveCommand.opcode = OPCODES_LT1.PuzzleSolverLayton.value

        output.commands.append(nameCommand)
        output.commands.append(hintCommand)
        output.commands.append(solveCommand)

        # TODO - Write SetQuestionEndBg, LoadBg

        return output

    def getScriptLt2(self):
        return None

    def getScriptLt3(self):
        return None
    
    def populateFromDataLt2(self, data):
        pass

    def getDataLt2(self, data):
        pass