"""Diagnostics for AVR-width risks in the active RX Hilbert expression.

The functions evaluate mathematical intermediate values with Python integers.
The wrap16 helper is only a candidate model of modulo-16-bit machine arithmetic;
it is NOT proof of the actual AVR-GCC output for signed-overflow expressions.
"""

from typing import Dict, Sequence

INT16_MIN = -32768
INT16_MAX = 32767


def trunc_div(numerator: int, denominator: int) -> int:
    """C/C++ signed integer division, truncating toward zero."""
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    if numerator >= 0:
        return numerator // denominator
    return -((-numerator) // denominator)


def wrap_int16(value: int) -> int:
    """Return the two's-complement signed 16-bit representation."""
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def hilbert_intermediates(
    q_history: Sequence[int],
    q_current: int,
) -> Dict[str, int]:
    """Return the wide mathematical intermediates in source expression order."""
    if len(q_history) != 14:
        raise ValueError("q_history must contain 14 samples")

    v = [int(sample) for sample in q_history]
    q = int(q_current)

    d0 = v[0] - q
    d1 = v[2] - v[12]
    d1_times_4 = d1 * 4
    first_numerator = d0 + d1_times_4

    d2 = v[4] - v[10]
    d3 = v[6] - v[8]
    second_numerator = d2 + d3

    third_multiply = d2 * 5
    third_numerator = third_multiply - d3

    term1 = trunc_div(first_numerator, 64)
    term2 = trunc_div(second_numerator, 8)
    term3 = trunc_div(third_numerator, 128)
    term4 = trunc_div(d3, 2)

    return {
        "d0": d0,
        "d1": d1,
        "d1_times_4": d1_times_4,
        "first_numerator": first_numerator,
        "d2": d2,
        "d3": d3,
        "second_numerator": second_numerator,
        "third_multiply": third_multiply,
        "third_numerator": third_numerator,
        "term1": term1,
        "term2": term2,
        "term3": term3,
        "term4": term4,
        "qh_wide": term1 + term2 + term3 + term4,
    }


def signed_int16_overflows(values: Dict[str, int]) -> Dict[str, int]:
    """Return named values outside signed int16 range."""
    return {
        name: value
        for name, value in values.items()
        if isinstance(value, int) and not INT16_MIN <= value <= INT16_MAX
    }


def hilbert_int16_wrap_hypothesis(
    q_history: Sequence[int],
    q_current: int,
) -> Dict[str, int]:
    """Evaluate a modulo-16-bit candidate, not a verified AVR compiler model.

    Signed overflow is undefined in C. This function is included only to show
    how a simple two's-complement wrap at each 16-bit operation would alter
    the sample. Compare it with actual AVR-GCC assembly/runtime before using
    it as a bit-exact reference.
    """
    if len(q_history) != 14:
        raise ValueError("q_history must contain 14 samples")

    v = [wrap_int16(int(sample)) for sample in q_history]
    q = wrap_int16(int(q_current))

    d0 = wrap_int16(v[0] - q)
    d1 = wrap_int16(v[2] - v[12])
    first_numerator = wrap_int16(d0 + wrap_int16(d1 * 4))

    d2 = wrap_int16(v[4] - v[10])
    d3 = wrap_int16(v[6] - v[8])
    second_numerator = wrap_int16(d2 + d3)

    third_multiply = wrap_int16(d2 * 5)
    third_numerator = wrap_int16(third_multiply - d3)

    term1 = trunc_div(first_numerator, 64)
    term2 = trunc_div(second_numerator, 8)
    term3 = trunc_div(third_numerator, 128)
    term4 = trunc_div(d3, 2)

    qh = wrap_int16(wrap_int16(wrap_int16(term1 + term2) + term3) + term4)

    return {
        "first_numerator": first_numerator,
        "second_numerator": second_numerator,
        "third_multiply": third_multiply,
        "third_numerator": third_numerator,
        "term1": term1,
        "term2": term2,
        "term3": term3,
        "term4": term4,
        "qh": qh,
    }
