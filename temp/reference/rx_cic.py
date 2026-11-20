"""Source-scheduled RX CIC reference model for PE1NNZ uSDX NEW_RX path.

Source snapshot:
    threeme3/usdx @ bf8acd31b8a2506c4e1d203dfb283feecae947e1

This module models the active eight-event CIC state machine only.
Input samples must already be assigned to their logical I/Q channels.
ADC mux scheduling, sample-and-hold timing and I interpolation are
documented separately in ../09_ADC_TIMING.md.

Arithmetic uses Python integers. For the original ADC range (-511..512),
the CIC intermediate values remain within signed 16-bit range for this
filter/scaling configuration. The output pair is raw CIC data before att2;
att2 is applied by RxQuadratureState, matching the source process() boundary.
"""

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

Channel = str
IqPair = Tuple[int, int]


@dataclass
class RxCicState:
    """Persistent state of the active NEW_RX=1 CIC schedule."""

    phase: int = 0

    # I branch state, copied by role from the source variables.
    i_s0za1: int = 0
    i_s0zb0: int = 0
    i_s0zb1: int = 0
    i_s1za1: int = 0
    i_s1zb0: int = 0
    i_s1zb1: int = 0

    # Q branch state.
    q_s0za1: int = 0
    q_s0zb0: int = 0
    q_s0zb1: int = 0
    q_s1za1: int = 0
    q_s1zb0: int = 0
    q_s1zb1: int = 0

    # Global source variable: Q result is produced on phase 7 and consumed
    # by process() on the following phase 0.
    q_ac2: int = 0

    def push_event(self, channel: Channel, sample: int) -> Optional[IqPair]:
        """Consume one source-ordered ADC sample.

        Required order is I,Q,I,Q,I,Q,I,Q, repeating.
        Returns one (I,Q) pair on phase 0; other phases return None.

        The first output pair after construction has Q=0 because the source
        state q_ac2 is initially zero and its first calculated value appears
        only on phase 7. This startup transient is preserved deliberately.
        """
        if channel not in ("I", "Q"):
            raise ValueError("channel must be 'I' or 'Q'")

        expected = "I" if self.phase in (0, 2, 4, 6) else "Q"
        if channel != expected:
            raise ValueError(
                "event order error: phase {} expects {}, received {}".format(
                    self.phase, expected, channel
                )
            )

        output: Optional[IqPair] = None
        phase = self.phase
        x = int(sample)

        if phase == 0:
            # sdr_rx_00(): even I polyphase output, then second CIC stage.
            i_s1za0 = (
                x + 3 * (self.i_s0za1 + self.i_s0zb0) + self.i_s0zb1
            ) >> 1
            self.i_s0za1 = x

            i_ac2 = (
                i_s1za0
                + 3 * (self.i_s1za1 + self.i_s1zb0)
                + self.i_s1zb1
            )
            self.i_s1za1 = i_s1za0

            # Return raw CIC outputs. Source process() applies att2 after
            # this boundary; RxQuadratureState models that next operation.
            output = (i_ac2, self.q_ac2)

        elif phase == 1:
            # sdr_rx_01(): update first-stage Q odd history.
            self.q_s0zb1 = self.q_s0zb0
            self.q_s0zb0 = x

        elif phase == 2:
            # sdr_rx_02(): update first-stage I odd history.
            self.i_s0zb1 = self.i_s0zb0
            self.i_s0zb0 = x

        elif phase == 3:
            # sdr_rx_03(): calculate and store first-stage Q odd output.
            q_s1za0 = (
                x + 3 * (self.q_s0za1 + self.q_s0zb0) + self.q_s0zb1
            ) >> 1
            self.q_s1zb1 = self.q_s1zb0
            self.q_s1zb0 = q_s1za0
            self.q_s0za1 = x

        elif phase == 4:
            # sdr_rx_04(): calculate and store first-stage I odd output.
            i_s1za0 = (
                x + 3 * (self.i_s0za1 + self.i_s0zb0) + self.i_s0zb1
            ) >> 1
            self.i_s1zb1 = self.i_s1zb0
            self.i_s1zb0 = i_s1za0
            self.i_s0za1 = x

        elif phase == 5:
            # sdr_rx_05(): update first-stage Q odd history.
            self.q_s0zb1 = self.q_s0zb0
            self.q_s0zb0 = x

        elif phase == 6:
            # sdr_rx_06(): update first-stage I odd history.
            self.i_s0zb1 = self.i_s0zb0
            self.i_s0zb0 = x

        else:  # phase == 7
            # sdr_rx_07(): calculate even Q output and save q_ac2.
            q_s1za0 = (
                x + 3 * (self.q_s0za1 + self.q_s0zb0) + self.q_s0zb1
            ) >> 1
            self.q_s0za1 = x

            self.q_ac2 = (
                q_s1za0
                + 3 * (self.q_s1za1 + self.q_s1zb0)
                + self.q_s1zb1
            )
            self.q_s1za1 = q_s1za0

        self.phase = (phase + 1) & 0x07
        return output


def process_iq_stream(
    i_samples: Sequence[int],
    q_samples: Sequence[int],
) -> List[IqPair]:
    """Feed equally sized I and Q arrays in source interleaved order."""
    if len(i_samples) != len(q_samples):
        raise ValueError("I and Q input arrays must have equal length")

    state = RxCicState()
    output: List[IqPair] = []

    for i_sample, q_sample in zip(i_samples, q_samples):
        pair = state.push_event("I", i_sample)
        if pair is not None:
            output.append(pair)

        pair = state.push_event("Q", q_sample)
        if pair is not None:
            output.append(pair)

    return output
