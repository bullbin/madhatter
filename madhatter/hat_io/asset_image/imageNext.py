from PIL import Image
from .imageOpcodes import *
from .imageConst import *
from .. import binary
from ...common import Rect
from ..asset import File, LaytonPack2
from ..asset_script import LaytonScript
from math import log, ceil

def getColoursAsList(reader):
    packedColour = reader.readU16()
    b = ((packedColour >> 10) & 0x1f) / 31
    g = ((packedColour >> 5) & 0x1f) / 31
    r = (packedColour & 0x1f) / 31
    if IMAGE_FORCE_FULL_RANGE_COLOUR:
        return ([int(r * 255), int(g * 255), int(b * 255)])
    return ([int(r * 248), int(g * 248), int(b * 248)])

def getPaletteAsList(reader, countPalette):
    palette = []
    for _indexColour in range(countPalette):
        palette.extend(getColoursAsList(reader))
    return palette

def getBpp(lengthPalette):
    # Note: will fail if 1 colour, or above 8 bpp (bad)
    if lengthPalette == 1:
        return 4
    elif lengthPalette < 1 or lengthPalette > 256:
        return None
    return ceil(log(lengthPalette, 2) / 4) * 4 

def constructFinalImage(reader, palette, resolution, tileImages):
    width, height = resolution
    output = Image.new("P", resolution)
    output.putpalette(palette)
    output.paste(0, (0,0,width,height))
    for y in range(ceil(height / 8)):
        for x in range(ceil(width / 8)):
            tempSelectedTile = reader.readU16()
            tileSelectedIndex = tempSelectedTile & (2 ** 10 - 1)
            tileSelectedFlipX = tempSelectedTile & (2 ** 11)
            tileSelectedFlipY = tempSelectedTile & (2 ** 10)

            if tileSelectedIndex < (2 ** 10 - 1):
                tileFocus = tileImages[tileSelectedIndex % len(tileImages)]
                if tileSelectedFlipX:
                    tileFocus = tileFocus.transpose(method=Image.FLIP_LEFT_RIGHT)
                if tileSelectedFlipY:
                    tileFocus = tileFocus.transpose(method=Image.FLIP_TOP_BOTTOM)
                output.paste(tileFocus, (x * 8, y * 8))
    return output

class AnimationFramePartialDetails():
    def __init__(self, atlasKey, atlasSubImageIndex):
        self.atlasKey           = atlasKey
        self.atlasSubImageIndex = atlasSubImageIndex
        self.pos                = (0,0)

class AnimationFrame():
    def __init__(self):
        self.name = None
        self.dimensions = None
        self.imageComponents = []

    def getComposedFrame(self):
        pass

class AnimationKeyframe():
    def __init__(self):
        self.duration = 0
        self.indexFrame = 0

class Animation():
    def __init__(self):
        self.name = None
        self.keyframes = []
        self.indexSubanimation = None
        self.keySubanimation = None
    
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
                subFrameInfo            = AnimationFramePartialDetails(atlasesAsIndex[command.operands[0].value], command.operands[1].value)
                subFrameInfo.pos        = (command.operands[2].value, command.operands[3].value)
                workingFrame.imageComponents.append(subFrameInfo)

            elif command.opcode == OPCODE_DEFINITION_FRAME_END:
                output.frames.append(workingFrame)

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
        palette = getPaletteAsList(reader, reader.readU32())

        tilePilMap = {}
        for index in range(reader.readU32()):
            tilePilMap[index] = Tile(data=reader.read(64)).decodeToPil(palette, 8)
        
        resolution = (reader.readU16() * 8, reader.readU16() * 8)
        output.addImage(constructFinalImage(reader, palette, resolution, tilePilMap))
        return output
    
    @staticmethod
    def fromBytesLImg(data):
        output = StaticImage()
        reader = binary.BinaryReader(data=data)
        if reader.read(4) == b'LIMG':
            lengthHeader        = reader.readU32()
            offsetSubImageData  = reader.readU16()
            countSubImage       = reader.readU16()
            offsetImageParam    = reader.readU16()
            reader.seek(2,1)                            # UNK
            offsetTableTile     = reader.readU16()
            lengthTableTile     = reader.readU16()
            offsetTile          = reader.readU16()
            countTile           = reader.readU16()
            countPalette        = reader.readU16()
            lengthPalette       = reader.readU16()
            resolution          = (reader.readU16(),
                                   reader.readU16())
            
            bpp = getBpp(lengthPalette)
            reader.seek(lengthHeader)
            palette = getPaletteAsList(reader, lengthPalette)

            reader.seek(offsetTile)
            tilePilMap = {}
            for index in range(countTile):
                tilePilMap[index] = Tile(data=reader.read(int((bpp * 64) / 8))).decodeToPil(palette, bpp)
            
            reader.seek(offsetTableTile)
            packedTexture = constructFinalImage(reader, palette, resolution, tilePilMap)
            
            reader.seek(offsetSubImageData)
            for _subImageCount in range(countSubImage):
                left = reader.readUInt(1) * 8
                upper = reader.readUInt(1) * 8
                width = reader.readUInt(1) * 8
                height = reader.readUInt(1) * 8
                output.addImage(packedTexture.crop((left, upper, left + width, upper + height)))
                reader.seek(4,1)                        # UNK
        return output

class Tile():
    def __init__(self, data=None):
        self.data   = data
        self.glb    = (0,0)
        self.offset = (0,0)
        self.res    = (8,8)
    
    def fetchData(self, reader, bpp):
        self.offset = (reader.readU2(), reader.readU2())
        self.res = (2 ** (3 + reader.readU2()), 2 ** (3 + reader.readU2()))
        self.data = reader.read(int(bpp / 8 * self.res[0] * self.res[1]))

    def decodeToPil(self, palette, bpp):
        image = Image.new("P", self.res)
        image.putpalette(palette)
        pixelY = -1
        pixelX = 0
        for indexPixel in range(int(self.res[0] * self.res[1] * (bpp/8))):
            pixelByte = self.data[indexPixel]
            if indexPixel % int(self.res[0] * bpp/8) == 0:
                pixelY += 1
                pixelX = 0
            for _indexSubPixel in range(int(1/(bpp/8))):
                image.putpixel((pixelX, pixelY), (pixelByte & ((2**bpp) - 1)) % (len(palette) // 3))
                pixelByte = pixelByte >> bpp
                pixelX += 1
        return image