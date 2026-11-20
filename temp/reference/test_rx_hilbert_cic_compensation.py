"""Tests for CIC-compensated Q15 Hilbert FIR candidates."""

import math
import unittest

from rx_adc_input import RxAdcInputState
from rx_cic import RxCicState
from rx_hilbert_candidates import RxHilbertCandidateState
from rx_hilbert_cic_compensation import (
    COMPENSATED_HILBERT_23_Q15,
    COMPENSATED_HILBERT_27_Q15,
    INT32_MAX,
    accumulator_bound_for_peak,
    accumulator_bound_full_int16,
    compensation_target_magnitude,
    q15_magnitude_response,
)


def full_chain_image_rejection_db(frequency_hz, taps_q15, pair_count=2048,
                                  amplitude=511, att2=2):
    levels = []
    for q_sign in (1, -1):
        adc = RxAdcInputState(startup_adc_register=0)
        cic = RxCicState()
        hilbert = RxHilbertCandidateState(
            taps_q15=tuple(taps_q15),
            att2=att2,
        )
        squares = []

        for tick in range(pair_count * 8 + 1024):
            phase = 2.0 * math.pi * frequency_hz * tick / 62500.0
            i_sample = round(amplitude * math.cos(phase))
            q_sample = round(q_sign * amplitude * math.sin(phase))
            channel, sample = adc.push_tick(i_sample, q_sample)
            pair = cic.push_event(channel, sample)

            if pair is not None:
                output = hilbert.push_pair(*pair).ssb_audio_input
                if tick > 8 * 128:
                    squares.append(output * output)

        squares = squares[-pair_count:]
        levels.append(math.sqrt(sum(squares) / len(squares)))

    weak, strong = sorted(levels)
    if weak == 0:
        return float("inf")
    return 20.0 * math.log10(strong / weak)


class TestCicCompensatedHilbert(unittest.TestCase):
    def test_23_tap_candidate_preserves_full_chain_rejection(self):
        self.assertGreater(
            full_chain_image_rejection_db(650, COMPENSATED_HILBERT_23_Q15),
            70.0,
        )
        self.assertGreater(
            full_chain_image_rejection_db(2000, COMPENSATED_HILBERT_23_Q15),
            64.0,
        )
        self.assertGreater(
            full_chain_image_rejection_db(3400, COMPENSATED_HILBERT_23_Q15),
            45.0,
        )

    def test_27_tap_candidate_has_more_upper_edge_margin(self):
        self.assertGreater(
            full_chain_image_rejection_db(650, COMPENSATED_HILBERT_27_Q15),
            67.0,
        )
        self.assertGreater(
            full_chain_image_rejection_db(2000, COMPENSATED_HILBERT_27_Q15),
            65.0,
        )
        self.assertGreater(
            full_chain_image_rejection_db(3400, COMPENSATED_HILBERT_27_Q15),
            52.0,
        )

    def test_delay_matches_candidate_group_delay(self):
        for taps, delay in (
            (COMPENSATED_HILBERT_23_Q15, 11),
            (COMPENSATED_HILBERT_27_Q15, 13),
        ):
            state = RxHilbertCandidateState(taps_q15=taps, att2=0)
            values = []
            for n in range(delay + 2):
                values.append(
                    state.push_pair(128 if n == 0 else 0, 0).i_delayed
                )
            self.assertEqual(values[delay], 128)
            self.assertEqual(sum(values[:delay]), 0)

    def test_q15_accumulator_bounds_fit_signed_int32(self):
        expected = (
            (COMPENSATED_HILBERT_23_Q15, 250019840, 1000079360, 2000128200),
            (COMPENSATED_HILBERT_27_Q15, 257384448, 1029537792, 2059044165),
        )
        for taps, at_default, at_att2_zero, full_int16 in expected:
            self.assertEqual(
                accumulator_bound_for_peak(taps, 4096),
                at_default,
            )
            self.assertEqual(
                accumulator_bound_for_peak(taps, 16384),
                at_att2_zero,
            )
            self.assertEqual(
                accumulator_bound_full_int16(taps),
                full_int16,
            )
            self.assertLess(full_int16, INT32_MAX)

    def test_q15_fir_tracks_midpoint_compensation_target(self):
        for taps, tolerance_db in (
            (COMPENSATED_HILBERT_23_Q15, 0.09),
            (COMPENSATED_HILBERT_27_Q15, 0.04),
        ):
            for frequency in range(650, 3401, 25):
                actual = q15_magnitude_response(taps, frequency)
                target = compensation_target_magnitude(frequency)
                error_db = 20.0 * math.log10(actual / target)
                self.assertLessEqual(abs(error_db), tolerance_db)


if __name__ == "__main__":
    unittest.main()
