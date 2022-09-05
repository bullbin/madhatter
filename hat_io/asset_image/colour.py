from typing import List, Tuple

def eightToFive(eight):
    return round(eight/255 * 31)

def fiveToEight(five):
    return round(five/31 * 255)

def getPackedColourFromRgb888(r, g, b):
    r = eightToFive(r)
    g = eightToFive(g)
    b = eightToFive(b)
    return r + (g << 5) + (b << 10)

def getColoursAsListFromReader(reader):
    packedColour = reader.readU16()
    b = ((packedColour >> 10) & 0x1f)
    g = ((packedColour >> 5) & 0x1f)
    r = (packedColour & 0x1f)
    return (fiveToEight(r), fiveToEight(g), fiveToEight(b))
    
def getPaletteAsListFromReader(reader, countPalette) -> List[Tuple[int,int,int]]:
    palette = []
    for _indexColour in range(countPalette):
        palette.extend(getColoursAsListFromReader(reader))
    return palette