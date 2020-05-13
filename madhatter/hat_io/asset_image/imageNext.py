from PIL import Image
from .imageOpcodes import *
from .. import binary
from ...common import Rect
from ..asset import File, LaytonPack2
from ..asset_script import LaytonScript
from math import log, ceil
from .tiler import Tile, TiledImageHandler
from .colour import getPaletteAsListFromReader, getPackedColourFromRgb888

def getTransparentLaytonPaletted(inputImage):
    output = inputImage.copy().convert("RGBA")
    width, height = inputImage.size
    for y in range(height):
        for x in range(width):
            if inputImage.getpixel((x,y)) == 0:
                output.putpixel((x,y), (0,0,0,0))
    return output

class AnimationFramePartialDetails():
    def __init__(self, atlasImage, atlasSubImageIndex):
        self.atlasImageReference = atlasImage
        self.atlasSubImageIndex  = atlasSubImageIndex
        self.pos                 = (0,0)

class AnimationFrame():
    def __init__(self):
        self.name = ""
        self.dimensions = (0,0)
        self.imageComponents = []

    def getComposedFrame(self): # TODO : Store transparent version of atlas to avoid alpha reprocessing
        output = Image.new("RGBA", self.dimensions)
        for frameRef in self.imageComponents:
            targetImage = frameRef.atlasImageReference.getImage(frameRef.atlasSubImageIndex)
            targetImageAlpha = getTransparentLaytonPaletted(targetImage)
            output.paste(targetImageAlpha, frameRef.pos, targetImageAlpha)
        return output

class AnimationKeyframe():
    def __init__(self):
        self.duration = 0
        self.indexFrame = 0

class Animation():
    def __init__(self):
        self.name = ""
        self.keyframes = []
        self.indexSubanimation = None
        self.keySubanimation = None
    
    def addKeyframe(self, frame):
        self.keyframes.append(frame)
    
    def setName(self, name):
        self.name = name

    def getName(self, name):
        return self.name

    def getFrameAtIndex(self, index):
        pass

    def getCycleLength(self):
        cycleLength = 0
        for keyframe in self.keyframes:
            cycleLength += keyframe.duration
        return cycleLength

class AnimatedImage():
    def __init__(self):
        self.atlases = {}
        self.frames = []
        self.animations = []
    
    def debugSave(self):
        pass

    @staticmethod
    def fromBytesArc(data):
        pass

    @staticmethod
    def fromBytesCAni(data):
        output = AnimatedImage()

        scriptAnim  = LaytonScript()
        packAnim    = LaytonPack2()

        if packAnim.load(data):
            for file in packAnim.files:
                if file.name.split(".")[-1] == "lbin":
                    scriptAnim.load(file.data)
                else:
                    output.atlases[file.name] = StaticImage.fromBytesLImg(file.data)
        
        atlasesAsIndex  = {}
        workingFrame    = AnimationFrame()
        workingAnim     = Animation()
        
        for command in scriptAnim.commands:
            if command.opcode == OPCODE_LOAD_ASSET:
                atlasesAsIndex[len(atlasesAsIndex)] = command.operands[0].value

            elif command.opcode == OPCODE_DEFINITION_FRAME_START:
                # TODO : Implement offset
                workingFrame            = AnimationFrame()
                workingFrame.name       = command.operands[0].value
                workingFrame.dimensions = (command.operands[3].value, command.operands[4].value)

            elif command.opcode == OPCODE_DEFINITION_FRAME_MIX_CONTENT:
                # TODO : Research last unknown
                subFrameInfo            = AnimationFramePartialDetails(output.atlases[atlasesAsIndex[command.operands[0].value]], command.operands[1].value)
                subFrameInfo.pos        = (command.operands[2].value, command.operands[3].value)
                workingFrame.imageComponents.append(subFrameInfo)

            elif command.opcode == OPCODE_DEFINITION_FRAME_END:
                output.frames.append(workingFrame)
            
            elif command.opcode == OPCODE_DEFINITION_ANIM_START:
                workingAnim = Animation()
                workingAnim.setName(command.operands[0].value)
                # TODO: Implement rest of unknowns (crop, offset)
            
            elif command.opcode == OPCODE_DEFINITION_ANIM_MIX_FRAME:
                tempFrame = AnimationKeyframe()
                tempFrame.indexFrame = command.operands[0].value
                tempFrame.duration = command.operands[1].value
                workingAnim.keyframes.append(tempFrame)
            
            elif command.opcode == OPCODE_DEFINITION_ANIM_END:
                output.animations.append(workingAnim)
        
        return output

class StaticImage():
    def __init__(self):
        self.subImages = []
    
    def addImage(self, image:Image):
        self.subImages.append(image)

    def getImage(self, indexImage):
        if 0 <= indexImage < len(self.subImages):
            return self.subImages[indexImage]
        return None
    
    def getCountImages(self):
        return len(self.subImages)

    def removeImage(self, indexImage):
        if 0 <= indexImage < len(self.subImages):
            self.subImages.pop(indexImage)
            return True
        return False
    
    @staticmethod
    def fromBytesArc(data):
        output = StaticImage()
        reader = binary.BinaryReader(data=data)
        workingImage = TiledImageHandler()
        
        lengthPalette = reader.readU32()
        workingImage.setPaletteFromList(getPaletteAsListFromReader(reader, lengthPalette), countColours=lengthPalette)
        for index in range(reader.readU32()):
            workingImage.addTileFromReader(reader, overrideBpp=8)
        
        resolution = (reader.readU16() * 8, reader.readU16() * 8)
        tileMap = {}
        for index in range(int((resolution[0] * resolution[1]) // 64)):
            tileMap[index] = reader.readU16()

        workingImage.setTileMap(tileMap)
        output.addImage(workingImage.tilesToImage(resolution))
        return output
    
    def toBytesArc(self):
        # TODO - Not this...
        tempOutput = []
        for indexImage in range(self.getCountImages()):
            inputImage = self.getImage(indexImage)
            workingImage = TiledImageHandler()
            padWidth, padHeight = workingImage.imageToTiles(inputImage)

            palette = workingImage.getPalette()
            tiles = workingImage.getTiles()
            tileMap = workingImage.getTileMap()

            writer = binary.BinaryWriter()
            writer.writeU32(len(palette))
            for r,g,b in palette:
                writer.writeU16(getPackedColourFromRgb888(r,g,b))
            
            writer.writeU32(len(tiles))
            for tile in tiles:
                writer.write(tile.toBytes(8))

            writer.writeIntList([padWidth // 8, padHeight // 8], 2)
            for indexTile in range(len(tileMap)):
                writer.writeU16(tileMap[indexTile])

            tempOutput.append(writer.data)

        return tempOutput

    @staticmethod
    def fromBytesLImg(data):
        output = StaticImage()
        reader = binary.BinaryReader(data=data)
        if reader.read(4) == b'LIMG':
            lengthHeader        = reader.readU32()
            offsetSubImageData  = reader.readU16()
            countSubImage       = reader.readU16()
            _offsetImageParam    = reader.readU16()
            reader.seek(2,1)                            # UNK
            offsetTableTile     = reader.readU16()
            lengthTableTile     = reader.readU16()
            offsetTile          = reader.readU16()
            countTile           = reader.readU16()
            reader.seek(2,1)                            # UNK, maybe countPalette
            lengthPalette       = reader.readU16()
            resolution          = (reader.readU16(),
                                   reader.readU16())
            
            workingImage = TiledImageHandler()

            reader.seek(lengthHeader)
            workingImage.setPaletteFromList(getPaletteAsListFromReader(reader, lengthPalette), countColours=lengthPalette)

            reader.seek(offsetTile)
            for _index in range(countTile):
                workingImage.addTileFromReader(reader)
            
            reader.seek(offsetTableTile)
            tileMap = {}
            for index in range(lengthTableTile):
                tileMap[index] = reader.readU16()
            workingImage.setTileMap(tileMap)

            packedTexture = workingImage.tilesToImage(resolution)

            reader.seek(offsetSubImageData)
            for _subImageCount in range(countSubImage):
                left = reader.readUInt(1) * 8
                upper = reader.readUInt(1) * 8
                width = reader.readUInt(1) * 8
                height = reader.readUInt(1) * 8
                output.addImage(packedTexture.crop((left, upper, left + width, upper + height)))
                reader.seek(4,1)                        # UNK
        return output