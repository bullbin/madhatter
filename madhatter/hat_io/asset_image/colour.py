from .imageConst import IMAGE_FORCE_FULL_RANGE_COLOUR

def getPackedColourFromRgb888(r, g, b):
    if IMAGE_FORCE_FULL_RANGE_COLOUR:
        r = round(r / 255 * 31)
        g = round(g / 255 * 31)
        b = round(b / 255 * 31)
    else:
        r = r >> 3
        g = g >> 3
        b = b >> 3
    return r + (g << 5) + (b << 10)

def getColoursAsListFromReader(reader):
    packedColour = reader.readU16()
    b = ((packedColour >> 10) & 0x1f) / 31
    g = ((packedColour >> 5) & 0x1f) / 31
    r = (packedColour & 0x1f) / 31
    if IMAGE_FORCE_FULL_RANGE_COLOUR:
        return ([int(r * 255), int(g * 255), int(b * 255)])
    return ([int(r * 248), int(g * 248), int(b * 248)])

def getPaletteAsListFromReader(reader, countPalette):
    palette = []
    for _indexColour in range(countPalette):
        palette.extend(getColoursAsListFromReader(reader))
    return palette