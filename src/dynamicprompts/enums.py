from enum import Enum


class SamplingMethod(Enum):
    RANDOM = "random"
    COMBINATORIAL = "combinatorial"
    CYCLICAL = "cycle"

    def is_nonfinite(self):
        return self in NON_FINITE_SAMPLING_METHODS


NON_FINITE_SAMPLING_METHODS = {SamplingMethod.RANDOM, SamplingMethod.CYCLICAL}
