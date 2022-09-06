from __future__ import annotations

from math import log
from random import randint
from PIL.Image import Image as ImageType
from PIL import Image
from typing import Dict, List, Optional, Tuple
from ..colour import getPackedColourFromRgb888, getPaletteAsListFromReader
from ..tiler import TiledImageHandler
from ...binary import BinaryReader, BinaryWriter
from ..paletting.alpha_helper import funcRejectPixelByThresholdingAlpha
from ..paletting.nds_bpc_helper import getConversionBasis
from ..paletting.paletter import addToPalette, createPaletteFromImages
from ..paletting.quantizer import quantize

from ..paletting.transforms import ColorManagementController, NullColorManagementController, getTransformsForImage
from ....common import logVerbose
from ...const import ENCODING_DEFAULT_STRING

class Keyframe():
    def __init__(self, idxFrame : int, duration : int):
        """Representation for a keyframe in image-based animation.
        Negative values will be replaced with 0.

        Args:
            idxFrame (int): Frame index in main animation asset.
            duration (int): Amount of frames to hold the keyframe (60fps interval).
        """
        if idxFrame < 0:
            self.__idxFrame = 0
        else:
            self.__idxFrame = idxFrame
        if duration < 0:
            self.__duration = 0
        else:
            self.__duration = duration
    
    def setFrame(self, idxFrame : int):
        """Set the index of the image used for this keyframe.
        If the new index is negative, this operation will be skipped.

        Args:
            idxFrame (int): Index of the image.
        """
        if idxFrame < 0:
            return
        self.__idxFrame = idxFrame
    
    def getFrame(self) -> int:
        """Get the index of the image used for this keyframe.

        Returns:
            int: Index of the image.
        """
        return self.__idxFrame
    
    def setDuration(self, duration : int):
        """Set the duration (in frames, under 60fps) that this keyframe will be held for.
        If the new duration is negative, this operation will be skipped.

        Args:
            duration (int): Framecount (60fps)
        """
        if duration < 0:
            return
        self.__duration = duration
    
    def getDuration(self) -> int:
        """Get the duration (in frames, under 60fps) that this keyframe will be held for.

        Returns:
            int: Framecount (60fps)
        """
        return self.__duration

class Animation():
    def __init__(self):
        """Representation for Layton keyframed animations.
        """
        self.__name             : str               = "Create an Animation"
        self.keyframes          : List[Keyframe]    = []
        self.idxSubAnimation    : int               = 0
        self.offsetSubAnimation : Tuple[int,int]    = (0,0)
    
    def setName(self, name : str) -> str:
        """Sets the name of this animation. The name should be able to be stored under shift-jis.

        Args:
            name (str): Name. If over 30 characters long, it will be shortened to the first 30 characters.

        Returns:
            str: Name used for storing.
        """
        # TODO - Test encoding
        if len(name) > 30:
            name = name[:30]
        self.__name = name
    
    def getName(self) -> str:
        """Gets the name of this animation.

        Returns:
            str: Animation name.
        """
        return self.__name
    
class AnimatedEditableImage():
    """Editable representation for ARC and ARJ images. Alternative to madhatter.hat_io.asset_image.AnimatedImage with better usability and API.
    """

    MAX_COLOR_COUNT = 255
    MAX_COLOR_BG = 199
    MAX_COLOR_BGANI = 15

    DEFAULT_COLOR_ALPHA = (0,255,0)

    def __init__(self, maxColors : int = 199):
        """Editable representation for ARC and ARJ images. Alternative to madhatter.hat_io.asset_image.AnimatedImage with better usability and API.

        Args:
            maxColors (int, optional): Max color count. Limited to 199. Defaults to 199.
        """
        self.__maxColors : int = maxColors

        # TODO - Fix paletting operations with mixed color transforms
        # Currently, loaded palettes use the null transform. But if we add another image, it comes with a different transform
        # This means quantizing to a mixed palette, which starts crumbling
        # Currently, we just dispose of transform information altogether. This removes gamma-corrected dithering but ensures
        #     everything works as expected.
        self.__palette                  : List[Tuple[float,float,float]] = []

        self.__frames                   : List[ImageType] = []
        self.__framesQuantizedCache     : List[Optional[ImageType]] = []
        self.__framesColorTransforms    : List[ColorManagementController] = []
        self.__framesAlphaChannel       : List[Optional[ImageType]] = []

        self.__animations   : List[Animation]           = []
        self.__variables    : Dict[str, List[int]]      = {}
        self.__nameSubAnimation : str   = ""
        for index in range(1,17):
            self.__variables["Var%i" % index] = [0,0,0,0,0,0,0,0]
        
        self.__sourceWasArj : bool = False

    def __invalidQuantizedCache(self):
        self.__framesQuantizedCache = []
        for frame in self.__frames:
            self.__framesQuantizedCache.append(None)
        
    def getPalette(self) -> List[Tuple[float,float,float]]:
        """Returns a list of null-transformed tuples representing the colors stored in the palette.
        This list is dereferenced from the internal palette - changes to the output will not affect the image.

        Returns:
            List[Tuple[float,float,float]]: Palette triples under null RGB transform (scaling from [0...255] to [0...1])
        """
        return list(self.__palette)

    def paletteSetOverride(self, overrideLinearPalette : List[Tuple[float,float,float]]):
        """Replaces the internal palette with the given override palette. The input must be in null-transformed RGB space.
        The input will be dereferenced from the internal palette - changes to the list after this method is called will not affect the image.

        If the amount of colors is higher than the max color count for this image, it will be cut.

        Args:
            overrideLinearPalette (List[Tuple[float,float,float]]): List of linear RGB tuples for the palette.
        """
        self.__invalidQuantizedCache()
        self.__palette = list(overrideLinearPalette)
        if len(self.__palette) > self.__maxColors:
            self.__palette = self.__palette[:self.__maxColors]

    def paletteForceRegenerate(self):
        """Force regeneration of the palette for this image.

        The palette will be regenerated using all stored high-quality images against the max color count.
        This method is destructive to the original palette - all images are given equal priority in this process.
        """
        self.__invalidQuantizedCache()
        funcAlpha = []
        for alphaChannel in self.__framesAlphaChannel:
            funcAlpha.append(funcRejectPixelByThresholdingAlpha(alphaChannel))
        self.__palette = createPaletteFromImages(self.__frames, self.__framesColorTransforms, funcAlpha, maxColors=self.__maxColors)
    
    def paletteCullUnused(self):
        """Removes unused colors from the palette. Quantizing operations are not guaranteed to use every color in the palette, so this operation may free space in the palette.

        This operation is non-destructive but will force paletted images to need to be recomputed, which is expensive.
        """
        for idxFrame, quantized in enumerate(self.__framesQuantizedCache):
            if quantized == None:
                self.__getQuantizedFrameNoAlpha(idxFrame)

        usedPaletted : Dict[int, bool] = {}
        for idxColor in range(len(self.__palette)):
            usedPaletted[idxColor] = False

        for quantized, alphaChannel in zip(self.__framesQuantizedCache, self.__framesAlphaChannel):
            thresholdFunc = funcRejectPixelByThresholdingAlpha(alphaChannel)
            for y in range(quantized.size[1]):
                for x in range(quantized.size[0]):
                    if alphaChannel == None or thresholdFunc((x,y)):
                        usedPaletted[quantized.getpixel((x,y))] = True
        
        # TODO - Remap quantized images using palCull. For now, we'll invalidate cache instead
        palCull : Dict[int,int] = {}
        newPal : List[Tuple[float,float,float]] = []
        countReduced : int = 0
        for idxColor in usedPaletted:
            if usedPaletted[idxColor]:
                palCull[idxColor] = len(newPal)
                newPal.append(self.__palette[idxColor])
            else:
                countReduced += 1
        self.__palette = newPal
        self.__invalidQuantizedCache()
        logVerbose("Removed", countReduced, "colors.", name="AeiPalCull")

    def setMaxColorCount(self, countColors : int) -> bool:
        """Sets the maximum permitted palette length.
        
        If the given value is too small to fit the active palette, the palette will be regenerated.

        Args:
            countColors (int): New maximium color count. This should not include the reserved alpha color.

        Returns:
            bool: True if the operation was successful.
        """
        if 0 < countColors <= AnimatedEditableImage.MAX_COLOR_COUNT:
            if countColors >= self.__maxColors or countColors >= len(self.__palette):
                self.__maxColors = countColors
                return True
            self.__maxColors = countColors
            self.paletteForceRegenerate()
            return True
        return False

    def getMaxColorCount(self) -> int:
        """Get the maximum color count for this image.

        Returns:
            int: Maximum color count, not including the alpha transform.
        """
        return self.__maxColors

    def getCountFrames(self) -> int:
        """Get the frame count for this image.

        Returns:
            int: Number of frames in this image.
        """
        return len(self.__frames)

    def addFrameNoQuantizing(self, image : ImageType) -> int:
        """Append an image to the frames currently stored in this animation.
        This action will not change the palette.

        The palette may need to be regenerated manually to get nicer results.

        Args:
            image (ImageType): Image of any format. Alpha will be thresholded out.

        Returns:
            int: Index of new frame.
        """
        output = len(self.__frames)
        convImage, alphaChannel = getConversionBasis(image)
        transform = getTransformsForImage(image)
        self.__frames.append(convImage)
        self.__framesQuantizedCache.append(None)
        self.__framesColorTransforms.append(transform)
        self.__framesAlphaChannel.append(alphaChannel)
        return output

    def addFrame(self, image : ImageType, alphaResolveImage : Optional[ImageType] = None, alphaResolvePos : Tuple[int,int] = (0,0), protectPalette : bool = True) -> int:
        """Append an image to the frames currently stored in this animation.

        Color transformations are currently unsupported so will be dropped.

        This action will cause the palette to change to fit the new image.

        Args:
            image (ImageType): Image of any format. Alpha will be thresholded out.
            alphaResolveImage (Optional[ImageType], optional): Image to paste new image onto for better blending of semi-transparent edges. Defaults to None.
            alphaResolvePos (Tuple[int,int], optional): Place to paste new image onto the resolving image. Defaults to (0,0).
            protectPalette (bool): Will only add colors to the palette even if it means worse quality. Defaults to True.
        
        Returns:
            int: Index of new frame.
        """
        # TODO - Add multiple images variant
        convImage, alphaChannel = getConversionBasis(image, alphaResolveImage=alphaResolveImage, alphaPastePos=alphaResolvePos)
        transform = NullColorManagementController()
        alphaFunc = funcRejectPixelByThresholdingAlpha(alphaChannel)

        funcInternalAlpha = []
        for alp in self.__framesAlphaChannel:
            funcInternalAlpha.append(funcRejectPixelByThresholdingAlpha(alp))

        self.__palette = addToPalette(self.__frames, self.__framesColorTransforms, self.__palette, funcInternalAlpha,
                                      [convImage], [transform], [alphaFunc],
                                      maxColors=self.__maxColors, regenAllImageOnFail=not(protectPalette))
        self.__invalidQuantizedCache()
        output = len(self.__frames)
        self.__frames.append(convImage)
        self.__framesQuantizedCache.append(None)
        self.__framesColorTransforms.append(transform)
        self.__framesAlphaChannel.append(alphaChannel)
        return output
    
    def __applyAlpha(self, image : ImageType, alphaChannel : Optional[ImageType]) -> ImageType:
        if alphaChannel == None:
            return image.copy()
        alphaTest = funcRejectPixelByThresholdingAlpha(alphaChannel)
        image = image.convert("RGBA")
        for y in range(image.size[1]):
            for x in range(image.size[0]):
                if not(alphaTest((x,y))):
                    r,g,b,a = image.getpixel((x,y))
                    image.putpixel((x,y), (r,g,b,0))
        return image

    def __getQuantizedFrameNoAlpha(self, idxFrame : int) -> Optional[ImageType]:
        if 0 <= idxFrame < len(self.__frames):
            quantized = self.__framesQuantizedCache[idxFrame]
            if quantized == None:
                frame = self.__frames[idxFrame]
                transform = self.__framesColorTransforms[idxFrame]
                alphaChannel = self.__framesAlphaChannel[idxFrame]
                alphaFunc = funcRejectPixelByThresholdingAlpha(alphaChannel)
                self.__framesQuantizedCache[idxFrame] = quantize(frame, self.__palette, transform, funcPixelAllowedError=alphaFunc)
            return self.__framesQuantizedCache[idxFrame]
        return None

    def getQuantizedFrame(self, idxFrame : int) -> Optional[ImageType]:
        """Returns a copy of the image as it would appear on export.
        Any actions that change the palette may make the output of this method outdated.

        Args:
            idxFrame (int): Index of the frame to convert.

        Returns:
            Optional[ImageType]: Copy of the paletted version of this frame.
        """
        image = self.__getQuantizedFrameNoAlpha(idxFrame)
        if image == None:
            return None
        return self.__applyAlpha(image, self.__framesAlphaChannel[idxFrame])

    def getRawFrame(self, idxFrame : int) -> Optional[Tuple[ImageType, Optional[ImageType], ColorManagementController]]:
        """Returns a copy of the image as stored internally. This means that colors may exceed the capabilities of the DS.
        Call getQuantizedFrame to see what the frame would look like when exported.

        Args:
            idxFrame (int): Index of the frame to view.

        Returns:
            Optional[Tuple[ImageType, Optional[ImageType], ColorManagementController]]: A copy of the image alongside its alpha channel and color management data.
        """
        if 0 <= idxFrame < len(self.__frames):
            if self.__framesAlphaChannel[idxFrame] == None:
                return (self.__frames[idxFrame].copy(), None, self.__framesColorTransforms[idxFrame])
            return (self.__frames[idxFrame].copy(), self.__framesAlphaChannel[idxFrame].copy(), self.__framesColorTransforms[idxFrame])
        return None

    def getRawFrameAlphaPreintegrated(self, idxFrame : int) -> Optional[Tuple[ImageType, ColorManagementController]]:
        """Returns a copy of the image as stored internally. This means that colors may exceed the capabilities of the DS.

        This function applies the alpha channel to the output.

        Call getQuantizedFrame to see what the frame would look like when exported.

        Args:
            idxFrame (int): Index of the frame to view.

        Returns:
            Optional[Tuple[ImageType, ColorManagementController]]: A copy of the image alongside its color management data.
        """
        rawFrameData = self.getRawFrame(idxFrame)
        if rawFrameData == None:
            return None
        imageRgb, alphaChannel, colorManagement = rawFrameData
        return (self.__applyAlpha(imageRgb, alphaChannel), colorManagement)

    def setRawFrame(self, idxFrame : int, frame : ImageType, alpha : Optional[ImageType]) -> bool:
        """Replace the raw frame at this index with a new frame.
        This action will not update the palette, so is recommended for use only with small changes.
        If the image being replaced is very different to the previous, call paletteForceRegenerate().

        Args:
            idxFrame (int): Index of frame to replace.
            frame (ImageType): Image contents of the frame. This should be preprocessed and in RGB mode.
            alpha (Optional[ImageType]): Alpha channel for the image.

        Returns:
            bool: True if the operation was successful.
        """
        if not(0 <= idxFrame < len(self.__frames)):
            return False
        
        assert frame.mode == "RGB"
        self.__framesQuantizedCache[idxFrame] = None
        self.__frames[idxFrame] = frame
        self.__framesAlphaChannel[idxFrame] = alpha
        self.__framesColorTransforms[idxFrame] = NullColorManagementController()
        return True

    def setFrame(self, idxFrame : int, frame : ImageType, alphaResolveImage : Optional[ImageType] = None, alphaResolvePos : Tuple[int,int] = (0,0)) -> bool:
        """Replace the frame at this index with a new frame.
        This method is will preprocess the image for you. For more control, use setRawFrame.
        This action will not update the palette, so is recommended for use only with small changes.
        If the image being replaced is very different to the previous, call paletteForceRegenerate().

        Args:
            idxFrame (int): Index of frame to replace.
            frame (ImageType): Image contents of the frame. This can be in any mode. Alpha will be thresholded.
            alphaResolveImage (Optional[ImageType], optional): Image to paste new image onto for better blending of semi-transparent edges. Defaults to None.
            alphaResolvePos (Tuple[int,int], optional): Place to paste new image onto the resolving image. Defaults to (0,0).

        Returns:
            bool: True if the operation was successful.
        """
        if not(0 <= idxFrame < len(self.__frames)):
            return False
        
        convImage, alphaChannel = getConversionBasis(frame, alphaResolveImage=alphaResolveImage, alphaPastePos=alphaResolvePos)
        return self.setRawFrame(idxFrame, convImage, alphaChannel)
    
    # TODO - Reorder frame operation (might be difficult with frame 0 behaviours)
    # TODO - Reorder animation operation

    def deleteFrame(self, idxFrame : int, remapDeleted : Optional[int] = None) -> bool:
        """Removes a frame from this image. Animations will be modified to remove the frame as well.
        
        This action does not modify the palette. If the palette feels outdated, force regeneration. Palette culling can be called to remove unused colors after deletion.

        Args:
            idxFrame (int): Index of frame to remove.
            remapDeleted (Optional[int], optional): Frame index to remap references from the delete frame to. Overridden if given reference is improper. Defaults to None.
        
        Returns:
            bool: True if the operation was successful.
        """
        if not(0 <= idxFrame < len(self.__frames)):
            return False
        if remapDeleted != None:
            if not(0 <= remapDeleted < len(self.__frames)):
                remapDeleted = None

        for animation in self.__animations:
            keysToRemove : List[Keyframe] = []
            for keyframe in animation.keyframes:
                if keyframe.getFrame() == idxFrame:
                    keysToRemove.append(keyframe)
                elif keyframe.getFrame() > idxFrame:
                    # Shift frames above the deleted one down
                    keyframe.setFrame(keyframe.getFrame() - 1)
            for keyframe in reversed(keysToRemove):
                if remapDeleted:
                    keyframe.setFrame(remapDeleted)
                else:
                    animation.keyframes.remove(keyframe)

        self.__frames.pop(idxFrame)
        self.__framesAlphaChannel.pop(idxFrame)
        self.__framesColorTransforms.pop(idxFrame)
        self.__framesQuantizedCache.pop(idxFrame)
        return True

    def getAnimationCount(self) -> int:
        """Get the number of animations in this image.

        Returns:
            int: Number of animations.
        """
        return len(self.__animations)
    
    def getAnimationNames(self) -> List[str]:
        """Get the names of the animations in this image. There may be duplicates in a failure case.

        Returns:
            List[str]: List of animation names.
        """
        output = []
        for anim in self.__animations:
            output.append(anim.getName())
        return output

    def getAnimationByName(self, nameAnimation : str) -> Optional[Animation]:
        """Gets the first animation with a matching name.

        Args:
            nameAnimation (str): Name to match.

        Returns:
            Optional[Animation]: Matching animation, or None if not found.
        """
        for animation in self.__animations:
            if animation.getName() == nameAnimation:
                return animation
        return None

    def getAnimationByIndex(self, idxAnimation : int) -> Optional[Animation]:
        """Gets the animation at the given index.

        Args:
            idxAnimation (int): Index to find.

        Returns:
            Optional[Animation]: Matching animation, or None if not found.
        """
        if 0 <= idxAnimation < len(self.__animations):
            return self.__animations[idxAnimation]
        return None

    def ensureAnimations(self, applyExtendedAccuracy : bool = False):
        """Ensure the first animation is null.

        Extended accuracy culls unreachable keyframes. If an animation starts with frame zero, it will not animate so can be culled.

        Args:
            applyExtendedAccuracy (bool, optional): Apply extended accuracy culling. Defaults to False.
        """
        if len(self.__animations) == 0:
            self.__animations.insert(0, Animation())
            self.__animations[0].setName("Create an Animation")
        else:
            # TODO - Test for duplicates
            animNull = self.getAnimationByName("Create an Animation")
            nullAnimationOkay = False
            if animNull.keyframes == []:
                if self.__animations[0] == animNull:
                    nullAnimationOkay = True

            if not(nullAnimationOkay):
                rename = "Create an Animation %i"
                idxRename = 1
                while self.getAnimationByName(rename % idxRename) != None:
                    idxRename += 1
                animNull.setName(rename % idxRename)
                self.__animations.insert(0, Animation())
                self.__animations[0].setName("Create an Animation")
            
            if applyExtendedAccuracy:
                # Animations get culled if they start on the first frame
                for animation in self.__animations:
                    if len(animation.keyframes) > 0:
                        if animation.keyframes[0].getFrame() == 0:
                            animation.keyframes = animation.keyframes[:1]
        
        if self.__nameSubAnimation == "":
            # TODO - Check ranges on types
            for animation in self.__animations:
                animation.idxSubAnimation = 0
                animation.offsetSubAnimation = (0,0)

    def variablesGetNames(self) -> List[str]:
        """Get the names of the variables for this image.

        This list is dereferenced from the original. Changing the names in this list will not affect variable names for this image.

        Returns:
            List[str]: Variable names.
        """
        return list(self.__variables.keys())
    
    def variablesGetContents(self, varName : str) -> List[int]:
        """Get the contents of a variable in this image.
        
        This list is dereferenced from the original. Changing the contents of this list will not affect the contents for that variable.

        Args:
            varName (str): Name of target variable.

        Returns:
            List[int]: Contents for that variable. If the variable is not found, a blank list is returned.
        """
        if varName in self.__variables:
            return list(self.__variables[varName])
        return [0,0,0,0,0,0,0,0]
    
    def variablesGetContentsAtIndex(self, varName : str, index : int) -> int:
        """Get the data for a variable in this image at the specified index.
        
        The output is dereferenced from the original. Changing the output will not affect the contents for that variable.

        Args:
            varName (str): Name of target variable.
            index (int): Index for variable contents.

        Returns:
            int: Contents at that index. If the index or variable is not found, a blank value is returned.
        """
        contents = self.variablesGetContents(varName)
        if 0 <= index < len(contents):
            return contents[index]
        return 0
    
    def variablesSetContents(self, varName : str, contents : List[int]) -> bool:
        """Set the contents of a variable in this image.

        Args:
            varName (str): Name of target variable.
            contents (List[int]): Contents. Should be 8 shorts. Will be shortened if too long.

        Returns:
            bool: True if the operation was successful.
        """
        if varName in self.__variables and len(contents) >= 8:
            # TODO - Check can fit in short
            self.__variables[varName] = list(contents)[:8]
            return True
        return False
    
    def variablesSetContentsAtIndex(self, varName : str, index : int, data : int) -> bool:
        """Set the contents at a particular index for a variable in this image.

        Args:
            varName (str): Name of target variable.
            index (int): Index for variable contents to change.
            data (int): New content. Should be a short.

        Returns:
            bool: True if the operation was successful.
        """
        if varName in self.__variables and 0 <= index < len(self.__variables[varName]):
            # TODO - Check can fit in short
            self.__variables[varName][index] = data
            return True
        return False

    def variablesRename(self, oldName : str, newName : str) -> bool:
        """Renames a variable inside the image. The new variable name cannot be in use.

        Args:
            oldName (str): Variable name to modify.
            newName (str): New variable name. This will be shortened to the first 30 characters.

        Returns:
            bool: True if the operation was successful.
        """
        if oldName == newName:
            return True
        if len(newName) > 30:
            newName = newName[:30]
        if oldName in self.__variables and newName not in self.__variables:
            newVarDict = {}
            for key in self.__variables:
                if key == oldName:
                    newKeyName = newName
                else:
                    newKeyName = key
                newVarDict[newKeyName] = self.__variables[key]
            self.__variables = newVarDict
            return True
        return False

    def variablesReorder(self, newKeyOrder : List[str]) -> bool:
        """Reorders the variables inside this image.

        Args:
            newKeyOrder (List[str]): Ordered list containing the variable names. The list should contain all names in their new order.

        Returns:
            bool: True if the operaiton was successful.
        """
        for key in self.__variables:
            if key not in newKeyOrder:
                return False
        if len(newKeyOrder) != self.__variables:
            return False
        newVarDict = {}
        for keyName in newKeyOrder:
            newVarDict[keyName] = self.__variables[keyName]
        self.__variables = newVarDict
        return True
    
    def variablesReset(self):
        """Clears the contents of the variables back to their default state.
        """
        self.__variables = {}
        for index in range(1,17):
            self.__variables["Var%i" % index] = [0,0,0,0,0,0,0,0]

    def getSubAnimationStubPath(self) -> str:
        """Get the extension path for the subanimation. This path is an extension to /data_lt2/ani/sub/.

        Returns:
            str: Path extension.
        """
        return self.__nameSubAnimation
    
    def setSubAnimationStubPath(self, path : str) -> str:
        """Set the extension path for the subanimation. This path is an extension to /data_lt2/ani/sub/.

        Args:
            path (str): Path extension. This will be shortened if over 128 characters.

        Returns:
            str: Path extension (may be shortened).
        """
        # TODO - Check formatting
        if len(path) > 128:
            path = path[:128]
        self.__nameSubAnimation = path
        return path

    def wasImported(self) -> bool:
        """Check if this animation was created by importing.

        Returns:
            bool: True if the animation was imported.
        """
        return self.__sourceWasArj != None
    
    def wasSourceArj(self) -> bool:
        """Check if this animation was created from an ARJ import. This is only accurate if wasImported is True.

        Returns:
            bool: True if the source animation was from an ARJ. Will be False if either no importing was done or the import source was an ARC.
        """
        return self.__sourceWasArj

    @staticmethod
    def __fromBytesArcArj(data : bytes, isArj : bool = False) -> AnimatedEditableImage:
        # TODO - Rewrite this, ported from old library
        output = AnimatedEditableImage()
        reader = BinaryReader(data=data)

        countFrames = reader.readU16()
        bpp = 2 ** (reader.readU16() - 1)

        if isArj:
            countColors = reader.readU32()

        workingFrames           : List[TiledImageHandler]   = []
        workingFrameResolutions : List[Tuple[int,int]]      = []

        for _indexImage in range(countFrames):
            resolution = (reader.readU16(), reader.readU16())
            countTiles = reader.readU32()
            logVerbose("Add Image", resolution, countTiles, name="ImgImpArc")
            workingImage = TiledImageHandler()
            for _indexTile in range(countTiles):
                if isArj:
                    glb = (reader.readU16(), reader.readU16())
                else:
                    glb = (0,0)

                # TODO - Are tiles written if empty?
                offset = (reader.readU16(), reader.readU16())
                tileRes = (2 ** (3 + reader.readU16()), 2 ** (3 + reader.readU16()))
                workingImage.addTileFromReader(reader, prolongDecoding=True, glb=glb, resolution=tileRes, offset=offset, overrideBpp=bpp, useArjDecoding=isArj)
            
            workingFrames.append(workingImage)
            workingFrameResolutions.append(resolution)

        if not(isArj):
            countColors = reader.readU32()

        paletteRgb = getPaletteAsListFromReader(reader, countColors)
        for indexImage in range(countFrames):
            workingFrames[indexImage].setPaletteFromList(paletteRgb, countColours=countColors)
            
            frame = workingFrames[indexImage].tilesToImage(workingFrameResolutions[indexImage], useOffset=True)
            frameRgb = frame.copy().convert("RGB")
            alpha = Image.new("L", frame.size)
            
            for y in range(frame.size[1]):
                for x in range(frame.size[0]):
                    idxPal = frame.getpixel((x,y))
                    if idxPal == 0:
                        # Transparent
                        frameRgb.putpixel((x,y), (0,0,0))
                        alpha.putpixel((x,y), 0)
                    else:
                        frame.putpixel((x,y), max(0, idxPal - 1))
                        alpha.putpixel((x,y), 255)
            
            frame.putpalette(frame.getpalette()[3:])
            output.__frames.append(frameRgb)
            output.__framesQuantizedCache.append(frame)
            output.__framesColorTransforms.append(NullColorManagementController())
            output.__framesAlphaChannel.append(alpha)
        
        paletteRgb = paletteRgb[3:]
        paletteNull : List[Tuple[float,float,float]] = []

        # Merge palette?
        for idxColor in range(len(paletteRgb) // 3):
            idxColor *= 3
            paletteNull.append((paletteRgb[idxColor] / 255, paletteRgb[idxColor + 1] / 255, paletteRgb[idxColor + 2] / 255))
        
        output.__palette = paletteNull
        output.__maxColors = max(0, countColors - 1)

        reader.seek(30,1)
        countAnims = reader.readU32()
        for _idxAnim in range(countAnims):
            output.__animations.append(Animation())
            output.__animations[-1].setName(reader.readPaddedString(30, ENCODING_DEFAULT_STRING))
        for idxAnim in range(countAnims):
            countFrames = reader.readU32()
            indexKeyframe = reader.readU32List(countFrames)
            durationKeyframe = reader.readU32List(countFrames)
            indexFrame = reader.readU32List(countFrames)
            orderedKeyframes : Dict[int, Keyframe]= {}
            for indexAnimationKeyframe in range(countFrames):
                workingFrame = Keyframe(indexFrame[indexAnimationKeyframe], durationKeyframe[indexAnimationKeyframe])
                orderedKeyframes[indexKeyframe[indexAnimationKeyframe]] = workingFrame
            
            orderedKeyframeIndices = list(orderedKeyframes.keys())
            orderedKeyframeIndices.sort()
            for sortedIndex in orderedKeyframeIndices:
                output.__animations[idxAnim].keyframes.append(orderedKeyframes[sortedIndex])

        if reader.hasDataRemaining() and reader.read(2) == b'\x34\x12':
            # TODO - Improve variable access
            # TODO - Check length of block prior to reading
            output.__variables = {}
            varKeys = []
            for indexData in range(16):
                name = reader.readPaddedString(16, ENCODING_DEFAULT_STRING)
                varKeys.append(name)
                output.__variables[name] = [0,0,0,0,0,0,0,0]
            for indexData in range(8):
                for indexVariable in range(16):
                    output.__variables[varKeys[indexVariable]][indexData] = reader.readS16()
            
            tempOffset = [[],[]]
            for indexDimension in range(2):
                for indexOffset in range(countAnims):
                    tempOffset[indexDimension].append(reader.readS16())
            for indexAnim in range(countAnims):
                output.__animations[indexAnim].offsetSubAnimation = (tempOffset[0][indexAnim], tempOffset[1][indexAnim])
                output.__animations[indexAnim].idxSubAnimation = reader.readUInt(1)
            
            output.__nameSubAnimation = reader.readPaddedString(128, ENCODING_DEFAULT_STRING)
        
        output.__sourceWasArj = isArj
        return output
    
    @staticmethod
    def fromBytesArc(data : bytes) -> AnimatedEditableImage:
        """Creates an image representation from decompressed NDS ARC bytes.
        This method may throw an error if the image is formatted improperly.

        Args:
            data (bytes): Decompressed NDS ARC bytes.

        Returns:
            AnimatedEditableImage: Image representation.
        """
        return AnimatedEditableImage.__fromBytesArcArj(data, isArj = False)

    @staticmethod
    def fromBytesArj(data : bytes) -> AnimatedEditableImage:
        """Creates an image representation from decompressed NDS ARJ bytes.
        This method may throw an error if the image is formatted improperly.

        Args:
            data (bytes): Decompressed NDS ARJ bytes.

        Returns:
            AnimatedEditableImage: Image representation.
        """
        return AnimatedEditableImage.__fromBytesArcArj(data, isArj = True)

    def __toBytesArcArj(self, remapCustomAnimFrames : bool = True, exportVariables : bool = True, isArj : bool = False) -> bytearray:
        # TODO - Rewrite this, currently ported from old library

        def prepareImagingChunk() -> Tuple[List[Tuple[int,int,int]], List[ImageType]]:

            rawPalette = []
            palette = []

            if len(self.__frames) == 0:
                # Might not be needed but doesn't hurt
                return ([AnimatedEditableImage.DEFAULT_COLOR_ALPHA], [])

            def getTransparencyColor(image : ImageType) -> Optional[Tuple[int,int,int]]:

                def getUnusedColor() -> Tuple[int,int,int]:
                    def getRandom5Bit() -> int:
                        return randint(0, 31)
                    
                    def scaleColor(color : Tuple[int,int,int]) -> Tuple[int,int,int]:
                        return (int(round(color[0] * (255/31))), int(round(color[1] * (255/31))), int(round(color[2] * (255/31))))
                    
                    color = scaleColor((getRandom5Bit(), getRandom5Bit(), getRandom5Bit()))
                    while color in palette:
                        color = scaleColor((getRandom5Bit(), getRandom5Bit(), getRandom5Bit()))
                    return color

                imagePalette = image.getpalette()
                for idxColor in range(len(imagePalette) // 3):
                    idxColor = idxColor * 3
                    rawPalette.append((imagePalette[idxColor], imagePalette[idxColor + 1], imagePalette[idxColor + 2]))
                
                if AnimatedEditableImage.DEFAULT_COLOR_ALPHA not in rawPalette:
                    return AnimatedEditableImage.DEFAULT_COLOR_ALPHA
                return getUnusedColor()

            # TODO - Rework section. Color rejection can move to palette culling method and transparency color fetching needs to happen after culling
            colorTrans = getTransparencyColor(self.__getQuantizedFrameNoAlpha(0))
            palette.append(colorTrans)
            paletteMap : Dict[int,int] = {}
            outputImages : List[ImageType] = []

            # Quantize remaining frames
            for idxFrame, alphaChannel in zip(range(len(self.__frames)), self.__framesAlphaChannel):

                funcCheckAlpha = funcRejectPixelByThresholdingAlpha(alphaChannel)
                image = self.__getQuantizedFrameNoAlpha(idxFrame).copy()

                for y in range(image.size[1]):
                    for x in range(image.size[0]):
                        idxUsed = image.getpixel((x,y))
                        if funcCheckAlpha == None or funcCheckAlpha((x,y)):
                            if idxUsed not in paletteMap:
                                paletteMap[idxUsed] = len(palette)
                                palette.append(rawPalette[idxUsed])
                            image.putpixel((x,y), paletteMap[idxUsed])
                        else:
                            image.putpixel((x,y), 0)

                outputImages.append(image)
            
            pilPalette = []
            for color in palette:
                for val in color:
                    pilPalette.append(val)
            for image in outputImages:
                image.putpalette(pilPalette)

            return (palette, outputImages)

        self.ensureAnimations()

        writer = BinaryWriter()

        rgbPalette, images = prepareImagingChunk()
        packedImages : List[TiledImageHandler]  = []
        packedDimensions : List[Tuple[int,int]] = []

        # Prepare everything
        for indexImage, image in enumerate(images):
            workingImage = TiledImageHandler()
            width, height = workingImage.imageToTiles(image, useOffset=True)
            packedImages.append(workingImage)
            packedDimensions.append((width,height))

        writer.writeU16(len(images))
        if isArj:
            outputBpp = 8
        else:
            outputBpp = 4
            for image in packedImages:
                outputBpp = max(image.getBpp(), outputBpp)

        encodedBpp = int(log(outputBpp, 2) + 1)
        writer.writeU16(encodedBpp)

        if isArj:
            writer.writeU32(len(rgbPalette))

        for indexImage, image in enumerate(packedImages):
            width, height = packedDimensions[indexImage]
            writer.writeU16(width)
            writer.writeU16(height)
            writer.writeU32(len(image.getTiles()))
            for tile in image.getTiles():       # TODO : Optimisation, tiles can be up to 128x128 which can reduce header overhead
                if isArj:
                    glbX, glbY = tile.glb
                    writer.writeU16(glbX)
                    writer.writeU16(glbY)
                
                offsetX, offsetY = tile.offset
                writer.writeU16(offsetX)
                writer.writeU16(offsetY)
                tileX, tileY = tile.image.size
                writer.writeU16(int(log(tileX, 2) - 3))
                writer.writeU16(int(log(tileY, 2) - 3))
                writer.write(tile.toBytes(outputBpp, isArj=isArj))
        
        if not(isArj):
            writer.writeU32(len(rgbPalette))

        for r,g,b in rgbPalette:
            writer.writeU16(getPackedColourFromRgb888(r,g,b))
        writer.pad(30)

        writer.writeU32(len(self.__animations))
        for anim in self.__animations:
            writer.writePaddedString(anim.getName(), 30, 'shift-jis')

        for anim in self.__animations:
            writer.writeU32(len(anim.keyframes))
            # TODO - Fix this... for now we'll just rearrange...
            if remapCustomAnimFrames:
                for indexShifted in range(len(anim.keyframes)):
                    indexShifted = (indexShifted + 1) % len(anim.keyframes)
                    writer.writeU32(indexShifted)
                for indexKeyframe, _keyframe in enumerate(anim.keyframes):
                    indexShifted = (indexKeyframe + 1) % len(anim.keyframes)
                    writer.writeU32(anim.keyframes[indexShifted].getDuration())
                for indexKeyframe, _keyframe in enumerate(anim.keyframes):
                    indexShifted = (indexKeyframe + 1) % len(anim.keyframes)
                    writer.writeU32(anim.keyframes[indexShifted].getFrame())
            else:
                for indexShifted in range(len(anim.keyframes)):
                    writer.writeU32(indexShifted)
                for keyframe in anim.keyframes:
                    writer.writeU32(keyframe.getDuration())
                for keyframe in anim.keyframes:
                    writer.writeU32(keyframe.getFrame())
        
        if exportVariables:
            writer.write(b'\x34\x12')
            for variableName in self.__variables:
                writer.writePaddedString(variableName, 16, ENCODING_DEFAULT_STRING)

            for indexData in range(8):
                for variableName in self.__variables:
                    writer.writeInt(self.__variables[variableName][indexData], 2, signed=True)
            

            nameSubAnimation = self.__nameSubAnimation
            if isArj:
                nameSubAnimation = ""

            if nameSubAnimation != "":
                for anim in self.__animations:
                    writer.writeS16(anim.offsetSubAnimation[0])
                for anim in self.__animations:
                    writer.writeS16(anim.offsetSubAnimation[1])
                for anim in self.__animations:
                    writer.writeInt(anim.idxSubAnimation, 1)
            else:
                for anim in self.__animations:
                    writer.pad(5)
            writer.writePaddedString(nameSubAnimation, 128, ENCODING_DEFAULT_STRING)

        return writer.data
    
    def toBytesArc(self, remapCustomAnimFrames : bool = True, exportVariables : bool = True) -> bytearray:
        """Converts this image into an NDS ARC representation.

        Args:
            remapCustomAnimFrames (bool, optional): Remaps animations to avoid frame sticking. Defaults to True.
            exportVariables (bool, optional): Exports variable block. Not part of LAYTON1, but used in LAYTON2. Defaults to True.

        Returns:
            bytearray: Decompressed ARC image bytes.
        """
        return self.__toBytesArcArj(remapCustomAnimFrames=remapCustomAnimFrames, exportVariables=exportVariables, isArj=False)
    
    def toBytesArj(self, remapCustomAnimFrames : bool = True, exportVariables : bool = True) -> bytearray:
        """Converts this image into an NDS ARJ representation.

        Args:
            remapCustomAnimFrames (bool, optional): Remaps animations to avoid frame sticking. Defaults to True.
            exportVariables (bool, optional): Exports variable block. Not part of LAYTON1, but used in LAYTON2. Defaults to True.

        Returns:
            bytearray: Decompressed ARJ image bytes.
        """
        return self.__toBytesArcArj(remapCustomAnimFrames=remapCustomAnimFrames, exportVariables=exportVariables, isArj=True)