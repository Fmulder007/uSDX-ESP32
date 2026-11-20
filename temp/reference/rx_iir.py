"""Wide-intermediate reference model of the SSB filt_var() branches.

This preserves source expression order and arithmetic right shifts, but Python
integers do not overflow like AVR 16-bit int. It is a mathematical baseline,
not a bit-exact AVR-GCC emulator.
"""

from dataclasses import dataclass


@dataclass
class RxSsbIirState:
    """Persistent SSB IIR state shared across filter IDs 1, 2 and 3."""

    zz1: int = 0
    zz2: int = 0
    za1: int = 0
    za2: int = 0
    zb0: int = 0
    zb1: int = 0
    zb2: int = 0
    zc0: int = 0
    zc1: int = 0
    zc2: int = 0

    def reset(self) -> None:
        """Explicit test/helper reset; the original filt_var() has no such reset."""
        self.zz1 = self.zz2 = 0
        self.za1 = self.za2 = 0
        self.zb0 = self.zb1 = self.zb2 = 0
        self.zc0 = self.zc1 = self.zc2 = 0

    def push(self, sample: int, filt: int) -> int:
        """Process one sample with SSB filter 1..3, or bypass with filt=0.

        Bypass returns the input and leaves all stored filter histories
        unchanged, matching slow_dsp() which does not call filt_var() at all
        when filt==0. CW filters 4..7 are intentionally not implemented here.
        """
        value = int(sample)
        if filt == 0:
            return value
        if filt not in (1, 2, 3):
            raise ValueError("SSB filter ID must be 0..3")

        # Shared input section. Preserve the exact order of the source:
        # zz2=zz1; zz1=za0; then use the newly assigned zz2 and zz1.
        old_zz1 = self.zz1
        self.zz2 = old_zz1
        self.zz1 = value
        za0 = (30 * (value - self.zz2) + 25 * self.zz1) >> 5

        # First Direct Form I biquad section.
        if filt == 1:
            zb0 = ((za0 + 2 * self.za1 + self.za2) >> 1) - (
                (13 * self.zb1 + 11 * self.zb2) >> 4
            )
        elif filt == 2:
            zb0 = ((za0 + 2 * self.za1 + self.za2) >> 1) - (
                (2 * self.zb1 + 8 * self.zb2) >> 4
            )
        else:
            zb0 = ((za0 + 2 * self.za1 + self.za2) >> 1) - (
                (0 * self.zb1 + 4 * self.zb2) >> 4
            )

        # Second Direct Form I biquad section.
        if filt == 1:
            zc0 = ((zb0 + 2 * self.zb1 + self.zb2) >> 1) - (
                (18 * self.zc1 + 11 * self.zc2) >> 4
            )
        elif filt == 2:
            zc0 = ((zb0 + 2 * self.zb1 + self.zb2) >> 2) - (
                (4 * self.zc1 + 8 * self.zc2) >> 4
            )
        else:
            zc0 = ((zb0 + 2 * self.zb1 + self.zb2) >> 2) - (
                (0 * self.zc1 + 4 * self.zc2) >> 4
            )

        # Match the source history update order.
        self.zc2 = self.zc1
        self.zc1 = zc0
        self.zb2 = self.zb1
        self.zb1 = zb0
        self.za2 = self.za1
        self.za1 = za0
        self.zb0 = zb0
        self.zc0 = zc0

        return zc0
