"""Cycle-level startup timing model for the PE1NNZ uSDX RX ADC pipeline.

This model covers the AVR ADC conversion scheduler, including the extended
first conversion after ADEN is enabled. It is intentionally separate from
rx_adc_input.py, which models the already-running logical I/Q pipeline.
"""

from dataclasses import dataclass
from typing import Callable, Optional


def trunc_div(numerator: int, denominator: int) -> int:
    """C/C++ signed integer division, truncating toward zero."""
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    if numerator >= 0:
        return numerator // denominator
    return -((-numerator) // denominator)


@dataclass(frozen=True)
class _Conversion:
    channel: str
    start_cycle: int
    sample_cycle: int
    complete_cycle: int
    first: bool
    value: int


@dataclass(frozen=True)
class RxAdcTick:
    """Observable state for one Timer2 RX event."""

    event_index: int
    event_cycle: int
    logical_channel: str
    raw_adc: int
    raw_adc_channel: Optional[str]
    raw_adc_sample_cycle: Optional[int]
    aligned_i: Optional[int]
    conversion_started: bool
    started_channel: Optional[str]
    conversion_start_cycle: Optional[int]
    conversion_sample_cycle: Optional[int]
    conversion_complete_cycle: Optional[int]
    first_conversion: bool


class RxAdcTimingModel:
    """Model ADMUX/ADSC/ADC reads on the Timer2 event cadence.

    The source writes the next ADMUX channel, sets ADSC, then reads ADC.
    A write to ADSC while a conversion is already active does not start a
    second conversion. The ADC data register changes only when a conversion
    completes.

    The ADC prescaler is free-running after ADEN. `adc_phase_cycle` defines
    the absolute CPU-cycle phase of its rising edges. `handler_delay_cycles`
    can be supplied per event to explore ISR-path timing differences; zero is
    an intentionally simplified default, not a measured ISR latency.
    """

    def __init__(
        self,
        sample_provider: Callable[[str, int], int],
        *,
        startup_adc_register: int = 0,
        previous_i_sample: int = 0,
        adc_prescaler: int = 16,
        event_period_cpu_cycles: int = 320,
        adc_phase_cycle: int = 0,
        first_conversion_adc_cycles: int = 25,
        normal_conversion_adc_cycles: int = 13,
        first_sample_hold_adc_cycles_x2: int = 27,
        normal_sample_hold_adc_cycles_x2: int = 3,
    ) -> None:
        if adc_prescaler <= 0 or event_period_cpu_cycles <= 0:
            raise ValueError("clock dividers and event period must be positive")
        if first_conversion_adc_cycles <= 0 or normal_conversion_adc_cycles <= 0:
            raise ValueError("conversion lengths must be positive")

        self.sample_provider = sample_provider
        self.adc_prescaler = adc_prescaler
        self.event_period_cpu_cycles = event_period_cpu_cycles
        self.adc_phase_cycle = adc_phase_cycle
        self.first_conversion_adc_cycles = first_conversion_adc_cycles
        self.normal_conversion_adc_cycles = normal_conversion_adc_cycles
        self.first_sample_hold_adc_cycles_x2 = first_sample_hold_adc_cycles_x2
        self.normal_sample_hold_adc_cycles_x2 = normal_sample_hold_adc_cycles_x2

        self.adc_register = int(startup_adc_register)
        self.adc_register_channel: Optional[str] = None
        self.adc_register_sample_cycle: Optional[int] = None
        self.active_conversion: Optional[_Conversion] = None
        self.first_conversion_pending = True
        self.previous_i_sample = int(previous_i_sample)
        self.event_index = 0

    def _next_adc_rising_edge(self, cpu_cycle: int) -> int:
        """Return the first ADC rising edge strictly after ADSC is written."""
        phase = self.adc_phase_cycle
        return phase + ((cpu_cycle - phase) // self.adc_prescaler + 1) * self.adc_prescaler

    def push_tick(self, handler_delay_cycles: int = 0) -> RxAdcTick:
        """Process one Timer2 event; delays are measured from the event edge."""
        if handler_delay_cycles < 0:
            raise ValueError("handler delay cannot be negative")

        event_index = self.event_index
        event_cycle = event_index * self.event_period_cpu_cycles
        write_cycle = event_cycle + handler_delay_cycles

        # A completed conversion updates ADC before software reads the register.
        if (
            self.active_conversion is not None
            and self.active_conversion.complete_cycle <= write_cycle
        ):
            completed = self.active_conversion
            self.adc_register = completed.value
            self.adc_register_channel = completed.channel
            self.adc_register_sample_cycle = completed.sample_cycle
            self.active_conversion = None

        logical_channel = "I" if (event_index & 1) == 0 else "Q"
        next_channel = "Q" if logical_channel == "I" else "I"

        # Mirror `ADMUX = ...; ADCSRA |= (1 << ADSC);`.
        # If conversion is busy, the MUX write is retained for the next start,
        # but ADSC is already one and no second conversion begins.
        started = False
        started_channel: Optional[str] = None
        start_cycle: Optional[int] = None
        sample_cycle: Optional[int] = None
        complete_cycle: Optional[int] = None
        is_first = False

        if self.active_conversion is None:
            is_first = self.first_conversion_pending
            start_cycle = self._next_adc_rising_edge(write_cycle)
            if is_first:
                conversion_cycles = self.first_conversion_adc_cycles
                aperture_x2 = self.first_sample_hold_adc_cycles_x2
            else:
                conversion_cycles = self.normal_conversion_adc_cycles
                aperture_x2 = self.normal_sample_hold_adc_cycles_x2

            # x2 representation preserves the half-ADC-clock sample aperture.
            sample_cycle = start_cycle + (
                aperture_x2 * self.adc_prescaler // 2
            )
            complete_cycle = (
                start_cycle + conversion_cycles * self.adc_prescaler
            )
            value = int(self.sample_provider(next_channel, sample_cycle))
            self.active_conversion = _Conversion(
                channel=next_channel,
                start_cycle=start_cycle,
                sample_cycle=sample_cycle,
                complete_cycle=complete_cycle,
                first=is_first,
                value=value,
            )
            self.first_conversion_pending = False
            started = True
            started_channel = next_channel

        raw_adc = self.adc_register
        raw_channel = self.adc_register_channel
        raw_sample_cycle = self.adc_register_sample_cycle

        aligned_i: Optional[int] = None
        if logical_channel == "I":
            aligned_i = trunc_div(self.previous_i_sample + raw_adc, 2)
            self.previous_i_sample = raw_adc

        self.event_index += 1
        return RxAdcTick(
            event_index=event_index,
            event_cycle=event_cycle,
            logical_channel=logical_channel,
            raw_adc=raw_adc,
            raw_adc_channel=raw_channel,
            raw_adc_sample_cycle=raw_sample_cycle,
            aligned_i=aligned_i,
            conversion_started=started,
            started_channel=started_channel,
            conversion_start_cycle=start_cycle,
            conversion_sample_cycle=sample_cycle,
            conversion_complete_cycle=complete_cycle,
            first_conversion=is_first,
        )
