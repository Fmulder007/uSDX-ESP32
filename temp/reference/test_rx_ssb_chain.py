"""Tests for the partial CIC -> quadrature -> baseline SSB chain."""

import unittest

from rx_ssb_chain import RxSsbReferencePipeline
from rx_ssb_post import RxSsbPostState


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

    def test_quadrature_values_feed_the_baseline_post_stage(self):
        pipeline = RxSsbReferencePipeline(att2=0, volume=12)
        expected_post = RxSsbPostState()
        output = []
        for n in range(64):
            i_sample = ((n * 17) % 256) - 128
            q_sample = ((n * 29) % 256) - 128
            for channel, sample in (("I", i_sample), ("Q", q_sample)):
                value = pipeline.push_event(channel, sample)
                if value is not None:
                    output.append(value)
        self.assertTrue(output)
        for item in output:
            expected = expected_post.process(
                item.quadrature.ssb_audio_input,
                volume=12,
                agc=1,
                nr=0,
                filt=0,
                mode="USB",
            )
            self.assertEqual(item.audio_sample, expected)

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
