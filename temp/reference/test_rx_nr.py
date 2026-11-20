"""Tests for the uSDX NR exponential smoother reference model."""

import unittest

from rx_nr import RxNrState


class TestRxNr(unittest.TestCase):
    def test_level_one_is_passthrough(self):
        state = RxNrState(ea1=-123)
        for sample in (0, 100, -100, 511, -512):
            self.assertEqual(state.push(sample, 1), sample)
        self.assertEqual(state.ea1, -512)

    def test_level_two_integer_step_response(self):
        state = RxNrState()
        self.assertEqual(
            [state.push(100, 2) for _ in range(4)],
            [50, 75, 87, 93],
        )

    def test_level_eight_has_127_count_deadband(self):
        state = RxNrState()
        self.assertEqual(state.push(127, 8), 0)
        self.assertEqual(state.ea1, 0)

        state = RxNrState()
        self.assertEqual(state.push(128, 8), 1)
        self.assertEqual(state.push(128, 8), 1)
        self.assertEqual(state.ea1, 1)

    def test_negative_delta_truncates_toward_zero(self):
        state = RxNrState(ea1=1)
        self.assertEqual(state.push(0, 2), 1)
        self.assertEqual(state.ea1, 1)

    def test_nr_off_freezes_state_and_level_change_reuses_it(self):
        state = RxNrState(ea1=0)
        self.assertEqual(state.push(128, 8), 1)
        self.assertEqual(state.push(-300, 0), -300)
        self.assertEqual(state.ea1, 1)
        self.assertEqual(state.push(128, 1), 128)
        self.assertEqual(state.ea1, 128)

    def test_invalid_level_is_rejected(self):
        state = RxNrState()
        with self.assertRaises(ValueError):
            state.push(10, 9)


if __name__ == "__main__":
    unittest.main()
