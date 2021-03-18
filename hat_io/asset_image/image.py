from PIL import Image
from .opcodes import *
from .. import binary
from ...common import Rect
from ...common import log as logPrint
from ..asset import File, LaytonPack2
from ..asset_script import LaytonScript
from math import log
from .tiler import Tile, TiledImageHandler, getPaletteFromImages
from .colour import getPaletteAsListFromReader, getPackedColourFromRgb888
from ..const import ENCODING_DEFAULT_STRING

# TODO - Split animation into own submodule
# TODO - With LT3 images, the encoding is different which could result in bad characters moving to LT2

def getTransparentLaytonPaletted(inputImage):
    output = inputImage.copy().convert("RGBA")
    width, height = inputImage.size
    for y in range(height):
        for x in range(width):
            if inputImage.getpixel((x,y)) == 0:
                output.putpixel((x,y), (0,0,0,0))
    return output

def mergePalettedImage(inputImage, outputImage, pos):
    width, height = inputImage.size
    for y in range(height):
        for x in range(width):
            if inputImage.getpixel((x,y)) != 0:
                outputImage.putpixel((x + pos[0],y + pos[1]), inputImage.getpixel((x,y)))

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
        reusePalette = True
        targetPalette = None
        for frameRef in self.imageComponents:
            targetImage = frameRef.atlasImageReference.getImage(frameRef.atlasSubImageIndex)
            targetImage : Image
            if targetImage.mode == "P":
                if targetPalette == None:
                    targetPalette = targetImage.getpalette()
                elif targetPalette != targetImage.getpalette():
                    reusePalette = False
                    break
            else:
                reusePalette = False
                break
        
        if reusePalette and targetPalette != None:
            output = Image.new("P", self.dimensions)
            output.putpalette(targetPalette)
        else:
            output = Image.new("RGBA", self.dimensions)

        for frameRef in self.imageComponents:
            targetImage = frameRef.atlasImageReference.getImage(frameRef.atlasSubImageIndex)
            if output.mode == "RGBA":
                targetImageAlpha = getTransparentLaytonPaletted(targetImage)
                output.paste(targetImageAlpha, frameRef.pos, targetImageAlpha)
            else:
                mergePalettedImage(targetImage, output, frameRef.pos)

        return output

class AnimationKeyframe():
    def __init__(self):
        self.duration = 0
        self.indexFrame = 0

# TODO : Rewrite some of this to remove indexing, as values are passed by reference so not relevant
# TODO : Sort out variable space, setters and getters on public variables
# TODO : Add support for arj decoding
# TODO : Change to @property setup

class Animation():
    def __init__(self):
        self.name                        = ""
        self.keyframes                   = []
        self.subAnimationIndex  = None
        self.subAnimationOffset = (0,0)
    
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

    PREFIX_ARC_ATLAS_NAME = "ARC"

    def __init__(self):
        self.atlases = {}
        self.frames = []
        self.animations = []
        self.variables = {}

        for index in range(1,17):
            self.variables["Var" + str(index)] = [0,0,0,0,0,0,0,0]

        self.subAnimation = None
    
    def normaliseAnimation(self, animation):
        # Merge subanimation and animation by looking at subanimation cycle and merging
        # TODO : getAnimations method which gives this automagically
        return animation

    @staticmethod
    def fromBytesArc(data, functionGetFileByName=None):
        output = AnimatedImage()
        workingAtlas = StaticImage()
        reader = binary.BinaryReader(data=data)

        countSubImage = reader.readU16()
        givenBpp = 2 ** (reader.readU16() - 1)
        logPrint("Frames", countSubImage)
        logPrint("Bpp", givenBpp)

        tempWorkingImages           = []
        tempWorkingImageResolutions = []

        for indexImage in range(countSubImage):
            logPrint("Add Image")
            resolution = (reader.readU16(), reader.readU16())
            countTiles = reader.readU32()
            logPrint("\t", resolution, countTiles)
            workingImage = TiledImageHandler()
            for _indexTile in range(countTiles):
                # TODO - Are tiles written if empty?
                offset = (reader.readU16(), reader.readU16())
                tileRes = (2 ** (3 + reader.readU16()), 2 ** (3 + reader.readU16()))
                workingImage.addTileFromReader(reader, prolongDecoding=True, resolution=tileRes, offset=offset, overrideBpp=givenBpp)
            tempWorkingImages.append(workingImage)
            tempWorkingImageResolutions.append(resolution)
        
        countColours = reader.readU32()
        palette = getPaletteAsListFromReader(reader, countColours)
        atlasKey = AnimatedImage.PREFIX_ARC_ATLAS_NAME + str(len(output.atlases))
        output.atlases[atlasKey] = workingAtlas
        for indexImage in range(countSubImage):
            tempWorkingImages[indexImage].setPaletteFromList(palette, countColours=countColours)
            workingAtlas.addImage(tempWorkingImages[indexImage].tilesToImage(tempWorkingImageResolutions[indexImage], useOffset=True))
            workingFrame = AnimationFrame()
            workingFrame.name = str(indexImage)
            workingFrame.dimensions = workingAtlas.getImage(indexImage).size
            workingFrame.imageComponents.append(AnimationFramePartialDetails(output.atlases[atlasKey], indexImage))
            output.frames.append(workingFrame)
        
        reader.seek(30,1)
        countAnims = reader.readU32()
        for animIndex in range(countAnims):
            workingAnim = Animation()
            workingAnim.setName(reader.readPaddedString(30, ENCODING_DEFAULT_STRING))
            output.animations.append(workingAnim)
        
        for animIndex in range(countAnims):
            countFrames = reader.readU32()

            indexKeyframe = reader.readU32List(countFrames)
            durationKeyframe = reader.readU32List(countFrames)
            indexFrame = reader.readU32List(countFrames)

            orderedKeyframes = {}
            for indexAnimationKeyframe in range(countFrames):
                workingFrame = AnimationKeyframe()
                workingFrame.duration = durationKeyframe[indexAnimationKeyframe]
                workingFrame.indexFrame = indexFrame[indexAnimationKeyframe]
                orderedKeyframes[indexKeyframe[indexAnimationKeyframe]] = workingFrame
            orderedKeyframeIndices = list(orderedKeyframes.keys())
            orderedKeyframeIndices.sort()
            for sortedIndex in orderedKeyframeIndices:
                output.animations[animIndex].addKeyframe(orderedKeyframes[sortedIndex])

        variableNames = []
        if reader.hasDataRemaining():
            reader.seek(2,1)
            output.variables = {}

            for indexData in range(16):
                name = reader.readPaddedString(16, ENCODING_DEFAULT_STRING)
                variableNames.append(name)
                output.variables[name] = [0,0,0,0,0,0,0,0]

            for indexData in range(8):
                for indexVariable in range(16):
                    output.variables[variableNames[indexVariable]][indexData] = reader.readS16()
            
            offsetSubAnimationData = reader.tell()
            if callable(functionGetFileByName):
                try:
                    reader.seek(int(5 * countAnims), 1)
                    nameSubAnimation = reader.readPaddedString(128, ENCODING_DEFAULT_STRING)
                    if nameSubAnimation != "":
                        subAnimationData = functionGetFileByName(nameSubAnimation)
                        if subAnimationData != None:
                            output.subAnimation = AnimatedImage.fromBytesArc(subAnimationData, functionGetFileByName=functionGetFileByName)

                            reader.seek(offsetSubAnimationData)
                            tempOffset = [[],[]]
                            for indexDimension in range(2):
                                for indexOffset in range(countAnims):
                                    tempOffset[indexDimension].append(reader.readS16())
                            for indexAnim in range(countAnims):
                                output.animations[indexAnim].subAnimationOffset = (tempOffset[0][indexAnim], tempOffset[1][indexAnim])
                                output.animations[indexAnim].subAnimationIndex = reader.readUInt(1)

                except:
                    pass

        return output
    
    def toBytesArc(self, exportVariables=False):

        # Squashes all frames into one ARC. Palette is shared so potential to lose much quality
        # TODO - When input is an ARC, no requantization should be done (unless a face, but should be worked around).
        # Loss of quality is steep so more care should be taken to preserve anim quality

        images = []
        for frame in self.frames:
            images.append(frame.getComposedFrame())
        
        if len(images) > 0:
            palette  = getPaletteFromImages(images)

            packedImages = []
            packedDimensions = []

            # Prepare everything
            for indexImage, image in enumerate(images):
                workingImage = TiledImageHandler()
                width, height = workingImage.imageToTiles(image, useOffset=True, usePalette=palette)
                packedImages.append(workingImage)
                packedDimensions.append((width,height))
            
            writer = binary.BinaryWriter()
            writer.writeU16(len(images))

            encodedBpp = int(log(packedImages[0].getBpp(), 2) + 1)
            writer.writeU16(encodedBpp)

            for indexImage, image in enumerate(packedImages):
                width, height = packedDimensions[indexImage]
                writer.writeU16(width)
                writer.writeU16(height)
                writer.writeU32(len(image.getTiles()))
                for tile in image.getTiles():       # TODO : Optimisation, tiles can be up to 128x128 which can reduce header overhead
                    offsetX, offsetY = tile.offset
                    writer.writeU16(offsetX)
                    writer.writeU16(offsetY)
                    tileX, tileY = tile.image.size
                    writer.writeU16(int(log(tileX, 2) - 3))
                    writer.writeU16(int(log(tileY, 2) - 3))
                    writer.write(tile.toBytes(packedImages[0].getBpp()))
            
            palette = image.getPalette()    # Switch to RGB triplets
            writer.writeU32(len(palette))
            for r,g,b in palette:
                writer.writeU16(getPackedColourFromRgb888(r,g,b))

            writer.pad(30)
            writer.writeU32(len(self.animations))
            for anim in self.animations:
                writer.writePaddedString(anim.name, 30, ENCODING_DEFAULT_STRING)

            for anim in self.animations:
                writer.writeU32(len(anim.keyframes))
                for indexKeyframe, keyframe in enumerate(anim.keyframes):
                    writer.writeU32(indexKeyframe)
                for indexKeyframe, keyframe in enumerate(anim.keyframes):
                    writer.writeU32(keyframe.duration)
                for indexKeyframe, keyframe in enumerate(anim.keyframes):
                    writer.writeU32(keyframe.indexFrame)
            
            if exportVariables:
                writer.write(b'\x34\x12')
                for variableName in self.variables:
                    writer.writePaddedString(variableName, 16, ENCODING_DEFAULT_STRING)
                
                writer : binary.BinaryWriter

                for indexData in range(8):
                    for variableName in self.variables:
                        writer.writeInt(self.variables[variableName][indexData], 2, signed=True)
                        
                # TODO - Is this Layton2 specific?
                writer.pad(203) # TODO - Read variables and subanimation

            return writer.data
        return None

    def toBytesCAni(self):
        packAnim = LaytonPack2()
        scriptAnim = LaytonScript()

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
