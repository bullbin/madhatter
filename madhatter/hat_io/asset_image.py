import math
from PIL import Image
from os import path

from . import binary
from .asset import File

EXPORT_EXTENSION = "png"
EXPORT_WITH_ALPHA = True    # Not recommended for in-engine as masking is faster
EXPORT_EXPANDED_COLOUR = True

def pilPaletteToRgbTriplets(image):
    paletteData = image.getpalette()
    output = []
    for rgbTriplet in range(256):
        output.append((paletteData[rgbTriplet * 3], paletteData[rgbTriplet * 3 + 1], paletteData[rgbTriplet * 3 + 2]))
    return output

def countPilPaletteColours(image):
    lastColour = None
    for indexColour, colour in enumerate(pilPaletteToRgbTriplets(image)):
        if lastColour == colour:
            return indexColour
        lastColour = colour
    return 256

class Colour():
    def __init__(self, r = 1, g = 1, b = 1):
        self.r, self.g, self.b = r, g, b
    
    @staticmethod
    def fromInt(encodedColour):
        colourOut = Colour()
        colourOut.b = ((encodedColour >> 10) & 0x1f) / 31
        colourOut.g = ((encodedColour >> 5) & 0x1f) / 31
        colourOut.r = (encodedColour & 0x1f) / 31
        return colourOut
    
    def toList(self):
        if EXPORT_EXPANDED_COLOUR:
            return ([int(self.r * 255), int(self.g * 255), int(self.b * 255)])
        return ([int(self.r * 248), int(self.g * 248), int(self.b * 248)])

class ImageVariable():
    def __init__(self, name):
        self.name = name
        self.data = []
    
    def addData(self, data):
        if len(self.data) == 8:
            return False
        self.data.append(data)
        return True

class Tile():
    def __init__(self, data=None):
        self.data = data
        self.glb = (0,0)
        self.offset = (0,0)
        self.res = (8,8)
    
    def fetchData(self, reader, bpp):
        self.offset = (reader.readU2(), reader.readU2())
        self.res = (2 ** (3 + reader.readU2()), 2 ** (3 + reader.readU2()))
        self.data = reader.read(int(bpp / 8 * self.res[0] * self.res[1]))

    def decodeToPil(self, palette, bpp):
        image = Image.new("P", self.res)
        image.putpalette(palette)
        pixelY = -1
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
    
    def decodeToPilArj(self, palette, bpp):
        image = Image.new("P", self.res)
        image.putpalette(palette)
        pixelIndex = 0
        for ht in range(self.res[1] // 8):
            for wt in range(self.res[0] // 8):
                for h in range(8):
                    for w in range(8):
                        if bpp == 4:
                            pixelByte = self.data[pixelIndex // 2]
                            if pixelIndex % 2 == 1:
                                pixelByte = pixelByte >> bpp
                            pixelByte = pixelByte & ((2**bpp) - 1)
                        else:
                            pixelByte = self.data[pixelIndex]
                        image.putpixel((w + wt * 8, h + ht * 8), pixelByte % (len(palette) // 3))
                        pixelIndex += 1
        return image

class TiledImage():
    def __init__(self, res=(0,0)):
        self.res = res
        self.tiles = []
    
    def getPilConstructedImage(self, palette, bpp, isArj):
        # TODO : Fill with transparency
        outputImage = Image.new('P', self.res)
        outputImage.putpalette(palette)
        for tile in self.tiles:
            if isArj:
                outputImage.paste(tile.decodeToPilArj(palette, bpp), box=tile.offset)
            else:
                outputImage.paste(tile.decodeToPil(palette, bpp), box=tile.offset)
        return outputImage

class AnimationBasicSequence():
    def __init__(self):
        self.indexFrames = []
        self.frameDuration = []
        self.indexImages = []
        self.name = "Create an Animation"
        self.offsetFace = (0,0)
        self.indexAnimFace = 0
    def __str__(self):
        return "Animation Details\nName:\t" + self.name + "\nFrmIdx:\t" + str(self.indexFrames) + "\nImgIdx:\t" + str(self.indexImages) + "\nUnkFrm:\t" + str(self.frameDuration) + "\n"

class LaytonAnimatedImage(File):
    def __init__(self):
        File.__init__(self)
        self.images = []
        self.anims = []
        self.alphaMask = None

        self.variableName = ""
        self.variables = []
        for indexVar in range(16):
            self.variables.append(ImageVariable("Var" + str(indexVar + 1)))
    
    def load(self, data, isArj=False):
        reader = binary.BinaryReader(data = data)
        
        countImages = reader.readU2()
        bpp = 2 ** (reader.readU2() - 1)
        if isArj:
            countColours = reader.readU4()

        for indexImage in range(countImages):
            self.images.append(TiledImage(res=(reader.readU2(), reader.readU2())))
            imageCountTiles = reader.readU4()
            for indexTile in range(imageCountTiles):
                self.images[indexImage].tiles.append(Tile())
                if isArj:
                    self.images[indexImage].tiles[indexTile].glb = (reader.readU2(), reader.readU2())
                self.images[indexImage].tiles[indexTile].fetchData(reader, bpp)
        
        if not(isArj):
            countColours = reader.readU4()

        palette = self.getPaletteAndAnimations(reader, countColours)

        # Variable-space
        if reader.hasDataRemaining():
            unk = reader.read(2)
            if unk != b'\x34\x12':
                print("Variable magic failed, still reading forwards...")

            self.variables      = []
            for _indexVar in range(16):
                self.variables.append(ImageVariable(reader.readPaddedString(16, 'shift-jis')))
            for _indexData in range(8):
                for indexVar in range(16):
                    self.variables[indexVar].addData(reader.readS2())

            tempDimensions = [[],[]]
            for indexDimension in range(2):
                for _indexPos in range(len(self.anims)):
                    tempDimensions[indexDimension].append(reader.readU2())
            for indexAnim in range(len(self.anims)):
                self.anims[indexAnim].offsetFace = (tempDimensions[0][indexAnim], tempDimensions[1][indexAnim])
                self.anims[indexAnim].indexAnimFace = reader.readUInt(1)
            self.variableName = reader.readPaddedString(128, 'shift-jis')
            if reader.hasDataRemaining():
                print("Did not reach end of image file!")
            
        for indexImage, image in enumerate(self.images):
            self.images[indexImage] = image.getPilConstructedImage(palette, bpp, isArj)
            
    def getPaletteAndAnimations(self, reader, countColours):
        palette = []
        if countColours > 1:
            self.alphaMask = Colour.fromInt(reader.readU2()).toList()
            countColours -= 1
            palette.extend(self.alphaMask)
        for _indexColour in range(countColours):
            palette.extend(Colour.fromInt(reader.readU2()).toList())
        
        reader.seek(30, 1)
        countAnims = reader.readU4()
        for indexAnim in range(countAnims):
            self.anims.append(AnimationBasicSequence())
            tempName = ((reader.read(30)).decode("ascii")).split("\x00")[0]

            nameCorrection = ""
            for nameCorrectionSection in tempName.split(" "):
                if len(nameCorrectionSection) > 0:
                    if len(nameCorrection) == 0:
                        nameCorrection = nameCorrectionSection
                    else:
                        nameCorrection = nameCorrection + " " + nameCorrectionSection
            self.anims[indexAnim].name = nameCorrection

        for indexAnim in range(countAnims):
            countFrames = reader.readU4()
            for _indexFrame in range(countFrames):
                self.anims[indexAnim].indexFrames.append(reader.readU4())
            for _indexFrame in range(countFrames):
                self.anims[indexAnim].frameDuration.append(reader.readU4())
            for _indexFrame in range(countFrames):
                self.anims[indexAnim].indexImages.append(reader.readU4())
        return palette

    def save(self):
        tileSize = 64
        # TODO: Assumes all images have dimensions of multiples of 8
        maxRes = (0,0)
        for image in self.images:
            maxRes = (maxRes[0] + image.size[0], max(maxRes[1], image.size[1]))
        paletteSurface = Image.new('RGB', maxRes)
        offsetX = 0
        for image in self.images:
            paletteSurface.paste(image, box=(offsetX, 0))
            offsetX += image.size[0]

        paletteSurface = paletteSurface.quantize(colors=10)

        writer = binary.BinaryWriter()
        writer.writeU2(len(self.images))
        bpp = math.log(int(math.ceil(math.ceil(math.log(len(paletteSurface.getcolors()), 2)) / 4) * 4), 2)
        writer.writeU2(int(bpp) + 1)
        bpp = 2 ** bpp

        offsetX = 0
        for indexImage, image in enumerate(self.images):
            imageTilemap = []
            imageTiles = []
            image = paletteSurface.crop((offsetX, 0, offsetX + image.size[0], image.size[1]))
            
            for tileResY in range(self.images[indexImage].size[1] // tileSize):
                for tileResX in range(self.images[indexImage].size[0] // tileSize):
                    tempTile = paletteSurface.crop(((tileResX * tileSize) + offsetX,
                                                    tileResY * tileSize,
                                                    ((tileResX + 1) * tileSize) + offsetX,
                                                    (tileResY + 1) * tileSize))
                    if tempTile in imageTiles:
                        imageTilemap.append(imageTiles.index(tempTile))
                    else:
                        imageTilemap.append(len(imageTiles))
                        imageTiles.append(tempTile)
            offsetX += image.size[0]

            writer.writeIntList([image.size[0], image.size[1]], 2)

    def export(self, filename):
        for i, image in enumerate(self.images):
            image.save(path.splitext(filename)[0] + "_" + str(i) + "." + EXPORT_EXTENSION)

class LaytonBackgroundImage(File):

    COLOUR_MAX = 250    # Anything above 250 causes graphical corruption
    COLOUR_ALPHA = [224,0,120]

    def __init__(self):
        File.__init__(self)
        self.image = None
    
    @staticmethod
    def fromPil(image):
        """Create a new background from a PIL-based RGBA/RGB image.
        \nAll transparency must be represented in the alpha channel of the image.
        Any blending will be converted to alpha masking.
        
        Arguments:
            image {PIL.Image} -- Image in P, RGB or RGBA mode
        """

        def addAlphaToOutputImageAndRescaleColour():
            countColours = countPilPaletteColours(output.image)
            if countColours > LaytonBackgroundImage.COLOUR_MAX - 1:
                countColours = LaytonBackgroundImage.COLOUR_MAX - 1
            output.image = Image.eval(output.image, (lambda p: p + 1))    # Shift palette to make room for alpha
            tempPalette = LaytonBackgroundImage.COLOUR_ALPHA
            for channel in output.image.getpalette()[0:countColours * 3]:
                tempPalette.append(channel << 3)
            tempPalette.extend(tempPalette[-3:] * (256 - (len(tempPalette) // 3)))
            output.image.putpalette(tempPalette)

        output = LaytonBackgroundImage()
        
        if image.mode in ["P", "RGB", "RGBA"]:
            # Validate if transparency pathway required because it is slow
            if image.mode == "P":       # Detect transparency in paletted images
                if image.info.get("transparency", None) != None:
                    image = image.convert("RGBA")   # TODO: Hunt in palette for whether transparent colour is used
                else:
                    image = image.convert("RGB")
            if image.mode == "RGBA":    # Validate if image is actually transparent
                if image.getextrema()[3][0] == 255:
                    image = image.convert("RGB")
            
            alphaPix = []
            # Strict, but ensures alpha is always preserved even for tiny palettes and/or small details
            if image.mode == "RGBA":
                # Produce a 5-bit version of the image with crushed alpha ready for mixing
                reducedImage = Image.eval(image.convert('RGB'), (lambda p: p >> 3)).convert("RGBA")
                reducedImage.putalpha(Image.eval(image.split()[-1], (lambda p: int((p >> 7) * 255))))

                colours = {}
                colourSurfaceX = 0
                for x in range(image.size[0]):
                    for y in range(image.size[1]):
                        r,g,b,a = reducedImage.getpixel((x,y))
                        if a > 0:
                            if (r,g,b) not in colours.keys():
                                colours[(r,g,b)] = 1
                            else:
                                colours[(r,g,b)] += 1
                            colourSurfaceX += 1
                        else:
                            alphaPix.append((x,y))
                
                # Produce new palette from used colour strip
                palette = Image.new('RGB', (colourSurfaceX, 1))
                colourSurfaceX = 0
                averageColour = [0,0,0]
                for colour in colours.keys():
                    for indexPixel in range(colours[colour]):
                        palette.putpixel((colourSurfaceX + indexPixel, 0), colour)
                    colourSurfaceX += colours[colour]
                    averageColour[0], averageColour[1], averageColour[2] = averageColour[0] + (colour[0] * colours[colour]), averageColour[1] + (colour[1] * colours[colour]), averageColour[2] + (colour[2] * colours[colour])
                palette = palette.quantize(colors=LaytonBackgroundImage.COLOUR_MAX - 1)
                averageColour = (averageColour[0] // colourSurfaceX, averageColour[1] // colourSurfaceX, averageColour[2] // colourSurfaceX)

                # Reduce colour bleeding on alpha edges by producing a new image with alpha given the average colour
                alphaCoverage = Image.new("RGB", image.size, averageColour)
                alphaCoverage.paste(reducedImage, (0,0), mask=reducedImage)

                # Finally quantize image
                output.image = alphaCoverage.convert("RGB").quantize(palette=palette)   
            else:
                # Quantize image if no pre-processing is required
                output.image = Image.eval(image, (lambda p: p >> 3)).quantize(colors=LaytonBackgroundImage.COLOUR_MAX - 1)
            
            addAlphaToOutputImageAndRescaleColour()
            for alphaLoc in alphaPix: # TODO - Reusing alphaCoverage mask and then overlaying it may be faster
                output.image.putpixel(alphaLoc, 0)

            if output.image.size[0] % 8 != 0 or output.image.size[1] % 8 != 0:  # Align image to block sizes by filling with transparency
                tempOriginalImage = output.image
                tempScaledDimensions = (math.ceil(output.image.size[0] / 8) * 8, math.ceil(output.image.size[1] / 8) * 8)
                output.image = Image.new(tempOriginalImage.mode, tempScaledDimensions, color=0)
                output.image.putpalette(tempOriginalImage.getpalette())
                output.image.paste(tempOriginalImage, (0,0))

        # TODO - Exception on None
        return output

    def save(self):
        writer = binary.BinaryWriter()
        countColours = countPilPaletteColours(self.image)
        writer.writeU4(countColours)
        for colour in pilPaletteToRgbTriplets(self.image)[0:countColours]:
            r,g,b = colour
            tempEncodedColour = (b << 7) + (g << 2) + (r >> 3)
            writer.writeU2(tempEncodedColour)

        tiles = []
        tilemap = []
        tileOptimisationMap = self.image.resize((self.image.size[0] // 8 , self.image.size[1] // 8), resample=Image.BILINEAR)
        tileOptimisationMap = tileOptimisationMap.quantize(colors=256)
        tileOptimisationDict = {}

        for yTile in range(self.image.size[1] // 8):
            # TODO - Evaluate each tile for any similar tiles
            for xTile in range(self.image.size[0] // 8):
                tempTile = self.image.crop((xTile * 8, yTile * 8, (xTile + 1) * 8, (yTile + 1) * 8))
                if tempTile in tiles:
                    tilemap.append(tiles.index(tempTile))
                else:
                    tilemap.append(len(tiles))
                    tiles.append(tempTile)
        
        writer.writeU4(len(tiles))
        for tile in tiles:
            writer.write(tile.tobytes())
        
        writer.writeU2(self.image.size[0] // 8)
        writer.writeU2(self.image.size[1] // 8)
        for key in tilemap:
            writer.writeU2(key)

        self.data = writer.data

    def load(self, data):
        reader = binary.BinaryReader(data=data)
        lengthPalette = reader.readU4()
        palette = []
        for _indexColour in range(lengthPalette):
            palette.extend(Colour.fromInt(reader.readU2()).toList())

        tilePilMap = {}
        countTile = reader.readU4()
        for index in range(countTile):
            tilePilMap[index] = Tile(data=reader.read(64)).decodeToPil(palette, 8)
        
        resTile = [reader.readU2(), reader.readU2()]
        self.image = Image.new("P", (int(resTile[0] * 8), int(resTile[1] * 8)))
        self.image.putpalette(palette)

        for y in range(resTile[1]):
            for x in range(resTile[0]):
                tempSelectedTile = reader.readU2()
                tileSelectedIndex = tempSelectedTile & (2 ** 10 - 1)
                tileSelectedFlipX = tempSelectedTile & (2 ** 11)
                tileSelectedFlipY = tempSelectedTile & (2 ** 10)

                if tileSelectedIndex < (2 ** 10 - 1):
                    # TODO: Blank out tile (should be default if alpha added)
                    tileFocus = tilePilMap[tileSelectedIndex % countTile]
                    if tileSelectedFlipX:
                        tileFocus = tileFocus.transpose(method=Image.FLIP_LEFT_RIGHT)
                    if tileSelectedFlipY:
                        tileFocus = tileFocus.transpose(method=Image.FLIP_TOP_BOTTOM)
                    self.image.paste(tileFocus, (x*8, y*8))