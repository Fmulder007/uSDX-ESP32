"""Tests for experimental longer Q15 Hilbert FIR candidates."""

import math
import unittest

from rx_hilbert_candidates import (
    HILBERT_19_Q15,
    HILBERT_23_Q15,
    INT32_MAX,
    RxHilbertCandidateState,
)


def image_rejection_db(
    taps,
    frequency_hz,
    sample_rate_hz=7812.5,
    amplitude=1000,
):
    levels = []
    for q_sign in (1, -1):
        state = RxHilbertCandidateState(taps_q15=taps, att2=0)
        squares = []
        for n in range(8192):
            phase = 2.0 * math.pi * frequency_hz * n / sample_rate_hz
            i_sample = round(amplitude * math.cos(phase))
            q_sample = round(q_sign * amplitude * math.sin(phase))
            output = state.push_pair(i_sample, q_sample).ssb_audio_input
            if n >= 256:
                squares.append(output * output)
        levels.append(math.sqrt(sum(squares) / len(squares)))
    weak, strong = sorted(levels)
    if weak == 0:
        return float("inf")
    return 20.0 * math.log10(strong / weak)


class TestHilbertCandidates(unittest.TestCase):
    def test_19_tap_candidate_exceeds_43db_at_both_band_edges(self):
        self.assertGreater(image_rejection_db(HILBERT_19_Q15, 650), 47.0)
        self.assertGreater(image_rejection_db(HILBERT_19_Q15, 3400), 46.0)

    def test_23_tap_candidate_has_more_margin(self):
        self.assertGreater(image_rejection_db(HILBERT_23_Q15, 650), 56.0)
        self.assertGreater(image_rejection_db(HILBERT_23_Q15, 3400), 53.0)

    def test_i_delay_matches_linear_phase_group_delay(self):
        for taps, expected_delay in ((HILBERT_19_Q15, 9), (HILBERT_23_Q15, 11)):
            state = RxHilbertCandidateState(taps_q15=taps, att2=0)
            delayed = []
            for n in range(expected_delay + 2):
                result = state.push_pair(128 if n == 0 else 0, 0)
                delayed.append(result.i_delayed)
            self.assertEqual(delayed[expected_delay], 128)
            self.assertEqual(sum(delayed[:expected_delay]), 0)

    def test_coefficients_are_antisymmetric_and_int32_accumulator_is_safe(self):
        for taps in (HILBERT_19_Q15, HILBERT_23_Q15):
            self.assertEqual(taps[len(taps) // 2], 0)
            self.assertTrue(all(taps[k] == -taps[-1-k] for k in range(len(taps) // 2)))
            state = RxHilbertCandidateState(taps_q15=taps, att2=0)
            self.assertLess(state.accumulator_bound_int16, INT32_MAX)


if __name__ == "__main__":
    unittest.main()
