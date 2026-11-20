"""Source-compatible baseline SSB slow_dsp() post-processing.

Scope:
- USB/LSB/CW path (no AM/FM demodulation);
- FAST_AGC compile option disabled;
- agc == 1: process_agc_fast();
- nr == 0 and filt == 0;
- volume scaling and final -512..511 clamp.

Unsupported paths raise NotImplementedError rather than silently approximating
NR, IIR filters, AM or FM.
"""

from dataclasses import dataclass


INT16_MIN = -32768
INT16_MAX = 32767


def wrap_i16(value: int) -> int:
    """Wrap to signed 16-bit as observed on the AVR target."""
    value &= 0xFFFF
    return value if value < 0x8000 else value - 0x10000


@dataclass
class RxSsbPostState:
    """Persistent state for the default SSB post-processing path."""

    gain: int = 1024

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
        """Process one demodulated SSB sample through baseline slow_dsp()."""
        if mode not in ("USB", "LSB", "CW"):
            raise NotImplementedError("AM/FM demodulation is not in this model")
        if nr != 0:
            raise NotImplementedError("NR is not in this model")
        if filt != 0:
            raise NotImplementedError("IIR filtering is not in this model")
        if not 0 <= volume <= 16:
            raise ValueError("volume must be in the source range 0..16")

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

        return min(max(ac, -512), 511)
