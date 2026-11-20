"""Partial RX SSB reference from timer ADC events to baseline audio.

Stages:
    raw analog I/Q values available at each Timer2 event
      -> source ADMUX/read-previous ADC pipeline
      -> I midpoint interpolation
      -> active NEW_RX CIC schedule
      -> att2 + Hilbert + I delay
      -> baseline SSB fast AGC + volume + clipping

The exact ADC sample-and-hold aperture within each timer event is not modeled.
The first ADC register value after start_rx() is configurable because the
original source does not explicitly start the first conversion before Timer2.
"""

from dataclasses import dataclass, field
from typing import Optional

from rx_adc_input import RxAdcInputState
from rx_ssb_chain import RxSsbOutput, RxSsbReferencePipeline


@dataclass
class RxSsbAdcReferencePipeline:
    """Stateful partial SSB chain accepting Timer2-event I/Q analog values."""

    att2: int = 2
    volume: int = 12
    agc: int = 1
    startup_adc_register: int = 0
    adc_input: RxAdcInputState = field(init=False)
    ssb_chain: RxSsbReferencePipeline = field(init=False)

    def __post_init__(self) -> None:
        self.adc_input = RxAdcInputState(
            startup_adc_register=self.startup_adc_register
        )
        self.ssb_chain = RxSsbReferencePipeline(
            att2=self.att2,
            volume=self.volume,
            agc=self.agc,
        )

    def push_timer_event(
        self,
        i_sample_at_tick: int,
        q_sample_at_tick: int,
    ) -> Optional[RxSsbOutput]:
        """Process one Timer2 event and return audio when phase 0 is reached."""
        channel, sample = self.adc_input.push_tick(
            i_sample_at_tick,
            q_sample_at_tick,
        )
        return self.ssb_chain.push_event(channel, sample)
