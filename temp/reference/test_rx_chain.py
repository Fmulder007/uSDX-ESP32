"""Integration tests for the partial RX CIC -> quadrature reference chain."""

import random
import unittest

from rx_chain import RxReferencePipeline


def _get(values, index):
    return values[index] if 0 <= index < len(values) else 0


def _direct_i_cic(samples):
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
        output.append(value)
    return output


class TestRxReferencePipeline(unittest.TestCase):
    def test_cic_raw_output_is_scaled_once_at_process_boundary(self):
        rng = random.Random(0xB10C)
        i_samples = [rng.randint(-511, 512) for _ in range(64)]
        q_samples = [rng.randint(-511, 512) for _ in range(64)]

        pipeline = RxReferencePipeline(att2=2)
        actual = []
        for i_sample, q_sample in zip(i_samples, q_samples):
            output = pipeline.push_event("I", i_sample)
            if output is not None:
                actual.append(output)
            output = pipeline.push_event("Q", q_sample)
            if output is not None:
                actual.append(output)

        raw_i = _direct_i_cic(i_samples)
        expected_i = [sample >> 2 for sample in raw_i]
        self.assertEqual(
            [item.i_current for item in actual],
            expected_i,
        )

    def test_pair_output_count_and_initial_q_pipeline(self):
        i_samples = [0] * 16
        q_samples = [0] * 16
        pipeline = RxReferencePipeline()
        outputs = []

        for i_sample, q_sample in zip(i_samples, q_samples):
            for channel, sample in (("I", i_sample), ("Q", q_sample)):
                output = pipeline.push_event(channel, sample)
                if output is not None:
                    outputs.append(output)

        self.assertEqual(len(outputs), 4)
        self.assertEqual(outputs[0].q_current, 0)
        self.assertEqual(outputs[0].i_delayed, 0)


if __name__ == "__main__":
    unittest.main()
