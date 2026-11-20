"""Idealized steady-state AVR ADC mux/read-previous input model for RX.

This model does not reproduce the 25-cycle first conversion after ADEN;\nsee rx_adc_timing.py for the startup conversion scheduler.\n\nThe uSDX ISR selects the MUX for the next conversion, starts that conversion,
then reads the ADC data register containing the preceding conversion result.
The first read after start_rx() is a startup register value, because the
source configures ADC but does not explicitly start a conversion there.

This model represents the analog value captured by a conversion started at
each timer event. The exact ADC sample-and-hold aperture within the event
is not modeled; both channels use the same event-relative aperture.

Expected handler order: I,Q,I,Q,I,Q,...
- An I handler starts the next Q conversion, then reads previous I result.
- A Q handler starts the next I conversion, then reads previous Q result.
- The I result is midpoint-interpolated with the previous I result.
"""

from dataclasses import dataclass
from typing import Optional, Tuple


def trunc_div(numerator: int, denominator: int) -> int:
    """C/C++ signed integer division, truncating toward zero."""
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    if numerator >= 0:
        return numerator // denominator
    return -((-numerator) // denominator)


@dataclass
class RxAdcInputState:
    """Persistent ADC MUX pipeline and I midpoint interpolation state."""

    startup_adc_register: int = 0
    pending_channel: Optional[str] = None
    pending_sample: int = 0
    previous_i_sample: int = 0
    phase: int = 0

    def push_tick(self, i_sample_at_tick: int, q_sample_at_tick: int) -> Tuple[str, int]:
        """Process one Timer2 event and return the logical I or Q sample.

        i_sample_at_tick/q_sample_at_tick are analog values available to a
        conversion started on this timer event. Only the channel selected
        for the next conversion is captured; its result is returned next tick.
        """
        expected_channel = "I" if self.phase in (0, 2, 4, 6) else "Q"

        if self.pending_channel is None:
            # First ADC data-register read after start_rx(): source does not
            # explicitly start a conversion before the first Timer2 event.
            raw_previous_result = int(self.startup_adc_register)
        else:
            if self.pending_channel != expected_channel:
                raise RuntimeError(
                    "ADC pipeline mismatch: event phase {} expects previous {}, "
                    "but pending conversion is {}".format(
                        self.phase, expected_channel, self.pending_channel
                    )
                )
            raw_previous_result = int(self.pending_sample)

        # Mirror the source: choose MUX and start the NEXT conversion before
        # reading the previous ADC register.
        next_channel = "Q" if expected_channel == "I" else "I"
        self.pending_channel = next_channel
        self.pending_sample = int(
            q_sample_at_tick if next_channel == "Q" else i_sample_at_tick
        )

        if expected_channel == "I":
            aligned_i = trunc_div(self.previous_i_sample + raw_previous_result, 2)
            self.previous_i_sample = raw_previous_result
            result = aligned_i
        else:
            result = raw_previous_result

        self.phase = (self.phase + 1) & 0x07
        return expected_channel, result
