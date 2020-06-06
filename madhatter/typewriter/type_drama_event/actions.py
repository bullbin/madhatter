from .const import *
from ..type_common.templateAction import Action
from ...common import logSevere

class DramaActionFade(Action):
    def __init__(self, mode, durationMilliseconds=0):
        Action.__init__(self)
        if mode == MODE_FADE_IN or mode == MODE_FADE_OUT:
            self.mode = mode
        else:
            self.mode = MODE_FADE_IN
            logSevere("DramaActionError: Unknown fade mode, defaulting to fade in!")
        self.duration = durationMilliseconds

class DramaActionWait(Action):
    def __init__(self, durationMilliseconds):
        Action.__init__(self)
        self.duration = durationMilliseconds

class DramaActionTalk(Action):
    def __init__(self, text):
        Action.__init__(self)
        self.text = text
        self.animOnStart    = None
        self.animOnEnd      = None
        self.idVoiceLine    = None  # Maybe change to file holding raw and converted version
        self.idCharacter    = None  # Ditto

class DramaActionPopup():
    pass

class DramaActionCharacter():
    pass