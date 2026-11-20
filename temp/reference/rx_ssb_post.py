"""Partial source-compatible SSB slow_dsp() post-processing reference.

Implements:
- USB/LSB/CW path (no AM/FM demodulation);
- selected build with FAST_AGC compile option disabled;
- agc == 1: process_agc_fast();
- volume scaling;
- NR=0..8 exponential smoother;
- SSB filt=0..3 IIR path;
- final -512..511 clamp.

All DSP stages are reference models. NR and IIR use wide Python intermediates;
they are not a bit-exact AVR signed-overflow emulator. CW IIR filters 4..7 and
AM/FM demodulation remain unsupported.
"""

from dataclasses import dataclass, field

from rx_iir import RxSsbIirState
from rx_nr import RxNrState


INT16_MIN = -32768
INT16_MAX = 32767


def wrap_i16(value: int) -> int:
    """Wrap to signed 16-bit at the existing baseline input/AGC boundaries."""
    value &= 0xFFFF
    return value if value < 0x8000 else value - 0x10000


@dataclass
class RxSsbPostState:
    """Persistent state for baseline AGC plus optional NR and SSB IIR."""

    gain: int = 1024
    nr_state: RxNrState = field(default_factory=RxNrState)
    iir_state: RxSsbIirState = field(default_factory=RxSsbIirState)

    def process(
        self,
        audio_input: int,
        *,
        volume: int = 12,
        agc: int = 1,
        nr: int = 0,
        filt: int = 0,
        mode: str = "USB",
    ) -> int:
        """Process one demodulated sample through the supported SSB path."""
        if mode not in ("USB", "LSB", "CW"):
            raise NotImplementedError("AM/FM demodulation is not in this model")
        if not 0 <= volume <= 16:
            raise ValueError("volume must be in the source range 0..16")
        if not 0 <= nr <= 8:
            raise ValueError("NR must be in the source range 0..8")
        if filt not in (0, 1, 2, 3):
            raise NotImplementedError("CW IIR filters 4..7 are not yet modeled")

        ac = wrap_i16(audio_input)

        if agc == 1:
            if self.gain >= 1024:
                out = wrap_i16((self.gain >> 10) * ac)
            else:
                out = ac

            accum = 1 - abs(out >> 10)
            if (INT16_MAX - self.gain) > accum:
                self.gain = wrap_i16(self.gain + accum)
            if self.gain < 1:
                self.gain = 1

            # Source slow_dsp(): AGC output then volume shift.
            ac = out >> (16 - volume)
        else:
            # FAST_AGC is disabled in the selected source configuration.
            if volume <= 13:
                ac = ac >> (13 - volume)
            else:
                ac = wrap_i16(ac << (volume - 13))

        # Source order: NR after AGC/volume, then optional filt_var().
        ac = self.nr_state.push(ac, nr)
        ac = self.iir_state.push(ac, filt)

        return min(max(ac, -512), 511)
