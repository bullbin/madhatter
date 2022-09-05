from typing import List, Optional, Callable, Tuple
from PIL.Image import Image as ImageType
from PIL import Image
import numpy as np

from sklearn.cluster import KMeans, MiniBatchKMeans
from sklearn.utils import shuffle

from .transforms import ColorManagementController, NullColorManagementController
from ....common import logSevere

def encodedPaletteToRgb(palette : List[Tuple[float,float,float]], colorConvertBackward : Callable[[np.ndarray, float], np.ndarray], gamma : float) -> List[Tuple[int,int,int]]:
    output = []
    for idxPal, pal in enumerate(palette):
        pal = colorConvertBackward(pal, gamma=gamma)
        # Convert back to 8-bit and release from color transform
        r,g,b = pal
        output.append((round(r * 255), round(g * 255), round(b * 255)))
    return output

def generate5BitEncodedPalette(image : ImageType, 
                               colorTransforms : ColorManagementController = NullColorManagementController(),
                               funcPixelAllowedInPalette : Optional[Callable[[Tuple[int,int]], bool]] = None,
                               maxColors : int = 199,
                               fastKMeans : bool = True,
                               kMeansSamples : int = 25000,
                               seed : int = 1,
                               thresholdCloseColors : Optional[float] = 0.0005) -> List[Tuple[float,float,float]]:
    """Function to generate a 5-bit compatible palette from the given image. K-means clustering is used for palette extraction. The output palette has been scaled by 255/31.

    An optional thresholding function is given to reduce the amount of colors output from the algorithm. This is enabled by default and collapses close colors into one by picking the first of the cluster.
    The quality loss from this is subtle to inperceptible at low values. At high values, compression can be extreme. This is not intended for palette reduction, just palette optimization.
    
    For reducing colors, first reduce maxColors to the desired amount to tune the k-means output. Slight reductions can then be made with thresholding.

    Args:
        image (ImageType): PIL image to use for palette generation. This should be in 8bpc RGB format without any alpha.
        colorTransforms (ColorManagementController, optional): Color transformation manager used to shift color space. Defaults to NullColorManagementController().
        funcPixelAllowedInPalette (Optional[Callable[[Tuple[int,int]], bool]], optional): Function to exclude pixels at locations from generation. If not provided, all pixels can contribute. Defaults to None.
        maxColors (int, optional): Maximum length for the palette. Defaults to 199.
        fastKMeans (bool, optional): Uses mini-batched k-means for large speed increase at slight cost in optimality. Defaults to True.
        kMeansSamples (int, optional): Number of samples to be used in clustering. Smaller values are faster. Defaults to 25000.
        seed (int, optional): Random seed. Defaults to 1.
        thresholdCloseColors (Optional[float], optional): Compression distance to group close colors into one. If none, no compression is applied. Defaults to 0.0005, which safely reduces colors without much loss.

    Returns:
        List[Tuple[float,float,float]]: List of linear RGB tuples for use as palette.
    """
    assert image.mode == "RGB"

    # Reshape and run k-means in RGB space to get initial palette
    # This is expensive!
    imageReducedDepth : np.ndarray = colorTransforms.transToLinear((np.asarray(image) / 255))
    
    if funcPixelAllowedInPalette == None:
        kmeansInput = imageReducedDepth.reshape(-1, 3)
    else:
        safeToSample = []
        for y in range(imageReducedDepth.shape[0]):
            for x in range(imageReducedDepth.shape[1]):
                if funcPixelAllowedInPalette((x,y)):
                    safeToSample.append(imageReducedDepth[y][x])
        
        assert len(safeToSample) > 0
        kmeansInput = np.array(safeToSample)
    
    maxColors = min(maxColors, kmeansInput.shape[0])
    kmeansInput = shuffle(kmeansInput, random_state=seed, n_samples=min(kMeansSamples, kmeansInput.shape[0]))
    # kMeansSamples = min(kMeansSamples)
    if fastKMeans:
        # Don't use shuffling - quality degradation begins to get too extreme
        kmeans = MiniBatchKMeans(n_clusters=maxColors, random_state=seed, batch_size=4096).fit(kmeansInput)
    else:
        # Reducing sample count gives a huge speed increase at a small cost to palette (with high sample count)
        kmeans = KMeans(n_clusters=maxColors, random_state=seed).fit(kmeansInput)
    centroids = kmeans.cluster_centers_

    # Remove duplicates
    palette : List[Tuple[int,int,int]] = []
    for val in centroids:
        val = colorTransforms.transFromLinear(val)
        # Range is 0 to 1, but apply 5bit RGB clamping now
        val = (np.round(val * 31)) / 31
        val = colorTransforms.transToLinear(val)
        
        val = (val[0], val[1], val[2])
        if val not in palette:
            palette.append(val)

    # Note : Palette is linearised 5bpc palette colors
    assert len(palette) > 0
    
    def getDistanceBetweenValues(val0 : Tuple[int,int,int], val1 : Tuple[int,int,int]) -> float:
        total = 0
        for item0, item1 in zip(val0, val1):
            total += ((item0 - item1) ** 2)
        return total

    # We can apply color reduction by finding close colors and removing them
    if thresholdCloseColors != None:
        # Gamma correction - 0.01 is okay, but unideal. 0.005 is acceptable with some degradation. 0.001 provides good quality with minimal degradation.
        # This value is seemingly dependent on applied correction model...
        # TODO - Average
        hasReduced = True
        lenOld = len(palette)
        while hasReduced:
            hasReduced = False
            for idxColor, color in enumerate(palette):
                others = palette[:idxColor] + palette[idxColor + 1:]
                toRemove = []
                for altColor in others:
                    if getDistanceBetweenValues(color, altColor) <= thresholdCloseColors:
                        toRemove.append(altColor)
                if len(toRemove) > 0:
                    for item in toRemove:
                        palette.remove(item)
                    hasReduced = True
                    break
        logSevere("Compressed palette from", lenOld, "to", len(palette), name="Paletter")

    return palette

def addToPalette(currentImages : List[ImageType], currentTransforms : List[ColorManagementController], currentPalette : List[Tuple[float,float,float]],
                 currentFuncPixelAllowedInPalette : List[Optional[Callable[[Tuple[int,int]], bool]]], 
                 imagesToAdd : List[ImageType], imageTransforms : List[ColorManagementController],
                 addFuncPixelAllowedInPalette : List[Optional[Callable[[Tuple[int,int]], bool]]],
                 errorThreshold : float = 0.005, maxColors : int = 199,
                 regenAllImageOnFail : bool = True) -> List[Tuple[float,float,float]]:
    
    assert len(currentImages) == len(currentTransforms) == len(currentFuncPixelAllowedInPalette)
    assert len(imagesToAdd) == len(imageTransforms) == len(addFuncPixelAllowedInPalette)

    paletteNumpy = np.array(currentPalette)
    # TODO - Unify perceptual version of this
    def getClosestColor(paletteNumpy : np.ndarray, val : np.ndarray) -> Tuple[float, np.ndarray]:
        distances = np.sum((paletteNumpy-val)**2,axis=1)
        idxSmallest = np.where(distances==np.amin(distances))
        outIdx = np.amin(idxSmallest[0])
        return (distances[outIdx], paletteNumpy[outIdx])
    
    # TODO - Conversion between color spaces to enable this properly
    logSevere("Color quality loss likely - multiple color mappings detected!", name="AddToPaletter")
    unifiedColorControl = NullColorManagementController()

    # Generate a list of all pixels which are not close enough to the current palette and need new colors
    erroneousPixelsSRgb : List[np.ndarray] = []
    for image, transform, isPermitted in zip(imagesToAdd, imageTransforms, addFuncPixelAllowedInPalette):
        assert image.mode == "RGB"
        imageReducedDepth : np.ndarray = transform.transToLinear((np.asarray(image) / 255))
        for y in range(image.size[1]):
            for x in range(image.size[0]):
                if isPermitted == None or isPermitted((x,y)):
                    color = imageReducedDepth[y,x]
                    if len(currentPalette) == 0:
                        erroneousPixelsSRgb.append(unifiedColorControl.transFromLinear(color))
                    else:
                        distance, _closest = getClosestColor(paletteNumpy, color)
                        if distance >= errorThreshold:
                            erroneousPixelsSRgb.append(unifiedColorControl.transFromLinear(color))
    
    if len(erroneousPixelsSRgb) == 0:
        return currentPalette
    else:
        logSevere("Repaletting for", len(erroneousPixelsSRgb), "bad pixels...", name="AddToPaletter")
    
    colorsRemaining = maxColors - len(currentPalette)

    # If we don't have colors remaining, we need to deal with this failure case
    if colorsRemaining == 0:
        # If we're permitting all images to be regenerated, try that
        if regenAllImageOnFail:
            # Return one iteration of the algorithm but give up if we can't reduce error far enough
            return addToPalette([], [], [], [], currentImages + imagesToAdd, currentTransforms + imageTransforms,
                                currentFuncPixelAllowedInPalette + addFuncPixelAllowedInPalette,
                                errorThreshold=errorThreshold, maxColors=maxColors, regenAllImageOnFail=False)
        # Else, give up and return the input palette
        else:
            return currentPalette
    
    # If we do have some colors remaining, try quantizing
    paletteImage = Image.new("RGB", (len(erroneousPixelsSRgb), 1))
    for idxColor, color in enumerate(erroneousPixelsSRgb):
        color = np.round(color * 255).astype(np.uint8)
        paletteImage.putpixel((idxColor,0), (int(color[0]), int(color[1]), int(color[2])))
    
    # Get our new palette and calculate error
    newPalette = generate5BitEncodedPalette(paletteImage, colorTransforms=unifiedColorControl, maxColors=colorsRemaining)
    paletteNumpy = np.array(newPalette)

    maxDistance = 0
    failed = False
    for color in erroneousPixelsSRgb:
        color = unifiedColorControl.transToLinear(color)
        distance, _closest = getClosestColor(paletteNumpy, color)
        if distance > errorThreshold:
            maxDistance = max(maxDistance, distance)
            failed = True
            break
    
    if failed:
        logSevere("Initial pass failed with distance", maxDistance, "generating", len(newPalette), "colors!", name="AddToPaletter")
        if regenAllImageOnFail:
            # Return one iteration of the algorithm but give up if we can't reduce error far enough
            return addToPalette([], [], [], [], currentImages + imagesToAdd, currentTransforms + imageTransforms,
                                currentFuncPixelAllowedInPalette + addFuncPixelAllowedInPalette,
                                errorThreshold=errorThreshold, maxColors=maxColors, regenAllImageOnFail=False)

    # Return the new palette. If we did fail, don't waste the work
    return currentPalette + newPalette

def createPaletteFromImages(images : List[ImageType], transforms : List[ColorManagementController], funcPixelAllowedInPalette : List[Optional[Callable[[Tuple[int,int]], bool]]],
                            maxColors : int = 199):
    return addToPalette([], [], [], [], images, transforms, funcPixelAllowedInPalette, maxColors=maxColors, regenAllImageOnFail=False)