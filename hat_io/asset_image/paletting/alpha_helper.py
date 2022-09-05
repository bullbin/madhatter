from typing import Optional, Callable, Tuple
from PIL.Image import Image as ImageType

def funcRejectPixelByThresholdingAlpha(alphaChannel : Optional[ImageType], threshold : int = 127) -> Optional[Callable[[Tuple[int,int]], bool]]:
    if alphaChannel != None:
        def funcThresholdAlpha(pos : Tuple[int,int]) -> bool:
            return alphaChannel.getpixel(pos) > threshold
        return funcThresholdAlpha
    return None