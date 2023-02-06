from enum import Enum


class SamplingMethod(Enum):
    RANDOM = "random"
    COMBINATORIAL = "combinatorial"
    CYCLICAL = "cycle"
    DEFAULT = "default"

    def is_nonfinite(self):
        return self in [SamplingMethod.RANDOM, SamplingMethod.CYCLICAL]
