# Candidate Hilbert FIRs for the 650…3400 Hz RX band

**Status:** two flat-gain experimental Hilbert filters designed, Q15-quantized and tested in isolation. A later full-chain test showed they are not suitable as drop-in replacements because the source I midpoint average creates a Q/I gain mismatch which the original filter partly compensates. The active PE1NNZ 15-tap filter is unchanged.

## 1. Design target and method

- Actual decimated I/Q pair sample rate: 7812.5 SPS.
- Target passband: 650…3400 Hz.
- FIR type: odd-length, antisymmetric Type-III Hilbert transformer.
- Design: equiripple Remez, then symmetric Q15 quantization.
- Coefficient sign was chosen to preserve the current source Hilbert polarity.
- The matching I delay is the FIR group delay (N-1)/2.

These designs optimize an isolated, equal-amplitude I/Q Hilbert block. That is useful for understanding the FIR itself, but it is not the source's complete image-rejection scenario: the upstream I midpoint interpolator changes I amplitude with frequency. See 19_RX_HILBERT_IMAGE_REJECTION.md for the complete ADC-input → CIC → Hilbert comparison, and 21_RX_HILBERT_CIC_COMPENSATION.md for filters designed against that real input-path mismatch.

## 2. Candidate results

All candidate values below use quantized Q15 coefficients and truncation toward zero after the FIR accumulator.

| Filter | Taps | Non-zero symmetric pairs | I delay | Extra delay vs current | Analytic minimum IRR, 650…3400 Hz | Time-domain IRR at 3400 Hz |
|---|---:|---:|---:|---:|---:|---:|
| Current source | 15 | 4 | 7 | — | 27.36 dB | 27.13 dB |
| Remez candidate | 17 | 8 | 8 | +1 pair | 42.24 dB | 41.88 dB |
| **Candidate A** | **19** | **9** | **9** | **+2 pairs** | **47.80 dB** | **47.11 dB** |
| Candidate B | 23 | 11 | 11 | +4 pairs | 55.64 dB | 54.20 dB |

In isolation, Candidate A and Candidate B meet the target comfortably. **They are not recommended for direct substitution in the uSDX RX path.** The full-chain comparison shows that flattening Hilbert amplitude can reduce image rejection at parts of the band because it removes compensation for the I midpoint average. Use these flat candidates as FIR reference experiments only.

Time-domain test setup: I=cos(2πfn/fs), Q=±sin(2πfn/fs), 1000-count amplitude, 8192 samples, first 256 discarded. IRR is the ratio of the two output RMS levels. This is an isolated quadrature-stage test, not an end-to-end RF performance measurement.

## 3. Candidate A — 19 taps, Q15

Group delay: **9 I/Q pairs** (about 1.152 ms at 7812.5 SPS).

    [-482, -3, -1210, -7, -2704, -9, -5980, -6, -20520,
         0,
      20520, 6, 5980, 9, 2704, 7, 1210, 3, 482]

The tap sequence is exactly antisymmetric. In pair form the implementation needs nine products of an integer coefficient by a difference between symmetric Q samples, plus one accumulator. I must be delayed by nine pairs.

- Time-domain IRR at 650 Hz: 48.57 dB.
- Time-domain IRR at 3400 Hz: 47.11 dB.
- Worst-case accumulator bound for arbitrary signed-int16 input samples: 2,026,407,735, which fits signed int32 (margin 121,075,912).
- For Q samples constrained to ±4096 after default att2=2, the accumulator bound is 253,304,832.

## 4. Candidate B — 23 taps, Q15

Group delay: **11 I/Q pairs** (about 1.408 ms).

    [-226, -7, -626, -17, -1423, -26, -2908, -27, -6128, -17, -20573,
         0,
      20573, 17, 6128, 27, 2908, 26, 1423, 17, 626, 7, 226]

- Time-domain IRR at 650 Hz: 57.42 dB.
- Time-domain IRR at 3400 Hz: 54.20 dB.
- Worst-case accumulator bound for arbitrary signed-int16 input samples: 2,095,678,230, which fits signed int32 (margin 51,805,417).
- At default att2=2, bound is 261,963,776.

## 5. Scope correction after the full-chain test

reference/rx_hilbert_candidates.py contains both candidate coefficient sets and a stateful test model. It:
- applies att2 before the Hilbert FIR;
- accumulates Q15 products in a wide integer;
- divides by 32768 with C-style truncation toward zero;
- delays I by the exact candidate group delay.

The model is not the production ESP32 implementation. For a C++ port, use a signed int32 accumulator for these two candidate tables with the stated input range, and retain the exact Q15 coefficients. Do not shorten or re-order the accumulation without rerunning tests.

The full steady-state CIC + Hilbert check is now available in 19_RX_HILBERT_IMAGE_REJECTION.md. It shows that a replacement should target the amplitude response introduced by I midpoint interpolation. The compensated 23/27-tap candidates are documented separately in 21_RX_HILBERT_CIC_COMPENSATION.md. Remaining checks are exact ADC aperture/startup, analog I/Q mismatch, SSB/USB/LSB audio response, and ESP32 cycle profiling. No active filter has been changed.

