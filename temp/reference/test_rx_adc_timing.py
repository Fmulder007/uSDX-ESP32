"""Tests for the AVR RX ADC conversion-startup timing model."""

import unittest

from rx_adc_timing import RxAdcTimingModel


class TestRxAdcTimingModel(unittest.TestCase):
    def setUp(self):
        # Constant but clearly distinguishable analog inputs.
        self.model = RxAdcTimingModel(
            lambda channel, _cycle: {"I": 1000, "Q": 2000}[channel],
            startup_adc_register=77,
        )

    def test_first_conversion_misses_the_next_timer_event(self):
        ticks = [self.model.push_tick() for _ in range(5)]

        # Event 0 starts the 25-ADC-clock first conversion and reads old data.
        self.assertTrue(ticks[0].first_conversion)
        self.assertEqual(ticks[0].started_channel, "Q")
        self.assertEqual(ticks[0].raw_adc, 77)

        # Event 1 occurs after 320 CPU cycles, but the first conversion needs
        # 400 CPU cycles after its ADC-clock start. ADSC is still set.
        self.assertFalse(ticks[1].conversion_started)
        self.assertEqual(ticks[1].raw_adc, 77)

        # Event 2 finally reads the first conversion result. It is Q data,
        # even though this timer slot is logically the I handler.
        self.assertEqual(ticks[2].raw_adc, 2000)
        self.assertEqual(ticks[2].raw_adc_channel, "Q")
        self.assertEqual(ticks[2].logical_channel, "I")

    def test_normal_alternation_is_restored_after_the_startup_slot(self):
        ticks = [self.model.push_tick() for _ in range(7)]
        self.assertEqual(
            [(t.logical_channel, t.raw_adc_channel) for t in ticks[2:7]],
            [
                ("I", "Q"),  # first conversion mislabelled by startup
                ("Q", "Q"),
                ("I", "I"),
                ("Q", "Q"),
                ("I", "I"),
            ],
        )

    def test_sample_hold_apertures_use_first_and_normal_timing(self):
        first = self.model.push_tick()
        self.assertEqual(
            first.conversion_sample_cycle - first.conversion_start_cycle,
            216,
        )
        self.model.push_tick()  # first conversion is still busy
        normal = self.model.push_tick()
        self.assertEqual(
            normal.conversion_sample_cycle - normal.conversion_start_cycle,
            24,
        )

    def test_i_midpoint_uses_mislabelled_startup_result_once_more(self):
        ticks = [self.model.push_tick() for _ in range(7)]
        self.assertEqual(ticks[2].aligned_i, 1038)  # trunc((77 + 2000) / 2)
        self.assertEqual(ticks[4].aligned_i, 1500)  # trunc((2000 + 1000) / 2)
        self.assertEqual(ticks[6].aligned_i, 1000)  # steady state


if __name__ == "__main__":
    unittest.main()
