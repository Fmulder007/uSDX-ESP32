"""Repeatable 50-Hz full-chain image-rejection sweep for Hilbert candidates.

Run from temp/reference:
    python rx_hilbert_cic_sweep.py

The script compares the original source 15-tap Hilbert with the 23- and
27-tap CIC-compensated Q15 candidates through:
    ADC MUX/read-previous + I midpoint -> original CIC -> Hilbert + I delay

This is an ideal steady-state model. It does not include the separate ADC
startup timing scheduler, physical sample-and-hold aperture, analog settling,
or real I/Q hardware mismatch.
"""

import math

from rx_adc_input import RxAdcInputState
from rx_cic import RxCicState
from rx_hilbert_candidates import RxHilbertCandidateState
from rx_quadrature import RxQuadratureState
from rx_hilbert_cic_compensation import (
    COMPENSATED_HILBERT_17_MINIMAX_Q15,
    COMPENSATED_HILBERT_19_MINIMAX_Q15,
    COMPENSATED_HILBERT_21_MINIMAX_Q15,
    COMPENSATED_HILBERT_23_Q15,
    COMPENSATED_HILBERT_27_Q15,
)


SAMPLE_RATE_TIMER = 62500.0
PAIR_COUNT = 1024
INPUT_AMPLITUDE = 511
ATT2 = 2
WARMUP_PAIRS = 128


def measure_one_orientation(frequency_hz, q_sign, hilbert_kind, taps=None):
    adc = RxAdcInputState(startup_adc_register=0)
    cic = RxCicState()

    if hilbert_kind == "source":
        quadrature = RxQuadratureState(att2=ATT2)
    elif hilbert_kind == "q15":
        quadrature = RxHilbertCandidateState(taps_q15=tuple(taps), att2=ATT2)
    else:
        raise ValueError("unknown Hilbert kind")

    squares = []
    for tick in range(PAIR_COUNT * 8 + (WARMUP_PAIRS * 8)):
        phase = 2.0 * math.pi * frequency_hz * tick / SAMPLE_RATE_TIMER
        i_sample = round(INPUT_AMPLITUDE * math.cos(phase))
        q_sample = round(q_sign * INPUT_AMPLITUDE * math.sin(phase))

        channel, sample = adc.push_tick(i_sample, q_sample)
        pair = cic.push_event(channel, sample)
        if pair is None:
            continue

        output = quadrature.push_pair(*pair).ssb_audio_input
        if tick >= WARMUP_PAIRS * 8:
            squares.append(output * output)

    squares = squares[-PAIR_COUNT:]
    if not squares:
        raise RuntimeError("no output samples collected")
    return math.sqrt(sum(squares) / len(squares))


def measure_image_rejection(frequency_hz, hilbert_kind, taps=None):
    levels = [
        measure_one_orientation(frequency_hz, sign, hilbert_kind, taps)
        for sign in (1, -1)
    ]
    weak, strong = sorted(levels)
    if weak == 0:
        return float("inf")
    return 20.0 * math.log10(strong / weak)


def sweep():
    candidates = (
        ("source15", "source", None),
        ("comp17_minimax", "q15", COMPENSATED_HILBERT_17_MINIMAX_Q15),
        ("comp19_minimax", "q15", COMPENSATED_HILBERT_19_MINIMAX_Q15),
        ("comp21_minimax", "q15", COMPENSATED_HILBERT_21_MINIMAX_Q15),
        ("comp23_ls", "q15", COMPENSATED_HILBERT_23_Q15),
        ("comp27_ls", "q15", COMPENSATED_HILBERT_27_Q15),
    )
    rows = []
    for frequency in range(650, 3401, 50):
        row = {"frequency_hz": frequency}
        for name, kind, taps in candidates:
            row[name] = measure_image_rejection(frequency, kind, taps)
        rows.append(row)
    return rows


def main():
    rows = sweep()
    names = ("source15", "comp17_minimax", "comp19_minimax", "comp21_minimax", "comp23_ls", "comp27_ls")
    print("frequency_hz," + ",".join(name + "_db" for name in names))
    for row in rows:
        print(
            "{frequency_hz},".format(**row)
            + ",".join("{:.2f}".format(row[name]) for name in names)
        )

    print("\nMinimum full-chain image rejection:")
    for name in names:
        minimum = min(rows, key=lambda row: row[name])
        print(
            "{}: {:.2f} dB at {} Hz".format(
                name,
                minimum[name],
                minimum["frequency_hz"],
            )
        )


if __name__ == "__main__":
    main()
