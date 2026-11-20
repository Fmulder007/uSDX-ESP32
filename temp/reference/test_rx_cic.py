"""Tests for rx_cic.py. Run: python -m unittest -v"""

import random
import unittest

from rx_cic import RxCicState, process_iq_stream


def _get(values, index):
    return values[index] if 0 <= index < len(values) else 0


def direct_i_cic(samples, att2=2):
    """Direct two-stage decimate-by-2 reference, I phase."""
    stage1 = []
    for n in range(0, len(samples), 2):
        value = (
            _get(samples, n)
            + 3 * _get(samples, n - 1)
            + 3 * _get(samples, n - 2)
            + _get(samples, n - 3)
        )
        stage1.append(value >> 1)

    output = []
    for n in range(0, len(stage1), 2):
        value = (
            _get(stage1, n)
            + 3 * _get(stage1, n - 1)
            + 3 * _get(stage1, n - 2)
            + _get(stage1, n - 3)
        )
        output.append(value >> att2)
    return output


def direct_q_cic(samples, att2=2):
    """Direct two-stage reference using the Q branch's odd phase.

    Q first-stage outputs occur at Q sample indexes 1,3,5,... .
    The second stage emits at indexes 3,7,11,... .
    """
    stage1 = {}
    for n in range(1, len(samples), 2):
        value = (
            _get(samples, n)
            + 3 * _get(samples, n - 1)
            + 3 * _get(samples, n - 2)
            + _get(samples, n - 3)
        )
        stage1[n] = value >> 1

    output = []
    for n in range(3, len(samples), 4):
        value = (
            stage1.get(n, 0)
            + 3 * stage1.get(n - 2, 0)
            + 3 * stage1.get(n - 4, 0)
            + stage1.get(n - 6, 0)
        )
        output.append(value >> att2)
    return output


class TestRxCic(unittest.TestCase):
    def test_event_order_is_enforced(self):
        state = RxCicState()
        with self.assertRaises(ValueError):
            state.push_event("Q", 123)

    def test_i_branch_matches_direct_cascade(self):
        rng = random.Random(0xC1C)
        for count in (4, 8, 32, 128, 1024):
            with self.subTest(count=count):
                i_samples = [rng.randint(-511, 512) for _ in range(count)]
                q_samples = [0] * count
                actual = process_iq_stream(i_samples, q_samples)
                self.assertEqual(
                    [pair[0] for pair in actual],
                    direct_i_cic(i_samples),
                )

    def test_q_branch_matches_direct_cascade_with_pair_pipeline(self):
        rng = random.Random(0x10)
        for count in (4, 8, 32, 128, 1024):
            with self.subTest(count=count):
                i_samples = [0] * count
                q_samples = [rng.randint(-511, 512) for _ in range(count)]
                actual = process_iq_stream(i_samples, q_samples)
                q_reference = direct_q_cic(q_samples)

                # First output pair contains the source's initial q_ac2=0.
                # Each later pair consumes the Q result calculated on the
                # preceding phase 7.
                self.assertEqual(actual[0][1], 0)
                self.assertEqual(
                    [pair[1] for pair in actual][1:],
                    q_reference[: max(0, len(actual) - 1)],
                )

    def test_combined_iq_stream_matches_both_references(self):
        rng = random.Random(0x5A17)
        for count in (8, 32, 256):
            with self.subTest(count=count):
                i_samples = [rng.randint(-511, 512) for _ in range(count)]
                q_samples = [rng.randint(-511, 512) for _ in range(count)]
                actual = process_iq_stream(i_samples, q_samples)
                q_reference = direct_q_cic(q_samples)

                self.assertEqual(
                    [pair[0] for pair in actual],
                    direct_i_cic(i_samples),
                )
                self.assertEqual(actual[0][1], 0)
                self.assertEqual(
                    [pair[1] for pair in actual][1:],
                    q_reference[: max(0, len(actual) - 1)],
                )


if __name__ == "__main__":
    unittest.main()
