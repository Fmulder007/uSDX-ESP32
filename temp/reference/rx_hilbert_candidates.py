"""Experimental Q15 Hilbert FIR candidates; active uSDX filter is unchanged.

Coefficients were generated with an equiripple (Remez) Hilbert design for
650..3400 Hz at 7812.5 samples/s, then quantized symmetrically to Q15.
"""

from dataclasses import dataclass, field
from typing import List, Sequence, Tuple


HILBERT_19_Q15: Tuple[int, ...] = (
    -482, -3, -1210, -7, -2704, -9, -5980, -6, -20520,
    0,
    20520, 6, 5980, 9, 2704, 7, 1210, 3, 482,
)

HILBERT_23_Q15: Tuple[int, ...] = (
    -226, -7, -626, -17, -1423, -26, -2908, -27, -6128, -17, -20573,
    0,
    20573, 17, 6128, 27, 2908, 26, 1423, 17, 626, 7, 226,
)

Q15_SCALE = 1 << 15
INT32_MAX = (1 << 31) - 1


def trunc_div(numerator: int, denominator: int) -> int:
    """C/C++ signed integer division, truncating toward zero."""
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    return numerator // denominator if numerator >= 0 else -((-numerator) // denominator)


def q15_accumulator_bound_for_int16(taps_q15: Sequence[int]) -> int:
    """Worst-case absolute FIR accumulator for any signed-int16 input history."""
    if len(taps_q15) < 3 or len(taps_q15) % 2 != 1:
        raise ValueError("Hilbert FIR must have odd length >= 3")
    half = len(taps_q15) // 2
    if int(taps_q15[half]) != 0:
        raise ValueError("odd-symmetric Hilbert FIR centre tap must be zero")
    if any(int(taps_q15[k]) != -int(taps_q15[-1-k]) for k in range(half)):
        raise ValueError("Hilbert FIR coefficients must be antisymmetric")
    return 65535 * sum(abs(int(taps_q15[k])) for k in range(half))


@dataclass(frozen=True)
class HilbertCandidateOutput:
    i_delayed: int
    q_hilbert: int
    ssb_audio_input: int
    accumulator: int


@dataclass
class RxHilbertCandidateState:
    """Experimental linear-phase Hilbert plus matching I delay."""

    taps_q15: Tuple[int, ...] = HILBERT_19_Q15
    att2: int = 2
    q_history: List[int] = field(default_factory=list)
    i_history: List[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.taps_q15) < 3 or len(self.taps_q15) % 2 != 1:
            raise ValueError("Hilbert FIR must have odd length >= 3")
        half = len(self.taps_q15) // 2
        if self.taps_q15[half] != 0:
            raise ValueError("centre tap must be zero")
        if any(self.taps_q15[k] != -self.taps_q15[-1-k] for k in range(half)):
            raise ValueError("Hilbert FIR must be antisymmetric")
        if not 0 <= self.att2 <= 15:
            raise ValueError("att2 must be in range 0..15")
        if not self.q_history:
            self.q_history = [0] * (len(self.taps_q15) - 1)
        if not self.i_history:
            self.i_history = [0] * self.delay
        if len(self.q_history) != len(self.taps_q15) - 1:
            raise ValueError("q_history length does not match tap count")
        if len(self.i_history) != self.delay:
            raise ValueError("i_history length does not match FIR group delay")

    @property
    def delay(self) -> int:
        return (len(self.taps_q15) - 1) // 2

    @property
    def accumulator_bound_int16(self) -> int:
        return q15_accumulator_bound_for_int16(self.taps_q15)

    def push_pair(self, i_raw: int, q_raw: int) -> HilbertCandidateOutput:
        i_current = int(i_raw) >> self.att2
        q_current = int(q_raw) >> self.att2
        q_samples = [q_current] + self.q_history
        accumulator = sum(
            int(coefficient) * int(sample)
            for coefficient, sample in zip(self.taps_q15, q_samples)
        )
        q_hilbert = trunc_div(accumulator, Q15_SCALE)

        i_delayed = self.i_history[0] if self.i_history else i_current
        if self.delay:
            self.i_history = self.i_history[1:] + [i_current]
        self.q_history = [q_current] + self.q_history[:-1]

        return HilbertCandidateOutput(
            i_delayed=i_delayed,
            q_hilbert=q_hilbert,
            ssb_audio_input=-i_delayed - q_hilbert,
            accumulator=accumulator,
        )
