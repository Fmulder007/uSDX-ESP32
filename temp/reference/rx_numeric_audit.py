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


def audit_ssb_iir_intermediates(
    samples: Sequence[int],
    filt: int,
) -> Dict[str, object]:
    """Audit mathematical intermediates in SSB filt_var() filters 1..3.

    This runs the wide-integer recurrence while recording absolute maxima and
    first sample indices above signed int16. It does not emulate AVR overflow;
    once an AVR expression overflows, its later state may differ from this
    mathematical baseline.
    """
    if filt not in (1, 2, 3):
        raise ValueError("filt must be 1, 2 or 3")

    zz1 = zz2 = 0
    za1 = za2 = 0
    zb1 = zb2 = 0
    zc1 = zc2 = 0

    names = (
        "prefilter_difference",
        "prefilter_term30",
        "prefilter_term25",
        "prefilter_sum",
        "stage1_input_term2",
        "stage1_feed_sum",
        "stage1_feedback_term1",
        "stage1_feedback_term2",
        "stage1_feedback_sum",
        "stage2_input_term2",
        "stage2_feed_sum",
        "stage2_feedback_term1",
        "stage2_feedback_term2",
        "stage2_feedback_sum",
        "za0",
        "zb0",
        "zc0",
    )
    max_abs = {name: 0 for name in names}
    first_overrange = {}

    for index, input_sample in enumerate(samples):
        x = int(input_sample)
        if not INT16_MIN <= x <= INT16_MAX:
            raise ValueError("IIR input sample is outside signed int16 range")

        previous_zz1 = zz1
        zz2 = previous_zz1
        zz1 = x

        prefilter_difference = x - zz2
        prefilter_term30 = 30 * prefilter_difference
        prefilter_term25 = 25 * zz1
        prefilter_sum = prefilter_term30 + prefilter_term25
        za0 = prefilter_sum >> 5

        stage1_input_term2 = 2 * za1
        stage1_feed_sum = za0 + stage1_input_term2 + za2
        stage2_input_term2 = 0
        stage1_feedback_term1 = 0
        stage1_feedback_term2 = 0
        stage2_feedback_term1 = 0
        stage2_feedback_term2 = 0

        if filt == 1:
            stage1_feedback_term1 = 13 * zb1
            stage1_feedback_term2 = 11 * zb2
            stage1_feedback_sum = (
                stage1_feedback_term1 + stage1_feedback_term2
            )
            zb0 = (stage1_feed_sum >> 1) - (stage1_feedback_sum >> 4)

            stage2_input_term2 = 2 * zb1
            stage2_feed_sum = zb0 + stage2_input_term2 + zb2
            stage2_feedback_term1 = 18 * zc1
            stage2_feedback_term2 = 11 * zc2
            stage2_feedback_sum = (
                stage2_feedback_term1 + stage2_feedback_term2
            )
            zc0 = (stage2_feed_sum >> 1) - (stage2_feedback_sum >> 4)
        elif filt == 2:
            stage1_feedback_term1 = 2 * zb1
            stage1_feedback_term2 = 8 * zb2
            stage1_feedback_sum = (
                stage1_feedback_term1 + stage1_feedback_term2
            )
            zb0 = (stage1_feed_sum >> 1) - (stage1_feedback_sum >> 4)

            stage2_input_term2 = 2 * zb1
            stage2_feed_sum = zb0 + stage2_input_term2 + zb2
            stage2_feedback_term1 = 4 * zc1
            stage2_feedback_term2 = 8 * zc2
            stage2_feedback_sum = (
                stage2_feedback_term1 + stage2_feedback_term2
            )
            zc0 = (stage2_feed_sum >> 2) - (stage2_feedback_sum >> 4)
        else:
            stage1_feedback_term1 = 0 * zb1
            stage1_feedback_term2 = 4 * zb2
            stage1_feedback_sum = (
                stage1_feedback_term1 + stage1_feedback_term2
            )
            zb0 = (stage1_feed_sum >> 1) - (stage1_feedback_sum >> 4)

            stage2_input_term2 = 2 * zb1
            stage2_feed_sum = zb0 + stage2_input_term2 + zb2
            stage2_feedback_term1 = 0 * zc1
            stage2_feedback_term2 = 4 * zc2
            stage2_feedback_sum = (
                stage2_feedback_term1 + stage2_feedback_term2
            )
            zc0 = (stage2_feed_sum >> 2) - (stage2_feedback_sum >> 4)

        observed = {
            "prefilter_difference": prefilter_difference,
            "prefilter_term30": prefilter_term30,
            "prefilter_term25": prefilter_term25,
            "prefilter_sum": prefilter_sum,
            "stage1_input_term2": stage1_input_term2,
            "stage1_feed_sum": stage1_feed_sum,
            "stage1_feedback_term1": stage1_feedback_term1,
            "stage1_feedback_term2": stage1_feedback_term2,
            "stage1_feedback_sum": stage1_feedback_sum,
            "stage2_input_term2": stage2_input_term2,
            "stage2_feed_sum": stage2_feed_sum,
            "stage2_feedback_term1": stage2_feedback_term1,
            "stage2_feedback_term2": stage2_feedback_term2,
            "stage2_feedback_sum": stage2_feedback_sum,
            "za0": za0,
            "zb0": zb0,
            "zc0": zc0,
        }
        for name, value in observed.items():
            magnitude = abs(value)
            if magnitude > max_abs[name]:
                max_abs[name] = magnitude
            if magnitude > INT16_MAX and name not in first_overrange:
                first_overrange[name] = index

        zc2, zc1 = zc1, zc0
        zb2, zb1 = zb1, zb0
        za2, za1 = za1, za0

    return {
        "filt": filt,
        "samples": len(samples),
        "max_abs": max_abs,
        "first_int16_overrange": first_overrange,
    }


def audit_nr_deltas(
    samples: Sequence[int],
    nr: int,
) -> Dict[str, object]:
    """Audit the mathematical in - ea1 delta used by process_nr().

    The state update is evaluated in wide integers. The result reports which
    deltas cannot be represented by AVR's signed 16-bit int before division.
    """
    if not 1 <= nr <= 8:
        raise ValueError("nr must be in range 1..8")

    state = 0
    divisor = 1 << (nr - 1)
    max_abs_delta = 0
    first_overrange = None
    deltas = []

    for index, sample in enumerate(samples):
        value = int(sample)
        if not INT16_MIN <= value <= INT16_MAX:
            raise ValueError("NR input sample is outside signed int16 range")

        delta = value - state
        deltas.append(delta)
        if abs(delta) > max_abs_delta:
            max_abs_delta = abs(delta)
        if abs(delta) > INT16_MAX and first_overrange is None:
            first_overrange = index

        state += trunc_div(delta, divisor)

    return {
        "nr": nr,
        "samples": len(samples),
        "max_abs_delta": max_abs_delta,
        "first_int16_overrange_index": first_overrange,
        "final_wide_state": state,
        "deltas": deltas,
    }
