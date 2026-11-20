"""Tests for the source-compatible AVR RX ADC input pipeline."""

import unittest

from rx_adc_input import RxAdcInputState


class TestRxAdcInput(unittest.TestCase):
    def test_mux_pipeline_and_i_midpoint_interpolation(self):
        state = RxAdcInputState(startup_adc_register=0)
        i_values = [10, 20, 30, 40, 50, 60, 70, 80, 90]
        q_values = [100, 200, 300, 400, 500, 600, 700, 800, 900]

        actual = [
            state.push_tick(i_values[n], q_values[n])
            for n in range(9)
        ]

        self.assertEqual(
            actual,
            [
                ("I", 0),    # first read is startup ADC register value
                ("Q", 100),  # Q conversion started on event 0
                ("I", 10),   # midpoint of stale/initial I=0 and I=20
                ("Q", 300),  # Q conversion started on event 2
                ("I", 30),   # midpoint of I=20 and I=40
                ("Q", 500),
                ("I", 50),   # midpoint of I=40 and I=60
                ("Q", 700),
                ("I", 70),   # midpoint of I=60 and I=80
            ],
        )

    def test_signed_division_truncates_toward_zero(self):
        state = RxAdcInputState(startup_adc_register=0)
        state.push_tick(0, 0)     # phase 0: start Q conversion
        state.push_tick(-3, 0)    # phase 1: start I conversion with sample -3
        channel, sample = state.push_tick(0, 0)  # phase 2: read previous I
        self.assertEqual(channel, "I")
        self.assertEqual(sample, -1)

    def test_event_sequence_wraps_every_eight_ticks(self):
        state = RxAdcInputState()
        channels = [state.push_tick(n, -n)[0] for n in range(16)]
        self.assertEqual(channels, ["I", "Q"] * 8)
        self.assertEqual(state.phase, 0)

    def test_startup_register_value_is_configurable(self):
        state = RxAdcInputState(startup_adc_register=37)
        channel, sample = state.push_tick(100, 200)
        self.assertEqual(channel, "I")
        self.assertEqual(sample, 18)  # trunc((0 + 37) / 2)


if __name__ == "__main__":
    unittest.main()
