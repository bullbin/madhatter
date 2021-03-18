from .templateAction import Action
from .const import *
from ...common import logSevere

# TODO - Maybe implement container system holding all assets to reduce memory consumption on overlap or long computation converting sound files
# Would require each command to poll back the id and type of file required, which could be tedious

class GenericLoadScreenImage(Action):        # TopScreen = LoadSubBg
    def __init__(self, encodedImage, idScreen, layer=3):
        Action.__init__(self)
        self.image = encodedImage
        if idScreen == ID_TOP_SCREEN or idScreen == ID_BOTTOM_SCREEN:
            self.idScreen = idScreen
        else:
            self.idScreen = ID_BOTTOM_SCREEN
            logSevere("GenericLoadScreenImage: Invalid screen ID specified! Defaulting to bottom screen.")
        self.layer = layer

class GenericWait(Action):
    def __init__(self, durationMilliseconds):
        Action.__init__(self)
        self.duration = durationMilliseconds