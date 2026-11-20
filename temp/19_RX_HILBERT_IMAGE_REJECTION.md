# Hilbert FIR: isolated response versus the complete RX image-rejection path

**Important correction:** a standalone Hilbert response is not the same as the source's image-rejection scenario. The input path applies a two-sample midpoint average to I before the CIC. That operation creates a frequency-dependent I/Q gain mismatch which the original Hilbert filter partly compensates.

## 1. Isolated Hilbert result

The current source coefficient sequence is:

    [-2, 0, -8, 0, -21, 0, -79, 0, 79, 0, 21, 0, 8, 0, 2] / 128

As an isolated quadrature block with ideal equal-amplitude I and Q input, it gives approximately:

| Frequency | At 8000 SPS | At 7812.5 SPS |
|---:|---:|---:|
| 650 Hz | 43.94 dB analytic | 47.82 dB analytic |
| 3400 Hz | 35.77 dB analytic | 27.36 dB analytic |

The time-domain isolated test gives 35.19 dB at 3400 Hz / 8000 SPS and 27.13 dB at 3400 Hz / 7812.5 SPS. These numbers are valid for the isolated FIR, but they do not include the upstream I midpoint interpolation.

## 2. Why the source filter is not a flat-gain Hilbert

In the active ADC path, neighbouring I-channel samples are averaged:

    I_aligned[n] = (I[n] + I[n-1]) / 2

The I channel sampling rate is 31,250 samples/s. For a sinusoid, this two-sample average has magnitude response:

    A_I(f) = cos(pi*f/31250)

Q does not get this averaging. Before the Hilbert stage, the Q/I amplitude ratio is therefore approximately:

    A_Q(f) / A_I(f) = 1 / cos(pi*f/31250)

This ratio grows from about 1.0028 at 650 Hz to about 1.0620 at 3400 Hz. The CIC applies the same magnitude response to both branches. The original Hilbert FIR's amplitude roll-off therefore partly counteracts the upstream mismatch.

This also explains why the flat unity-magnitude candidates in 20_RX_HILBERT_CANDIDATES.md are not drop-in replacements: they remove the compensation which the original path relies on.

## 3. End-to-end steady-state test

The correct comparison is made after:

1. ADC MUX/read-previous model and I midpoint averaging;
2. the original eight-phase CIC;
3. the candidate Hilbert and its matching I delay.

The model uses a 62.5 kHz timer event rate, centered sine inputs with amplitude 511, att2=2, two opposite Q polarities, and compares output RMS after warm-up. Sample rate after CIC is 7812.5 I/Q pairs/s.

| Audio frequency | Source 15 taps | Flat 19 taps | Flat 23 taps |
|---:|---:|---:|---:|
| 650 Hz | 50.55 dB | 45.45 dB | 50.71 dB |
| 1000 Hz | 57.95 dB | 58.36 dB | 48.05 dB |
| 1500 Hz | 46.56 dB | 51.50 dB | 44.43 dB |
| 2000 Hz | 39.79 dB | 37.10 dB | 41.16 dB |
| 2500 Hz | 38.02 dB | 36.29 dB | 36.67 dB |
| 2750 Hz | 38.63 dB | 32.76 dB | 34.01 dB |
| 3000 Hz | 32.57 dB | 34.28 dB | 32.70 dB |
| 3200 Hz | 31.17 dB | 31.18 dB | 31.82 dB |
| 3400 Hz | 37.37 dB | 31.76 dB | 30.96 dB |

A wider sweep in 50 Hz steps over 650…3400 Hz found:
- original source chain: minimum about 30.67 dB near 3150 Hz;
- flat 19-tap candidate: local dips around 3200…3400 Hz;
- flat 23-tap candidate: no better as a general drop-in option.

**Interpretation:** this steady-state ideal model does not reproduce 43 dB uniformly across the complete band. However, it also shows that the isolated-Hilbert calculation was incomplete. Do not conclude the original author's measurement is wrong until exact AVR timing, analog acquisition, gain/phase mismatch, and the precise image-rejection setup are reproduced.

## 4. Correct design target

The replacement filter must compensate the I midpoint response, not flatten it. The desired Hilbert magnitude is approximately:

    |H_target(f)| = cos(pi*f/31250)

with the required quadrature phase and original polarity. Two Q15 candidates fitted to this target and tested through the full steady-state chain are documented in 21_RX_HILBERT_CIC_COMPENSATION.md:

- 23 taps: minimum about 46.29 dB in the 50 Hz frequency sweep;
- 27 taps: minimum about 53.20 dB in the same sweep.

The original 15-tap coefficients and all flat candidates are retained as comparison baselines. No production filter has been replaced.
