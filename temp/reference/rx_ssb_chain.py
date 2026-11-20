"""Partial source-compatible RX SSB reference pipeline.

Stages:
    alternating logical I/Q events
      -> active NEW_RX CIC
      -> source process() boundary (att2 + Hilbert + I delay)
      -> baseline SSB slow_dsp() (fast AGC + volume + optional NR/SSB IIR)

The input begins after ADC channel demultiplexing. It does not model ADMUX,
ADC conversion pipeline or the original midpoint interpolation on I.
"""

from dataclasses import dataclass, field
from typing import Optional

from rx_cic import RxCicState
from rx_quadrature import RxQuadratureOutput, RxQuadratureState
from rx_ssb_post import RxSsbPostState


@dataclass(frozen=True)
class RxSsbOutput:
    """Intermediate quadrature values plus final supported SSB audio sample."""

    quadrature: RxQuadratureOutput
    audio_sample: int


@dataclass
class RxSsbReferencePipeline:
    """Stateful partial RX SSB chain, one input event at a time."""

    att2: int = 2
    volume: int = 12
    agc: int = 1
    nr: int = 0
    filt: int = 0
    cic: RxCicState = field(default_factory=RxCicState)
    quadrature: RxQuadratureState = field(init=False)
    post: RxSsbPostState = field(default_factory=RxSsbPostState)

    def __post_init__(self) -> None:
        self.quadrature = RxQuadratureState(att2=self.att2)

    def push_event(self, channel: str, sample: int) -> Optional[RxSsbOutput]:
        """Consume one event; return one audio sample when an I/Q pair is ready."""
        raw_pair = self.cic.push_event(channel, sample)
        if raw_pair is None:
            return None

        quadrature = self.quadrature.push_pair(raw_pair[0], raw_pair[1])
        audio = self.post.process(
            quadrature.ssb_audio_input,
            volume=self.volume,
            agc=self.agc,
            nr=self.nr,
            filt=self.filt,
            mode="USB",
        )
        return RxSsbOutput(quadrature=quadrature, audio_sample=audio)
