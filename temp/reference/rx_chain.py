"""Partial source-compatible RX reference chain: CIC -> Hilbert/I delay.

This joins only the two currently modeled RX blocks. It stops before
slow_dsp(), AGC, NR, IIR and the audio output interpolator.
"""

from dataclasses import dataclass, field
from typing import Optional

from rx_cic import RxCicState
from rx_quadrature import RxQuadratureOutput, RxQuadratureState


@dataclass
class RxReferencePipeline:
    """Process interleaved I/Q events through CIC and quadrature alignment."""

    att2: int = 2
    cic: RxCicState = field(default_factory=RxCicState)
    quadrature: RxQuadratureState = field(init=False)

    def __post_init__(self) -> None:
        self.quadrature = RxQuadratureState(att2=self.att2)

    def push_event(self, channel: str, sample: int) -> Optional[RxQuadratureOutput]:
        """Consume one I/Q event; return output only when a pair is ready."""
        raw_pair = self.cic.push_event(channel, sample)
        if raw_pair is None:
            return None
        return self.quadrature.push_pair(raw_pair[0], raw_pair[1])
