"""Hilbert FIR candidates compensated for the source I midpoint interpolator.

The I channel is averaged across adjacent I samples before CIC. This produces
a frequency-dependent I amplitude factor cos(pi*f/31250), while Q is not
averaged. These candidates therefore approximate that factor in the Q Hilbert
branch rather than implementing a flat, unity-magnitude Hilbert transform.

The 17/19/21-tap tables are minimax relative-error fits; the 23/27-tap tables
are retained least-squares fits. They are experimental. The active 15-tap
source model is unchanged.
"""

from typing import Sequence, Tuple
import cmath
import math

COMPENSATED_HILBERT_17_MINIMAX_Q15: Tuple[int, ...] = (
    335, -691, 316, -2040, 245, -5312, -123, -19884,
    0,
    19884, 123, 5312, -245, 2040, -316, 691, -335,
)

COMPENSATED_HILBERT_19_MINIMAX_Q15: Tuple[int, ...] = (
    -458, -23, -1156, -64, -2594, -148, -5757, -372, -20054,
    0,
    20054, 372, 5757, 148, 2594, 64, 1156, 23, 458,
)

COMPENSATED_HILBERT_21_MINIMAX_Q15: Tuple[int, ...] = (
    184, -266, 259, -889, 304, -2285, 203, -5507, -157, -19958,
    0,
    19958, 157, 5507, -203, 2285, -304, 889, -259, 266, -184,
)

# Longer least-squares compensation fits retained as comparison options.
COMPENSATED_HILBERT_23_Q15: Tuple[int, ...] = (
    -122, 21, -445, 31, -1152, 12, -2570, -72, -5729, -324, -20042,
    0,
    20042, 324, 5729, 72, 2570, -12, 1152, -31, 445, -21, 122,
)

COMPENSATED_HILBERT_27_Q15: Tuple[int, ...] = (
    -57, 11, -222, 20, -597, 19, -1338, -10, -2753, -96, -5864, -340, -20092,
    0,
    20092, 340, 5864, 96, 2753, 10, 1338, -19, 597, -20, 222, -11, 57,
)

Q15_SCALE = 1 << 15
INT32_MAX = (1 << 31) - 1


def accumulator_bound_for_peak(taps_q15: Sequence[int], sample_peak: int) -> int:
    """Bound Q15 accumulator for antisymmetric FIR and |x[n]| <= sample_peak.

    Each mirrored tap pair contributes c*(x[n-k] - x[n-(N-1-k)]), whose
    absolute sample difference is at most 2*sample_peak.
    """
    if sample_peak < 0:
        raise ValueError("sample_peak must be non-negative")
    if len(taps_q15) < 3 or len(taps_q15) % 2 != 1:
        raise ValueError("Hilbert FIR length must be odd and >= 3")
    half = len(taps_q15) // 2
    if int(taps_q15[half]) != 0:
        raise ValueError("Hilbert centre coefficient must be zero")
    if any(int(taps_q15[k]) != -int(taps_q15[-1-k]) for k in range(half)):
        raise ValueError("Hilbert coefficients must be antisymmetric")
    return 2 * int(sample_peak) * sum(abs(int(v)) for v in taps_q15[:half])


def accumulator_bound_full_int16(taps_q15: Sequence[int]) -> int:
    """Exact endpoint-difference bound for arbitrary signed-int16 history.

    The largest possible signed-int16 difference is 32767 - (-32768) = 65535,
    not 65536. Using the generic symmetric-peak helper would be one count
    more conservative per coefficient pair.
    """
    if len(taps_q15) < 3 or len(taps_q15) % 2 != 1:
        raise ValueError("Hilbert FIR length must be odd and >= 3")
    half = len(taps_q15) // 2
    if int(taps_q15[half]) != 0:
        raise ValueError("Hilbert centre coefficient must be zero")
    if any(int(taps_q15[k]) != -int(taps_q15[-1-k]) for k in range(half)):
        raise ValueError("Hilbert coefficients must be antisymmetric")
    return 65535 * sum(abs(int(v)) for v in taps_q15[:half])


def compensation_target_magnitude(frequency_hz: float) -> float:
    """Magnitude needed to compensate the two-point I midpoint average."""
    return math.cos(math.pi * frequency_hz / 31250.0)


def q15_magnitude_response(
    taps_q15: Sequence[int],
    frequency_hz: float,
    sample_rate_hz: float = 7812.5,
) -> float:
    """Magnitude of the quantized FIR response, with Q15 scale removed."""
    omega = 2.0 * math.pi * frequency_hz / sample_rate_hz
    response = sum(
        int(coefficient) * cmath.exp(-1j * omega * index)
        for index, coefficient in enumerate(taps_q15)
    )
    return abs(response) / Q15_SCALE
