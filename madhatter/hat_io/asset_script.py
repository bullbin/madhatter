from . import binary
from .const import ENCODING_DEFAULT_STRING
from .asset import File

# TODO - Restructure this to fetch instructions instead of prepopulate (less intensive)

class Operand():
    def __init__(self, operandType, operandValue):
        self.type = operandType
        self.value = operandValue

    def __str__(self):
        return str(self.type) + "\t" + str(self.value)

class Instruction():
    def __init__(self):
        self.opcode = None
        self.operands = []

    def __str__(self):
        if self.opcode == None:
            return "NO-OP"
        output = self.opcode.hex() + "\t" + str(len(self.operands)) + " ops"
        for operand in self.operands:
            output += "\n\t" + str(operand)
        return output

class FutureInstruction(Instruction):
    def __init__(self):
        Instruction.__init__(self)
        self.countOperands = 0
        self.indexOperandsStart = 0
    
    def setFromData(self, data):
        reader = binary.BinaryReader(data=data)
        self.opcode = reader.read(2)
        self.countOperands = reader.readU16()
        self.indexOperandsStart = reader.readU32()

    @staticmethod
    def fromData(data):
        out = FutureInstruction()
        out.setFromData(data)
        return out

class LaytonScript(File):
    def __init__(self):
        File.__init__(self)
        self.commands       = []
    
    def load(self, data):

        def getBankString(reader, offsetString):
            bankString = {}
            reader.seek(offsetString)
            while reader.hasDataRemaining():
                index = reader.tell() - offsetString
                bankString[index] = reader.readNullTerminatedString(ENCODING_DEFAULT_STRING)
                reader.seek(1,1)
            return bankString
        
        def getBankOperand(reader, offsetOperands, countOperands, bankString):
            reader.seek(offsetOperands)
            bankOperands = {}
            for indexOperand in range(countOperands):
                tempOperandType = reader.readUInt(1)
                if tempOperandType == 0:
                    tempOperand = reader.readS32()
                elif tempOperandType == 1:
                    tempOperand = reader.readF32()
                elif tempOperandType == 2:
                    tempOperand = bankString[reader.readU32()]
                else:
                    tempOperand = reader.read(4)
                bankOperands[indexOperand] = Operand(tempOperandType, tempOperand)
            return bankOperands
        
        def populateInstructionOperands(bankOperands):
            for command in self.commands:
                for indexInstruction in range(command.indexOperandsStart, command.indexOperandsStart + command.countOperands):
                    command.operands.append(bankOperands[indexInstruction])

        reader = binary.BinaryReader(data=data)
        if reader.read(4) == b'LSCR':
            countCommand    = reader.readU16()
            countOperands   = 0
            offsetHeader    = reader.readU16()
            offsetOperands  = reader.readU32()
            offsetString    = reader.readU32()

            bankString = getBankString(reader, offsetString)

            reader.seek(offsetHeader)
            for indexCommand in range(countCommand):
                self.commands.append(FutureInstruction.fromData(reader.read(8)))
                countOperands = max(countOperands, self.commands[indexCommand].indexOperandsStart + self.commands[indexCommand].countOperands)
            
            bankOperand = getBankOperand(reader, offsetOperands, countOperands, bankString)
            populateInstructionOperands(bankOperand)
            return True
        return False
    
    def __str__(self):
        output = ""
        for operation in self.commands:
            output += "\n\n" + str(operation)
        return output