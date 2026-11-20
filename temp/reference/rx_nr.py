"""Reference model for the NR smoother in PE1NNZ uSDX slow_dsp()."""

from dataclasses import dataclass


def trunc_div(numerator: int, denominator: int) -> int:
    """C/C++ signed integer division, truncating toward zero."""
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    if numerator >= 0:
        return numerator // denominator
    return -((-numerator) // denominator)


@dataclass
class RxNrState:
    """Persistent state of process_nr(); one state is shared by all NR levels."""

    ea1: int = 0

    def push(self, sample: int, nr: int) -> int:
        """Apply the selected NR level to one slow_dsp sample.

        nr=0 means the caller's bypass path and returns sample unchanged
        without updating the stored EMA state. Levels 1..8 use a divisor
        of 2**(nr-1), exactly as in the source expression EA(ea1,in,...).
        """
        if not 0 <= nr <= 8:
            raise ValueError("nr must be in range 0..8")

        value = int(sample)
        if nr == 0:
            return value

        divisor = 1 << (nr - 1)
        self.ea1 += trunc_div(value - self.ea1, divisor)
        return self.ea1
