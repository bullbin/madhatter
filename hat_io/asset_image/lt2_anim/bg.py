from __future__ import annotations
from random import randint

from typing import List, Optional, Tuple
from PIL.Image import Image as ImageType
from PIL import Image
from ..colour import getPackedColourFromRgb888, getPaletteAsListFromReader
from ..paletting.alpha_helper import funcRejectPixelByThresholdingAlpha
from ..paletting.const import PREPROCESS_DITHER

from ..paletting.nds_bpc_helper import getConversionBasis
from ..paletting.paletter import generate5BitEncodedPalette
from ..paletting.quantizer import quantize
from ..paletting.transforms import ColorManagementController, NullColorManagementController, getTransformsForImage
from ..tiler import TiledImageHandler
from ...binary import BinaryReader, BinaryWriter

def _getSafeMaxColors(count : int) -> int:
    if 0 <= count <= EditableBackground.MAX_COLORS:
        return count
    return EditableBackground.MAX_COLORS

class EditableBackground():
    """Editable representation for ARC backgrounds. Alternative to madhatter.hat_io.asset_image.StaticImage with better usability and API.
    """

    MAX_COLORS          : int                   = 199
    DEFAULT_COLOR_ALPHA : Tuple[int,int,int]    = (0,255,0)

    def __init__(self):
        """Editable representation for ARC backgrounds. Alternative to madhatter.hat_io.asset_image.StaticImage with better usability and API.
        """
        self.__imageRaw         : Optional[ImageType]       = None
        self.__imageAlpha       : Optional[ImageType]       = None
        self.__imageQuantized   : Optional[ImageType]       = None
        self.__palette          : List[float,float,float]   = []
        self.__colorManagement  : Optional[ColorManagementController] = None
        self.__maxColors        : int = EditableBackground.MAX_COLORS

    @staticmethod
    def fromImage(image : ImageType, maxColors : int = 199, alphaResolveImage : Optional[ImageType] = None, alphaResolvePos : Tuple[int,int] = (0,0), preprocessMode : int = PREPROCESS_DITHER) -> EditableBackground:
        """Creates a background from an input image. No downscaling is applied, so keep images limited to around NDS sizes for processing.

        Args:
            image (ImageType): Input image. Any mode is permitted and transparency is thresholded.
            maxColors (int, optional): Maximum color count, not including alpha. Defaults to 199.
            alphaResolveImage (Optional[ImageType], optional): Image to place behind input to render partial alpha. Defaults to None.
            alphaResolvePos (Tuple[int,int], optional): Position to place input on resolving image. Defaults to (0,0).
            preprocessMode (int, optional): Preprocess mode constant. See getConversionBasis for more information. Defaults to PREPROCESS_DITHER.

        Returns:
            EditableBackground: Background image representation.
        """
        # TODO - Downscaling
        output = EditableBackground()
        maxColors = _getSafeMaxColors(maxColors)
        output.setImage(image, preprocessMode=preprocessMode, alphaResolveImage=alphaResolveImage, alphaResolvePos=alphaResolvePos)
        output.__maxColors = maxColors
        output.paletteRegenerate()
        return output

    @staticmethod
    def fromBytes(data : bytes) -> EditableBackground:
        """Creates a background from a decompressed ARC background file chunk.

        Args:
            data (bytes): Decompressed ARC background file chunk.

        Returns:
            EditableBackground: Background image representation.
        """
        output = EditableBackground()
        reader = BinaryReader(data=data)
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

        quantized = workingImage.tilesToImage(resolution)
        alphaChannel = None

        if lengthPalette > 0:
            alphaChannel = Image.new("L", resolution, 0)
            for y in range(resolution[1]):
                for x in range(resolution[0]):
                    pixel = quantized.getpixel((x,y))
                    if pixel == 0:
                        alphaChannel.putpixel((x,y), 0)
                    else:
                        alphaChannel.putpixel((x,y), 255)
                        quantized.putpixel((x,y), pixel - 1)
            quantized.putpalette(quantized.getpalette()[3:])
        
            output.__maxColors = lengthPalette - 1
        else:
            output.__maxColors = 0
        
        output.__imageRaw = quantized.convert("RGB")
        output.__imageAlpha = alphaChannel
        output.__imageQuantized = quantized
        output.__colorManagement = NullColorManagementController()

        palette = []
        rawPalette = quantized.getpalette()
        for indexColor in range(len(rawPalette) // 3):
            indexColor *= 3
            r = rawPalette[indexColor] / 255
            g = rawPalette[indexColor + 1] / 255
            b = rawPalette[indexColor + 2] / 255
            palette.append((r,g,b))

        output.__palette = palette
        return output

    def setMaxColors(self, maxColors : int):
        """Set maximum color count. This count does not include the alpha. If invalid, it will be fixed to 199.

        Args:
            maxColors (int): Maximum color count.
        """
        maxColors = _getSafeMaxColors(maxColors)
        if len(self.__palette) > maxColors:
            self.__palette = self.__palette[:maxColors]
            self.__imageQuantized = None

    def getMaxColors(self) -> int:
        """Get the maximum color count. This count does not include the alpha color.

        Returns:
            int: Maximum color count.
        """
        return self.__maxColors

    def paletteRegenerate(self, threshold : Optional[float] = 0.00025):
        """Force a regeneration of the internal palette.

        Args:
            threshold (Optional[float], optional): Color compression threshold. Refer to quantize function. Defaults to 0.00025.
        """
        if self.__imageRaw == None:
            return
        
        alphaFunc = funcRejectPixelByThresholdingAlpha(self.__imageAlpha)
        self.__palette = generate5BitEncodedPalette(self.__imageRaw, self.__colorManagement, funcPixelAllowedInPalette=alphaFunc, maxColors=self.__maxColors, thresholdCloseColors=threshold)
        self.__imageQuantized = None

    def paletteSetOverride(self, overridePaletteLinRgb : List[Tuple[float,float,float]]):
        """Override internal palette with input list. The list should be in the linear RGB space with components from 0 to 1.

        The input palette will be limited to the first colors before the maximum count is reached.

        Args:
            overridePaletteLinRgb (List[Tuple[float,float,float]]): New palette in linear RGB space.
        """
        if len(overridePaletteLinRgb) >= self.__maxColors:
            self.__palette = list(overridePaletteLinRgb)[:self.__maxColors]
        else:
            self.__palette = list(overridePaletteLinRgb)
        self.__imageQuantized = None

    def getPalette(self) -> List[Tuple[float,float,float]]:
        """Returns a copy of the internal palette. Changes to the output will not change the internal palette.

        Returns:
            List[Tuple[float,float,float]]: Copy of the internal palette.
        """
        return list(self.__palette)

    def __getQuantized(self) -> Optional[ImageType]:
        if self.__imageQuantized == None:
            if self.__imageRaw == None or self.__palette == []:
                return None
            
            alphaFunc = funcRejectPixelByThresholdingAlpha(self.__imageAlpha)
            self.__imageQuantized = quantize(self.__imageRaw, self.__palette, self.__colorManagement, funcPixelAllowedError=alphaFunc)
        return self.__imageQuantized
    
    def setImage(self, image : ImageType, alphaResolveImage : Optional[ImageType] = None, alphaResolvePos : Tuple[int,int] = (0,0), preprocessMode : int = PREPROCESS_DITHER):
        """Replace the current image with another image. This is similar to creating a new background from the input image, but does not modify the palette.

        Update the palette with paletteRegenerate to improve quality for the input image.

        Args:
            image (ImageType): Input image. Any mode is permitted and transparency is thresholded.
            alphaResolveImage (Optional[ImageType], optional): Image to place behind input to render partial alpha. Defaults to None.
            alphaResolvePos (Tuple[int,int], optional): Position to place input on resolving image. Defaults to (0,0).
            preprocessMode (int, optional): Preprocess mode constant. See getConversionBasis for more information. Defaults to PREPROCESS_DITHER.
        """
        basis, alpha = getConversionBasis(image, mode=preprocessMode, alphaResolveImage=alphaResolveImage, alphaPastePos=alphaResolvePos)
        self.__colorManagement = getTransformsForImage(image)
        self.__imageRaw = basis
        self.__imageAlpha = alpha
    
    def getRawImage(self) -> Optional[ImageType]:
        """Returns a copy of the non-paletted image. This refers to the source image so may exceed the capabilities of the NDS. Transparency is pre-applied.

        Modifications made to the returned image will not affect the internal image. If this background has no configured image, None will be returned.

        Returns:
            Optional[ImageType]: Source image, or None if this background has not been configured.
        """
        if self.__imageRaw == None:
            return None

        rgbSource = self.__imageRaw.convert("RGBA")
        if self.__imageAlpha != None:
            funcAlpha = funcRejectPixelByThresholdingAlpha(self.__imageAlpha)
            for y in range(rgbSource.size[1]):
                for x in range(rgbSource.size[0]):
                    r,g,b,a = rgbSource.getpixel((x,y))
                    if funcAlpha((x,y)):
                        a = 255
                    else:
                        a = 0
                    rgbSource.putpixel((x,y), (r,g,b,a))
        return rgbSource

    def getQuantizedImage(self) -> Optional[ImageType]:
        """Returns a copy of the paletted image. This refers to the quantized image, so approximates the appearance on NDS. Transparency is pre-applied.

        Modifications made to the returned image will not affect the internal image. If this background has no configured image, None will be returned.

        Returns:
            Optional[ImageType]: Quantized image, or None if this background has not been configured.
        """
        if self.__imageRaw == None:
            return None
        quantized = self.__getQuantized()
        if quantized == None:
            return Image.new("RGBA", (256,192), (255,255,255,0))
        else:
            rgbSource = quantized.convert("RGBA")
            if self.__imageAlpha != None:
                funcAlpha = funcRejectPixelByThresholdingAlpha(self.__imageAlpha)
                for y in range(rgbSource.size[1]):
                    for x in range(rgbSource.size[0]):
                        r,g,b,a = rgbSource.getpixel((x,y))
                        if funcAlpha((x,y)):
                            a = 255
                        else:
                            a = 0
                        rgbSource.putpixel((x,y), (r,g,b,a))
            return rgbSource

    def toBytes(self) -> Optional[bytearray]:
        """Converts this background to the ARC format. Quantization will be applied to the source image if not completed already.

        If this background has not been configured, None will be returned.

        Returns:
            Optional[bytearray]: Decompressed ARC bytearray if image is available, else None.
        """
        quantized = self.__getQuantized()
        
        exportImage : ImageType = None
        
        if quantized == None:
            if self.__imageRaw != None:
                exportImage = Image.new("P", (256,192), 0)
                exportImage.putpalette([EditableBackground.DEFAULT_COLOR_ALPHA[0], EditableBackground.DEFAULT_COLOR_ALPHA[1], EditableBackground.DEFAULT_COLOR_ALPHA[2]])
            else:
                return None
        else:
            exportImage = quantized.copy()
            funcAlpha = funcRejectPixelByThresholdingAlpha(self.__imageAlpha)
            # TODO - Remove unused colors
            for y in range(exportImage.size[1]):
                for x in range(exportImage.size[0]):
                    if funcAlpha == None or funcAlpha((x,y)):
                        exportImage.putpixel((x,y), exportImage.getpixel((x,y)) + 1)
                    else:
                        exportImage.putpixel((x,y), 0)
        
            def getTransparencyColor(exportImage : ImageType) -> Tuple[int,int,int]:

                def getUnusedColor() -> Tuple[int,int,int]:
                    
                    def getRandom5Bit() -> int:
                        return randint(0, 31)
                    
                    def scaleColor(color : Tuple[int,int,int]) -> Tuple[int,int,int]:
                        return (int(round(color[0] * (255/31))), int(round(color[1] * (255/31))), int(round(color[2] * (255/31))))
                    
                    color = scaleColor((getRandom5Bit(), getRandom5Bit(), getRandom5Bit()))
                    while color in palette:
                        color = scaleColor((getRandom5Bit(), getRandom5Bit(), getRandom5Bit()))
                    return color

                rawPalette = []

                imagePalette = exportImage.getpalette()
                for idxColor in range(len(imagePalette) // 3):
                    idxColor = idxColor * 3
                    rawPalette.append((imagePalette[idxColor], imagePalette[idxColor + 1], imagePalette[idxColor + 2]))
                
                if EditableBackground.DEFAULT_COLOR_ALPHA not in rawPalette:
                    return EditableBackground.DEFAULT_COLOR_ALPHA
                return getUnusedColor()

            colorTransparency = getTransparencyColor(exportImage)
            newPalette = []
            for color in colorTransparency:
                newPalette.append(color)
            for color in exportImage.getpalette()[:len(self.__palette) * 3]:
                newPalette.append(color)
            exportImage.putpalette(newPalette)

        workingImage = TiledImageHandler()
        padWidth, padHeight = workingImage.imageToTiles(exportImage)

        palette = workingImage.getPalette()
        tiles = workingImage.getTiles()
        tileMap = workingImage.getTileMap()

        writer = BinaryWriter()
        writer.writeU32(len(palette))
        for r,g,b in palette:
            writer.writeU16(getPackedColourFromRgb888(r,g,b))
        
        writer.writeU32(len(tiles))
        for tile in tiles:
            writer.write(tile.toBytes(8))

        writer.writeIntList([padWidth // 8, padHeight // 8], 2)
        for indexTile in range(len(tileMap)):
            writer.writeU16(tileMap[indexTile])

        return writer.data