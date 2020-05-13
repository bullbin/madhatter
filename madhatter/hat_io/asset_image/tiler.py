from ..binary import BinaryWriter
from PIL import Image
from PIL.ImageFilter import GaussianBlur
from math import ceil

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
        if image.mode == "RGBA":
            output = Image.new("RGBA", (width, height))
        else:
            output = Image.new("RGB", (width, height))

        output.paste((0,0,0,0), (0, 0, width, height))

        if image.mode == "RGBA":
            output.paste(image, (0,0), image)
        else:
            output.paste(image.convert("RGB"), (0,0))
    return output

class Tile():

    DEFAULT_RESOLUTION  = (8,8)
    DEFAULT_OFFSET      = (0,0)
    DEFAULT_GLB         = (0,0)

    def __init__(self):
        self.image  = None
        self.glb    = (0,0)
        self.offset = (0,0)
    
    def setImageFromBytes(self, data, resolution, bpp, palette):
        self.image = Image.new("P", resolution)
        self.image.putpalette(palette)
        width, height = resolution
        x = 0
        y = 0
        for indexPixel in range(width * height * bpp // 8):
            packedPixel = data[indexPixel]
            for _indexSubPixel in range(8 // bpp):
                self.image.putpixel((x,y), (packedPixel & ((2 ** bpp) - 1)) & (len(palette) // 3))
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

class TiledImageHandler():

    MAX_COUNT_COLOURS = 250
    COLOUR_ALPHA = [200,0,200]

    def __init__(self):
        self.tiles = []
        self.tileMap = {}       # TilePackedPos -> Tile
        self.paletteRgbTriplets = []
        self.paletteContinuous = []
        self.bpp = 0
    
    def setPaletteFromList(self, palette):
        self.paletteContinuous = palette
        self.paletteRgbTriplets = []

        for indexTriplet in range(len(palette) // 3):
            indexTriplet = indexTriplet * 3
            tempTriplet = (palette[indexTriplet],
                           palette[indexTriplet + 1],
                           palette[indexTriplet + 2])
            if tempTriplet not in self.paletteRgbTriplets:
                self.paletteRgbTriplets.append(tempTriplet)
            else:  # Stop if duplicate found
                break

    def addTileFromReader(self, reader, resolution=Tile.DEFAULT_RESOLUTION, glb=Tile.DEFAULT_GLB, offset=Tile.DEFAULT_OFFSET):
        dataLength = resolution[0] * resolution[1] * self.bpp / 8
        tempTile = Tile.fromBytes(reader.read(dataLength), resolution, self.bpp, self.paletteContinuous)
        tempTile.setGlb(glb)
        tempTile.setOffset(offset)
        self.tiles.append(tempTile)
    
    def tilesToImage(self, resolution, useOffset = False):
        width, height = resolution
        output = Image.new("P", resolution)
        output.putpalette(self.paletteContinuous)
        output.paste(0, (0, 0, width, height))

        if useOffset:
            for tile in self.tiles:
                output.paste(tile.getImage(), box = tile.offset)
        else:
            tileMapIndices = self.tileMap.keys()
            resolutionXTiles = ceil(width / 8)
            for indexTile in tileMapIndices:
                y = indexTile // resolutionXTiles
                x = indexTile % resolutionXTiles
                tileSelectedIndex = indexTile & (2 ** 10 - 1)
                tileSelectedFlipX = indexTile & (2 ** 11)
                tileSelectedFlipY = indexTile & (2 ** 10)

                if tileSelectedIndex < (2 ** 10 - 1):
                    tileFocus = self.tiles[tileSelectedIndex % len(self.tiles)]
                    if tileSelectedFlipX:
                        tileFocus = tileFocus.transpose(method=Image.FLIP_LEFT_RIGHT)
                    if tileSelectedFlipY:
                        tileFocus = tileFocus.transpose(method=Image.FLIP_TOP_BOTTOM)
                    output.paste(tileFocus, (x * 8, y * 8))
        return output
    
    def imageToTiles(self, image, useOffset=False):
        # TODO : Extend palette, change palette, etc
        imagePadded = alignToFitTile(image)
        width, height = imagePadded.size
        if width > (2 ** 16 - 1) or height > (2 ** 16 - 1):
            return
        
        alphaFillPixels = []
        if imagePadded.mode == "RGBA":
            # Get alpha pixels
            blurredImage = imagePadded.convert("RGB").filter(GaussianBlur(radius=4))
            compositedImage = Image.new("RGB", imagePadded.size)
            for y in range(height):
                for x in range(width):
                    r,g,b,a = imagePadded.getpixel((x,y))
                    if a >= 0.5:
                        compositedImage.putpixel((x,y), (r,g,b))
                    else:
                        compositedImage.putpixel((x,y), blurredImage.getpixel(x,y))
                        alphaFillPixels.append((x,y))

            imagePadded = compositedImage

        if imagePadded.mode != "P":
            imagePadded = imagePadded.quantize(colors=(TiledImageHandler.MAX_COUNT_COLOURS - 1))
            alphaPalette = TiledImageHandler.COLOUR_ALPHA + imagePadded.getpalette()
            imagePadded = imagePadded.point(lambda c: c + 1)
            imagePadded.putpalette(alphaPalette)
            for alphaPos in alphaFillPixels:
                imagePadded.putpixel(alphaPos, 0)
        
        self.paletteContinous = imagePadded.getpalette()
        
        if useOffset:
            for tileY in range(height // 8):
                for tileX in range(width // 8):
                    left = tileX * 8
                    upper = tileY * 8
                    tempTile = Tile()
                    tempTile.setImage(imagePadded.crop(box=(left, upper, left + 8, upper + 8)))
                    tempTile.setOffset((left, upper))
                    self.tiles.append(tempTile)
        else:
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