from typing import Optional

from widebrim.madhatter.hat_io.asset_image.colour import eightToFive, fiveToEight
from ..binary import BinaryWriter
from ...common import logVerbose
from PIL import Image
from PIL.ImageFilter import GaussianBlur
from math import ceil, log

# TODO - Give method to TiledImage which iterates through every pixel of image,
#        and eliminates any unused colours from the palette.
#        Should be useful once alpha has been applied to cleanup excess pixels.

# TODO - Paletted non-Layton images will literally break everything

def alignToFitTile(image):
    width, height = image.size
    if width % 8 == 0 and height % 8 == 0:
        return image.copy()
    width   = ceil(width / 8) * 8
    height  = ceil(height / 8) * 8
    if image.mode == "P":
        output = Image.new("P", (width, height))
        output.putpalette(image.getpalette())
        output.paste(0, (0, 0, width, height))
        output.paste(image)
    else:
        output = Image.new("RGBA", (width, height))
        output.paste((0,0,0,0), (0, 0, width, height))

        if image.mode == "RGBA":
            output.paste(image, (0,0), image)
        else:
            output.paste(image.convert("RGB"), (0,0))
    return output

def purgePaletteList(palette):
    # TODO - Get palette length from image

    endIndex = len(palette) // 3

    for indexTriplet in range((len(palette) // 3) - 1, -1, -1):
        indexPalette = indexTriplet * 3
        tempTriplet = [palette[indexPalette],
                       palette[indexPalette + 1],
                       palette[indexPalette + 2]]
        
        if tempTriplet[0] == tempTriplet[1] == tempTriplet[2]:  # Primitive
            if tempTriplet[0] == indexTriplet:
                endIndex = indexTriplet
        else:
            break

    return list(palette[0:endIndex * 3])

def getMaxPaletteValue(image) -> Optional[int]:
    if image.mode == "P":
        return image.getextrema()[1]
    return None

def getPaletteFromImages(images):
    # There is a limit in PIL but hopefully this will never be reached
    countPixels = 0
    rgbImages = []
    for image in images:
        rgbImages.append(image.convert("RGB"))
        width, height = image.size
        countPixels += (width * height)
    colourSlice = Image.new("RGB", (countPixels, 1))
    colourSliceIndex = 0
    for image in rgbImages:
        width, height = image.size
        for y in range(height):
            for x in range(width):
                colourSlice.putpixel((colourSliceIndex,0), image.getpixel((x,y)))
                colourSliceIndex += 1
    colourSlice = colourSlice.quantize(colors=TiledImageHandler.MAX_COUNT_COLOURS - 1)
    return colourSlice.getpalette()

class Tile():

    DEFAULT_RESOLUTION  = (8,8)
    DEFAULT_OFFSET      = (0,0)
    DEFAULT_GLB         = (0,0)

    def __init__(self):
        self.image  = None
        self.glb    = (0,0)
        self.offset = (0,0)
    
    def setImageFromBytes(self, data, resolution, bpp, palette):
        # TODO - Fix length of palette as this will always be 768 under PIL
        self.image = Image.new("P", resolution)
        self.image.putpalette(palette)
        width, height = resolution
        x = 0
        y = 0
        for indexPixel in range(width * height * bpp // 8):
            packedPixel = data[indexPixel]
            for _indexSubPixel in range(8 // bpp):
                self.image.putpixel((x,y), (packedPixel & ((2 ** bpp) - 1)) % (len(palette) // 3))
                packedPixel = packedPixel >> bpp
                x += 1
                if x == width:
                    y += 1
                    x = 0

    @staticmethod
    def fromBytes(data, resolution, bpp, palette):
        output = Tile()
        output.setImageFromBytes(data, resolution, bpp, palette)
        return output
    
    def toBytes(self, bpp):
        # TODO : Buffer-style output? Overkill for only supporting 8bpp and 4bpp
        output = BinaryWriter()
        if self.image != None:
            width, height = self.getDimensions() #8x8
            pixelsPerByte = 8 // bpp
            for y in range(height):
                for x in range(width // pixelsPerByte):
                    workingByte = 0
                    x *= pixelsPerByte
                    for packIndex in range(pixelsPerByte):
                        packPixel = self.image.getpixel((x + packIndex, y))
                        workingByte += (packPixel << (packIndex * bpp))
                    output.writeInt(workingByte, 1)
        return output.data
    
    def setImage(self, image):
        self.image = image

    def setGlb(self, value):
        self.glb = value
    
    def setOffset(self, value):
        self.offset = value
    
    def getDimensions(self):
        if self.image == None:
            return None
        return self.image.size
    
    def getImage(self):
        return self.image

class TileProlongedDecode(Tile):
    def __init__(self):
        Tile.__init__(self)
        self.decodingData = b''
        self.bpp = 0
        self.needsDecode = True
        self.useArjDecoding = False
    
    @staticmethod
    def fromBytes(data, resolution, bpp, palette, useArjDecoding=False):
        output = TileProlongedDecode()
        output.useArjDecoding = useArjDecoding
        output.setImageFromBytes(data, resolution, bpp, palette)
        return output
    
    def setImageFromBytes(self, data, resolution, bpp, palette):
        self.image = Image.new("P", resolution)
        self.bpp = bpp
        self.decodingData = data
    
    def decode(self, palette):
        if self.needsDecode:
            self.image.putpalette(palette)
            width, height = self.image.size

            if self.useArjDecoding:
                pixelIndex = 0
                for ht in range(height // 8):
                    for wt in range(width // 8):
                        for h in range(8):
                            for w in range(8):
                                if self.bpp == 4:
                                    pixelByte = self.decodingData[pixelIndex // 2]
                                    if pixelIndex % 2 == 1:
                                        pixelByte = pixelByte >> self.bpp
                                    pixelByte = pixelByte & ((2**self.bpp) - 1)
                                else:
                                    pixelByte = self.decodingData[pixelIndex]
                                self.image.putpixel((w + wt * 8, h + ht * 8), pixelByte % (len(palette) // 3))
                                pixelIndex += 1

            else:
                x = 0
                y = 0
                for indexPixel in range(width * height * self.bpp // 8):
                    packedPixel = self.decodingData[indexPixel]
                    for _indexSubPixel in range(8 // self.bpp):
                        self.image.putpixel((x,y), (packedPixel & ((2 ** self.bpp) - 1)) % (len(palette) // 3))
                        packedPixel = packedPixel >> self.bpp
                        x += 1
                        if x == width:
                            y += 1
                            x = 0

            self.needsDecode = False

class TiledImageHandler():

    MAX_COUNT_COLOURS = 200
    COLOUR_ALPHA = [0,255,0]

    def __init__(self):
        self.tiles = []
        self.tileMap = {}       # TilePackedPos -> Tile
        self.paletteRgbTriplets = []
        self.paletteContinuous = []
    
    def getLengthPalette(self):
        return len(self.paletteRgbTriplets)

    def getBpp(self):
        if self.getLengthPalette() == 1:
            return 4
        elif self.getLengthPalette() < 1 or self.getLengthPalette() > 256:
            return None
        return ceil(log(self.getLengthPalette(), 2) / 4) * 4

    def getTiles(self):
        return self.tiles

    def getPalette(self):
        return self.paletteRgbTriplets

    def getTileMap(self):
        return self.tileMap

    def setTileMap(self, tileMap):
        self.tileMap = tileMap

    def extractPaletteFromImage(self, image : Image) -> bool:
        if image.mode != "P":
            return False
        
        self.paletteRgbTriplets = []
        countColors = getMaxPaletteValue(image) + 1
        palette = image.getpalette()
        for indexColor in range(countColors):
            indexColor *= 3
            self.paletteRgbTriplets.append((palette[indexColor], palette[indexColor + 1], palette[indexColor + 2]))
        return True

    def setPaletteFromList(self, palette, countColours=-1):
        # TODO : Get palette from any internal tiles to prevent too little/too many colours being added
        self.paletteRgbTriplets = []
        
        if countColours == -1:
            palette = purgePaletteList(palette)
            searchLength = len(palette) // 3
        else:
            searchLength = countColours

        self.paletteContinuous = palette

        for indexTriplet in range(searchLength):
            indexTriplet = indexTriplet * 3
            tempTriplet = (palette[indexTriplet],
                           palette[indexTriplet + 1],
                           palette[indexTriplet + 2])

            if tempTriplet not in self.paletteRgbTriplets:
                self.paletteRgbTriplets.append(tempTriplet)
            # TODO - Remap list in case of duplicates

        logVerbose("Palette set to", len(self.paletteRgbTriplets))

    # TODO - Improve tile support for arj and rewrite to force typing (make more resilient)
    # TODO - Multithread decoding for speedup especially on backgrounds
    def addTileFromReader(self, reader, prolongDecoding=False, useArjDecoding=False, resolution=Tile.DEFAULT_RESOLUTION, glb=Tile.DEFAULT_GLB, offset=Tile.DEFAULT_OFFSET, overrideBpp=-1):
        if overrideBpp != -1:
            bpp = overrideBpp
        else:
            bpp = self.getBpp()
        dataLength = int(resolution[0] * resolution[1] * bpp / 8)
        if prolongDecoding:
            tempTile = TileProlongedDecode.fromBytes(reader.read(dataLength), resolution, bpp, self.paletteContinuous, useArjDecoding=useArjDecoding)
        else:
            tempTile = Tile.fromBytes(reader.read(dataLength), resolution, bpp, self.paletteContinuous)
        tempTile.setGlb(glb)
        tempTile.setOffset(offset)
        self.tiles.append(tempTile)
    
    def decodeProlongedTiles(self):
        for tile in self.getTiles():
            if type(tile) == TileProlongedDecode:
                tile.decode(self.paletteContinuous)
 
    def tilesToImage(self, resolution, useOffset = False):
        self.decodeProlongedTiles()
        width, height = resolution
        output = Image.new("P", resolution)
        output.putpalette(self.paletteContinuous)
        output.paste(0, (0,0,width,height))

        if useOffset:
            for tile in self.tiles:
                output.paste(tile.getImage(), box = tile.offset)
        else:
            tileMapIndices = self.tileMap.keys()
            resolutionXTiles = ceil(width / 8)
            for indexTile in tileMapIndices:
                y = indexTile // resolutionXTiles
                x = indexTile % resolutionXTiles

                selectedTile = self.tileMap[indexTile]
                tileSelectedIndex = selectedTile & (2 ** 10 - 1)
                tileSelectedFlipX = selectedTile & (2 ** 11)
                tileSelectedFlipY = selectedTile & (2 ** 10)

                if tileSelectedIndex < (2 ** 10 - 1):
                    tileFocus = self.tiles[tileSelectedIndex % len(self.tiles)]
                    tileImage = tileFocus.getImage()
                    if tileSelectedFlipX:
                        tileImage = tileImage.transpose(method=Image.FLIP_LEFT_RIGHT)
                    if tileSelectedFlipY:
                        tileImage = tileImage.transpose(method=Image.FLIP_TOP_BOTTOM)
                    output.paste(tileImage, (x * 8, y * 8))
        return output
    
    def imageToTiles(self, image, useOffset=False, usePalette=[]):

        def getDimensionSplits(dimension, maxDim):
            dimension = round(ceil(dimension / 8) * 8)
            splits = [8]
            while splits[-1] < maxDim or splits[-1] < dimension:
                splits.append(splits[-1] * 2)
            splits.reverse()

            output = []
            while dimension > 0:
                for split in splits:
                    while split <= dimension:
                        output.append(split)
                        dimension -= split
                        break
            return output

        def getDimensionSplitsLayton2(dimension):
            return getDimensionSplits(dimension, maxDim=128)

        # TODO : Extend palette, change palette, etc
        logVerbose("Called to convert!")
        logVerbose("\tInput:", image.mode)
        imagePadded = alignToFitTile(image)
        width, height = imagePadded.size
        logVerbose("\tNew dimensions", width, "x", height)
        if width > (2 ** 16 - 1) or height > (2 ** 16 - 1):
            return
        
        alphaFillPixels = []
        if imagePadded.mode == "RGBA":
            logVerbose("Fixing alpha...")
            # Get alpha pixels
            blurredImage = imagePadded.convert("RGB").filter(GaussianBlur(radius=4))
            compositedImage = Image.new("RGB", imagePadded.size)
            for y in range(height):
                for x in range(width):
                    r,g,b,a = imagePadded.getpixel((x,y))
                    if a >= 0.5:
                        compositedImage.putpixel((x,y), (r,g,b))
                    else:
                        compositedImage.putpixel((x,y), blurredImage.getpixel((x,y)))
                        alphaFillPixels.append((x,y))

            imagePadded = compositedImage

        if imagePadded.mode != "P":
            logVerbose("\tQuantizing...")
            # TODO : Pick alpha colour based on whether it is not in the image
            if usePalette != []:
                # assume palette is already 5 bit (bad)
                imagePadded = imagePadded.quantize(palette=usePalette, dither=Image.FLOYDSTEINBERG)
            else:
                imagePaddedPalette = imagePadded.copy()

                # Quantize in 5 bit space
                width, height = imagePadded.size
                for x in range(width):
                    for y in range(height):
                        r,g,b = imagePaddedPalette.getpixel((x,y))
                        imagePaddedPalette.putpixel((x,y), (eightToFive(r), eightToFive(g), eightToFive(b)))
                imagePaddedPalette = imagePaddedPalette.quantize(colors=(TiledImageHandler.MAX_COUNT_COLOURS - 1))

                # Scale palette back to 8 bit space so dither can be more perceptually accurate
                palette = list(imagePaddedPalette.getpalette())
                newPalette = []
                for val in palette:
                    newPalette.append(fiveToEight(val))
                imagePaddedPalette.putpalette(newPalette)

                # PIL adds black as filler in its palette. Remove all black to prevent second quantization adding black
                countColors = getMaxPaletteValue(imagePaddedPalette) + 1
                for idxFixColor in range((len(palette) // 3) - countColors):
                    baseAddress = (countColors + idxFixColor) * 3
                    for trip in range(3):
                        newPalette[trip + baseAddress] = newPalette[trip]

                imagePaddedPalette.putpalette(newPalette)
                
                # Finally dither (PIL doesn't dither on initial for some reason, plus the colors argument is ignored here)
                imagePadded = imagePadded.quantize(colors=countColors, palette=imagePaddedPalette, dither=Image.FLOYDSTEINBERG)
            
            countColors = getMaxPaletteValue(imagePadded) + 1
            alphaPalette = TiledImageHandler.COLOUR_ALPHA + imagePadded.getpalette()[0:countColors * 3]
            # TODO - Cull used palette (can be too long)
            imagePadded = imagePadded.point(lambda c: c + 1)
            imagePadded.putpalette(alphaPalette)
            for alphaPos in alphaFillPixels:
                imagePadded.putpixel(alphaPos, 0)
        
        self.extractPaletteFromImage(imagePadded)
        
        if useOffset:
            logVerbose("\tFilling with offset data...")
            tileHeights = getDimensionSplitsLayton2(height)
            tileWidths = getDimensionSplitsLayton2(width)

            y = 0
            for tileY in list(tileHeights):
                x = 0
                for tileX in list(tileWidths):
                    tempTile = Tile()
                    tempTile.setImage(imagePadded.crop(box=(x, y, x + tileX, y + tileY)))
                    tempTile.setOffset((x,y))
                    self.tiles.append(tempTile)
                    x += tileX
                y += tileY
        else:
            logVerbose("\tFilling tilemap layout...")
            tileIndex = 0
            # TODO : Verify length of tiles to not exceed selectable amount (not possible?)
            # TODO : Improve detection to find mirrored tiles too
            for tileY in range(height // 8):
                for tileX in range(width // 8):
                    left = tileX * 8
                    upper = tileY * 8
                    tempTile = Tile()
                    tempTile.setImage(imagePadded.crop(box=(left, upper, left + 8, upper + 8)))
                    try:
                        self.tileMap[tileIndex] = self.tiles.index(tempTile)
                    except ValueError:
                        self.tileMap[tileIndex] = len(self.tiles)
                        self.tiles.append(tempTile)

                    tileIndex += 1
        
        return (width, height)