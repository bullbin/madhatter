from enum import Enum

ENCODING_DEFAULT_STRING     = 'utf-8'
ENCODING_LAYTON_3_STRING    = 'cp932'

class TYPE_OPERANDS(Enum):
    INT_SIGNED  = 1
    FLOAT       = 2
    STRING      = 3
    FLAGS       = 4
    OFFSET_A    = 6
    OFFSET_B    = 7