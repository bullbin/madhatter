def log(*args, **kwargs):
    print(*args, **kwargs)
        
def logSevere(*args, **kwargs):
    print(*args, **kwargs)

class Rect():
    def __init__(self,x,y,width,height):
        self.pos = (x,y)
        self.dimensions = (width,height)