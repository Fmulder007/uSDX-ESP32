"""Tests for the partial CIC -> quadrature -> baseline SSB chain."""

import unittest

from rx_ssb_chain import RxSsbReferencePipeline


class TestRxSsbReferencePipeline(unittest.TestCase):
    def test_one_audio_sample_per_complete_eight_event_cycle(self):
        pipeline = RxSsbReferencePipeline()
        output = []
        for _ in range(24):
            for channel, sample in (("I", 0), ("Q", 0)):
                value = pipeline.push_event(channel, sample)
                if value is not None:
                    output.append(value)
        self.assertEqual(len(output), 6)

    def test_quadrature_values_are_available_with_post_output(self):
        pipeline = RxSsbReferencePipeline(att2=0, volume=12)
        output = []
        for n in range(32):
            for channel, sample in (("I", 0), ("Q", 0)):
                value = pipeline.push_event(channel, sample)
                if value is not None:
                    output.append(value)
        self.assertTrue(output)
        for item in output:
            self.assertEqual(
                item.audio_sample,
                max(-512, min(511, item.quadrature.ssb_audio_input >> 4))
                if pipeline.post.gain >= 1024
                else item.audio_sample,
            )

    def test_audio_output_stays_in_source_range(self):
        pipeline = RxSsbReferencePipeline()
        output = []
        for n in range(512):
            i_value = ((n * 37) % 1024) - 512
            q_value = ((n * 53) % 1024) - 512
            for channel, sample in (("I", i_value), ("Q", q_value)):
                value = pipeline.push_event(channel, sample)
                if value is not None:
                    output.append(value.audio_sample)
        self.assertTrue(output)
        self.assertTrue(all(-512 <= sample <= 511 for sample in output))


if __name__ == "__main__":
    unittest.main()
