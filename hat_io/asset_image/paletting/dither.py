from typing import Optional, Tuple, Callable
import numpy as np

def _bypassRejection(coord : Tuple[int,int]) -> bool:
    return False

def _applyError(image : np.ndarray, error : np.ndarray, coord : Tuple[int,int], coefficient : float, funcRejectPixel : Callable[[Tuple[int,int]], bool]):
    if 0 <= coord[0] < image.shape[1] and 0 <= coord[1] < image.shape[0]:
        if not(funcRejectPixel(coord)):
            scaled = error * coefficient
            pixel = image[coord[1], coord[0]]
            image[coord[1], coord[0]] = pixel + scaled

def distributeErrorFloydSteinberg(image : np.ndarray, center : Tuple[int,int], error : np.ndarray, funcRejectPixel : Callable[[Tuple[int,int]], bool]):
    _applyError(image, error, (center[0] + 1, center[1]    ), 7/16, funcRejectPixel)
    _applyError(image, error, (center[0] - 1, center[1] + 1), 3/16, funcRejectPixel)
    _applyError(image, error, (center[0]    , center[1] + 1), 5/16, funcRejectPixel)
    _applyError(image, error, (center[0] + 1, center[1] + 1), 1/16, funcRejectPixel)

def distributeErrorAtkinson(image : np.ndarray, center : Tuple[int,int], error : np.ndarray, funcRejectPixel : Callable[[Tuple[int,int]], bool]):
    _applyError(image, error, (center[0] + 1, center[1]    ), 1/8, funcRejectPixel)
    _applyError(image, error, (center[0] + 2, center[1]    ), 1/8, funcRejectPixel)

    _applyError(image, error, (center[0] - 1, center[1] + 1), 1/8, funcRejectPixel)
    _applyError(image, error, (center[0]    , center[1] + 1), 1/8, funcRejectPixel)
    _applyError(image, error, (center[0] + 1, center[1] + 1), 1/8, funcRejectPixel)

    _applyError(image, error, (center[0]    , center[1] + 2), 1/8, funcRejectPixel)

def errorCorrectionDithering(image : np.ndarray, funcGetClosestColor : Callable[[np.ndarray], np.ndarray], funcDistributeError : Callable[[np.ndarray, Tuple[int,int], np.ndarray, Callable[[Tuple[int,int]], bool]], None], funcRejectPixel : Callable[[Tuple[int,int]], bool]):
    
    image = image.astype(np.float32)

    for y in range(image.shape[0]):
        for x in range(image.shape[1]):
            oldPixel = image[y,x].copy()
            newPixel = funcGetClosestColor(oldPixel)
            image[y,x] = newPixel
            error = oldPixel - newPixel
            funcDistributeError(image, (x,y), error,funcRejectPixel)
    
    return image

def floydSteinbergDither(image : np.ndarray, funcGetClosestColor : Callable[[np.ndarray], np.ndarray], funcRejectPixel : Optional[Callable[[Tuple[int,int]], bool]] = None) -> np.ndarray:
    """Applies Floyd-Steinberg error-diffusion dithering on an input image array. This provides good gradation with medium chance of stray pixels in long gradations.

    Args:
        image (np.ndarray): Input image formatted as array.
        funcGetClosestColor (Callable[[np.ndarray], np.ndarray]): Function to return closest color. Color returned should be in same space (and therefore scale) as image.
        funcRejectPixel (Optional[Callable[[Tuple[int,int]], bool]], optional): Function to prevent dithering at certain pixels. This will set pixels to the closest color and throw away their error if the function returns False. Defaults to None.

    Returns:
        np.ndarray: Output image, dereferenced from original.
    """
    if funcRejectPixel == None:
        funcRejectPixel = _bypassRejection
    return errorCorrectionDithering(image, funcGetClosestColor, distributeErrorFloydSteinberg, funcRejectPixel)

def atkinsonDither(image : np.ndarray, funcGetClosestColor : Callable[[np.ndarray], np.ndarray], funcRejectPixel : Optional[Callable[[Tuple[int,int]], bool]] = None) -> np.ndarray:
    """Applies Atkinson error-diffusion dithering on an input image array. This provides okay gradation with low chance of stray pixels in long gradations.

    Args:
        image (np.ndarray): Input image formatted as array.
        funcGetClosestColor (Callable[[np.ndarray], np.ndarray]): Function to return closest color. Color returned should be in same space (and therefore scale) as image.
        funcRejectPixel (Optional[Callable[[Tuple[int,int]], bool]], optional): Function to prevent dithering at certain pixels. This will set pixels to the closest color and throw away their error if the function returns False. Defaults to None.

    Returns:
        np.ndarray: Output image as array, dereferenced from original.
    """
    if funcRejectPixel == None:
        funcRejectPixel = _bypassRejection
    return errorCorrectionDithering(image, funcGetClosestColor, distributeErrorAtkinson, funcRejectPixel)