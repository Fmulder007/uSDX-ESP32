"""Focused recurrence and lifecycle tests for the SSB IIR reference model."""

import unittest

from rx_iir import RxSsbIirState


class TestRxSsbIir(unittest.TestCase):
    def test_zero_input_remains_zero_for_all_ssb_filters(self):
        for filt in (1, 2, 3):
            state = RxSsbIirState()
            self.assertEqual([state.push(0, filt) for _ in range(32)], [0] * 32)

    def test_impulse_vectors_match_source_recurrence(self):
        expected = {
            1: [42, 65, -61, -57, 94, -22],
            2: [21, 66, 35, -69, -53, 57],
            3: [21, 73, 70, -22, -62, -5],
        }
        for filt, golden in expected.items():
            state = RxSsbIirState()
            actual = [state.push(100 if index == 0 else 0, filt) for index in range(6)]
            self.assertEqual(actual, golden)

    def test_bypass_does_not_advance_filter_histories(self):
        state = RxSsbIirState()
        state.push(100, 1)
        before = state.__dict__.copy()

        self.assertEqual(state.push(1234, 0), 1234)
        self.assertEqual(state.__dict__, before)

    def test_filter_change_reuses_old_histories(self):
        state = RxSsbIirState()
        for sample in (100, 0, 0, 0):
            state.push(sample, 1)

        carried = state.push(0, 2)
        fresh = RxSsbIirState().push(0, 2)
        self.assertEqual(carried, 34)
        self.assertEqual(fresh, 0)
        self.assertNotEqual(carried, fresh)

    def test_reset_helper_clears_all_histories(self):
        state = RxSsbIirState()
        for sample in (100, 0, 0, 0):
            state.push(sample, 1)
        state.reset()
        self.assertEqual(state, RxSsbIirState())

    def test_cw_filter_ids_are_not_silently_misrepresented(self):
        state = RxSsbIirState()
        for filt in (-1, 4, 7, 8):
            with self.assertRaises(ValueError):
                state.push(100, filt)


if __name__ == "__main__":
    unittest.main()
