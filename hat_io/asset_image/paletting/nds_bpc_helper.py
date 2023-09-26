from typing import Optional, Tuple
import numpy as np
from PIL.Image import Image as ImageType
from PIL import Image
from .dither import floydSteinbergDither
from .const import PREPROCESS_DITHER, PREPROCESS_NONE, PREPROCESS_SCALE

def ditherTo5bpc(image : ImageType, inBpp : int = 8) -> ImageType:

    maxInBpp = (2 ** inBpp) - 1
    max5 = (2 ** 5) - 1

    def getClosest5bitEquivalentColor(val : np.ndarray) -> np.ndarray:
        # Clip input to bounds
        val = np.clip(val, 0, maxInBpp)
        
        # Scale color (non-perceptual)
        val = (val / maxInBpp) * max5
        val = np.round(val)
        val = val * (maxInBpp / max5)
        return val

    # TODO - Atkinson dithering does provide slightly more contrast, although leans closer to banding
    return Image.fromarray(floydSteinbergDither(np.asarray(image).astype(np.float32), getClosest5bitEquivalentColor).astype(np.uint8))

def scale8bpcTo5bpc(image : ImageType) -> ImageType:
    imageArray : np.ndarray = np.asarray(image).astype(np.float32)
    imageArray = np.round((imageArray / 255) * 31)
    imageArray = np.round(imageArray * (255/31))
    return Image.fromarray(imageArray.astype(np.uint8), 'RGB')

def getConversionBasis(colorImage : ImageType, mode : int = PREPROCESS_DITHER,
                       alphaResolveImage : Optional[ImageType] = None, alphaPastePos : Tuple[int,int] = (0,0)) -> Tuple[ImageType, Optional[ImageType]]:
    """Prepare an image for palette creation and quantization. The output is two images, the second being the alpha map for the first.
    The first image is an RGB image with a preprocessing pass applied that changes the performance with the image in future computation.

    PREPROCESS_DITHER offers smoothest gradation and closest color at the cost of grain with smaller palettes.
    
    PREPROCESS_SCALE preserves blocks of color at the cost of poor gradation and banding that can't be resolved with larger palettes.
    
    PREPROCESS_NONE is in between DITHER and SCALE in performance. Gradation performance won't reach DITHER but color block preservation is better.

    Args:
        image (ImageType): Image used for future processing. Mode is RGB.
        mode (int, optional): Preprocess mode constant. Defaults to PREPROCESS_DITHER.

    Returns:
        Tuple[ImageType, Optional[ImageType]]: Preprocessed image and alpha channel if present.
    """
    alphaChannel = None
    if colorImage.mode in ['RGBA', 'LA'] or (colorImage.mode == 'P' and 'transparency' in colorImage.info):
        # Image has transparency, start transparency pathway        
        alphaChannel = colorImage.convert('RGBA').split()[-1]

        if alphaResolveImage != None:
            blend = alphaResolveImage.crop((alphaPastePos[0], alphaPastePos[1], alphaPastePos[0] + colorImage.size[0], alphaPastePos[1] + colorImage.size[1])).convert("RGBA")
            blend.alpha_composite(colorImage, (0,0))
            colorImage = blend
    
    # Alpha of 255 means opaque
    colorImage = colorImage.convert("RGB")

    # TODO - Reject alpha if needed
    if mode == PREPROCESS_DITHER:
        return (ditherTo5bpc(colorImage), alphaChannel)
    elif mode == PREPROCESS_SCALE:
        return (scale8bpcTo5bpc(colorImage), alphaChannel)
    elif mode == PREPROCESS_NONE:
        return (colorImage.copy(), alphaChannel)
    else:
        return (colorImage.copy(), alphaChannel)