from __future__ import annotations
from typing import Any, List, Optional
from . import binary
from .const import ENCODING_DEFAULT_STRING, ENCODING_LAYTON_3_STRING
from .asset import File
# TODO - Use const enums for operand type

class Operand():
    def __init__(self, operandType : int, operandValue : Any):
        self.type   : int   = operandType
        self.value  : Any   = operandValue

    def __str__(self):
        return str(self.type) + "\t" + str(self.value)

class Instruction():
    def __init__(self):
        self.opcode   : Optional[bytes] = None
        self.operands : List[Operand]   = []

    def __str__(self):
        if self.opcode == None:
            return "NO-OP"
        output = self.opcode.hex() + "\t" + str(int.from_bytes(self.opcode, byteorder='little'))
        output += "\t" + str(len(self.operands)) + " ops"
        for operand in self.operands:
            output += "\n\t" + str(operand)
        return output

class FutureInstruction(Instruction):
    def __init__(self):
        Instruction.__init__(self)
        self.countOperands      = 0
        self.indexOperandsStart = 0
    
    def setFromData(self, data):
        reader = binary.BinaryReader(data=data)
        self.opcode = reader.read(2)
        self.countOperands = reader.readU16()
        self.indexOperandsStart = reader.readU32()

    @staticmethod
    def fromData(data) -> FutureInstruction:
        out = FutureInstruction()
        out.setFromData(data)
        return out

class Script(File):
    def __init__(self):
        File.__init__(self)
        self.commands : List[Instruction] = []
    
    def load(self, data : bytes) -> bool:
        """Parse binary file into this script object.

        Args:
            data (bytes): Binary script data.

        Returns:
            bool: True if loading commenced successfully.
        """
        return False

    def getInstructionCount(self) -> int:
        """Get the number of instructions contained within this script.

        Returns:
            int: Number of instructions.
        """
        return len(self.commands)
    
    def getInstruction(self, index : int) -> Optional[Instruction]:
        """Get the instruction at a given index.

        Args:
            index (int): Instruction index.

        Returns:
            Optional[Instruction]: Instruction. None if index was not in range.
        """
        if 0 <= index < self.getInstructionCount():
            return self.commands[index]
        return None

    def addInstruction(self, instruction : Instruction) -> bool:
        """Add instruction to end of this script.

        Args:
            instruction (Instruction): Instruction to append.

        Returns:
            bool: True if addition was successful.
        """
        if instruction.opcode != None:
            self.commands.append(instruction)
            return True
        return False
    
    def insertInstruction(self, indexInstruction : int, instruction : Instruction) -> bool:
        """_summary_

        Args:
            indexInstruction (int): _description_
            instruction (Instruction): _description_

        Returns:
            bool: True if instruction was successfully inserted.
        """
        if 0 <= indexInstruction <= len(self.commands):
            self.commands.insert(indexInstruction, instruction)
            return True
        return False
    
    def removeInstruction(self, indexInstruction : int) -> bool:
        """Remove the instruction at a given index.

        Args:
            indexInstruction (int): Index of instruction, starting at 0.

        Returns:
            bool: True if instruction was successfully removed.
        """
        if 0 <= indexInstruction < len(self.commands):
            self.commands.pop(indexInstruction)
            return True
        return False
    
    def cullUnreachableInstructions(self):
        pass

    def __str__(self):
        output = ""
        for operation in self.commands:
            output += "\n\n" + str(operation)
        return output

class LaytonScript(Script):
    def __init__(self):
        Script.__init__(self)
    
    def load(self, data):

        def getBankString(reader, offsetString):
            bankString = {}
            reader.seek(offsetString)
            while reader.hasDataRemaining():
                index = reader.tell() - offsetString
                bankString[index] = reader.readNullTerminatedString(ENCODING_LAYTON_3_STRING)
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

class GdScript(Script):
    def __init__(self):
        Script.__init__(self)
    
    def cullUnreachableInstructions(self):
        # TODO - Not optimal, doesn't evaluate branches. Just cleans breakpoint
        isCurious = False
        for instruction in self.commands:
            for operand in instruction.operands:
                operand : Operand
                if operand.type == 6 or operand.type == 7:
                    isCurious = True
                    break
            if isCurious:
                break
        
        if not(isCurious):
            idxInstruction = 0
            hitBreakpoint = False
            for instruction in self.commands:
                idxInstruction += 1
                for operand in instruction.operands:
                    if operand.type == 0xc:
                        hitBreakpoint = True
                        break
                if hitBreakpoint:
                    break

            if hitBreakpoint:
                self.commands = self.commands[:idxInstruction]
            
        return super().cullUnreachableInstructions()

    def save(self, isTalkscript=False):
        if not(isTalkscript):
            self.cullUnreachableInstructions()

        scriptWriter = binary.BinaryWriter()
        # TODO - Validation, since command length is known for LAYTON1 and LAYTON2
        for indexCommand in range(self.getInstructionCount()):
            scriptWriter.writeU16(0)
            command = self.getInstruction(indexCommand)
            scriptWriter.write(command.opcode)
            for operand in command.operands:
                scriptWriter.writeU16(operand.type)
                if operand.type in [1,6,7]:
                    scriptWriter.writeS32(operand.value)
                elif operand.type == 2:
                    scriptWriter.writeFloat(operand.value)
                elif operand.type == 3:
                    scriptWriter.writeLengthAndString(operand.value, ENCODING_DEFAULT_STRING)
                elif operand.type == 4:
                    scriptWriter.writeU16(operand.value)
                else:
                    pass

        # 0xc triggers early termination for script. Inhouse tools add this at end for extra security
        #     but it's otherwise redundant, length is checked anyways.
        # TODO - Collapse repeated breakpoints (have to check for LAYTON2 behaviour)
        scriptWriter.write(b'\x0c\x00')
        self.data = len(scriptWriter.data).to_bytes(4, byteorder = 'little') + scriptWriter.data

    def load(self, data, isTalkscript=False):
        
        reader = binary.BinaryReader(data=data)
        length = reader.readU32()
        if isTalkscript:
            # Seek backwards to allow command to read as 0
            # Not based on binary, but game doesn't care when reading talkscripts as it only wants the operands
            reader.seek(2)
        command = None
        while reader.tell() < length + 4:
            lastType = reader.readU16()
            if lastType == 0:
                if command != None:
                    self.commands.append(command)
                command = Instruction()
                if isTalkscript:
                    command.opcode = lastType.to_bytes(2, byteorder = 'little')
                else:
                    command.opcode = reader.read(2)
            elif lastType == 1: # Signed int
                command.operands.append(Operand(lastType, reader.readS32()))
            elif lastType == 2: # Float
                command.operands.append(Operand(lastType, reader.readF32()))
            elif lastType == 3: # String
                command.operands.append(Operand(lastType, reader.readPaddedString(reader.readU16(), ENCODING_DEFAULT_STRING)))
            elif lastType == 4: # Flags
                command.operands.append(Operand(lastType, reader.read(reader.readU16())))
            elif lastType in [5,8,9,10,11]:  # Skip
                pass
            elif lastType == 0xc: # Breakpoint, we diverge from reversing here (HACK)
                # HACK - Script can be zero-length, meant to terminate here so makes sense (11092)
                if command != None:
                    command.operands.append(Operand(lastType, None))
            elif lastType in [6,7]: # Offset
                command.operands.append(Operand(lastType, reader.readS32()))

        if command != None: # Bugfix where last command missing
            self.commands.append(command)
        
        if not(isTalkscript):
            # TODO - Further research into instruction culling
            # Happens during runtime - once we hit an 0xc operand type,
            #     we end script execution.
            # Behaviour not understood for LAYTON1 with branching.
            self.cullUnreachableInstructions()