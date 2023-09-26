from enum import Enum

ENCODING_DEFAULT_STRING     = 'shift-jis'
ENCODING_LAYTON_3_STRING    = 'cp932'

DICT_BOOLEAN_TO_PYTHON = {"false"   :False,
                          "true"    :True}
DICT_PYTHON_TO_BOOLEAN = {False:    "false",
                          True      :"true"}

class TYPE_OPERANDS(Enum):
    INT_SIGNED  = 1
    FLOAT       = 2
    STRING      = 3
    FLAGS       = 4
    OFFSET_A    = 6
    OFFSET_B    = 7