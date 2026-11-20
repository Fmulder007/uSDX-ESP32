"""Tests for rx_quadrature.py. Run: python -m unittest -v"""

import unittest

from rx_quadrature import RxQuadratureState


class TestRxQuadrature(unittest.TestCase):
    def test_q_hilbert_impulse_response_and_order(self):
        state = RxQuadratureState(att2=0)
        output = []

        for n in range(15):
            q_sample = 128 if n == 0 else 0
            result = state.push_pair(0, q_sample)
            output.append(result.q_hilbert)

        # This sequence follows the source's separate integer divisions.
        # It is the time-domain impulse response in the source's order.
        self.assertEqual(
            output,
            [-2, 0, -8, 0, -21, 0, -79, 0, 79, 0, 21, 0, 8, 0, 2],
        )

    def test_i_delay_is_exactly_seven_iq_pairs(self):
        state = RxQuadratureState(att2=0)
        delayed = []

        for n in range(9):
            i_sample = 128 if n == 0 else 0
            result = state.push_pair(i_sample, 0)
            delayed.append(result.i_delayed)

        self.assertEqual(delayed, [0, 0, 0, 0, 0, 0, 0, 128, 0])

    def test_att2_is_applied_before_hilbert_and_i_delay(self):
        state = RxQuadratureState(att2=2)
        first = state.push_pair(512, 512)
        second = state.push_pair(0, 0)

        self.assertEqual(first.i_current, 128)
        self.assertEqual(first.q_current, 128)
        self.assertEqual(first.i_delayed, 0)
        self.assertEqual(second.i_delayed, 0)

    def test_ssb_audio_input_sign(self):
        state = RxQuadratureState(att2=0)
        result = state.push_pair(0, 128)

        # A positive Q impulse gives a negative Hilbert result; process()
        # inverts that quadrature branch when forming the SSB audio input.
        self.assertEqual(result.q_hilbert, -2)
        self.assertEqual(result.ssb_audio_input, 2)


if __name__ == "__main__":
    unittest.main()
