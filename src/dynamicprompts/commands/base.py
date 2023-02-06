from __future__ import annotations

from dynamicprompts.enums import SamplingMethod


class Command:
    """Base class for commands."""

    sampling_method: SamplingMethod = SamplingMethod.DEFAULT

    def propagate_sampling_method(
        self,
        sampling_method: SamplingMethod,
    ) -> None:

        if self.sampling_method == SamplingMethod.DEFAULT:
            self.sampling_method = sampling_method
        elif sampling_method.is_nonfinite() and not self.sampling_method.is_nonfinite():
            self.sampling_method = sampling_method
