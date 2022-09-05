# COLOR TRANSFORMS
# Credit : https://stackoverflow.com/questions/39792163/vectorizing-srgb-to-linear-conversion-properly-in-numpy
# NaN protection needed due to k-means not being space-aware
from typing import Callable, Optional
import numpy as np
from PIL.Image import Image as ImageType
from ....common import logSevere

class ColorManagementController():
    def __init__(self, toLinear : Callable[[np.ndarray, float], np.ndarray], fromLinear : Callable[[np.ndarray, float], np.ndarray], gamma : float):
        """Object to store color mapping information.

        Args:
            toLinear (Callable[[np.ndarray, float], np.ndarray]): Function to transform from native RGB to linear RGB space.
            fromLinear (Callable[[np.ndarray, float], np.ndarray]): Function to transform from linear RGB to native RGB space.
            gamma (float): Gamma.
        """
        self.__toLinear = toLinear
        self.fromLinear = fromLinear
        self.__gamma = gamma
    
    def transToLinear(self, val : np.ndarray) -> np.ndarray:
        """Transformation function from native RGB to linear RGB space.

        Args:
            val (np.ndarray): Corrected colors.

        Returns:
            np.ndarray: Linear colors.
        """
        return self.__toLinear(val, self.__gamma)
    
    def transFromLinear(self, val : np.ndarray) -> np.ndarray:
        """Transformation function from linear RGB to corrected RGB space.

        Args:
            val (np.ndarray): Linear colors.

        Returns:
            np.ndarray: Corrected colors.
        """
        return self.fromLinear(val, self.__gamma)
    
    def getGamma(self) -> float:
        """Returns the gamma for the transforms.

        Returns:
            float: Gamma.
        """
        return self.__gamma

class NullColorManagementController(ColorManagementController):
    def __init__(self, gamma : float = 2.2):
        """Object to bypass color mapping transforms.

        Args:
            gamma (float, optional): Gamma override. Defaults to 2.2.
        """
        super().__init__(passthrough, passthrough, gamma)

class SRgbColorManagementController(ColorManagementController):
    def __init__(self, gamma: float = 2.4):
        super().__init__(sRgbToLinear, linearToSRgb, gamma)

def sRgbToLinear(imageArray : np.ndarray, gamma : float = 2.4) -> np.ndarray:
    output = np.where(imageArray >= 0.04045,((imageArray + 0.055) / 1.055) ** gamma, imageArray/12.92)
    return np.where(np.isnan(output), 0, output)

def linearToSRgb(imageArray : np.ndarray, gamma : float = 2.4) -> np.ndarray:
    output = np.where(imageArray < 0.0031308, imageArray * 12.92, 1.055 * (np.power(imageArray, (1.0 / gamma))) - 0.055)
    return np.where(np.isnan(output), 0, output)

def rgbToGammaCorrectedRgb(imageArray : np.ndarray, gamma : float = 2.4) -> np.ndarray:
    output = np.power(imageArray, 1 / gamma)
    return np.where(np.isnan(output), 0, output)

def gammaCorrectedRgbToRgb(imageArray : np.ndarray, gamma : float = 2.4) -> np.ndarray:
    output = np.power(imageArray, gamma)
    return np.where(np.isnan(output), 0, output)

def passthrough(imageArray : np.ndarray, gamma : float = 2.4) -> np.ndarray:
    return imageArray.copy()

def getTransformsForImage(image : ImageType,
                          forceSRgbTransform : bool = False, forceGcRgbTransform : bool =  False, disableTransform : bool = False,
                          overrideGamma : Optional[float] = None) -> ColorManagementController:
    """Returns color management information for the given image. The information tags are decoded for gamma and colorspace.
    Only sRGB and gamma-corrected RGB are supported. If no information is found, the image will be treated as linear RGB with gamma 2.2.

    The priority of overrides is disabled followed by sRGB then gamma-corrected RGB.

    Args:
        image (ImageType): PIL Image to extract information from.
        forceSRgbTransform (bool, optional): Overrides detection to force sRGB transforms. Defaults to False.
        forceGcRgbTransform (bool, optional): Overrides detection to force gamma-correct RGB transforms. Defaults to False.
        disableTransform (bool, optional): Overrides detection to force no transforms. Defaults to False.
        overrideGamma (Optional[float], optional): Overrides detection to change gamma. Defaults to None.

    Returns:
        ColorManagementController: Management object providing color transforms.
    """
    gamma = 2.2
    if overrideGamma != None:
        gamma = overrideGamma
    elif "gamma" in image.info:
        gamma = 1/image.info["gamma"]
    
    if disableTransform:
        return NullColorManagementController(gamma=gamma)
    elif forceSRgbTransform:
        colorConvertForward : Callable[[np.ndarray, float], np.ndarray] = sRgbToLinear
        colorConvertBackward : Callable[[np.ndarray, float], np.ndarray] = linearToSRgb
    else:
        colorConvertForward : Callable[[np.ndarray, float], np.ndarray] = rgbToGammaCorrectedRgb
        colorConvertBackward : Callable[[np.ndarray, float], np.ndarray] = gammaCorrectedRgbToRgb
    
    if not(forceGcRgbTransform) and "srgb" in image.info:
        # What does the sRGB chunk mean here? Do we not do perceptual changes...?
        if image.info["srgb"] != 0:
            logSevere("Unimplemented sRGB:", image.info["srgb"], name="ImgGetTrans")
            colorConvertForward : Callable[[np.ndarray, float], np.ndarray] = sRgbToLinear
            colorConvertBackward : Callable[[np.ndarray, float], np.ndarray] = linearToSRgb
    
    return ColorManagementController(colorConvertForward, colorConvertBackward, gamma)