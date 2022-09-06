from typing import Dict, List, Optional, Tuple

from ...hat_io.asset_image.colour import eightToFive, fiveToEight
from ..binary import BinaryReader, BinaryWriter
from ...common import logVerbose
from PIL.Image import Image as ImageType
from PIL import Image
from PIL.ImageFilter import GaussianBlur
from math import ceil, log

# TODO - Give method to TiledImage which iterates through every pixel of image,
#        and eliminates any unused colours from the palette.
#        Should be useful once alpha has been applied to cleanup excess pixels.

# TODO - Paletted non-Layton images will literally break everything

def alignToFitTile(image : ImageType) -> ImageType:
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

def purgePaletteList(palette : List[int]) -> List[int]:
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

def getMaxPaletteValue(image : ImageType) -> Optional[int]:
    if image.mode == "P":
        return image.getextrema()[1]
    return None

def getPaletteFromImages(images : List[ImageType]) -> ImageType:
    # There is a limit in PIL but hopefully this will never be reached
    countPixels = 0
    rgbImages : List[ImageType] = []
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
    return colourSlice

class Tile():

    DEFAULT_RESOLUTION  = (8,8)
    DEFAULT_OFFSET      = (0,0)
    DEFAULT_GLB         = (0,0)

    def __init__(self):
        self.image  : Optional[ImageType]   = None
        self.glb    : Tuple[int,int]        = (0,0)
        self.offset : Tuple[int,int]        = (0,0)
    
    def setImageFromBytes(self, data : bytes, resolution : Tuple[int,int], bpp : int, palette : List[int]):
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
    def fromBytes(data : bytes, resolution : Tuple[int,int], bpp : int, palette : List[int]):
        output = Tile()
        output.setImageFromBytes(data, resolution, bpp, palette)
        return output
    
    def toBytes(self, bpp : int, isArj : bool = False) -> bytearray:
        # TODO : Buffer-style output? Overkill for only supporting 8bpp and 4bpp
        output = BinaryWriter()
        if self.image != None:
            if isArj:
                widthTile, heightTile = self.getDimensions()
                pixelsPerBytes = 8 // bpp
                # Should be 2 or 1...
                for hSubTile in range(heightTile // 8):
                    offsetH = hSubTile * 8
                    for wSubTile in range(widthTile // 8):
                        offsetW = wSubTile * 8
                        for height in range(8):
                            for widthChunk in range(8 // pixelsPerBytes):
                                width = widthChunk * pixelsPerBytes
                                encodedByte = 0
                                for idxPixel in range(pixelsPerBytes):
                                    pixel = self.image.getpixel((offsetW + width + idxPixel, offsetH + height))
                                    encodedByte = encodedByte | (pixel << (bpp * idxPixel))
                                output.writeInt(encodedByte, 1, signed=False)
            else:
                width, height = self.getDimensions()
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
    
    def setImage(self, image : Optional[ImageType]):
        self.image = image

    def setGlb(self, value : Tuple[int,int]):
        self.glb = value
    
    def setOffset(self, value : Tuple[int,int]):
        self.offset = value
    
    def getDimensions(self) -> Optional[Tuple[int,int]]:
        if self.image == None:
            return None
        return self.image.size
    
    def getImage(self) -> Optional[ImageType]:
        return self.image

class TileProlongedDecode(Tile):
    def __init__(self):
        Tile.__init__(self)
        self.decodingData   : bytes = b''
        self.bpp            : int   = 0
        self.needsDecode    : bool  = True
        self.useArjDecoding : bool  = False
    
    @staticmethod
    def fromBytes(data : bytes, resolution : Tuple[int,int], bpp : int, palette : List[int], useArjDecoding : bool = False):
        output = TileProlongedDecode()
        output.useArjDecoding = useArjDecoding
        output.setImageFromBytes(data, resolution, bpp, palette)
        return output
    
    def setImageFromBytes(self, data : bytes, resolution : Tuple[int,int], bpp : int, palette : List[int]):
        self.image = Image.new("P", resolution)
        self.bpp = bpp
        self.decodingData = data
    
    def decode(self, palette : List[int]):
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
        self.tiles              : List[Tile]                = []
        self.tileMap            : Dict[int,int]             = {}       # TilePackedPos -> Tile
        self.paletteRgbTriplets : List[Tuple[int,int,int]]  = []
        self.paletteContinuous  : List[int]                 = []
    
    def getLengthPalette(self) -> int:
        return len(self.paletteRgbTriplets)

    def getBpp(self) -> Optional[int]:
        if self.getLengthPalette() < 1 or self.getLengthPalette() > 256:
            return None
        elif self.getLengthPalette() < 16: # TODO - Min palette length
            return 4
        return ceil(log(self.getLengthPalette(), 2) / 4) * 4

    def getTiles(self) -> List[Tile]:
        return self.tiles

    def getPalette(self) -> List[Tuple[int,int,int]]:
        return self.paletteRgbTriplets

    def getTileMap(self) -> Dict[int,int]:
        return self.tileMap

    def setTileMap(self, tileMap : Dict[int,int]):
        self.tileMap = tileMap

    def extractPaletteFromImage(self, image : ImageType) -> bool:
        if image.mode != "P":
            return False
        
        self.paletteRgbTriplets = []
        countColors = getMaxPaletteValue(image) + 1
        palette = image.getpalette()
        for indexColor in range(countColors):
            indexColor *= 3
            self.paletteRgbTriplets.append((palette[indexColor], palette[indexColor + 1], palette[indexColor + 2]))
        return True

    def setPaletteFromList(self, palette : List[int], countColours : int = -1):
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

        logVerbose("Palette set to", len(self.paletteRgbTriplets), name="Tiler")

    # TODO - Improve tile support for arj and rewrite to force typing (make more resilient)
    # TODO - Multithread decoding for speedup especially on backgrounds
    def addTileFromReader(self, reader : BinaryReader, prolongDecoding : bool = False, useArjDecoding : bool = False,
                          resolution : Tuple[int,int] = Tile.DEFAULT_RESOLUTION, glb : Tuple[int,int] = Tile.DEFAULT_GLB,
                          offset : Tuple[int,int] = Tile.DEFAULT_OFFSET, overrideBpp : int = -1):
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
 
    def tilesToImage(self, resolution : Tuple[int,int], useOffset : bool = False) -> ImageType:
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
    
    def imageToTiles(self, image : ImageType, useOffset : bool = False, usePalette : List[int] = []) -> Optional[Tuple[int,int]]:

        def getDimensionSplits(dimension : int, maxDim : int) -> List[int]:
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

        def getDimensionSplitsLayton2(dimension : int) -> List[int]:
            return getDimensionSplits(dimension, maxDim=128)

        # TODO : Extend palette, change palette, etc
        logVerbose("Called to convert!", name="TilerToTile")
        logVerbose("\tInput:", image.mode, name="TilerToTile")
        imagePadded = alignToFitTile(image)
        width, height = imagePadded.size
        logVerbose("\tNew dimensions", width, "x", height, name="TilerToTile")
        if width > (2 ** 16 - 1) or height > (2 ** 16 - 1):
            return None
        
        alphaFillPixels = []
        if imagePadded.mode == "RGBA":
            logVerbose("Fixing alpha...", name="TilerToTile")
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
            logVerbose("\tQuantizing...", name="TilerToTile")
            # TODO - Pick alpha colour based on whether it is not in the image
            # TODO - Fix off-by-one bug where quantizing gives itself access to black
            if usePalette != []:
                logVerbose("Quantize source found!", usePalette, name="TilerToTile")
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
            logVerbose("\tFilling with offset data...", name="TilerToTile")
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
            logVerbose("\tFilling tilemap layout...", name="TilerToTile")
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