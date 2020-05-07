from math import ceil
from . import binary
from .asset import File

CONST_PROCYON_COEF      = [(0,0),
                           (60,0),
                           (115,-52),
                           (98, -55),
                           (122, -60)]
CONST_SIXTY_FOUR_SQUARED = 64 * 64

def flipUnsigned(inInt):
    if inInt & 0x08:
        inInt -= 16
    return inInt

def clamp(n, smallest, largest):
    return max(smallest, min(n, largest))

def decodeProcyon(inData, offset, samplesToDo, history, buffer, bufferSampleIndex):
    
    pos         = int(15 + offset)
    inData.seek(pos)
    header = inData.readInt(1)
    
    header      = header ^ 0x80
    scale       = abs(12 - (header & 0xf))
    coefIndex   = (header >> 4) & 0xf
    hist1       = history[0]
    hist2       = history[1]

    if (coefIndex > 4):
        coefIndex = 0

    coef1, coef2 = CONST_PROCYON_COEF[coefIndex]
    inData.seek(offset)

    for _i in range(samplesToDo // 2):
        sampleByte = inData.readUInt(1) ^ 0x80
        
        msbSample = (sampleByte & 0xf0) >> 4
        lsbSample = sampleByte & 0x0f

        for sample in [lsbSample, msbSample]:
            sample = flipUnsigned(sample) * CONST_SIXTY_FOUR_SQUARED
            sample = sample >> scale

            sample = (hist1 * coef1 + hist2 * coef2 + 32) / 64 + (sample * 64)
            hist2 = hist1
            hist1 = sample

            sample = (sample + 32) / 64
            buffer[bufferSampleIndex]:int = int(clamp(sample, -32768, 32767))
            bufferSampleIndex += 1

    history[0] = hist1
    history[1] = hist2

class MusicSadlAsWave(File):
    def __init__(self):
        File.__init__(self)
    
    def load(self, data):
        reader = binary.BinaryReader(data=data)
        if reader.read(4) == b'sadl':
            reader.seek(0x32)
            countChannels = reader.readUInt(1)
            coding = reader.readUInt(1)
            if coding & 0x06 == 4:
                sampleRate = 32728
            elif coding & 0x06 == 2:
                sampleRate = 16364

            coding = coding & 0xf0
            
            reader.seek(0x40)
            filesize = int.from_bytes(reader.readU4(), byteorder = 'little')
                
            if coding == 0x70:
                print("Unsupport: INT_IMA")
                sampleNumber = int((filesize - 0x100) / countChannels * 2)
                self.data = bytearray(b'')
            else:
                # Procyon
                # Credit : Tinke
                sampleNumber = int((filesize - 0x100) / countChannels / 16 * 30)
                startOffset = 0x100
                sizeBlock = 0x10
                buffer  = []
                hist    = []
                offset  = []

                for chan in range(countChannels):
                    offset.append(int(startOffset + sizeBlock * chan))
                    buffer.append(list([0] * sampleNumber))
                    hist.append(list([0,0]))

                samplesWritten = 0
                maxSplice = ceil(sampleNumber / 30)
                for sampleSpliceIndex in range(maxSplice):
                    samplesToDo = 30
                    if sampleSpliceIndex == maxSplice - 1:
                        samplesToDo = sampleNumber - samplesWritten

                    for chan in range(countChannels):
                        decodeProcyon(data, offset[chan], samplesToDo, hist[chan], buffer[chan], samplesWritten)
                        offset[chan] += int(sizeBlock * countChannels)

                    samplesWritten += samplesToDo

                lengthEncodedData = samplesWritten * countChannels * 2
                lengthWaveData = lengthEncodedData + 36

                self.data = bytearray(b'')
                self.data.extend(b'RIFF')
                self.data.extend(lengthWaveData.to_bytes(4, byteorder = 'little'))
                self.data.extend(b'WAVEfmt \x10\x00\x00\x00\x01\x00')
                self.data.extend(countChannels.to_bytes(2, byteorder = 'little'))
                self.data.extend(sampleRate.to_bytes(4, byteorder = 'little'))
                self.data.extend((sampleRate * 2 * countChannels).to_bytes(4, byteorder = 'little'))
                self.data.extend((countChannels * 2).to_bytes(2, byteorder = 'little'))
                self.data.extend(b'\x10\x00data')
                self.data.extend(lengthEncodedData.to_bytes(4, byteorder = 'little'))
                
                for indexSample in range(samplesWritten):
                    for chan in range(countChannels):
                        self.data.extend(buffer[chan][indexSample].to_bytes(2, byteorder = 'little', signed=True))