"""Image-rejection check for the PE1NNZ 15-tap RX Hilbert FIR."""

import math
import unittest

from rx_quadrature import RxQuadratureState


def image_rejection_db(
    frequency_hz: float,
    sample_rate_hz: float,
    amplitude: int = 1000,
    sample_count: int = 8192,
) -> float:
    """Compare the two quadrature orientations through the actual FIR model."""
    levels = []
    for q_sign in (1, -1):
        state = RxQuadratureState(att2=0)
        squares = []
        for n in range(sample_count):
            phase = 2.0 * math.pi * frequency_hz * n / sample_rate_hz
            i_sample = round(amplitude * math.cos(phase))
            q_sample = round(q_sign * amplitude * math.sin(phase))
            output = state.push_pair(i_sample, q_sample).ssb_audio_input
            if n >= 256:
                squares.append(output * output)
        rms = math.sqrt(sum(squares) / len(squares))
        levels.append(rms)

    weak, strong = sorted(levels)
    if weak == 0:
        return float("inf")
    return 20.0 * math.log10(strong / weak)


class TestRxHilbertImageRejection(unittest.TestCase):
    def test_comment_range_at_nominal_8ksps(self):
        low_edge = image_rejection_db(650.0, 8000.0)
        high_edge = image_rejection_db(3400.0, 8000.0)

        self.assertGreater(low_edge, 40.0)
        self.assertGreater(high_edge, 33.0)
        self.assertLess(high_edge, 38.0)

    def test_actual_rx_pair_rate_reduces_upper_edge_rejection(self):
        low_edge = image_rejection_db(650.0, 7812.5)
        high_edge = image_rejection_db(3400.0, 7812.5)

        self.assertGreater(low_edge, 43.0)
        self.assertGreater(high_edge, 25.0)
        self.assertLess(high_edge, 30.0)

    def test_fir_hilbert_impulse_coefficients_and_seven_sample_delay(self):
        state = RxQuadratureState(att2=0)
        response = []
        for n in range(15):
            result = state.push_pair(0, 128 if n == 0 else 0)
            response.append(result.q_hilbert)

        self.assertEqual(
            response,
            [-2, 0, -8, 0, -21, 0, -79, 0, 79, 0, 21, 0, 8, 0, 2],
        )


if __name__ == "__main__":
    unittest.main()
