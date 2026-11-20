"""Tests for RX CIC gain and Hilbert intermediate-width diagnostics."""

import math
import unittest

from rx_cic import RxCicState
from rx_numeric_audit import (
    hilbert_intermediates,
    hilbert_int16_wrap_hypothesis,
    signed_int16_overflows,
)
from rx_quadrature import RxQuadratureState


class TestRxNumericAudit(unittest.TestCase):
    def test_cic_dc_gain_and_int16_bounds(self):
        positive = RxCicState()
        positive_outputs = []
        negative = RxCicState()
        negative_outputs = []

        for _ in range(120):
            pair = positive.push_event("I", 512)
            if pair is not None:
                positive_outputs.append(pair)
            positive.push_event("Q", 512)

            pair = negative.push_event("I", -511)
            if pair is not None:
                negative_outputs.append(pair)
            negative.push_event("Q", -511)

        self.assertEqual(positive_outputs[-1], (16384, 16384))
        self.assertEqual(negative_outputs[-1], (-16352, -16352))

        # Raw CIC DC gain is 32; process() then applies the default att2=2.
        self.assertEqual(positive_outputs[-1][0] // 512, 32)
        self.assertEqual(positive_outputs[-1][0] >> 2, 4096)
        self.assertEqual(negative_outputs[-1][0] >> 2, -4088)

    def test_full_scale_650hz_reaches_hilbert_16bit_overflow(self):
        cic = RxCicState()
        quadrature = RxQuadratureState(att2=2)
        first_overflow = None

        # ADC-domain Q input: 31.25 ksample/s, centered 10-bit range.
        for input_index in range(100):
            q_sample = round(
                511 * math.sin(2.0 * math.pi * 650.0 * input_index / 31250.0)
            )

            pair = cic.push_event("I", 0)
            if pair is not None:
                report = hilbert_intermediates(
                    quadrature.q_history,
                    pair[1] >> 2,
                )
                overflows = signed_int16_overflows(report)
                if overflows and first_overflow is None:
                    first_overflow = (input_index, report, overflows)

                quadrature.push_pair(*pair)

            cic.push_event("Q", q_sample)

        self.assertIsNotNone(first_overflow)
        input_index, report, overflows = first_overflow
        self.assertEqual(input_index, 56)
        self.assertEqual(report["third_multiply"], 38790)
        self.assertEqual(report["third_numerator"], 34915)
        self.assertEqual(overflows["third_multiply"], 38790)
        self.assertEqual(overflows["third_numerator"], 34915)
        self.assertEqual(report["qh_wide"], 3890)

    def test_wrap16_is_only_a_candidate_and_can_change_hilbert_result(self):
        history = [
            0, 123, 1311, 2973, 3879, 3752, 2622,
            791, -1253, -2961, -3879, -3761, -2638, -813,
        ]
        q_current = 1231
        wide = hilbert_intermediates(history, q_current)
        wrapped = hilbert_int16_wrap_hypothesis(history, q_current)

        self.assertEqual(wide["third_numerator"], 34915)
        self.assertEqual(wrapped["third_numerator"], -30621)
        self.assertEqual(wide["qh_wide"], 3890)
        self.assertEqual(wrapped["qh"], 3379)
        self.assertNotEqual(wide["qh_wide"], wrapped["qh"])


if __name__ == "__main__":
    unittest.main()
