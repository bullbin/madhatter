from .common import PuzzleHandler
from ....hat_io.asset_script import GdScript, Instruction, Operand
from ....hat_io.const import TYPE_OPERANDS
from ...stringsLt1 import OPCODES_LT1
from ...stringsLt2 import OPCODES_LT2
from ....hat_io.const import DICT_BOOLEAN_TO_PYTHON, DICT_PYTHON_TO_BOOLEAN

# TODO - Set up infrastructure for screen dimensions, including for HD versions

class TracePoint():
    def __init__(self, pos, radius, isAnswer):
        self.pos = pos
        self.radius = radius
        self.isAnswer = isAnswer
    
    @property
    def pos(self):
        return self.__pos
    
    @pos.setter
    def pos(self, pos):
        x, y = pos
        if not(0 <= x < 256):
            x = 0
        if not(0 <= y < 192):
            y = 0
        self.__pos = (x, y)

    @property
    def radius(self):
        return self.__radius

    @radius.setter
    def radius(self, radius):
        if radius > 0:
            self.radius = radius
        self.radius = 1

    @property
    def isAnswer(self):
        return self.__isAnswer
    
    @isAnswer.setter
    def isAnswer(self, isAnswer):
        if isAnswer == True:
            self.__isAnswer = True
        else:
            self.__isAnswer = False

class HandlerTraceButton(PuzzleHandler):

    LAYTON_1_COMMAND_STRING = "Trace Button"

    def __init__(self):
        PuzzleHandler.__init__(self)
        self.locationsTrace = []

        # TODO - Switch colour implementation for something safer, RGB888
        self.colourAnswer = (0,0,0)
    
    def parseUnifiedCommand(self, command, referenceOpcode):
        if command.opcode == referenceOpcode.AddTracePoint.value:
            tempPoint = TracePoint((command.operands[0].value, command.operands[1].value),
                                    command.operands[2].value,
                                    DICT_BOOLEAN_TO_PYTHON[command.operands[3].value])
            self.locationsTrace.append(tempPoint)
        elif command.opcode == referenceOpcode.SetFontUserColor.value:
            self.colourAnswer = (command.operands[0].value,
                                 command.operands[1].value,
                                 command.operands[2].value)
        else:
            return False
        return True
    
    def parseCommandLt1(self, command):
        if not(self.parseUnifiedCommand(command, OPCODES_LT1)):
            return super().parseCommandLt1(command)
        return True
    
    def parseCommandLt2(self, command):
        if not(self.parseUnifiedCommand(command, OPCODES_LT2)):
            return super().parseCommandLt1(command)
        return True
    
    def extendUnifiedScript(self, script, referenceOpcode):
        r,g,b = self.colourAnswer
        commandColourDraw = Instruction()
        commandColourDraw.opcode = referenceOpcode.SetFontUserColor.value
        commandColourDraw.operands.append(Operand(TYPE_OPERANDS.INT_SIGNED.value, r))
        commandColourDraw.operands.append(Operand(TYPE_OPERANDS.INT_SIGNED.value, g))
        commandColourDraw.operands.append(Operand(TYPE_OPERANDS.INT_SIGNED.value, b))
        script.addInstruction(commandColourDraw)

        for location in self.locationsTrace:
            addTraceLocation = Instruction()
            addTraceLocation.opcode = referenceOpcode.AddTracePoint.value
    
            x,y = location.pos
            addTraceLocation.operands.append(Operand(TYPE_OPERANDS.INT_SIGNED.value, x))
            addTraceLocation.operands.append(Operand(TYPE_OPERANDS.INT_SIGNED.value, y))

            addTraceLocation.operands.append(Operand(TYPE_OPERANDS.FLOAT.value, location.radius))
            addTraceLocation.operands.append(Operand(TYPE_OPERANDS.STRING.value, DICT_PYTHON_TO_BOOLEAN[location.isAnswer]))
            script.addInstruction(addTraceLocation)
        
    def getScriptLt1(self):
        baseScript = super().getScriptLt1()
        self.extendUnifiedScript(baseScript, OPCODES_LT1)
        return baseScript

    def getScriptLt2(self):
        output = GdScript()
        self.extendUnifiedScript(output, OPCODES_LT2)
        return output