from typing import Callable, List, Optional, Tuple
from PIL.Image import Image as ImageType
from PIL import Image

import numpy as np

from .dither import atkinsonDither
from .transforms import ColorManagementController, NullColorManagementController, linearToSRgb

def quantize(conversionImage : ImageType, paletteLinRgbEncoded : List[Tuple[int,int,int]],
             colorTransforms : ColorManagementController = NullColorManagementController(), applyPerceptualBias : bool = True,
             funcPixelAllowedError : Optional[Callable[[Tuple[int,int]], bool]] = None,
             ditherFunction : Optional[Callable[[np.ndarray, Callable[[np.ndarray], np.ndarray], Callable[[Tuple[int,int]], bool]], np.ndarray]] = None) -> ImageType:
    """Error-diffusing quantizing function to quantize an image using the provided linear RGB palette.

    Args:
        conversionImage (ImageType): Basis PIL image for quantizing.
        paletteLinRgbEncoded (List[Tuple[int,int,int]]): List of linear RGB tuples for the palette.
        colorTransforms (ColorManagementController, optional): Color transformation controller. Defaults to NullColorManagementController().
        applyPerceptualBias (bool, optional): Adds perceptual biases into the color-comparison function. Can reduce excessive contrast. Defaults to True.
        funcPixelAllowedError (Optional[Callable[[Tuple[int,int]], bool]], optional): Function that returns True if pixel is allowed to be dithered. If not given, all pixels can contribute error. Defaults to None.
        ditherFunction (Optional[Callable[[np.ndarray, Callable[[np.ndarray], np.ndarray], Callable[[Tuple[int,int]], bool]], np.ndarray]], optional): Dither function. If not provided, uses Atkinson's. Defaults to None.

    Returns:
        ImageType: PIL image in paletted mode.
    """

    assert len(paletteLinRgbEncoded) > 0
    assert conversionImage.mode == "RGB"

    if ditherFunction == None:
        ditherFunction = atkinsonDither

    if funcPixelAllowedError == None:
        def rejectAlphaMaskPixels(coord : Tuple) -> bool:
            return False
    else:
        def rejectAlphaMaskPixels(coord : Tuple) -> bool:
            return not(funcPixelAllowedError(coord))

    paletteNp = np.array(paletteLinRgbEncoded)
    conversionImage = colorTransforms.transToLinear((np.asarray(conversionImage) / 255))

    if applyPerceptualBias:
        # Apply a cheap sRGB-shifted perceptually-adjusted color distance function instead
        # Differences are very small
        # Credit: https://en.wikipedia.org/wiki/Color_difference

        paletteSRgb = linearToSRgb(paletteNp, gamma=colorTransforms.getGamma())
        lowDiffCoeff = np.array([2,4,3])
        highDiffCoeff = np.array([3,4,2])
        
        def getClosestColor(val : np.ndarray) -> np.ndarray:
            val = linearToSRgb(val, gamma=colorTransforms.getGamma())
            deltas = paletteSRgb - val
            deltasSq = np.square(deltas)
            perceptLow = np.sum(deltasSq * lowDiffCoeff, axis=1)
            perceptHigh = np.sum(deltasSq * highDiffCoeff, axis=1)

            averageRed = (paletteSRgb + val)[:, 0]
            averageRed = averageRed / 2

            distances = np.where(averageRed < 0.5, perceptLow, perceptHigh)
            idxSmallest = np.where(distances==np.amin(distances))
            return paletteNp[np.amin(idxSmallest[0])]
    else:
        def getClosestColor(val : np.ndarray) -> np.ndarray:
            distances = np.sum((paletteNp-val)**2,axis=1)
            idxSmallest = np.where(distances==np.amin(distances))
            return paletteNp[np.amin(idxSmallest[0])]

    output : np.ndarray = ditherFunction(conversionImage, getClosestColor, rejectAlphaMaskPixels)
    newImage = Image.new("P", (output.shape[1], output.shape[0]))

    # TODO - Do this in numpy. Not too slow but should be possible
    #        There seems to be some precision loss that is making this harder though
    def getClosestColorIdx(val : np.ndarray) -> int:
        distances = np.sum((paletteNp-val)**2,axis=1)
        idxSmallest = np.amin(np.where(distances==np.amin(distances))[0])
        return idxSmallest

    for y in range(output.shape[0]):
        for x in range(output.shape[1]):
            pixel = int(getClosestColorIdx(output[y,x]))
            newImage.putpixel((x,y), pixel)

    pilPalette = []
    for color in paletteNp:
        outColor = np.round(colorTransforms.transFromLinear(color) * 255)
        pilPalette.append(int(outColor[0]))
        pilPalette.append(int(outColor[1]))
        pilPalette.append(int(outColor[2]))
    while len(pilPalette) < 768:
        pilPalette.append(pilPalette[-3])
    
    newImage.putpalette(pilPalette)
    newImage.info["srgb"] = 0
    newImage.info["gamma"] = colorTransforms.getGamma()
    return newImage