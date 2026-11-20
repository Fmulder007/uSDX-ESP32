"""Tests for the supported SSB slow_dsp() post-processing branches."""

import unittest

from rx_ssb_post import RxSsbPostState


class TestRxSsbPost(unittest.TestCase):
    def test_default_fast_agc_starts_at_unity(self):
        state = RxSsbPostState()
        self.assertEqual(state.gain, 1024)
        self.assertEqual(state.process(0), 0)
        self.assertEqual(state.gain, 1025)

    def test_signed_shift_gives_source_asymmetric_small_sample_update(self):
        positive = RxSsbPostState()
        negative = RxSsbPostState()

        self.assertEqual(positive.process(100, volume=12), 6)
        self.assertEqual(negative.process(-100, volume=12), -7)

        # On the AVR/GCC target, signed right shift is arithmetic:
        # +100 >> 10 == 0, while -100 >> 10 == -1.
        self.assertEqual(positive.gain, 1025)
        self.assertEqual(negative.gain, 1024)

    def test_manual_volume_path_when_agc_is_not_one(self):
        state = RxSsbPostState()
        self.assertEqual(state.process(100, volume=12, agc=0), 50)
        self.assertEqual(state.process(-100, volume=12, agc=0), -50)

    def test_nr_one_is_passthrough_after_volume(self):
        state = RxSsbPostState()
        self.assertEqual(
            state.process(100, volume=13, agc=0, nr=1),
            100,
        )
        self.assertEqual(state.nr_state.ea1, 100)

    def test_nr_eight_integer_deadband_is_visible_in_post_path(self):
        state = RxSsbPostState()
        self.assertEqual(
            state.process(127, volume=13, agc=0, nr=8),
            0,
        )
        self.assertEqual(state.nr_state.ea1, 0)

    def test_ssb_filter_one_is_applied_after_nr_and_volume(self):
        state = RxSsbPostState()
        self.assertEqual(
            state.process(100, volume=13, agc=0, nr=0, filt=1),
            42,
        )

    def test_final_output_clipping(self):
        state = RxSsbPostState()
        self.assertEqual(state.process(20000, volume=12, agc=0), 511)
        self.assertEqual(state.process(-20000, volume=12, agc=0), -512)

    def test_unsupported_modes_and_cw_filters_are_explicit(self):
        state = RxSsbPostState()
        with self.assertRaises(NotImplementedError):
            state.process(10, mode="AM")
        with self.assertRaises(NotImplementedError):
            state.process(10, filt=4)
        with self.assertRaises(ValueError):
            state.process(10, nr=9)


if __name__ == "__main__":
    unittest.main()
