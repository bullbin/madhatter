from typing import Optional, Callable, Tuple
from PIL.Image import Image as ImageType

def funcRejectPixelByThresholdingAlpha(alphaChannel : Optional[ImageType], threshold : int = 127) -> Optional[Callable[[Tuple[int,int]], bool]]:
    """Returns a function for alpha thresholding based on the alpha channel. Pixels with alpha above the threshold are considered opaque, so will return True.

    Args:
        alphaChannel (Optional[ImageType]): Alpha channel as image. Should be in L mode or will be rejected.
        threshold (int, optional): Minimum threshold (value itself excluded) where pixels are considered opaque. Defaults to 127.

    Returns:
        Optional[Callable[[Tuple[int,int]], bool]]: Function for alpha rejection. If inputs were invalid, returns None.
    """
    if alphaChannel != None and alphaChannel.mode == "L":
        def funcThresholdAlpha(pos : Tuple[int,int]) -> bool:
            return alphaChannel.getpixel(pos) > threshold
        return funcThresholdAlpha
    return None