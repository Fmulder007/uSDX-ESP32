"""Source-compatible RX Hilbert/I-delay stage from PE1NNZ uSDX NEW_RX.

Source snapshot:
    threeme3/usdx @ bf8acd31b8a2506c4e1d203dfb283feecae947e1

Input is the decimated I/Q pair before process() applies att2.
The model applies att2, then reproduces:
- the 14-value Q history and source Hilbert expression;
- the 7-value I delay;
- the SSB sum passed to slow_dsp(): -delayed_I - Hilbert_Q.

The current undelayed I/Q values are also returned because slow_dsp()
uses the global I/Q values for its AM/FM branches.

This model does not implement slow_dsp(), AGC, NR, IIR or audio output.
"""

from dataclasses import dataclass, field
from typing import List


def _trunc_div(numerator: int, denominator: int) -> int:
    """C/C++ signed integer division: truncate toward zero."""
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    if numerator >= 0:
        return numerator // denominator
    return -((-numerator) // denominator)


@dataclass(frozen=True)
class RxQuadratureOutput:
    """Values produced for one decimated I/Q pair."""

    i_current: int
    q_current: int
    i_delayed: int
    q_hilbert: int
    ssb_audio_input: int


@dataclass
class RxQuadratureState:
    """Persistent Hilbert and I-delay state used by process()."""

    att2: int = 2
    q_history: List[int] = field(default_factory=lambda: [0] * 14)
    i_history: List[int] = field(default_factory=lambda: [0] * 7)

    def __post_init__(self) -> None:
        if len(self.q_history) != 14:
            raise ValueError("q_history must contain 14 samples")
        if len(self.i_history) != 7:
            raise ValueError("i_history must contain 7 samples")

    def push_pair(self, i_raw: int, q_raw: int) -> RxQuadratureOutput:
        """Process one I/Q pair after CIC, preserving source operation order."""
        i_current = int(i_raw) >> self.att2
        q_current = int(q_raw) >> self.att2

        v = self.q_history
        q_hilbert = (
            _trunc_div((v[0] - q_current) + (v[2] - v[12]) * 4, 64)
            + _trunc_div((v[4] - v[10]) + (v[6] - v[8]), 8)
            + _trunc_div((v[4] - v[10]) * 5 - (v[6] - v[8]), 128)
            + _trunc_div(v[6] - v[8], 2)
        )

        # Source shifts history only after calculating q_hilbert.
        self.q_history = self.q_history[1:] + [q_current]

        # Source reads v[0] before shifting the 7-sample I delay line.
        i_delayed = self.i_history[0]
        self.i_history = self.i_history[1:] + [i_current]

        return RxQuadratureOutput(
            i_current=i_current,
            q_current=q_current,
            i_delayed=i_delayed,
            q_hilbert=q_hilbert,
            ssb_audio_input=-i_delayed - q_hilbert,
        )
