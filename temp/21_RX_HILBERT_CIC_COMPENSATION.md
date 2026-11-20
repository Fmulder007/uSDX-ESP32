# Hilbert FIR, компенсирующий I midpoint interpolation и CIC

**Статус:** после полного ADC-midpoint → CIC → Hilbert sweep найдены компактные minimax Q15-кандидаты. Самый короткий из проверенных фильтров, проходящий 43 dB во всём sweep, — 19 taps. Исходный 15-tap FIR не заменён.

## 1. Откуда возникает Q/I amplitude mismatch

В sdr_rx_common_i() исходник усредняет соседние I conversions:

    I_aligned[n] = (I[n] + I[n-1]) / 2

I stream имеет 31 250 samples/s. Для синусоиды частоты f такое среднее имеет амплитудный коэффициент:

    A_I(f) = cos(pi*f/31250)

Q branch этой двухточечной коррекции не получает. Поэтому перед Hilbert:

    A_Q(f) / A_I(f) = 1 / cos(pi*f/31250)

Между 650 и 3400 Hz отношение Q/I растёт примерно от 1.0028 до 1.0620. CIC имеет одинаковую magnitude response по I и Q, поэтому сам по себе это отношение не устраняет.

Исходный Hilbert FIR не является плоским по амплитуде: его roll-off частично компенсирует дисбаланс I/Q, созданный midpoint average. Поэтому плоские Remez candidates из 20_RX_HILBERT_CANDIDATES.md не подходят как drop-in replacement.

## 2. Цель и два способа подгонки

Чтобы уравнять ветви, Hilbert magnitude должна приближать:

    |H_target(f)| = cos(pi*f/31250)

при сохранении нужной quadrature phase и source polarity.

В репозитории сохранены два типа приближения:
- **Minimax relative fit** для 17/19/21 taps: минимизируется максимальная относительная ошибка амплитуды относительно target по всей полосе.
- **Least-squares fit** для более длинных 23/27 taps: сохранены как варианты для сравнения, но они не минимизируют худший image-rejection ripple так эффективно, как компактный 19-tap minimax.

Все коэффициенты Type-III antisymmetric, симметрично квантованы в Q15. Групповая задержка Q FIR компенсируется такой же задержкой I.

## 3. Полная проверка: ADC midpoint → CIC → candidate Hilbert

Использована steady-state chain:

1. RxAdcInputState: I/Q ADC mux/read-previous и I midpoint interpolation;
2. RxCicState: исходная восьмифазная CIC;
3. RxHilbertCandidateState: Q15 candidate и соответствующая I delay.

На каждом Timer2 event подаются:

    I = round(511*cos(2*pi*f*n/62500))
    Q = round(±511*sin(2*pi*f*n/62500))

Сравнивается RMS выход для двух Q полярностей. att2=2, первые128 decimated outputs отбрасываются. Основная частотная сетка: 650…3400 Hz с шагом50 Hz. Это идеальная модель без реального ADC aperture, analog settling и I/Q analog mismatch.

### Минимальное подавление по полному sweep

| Вариант | Taps | I delay | Прибавка к source 7 samples | Minimum IRR | Частота minimum |
|---|---:|---:|---:|---:|---:|
| Source original | 15 | 7 | — | 30.67 dB | 3150 Hz |
| Compensation minimax | 17 | 8 | +1 | 42.46 dB | 800 Hz |
| **Compensation minimax** | **19** | **9** | **+2** | **47.69 dB** | **650 Hz** |
| Compensation minimax | 21 | 10 | +3 | 50.31 dB | 1350 Hz |
| Compensation least-squares | 23 | 11 | +4 | 46.29 dB | 3400 Hz |
| Compensation least-squares | 27 | 13 | +6 | 53.20 dB | 3400 Hz |

17 taps немного не достигают 43 dB. **19 taps — самый короткий прошедший вариант из проверенных.** 21 taps добавляют примерно2.6 dB запаса при ещё одном sample group delay. 23/27 taps сохраняются как более длинные comparison designs.

### Контрольные частоты

| Частота | Source15 | Minimax19 | Minimax21 | LS23 | LS27 |
|---:|---:|---:|---:|---:|---:|
| 650 Hz | 50.55 | **47.70** | 51.80 | 71.43 | 69.00 |
| 1000 Hz | 57.95 | 56.68 | 51.66 | 68.29 | 68.62 |
| 1500 Hz | 46.56 | 50.79 | 59.08 | 69.01 | 68.81 |
| 2000 Hz | 39.79 | 48.67 | 52.70 | 65.17 | 66.04 |
| 2500 Hz | 38.02 | 61.63 | 52.37 | 60.91 | 69.48 |
| 2750 Hz | 38.63 | 48.87 | 50.92 | 60.27 | 63.94 |
| 3000 Hz | 32.57 | 48.70 | 53.81 | 59.59 | 63.17 |
| 3200 Hz | 31.17 | 57.13 | 61.98 | 59.53 | 61.87 |
| 3400 Hz | 37.37 | 48.16 | **50.87** | 46.29 | 53.22 |

Все значения — dB. Различие между минимумом по сетке и таблицей контрольных частот объясняется тем, что минимум minimax19/21 находится внутри полосы.

## 4. Коэффициенты minimax-кандидатов

### Candidate A — 19 taps, Q15

Групповая задержка: 9 I/Q pairs = около1.152 ms. Прирост к исходным 7 pairs: +2 samples = около0.256 ms.

    [-458, -23, -1156, -64, -2594, -148, -5757, -372, -20054,
         0,
      20054, 372, 5757, 148, 2594, 64, 1156, 23, 458]

Maximum absolute magnitude error against the compensation target over650…3400Hz: **0.068 dB**.

| Input range after att2 | Q15 accumulator bound |
|---|---:|
| ±4096 (att2=2) | 250,888,192 |
| ±16384 (att2=0) | 1,003,552,768 |
| arbitrary signed int16 history | 2,007,074,910 |

The full-int16 bound is below signed int32 maximum2,147,483,647 by140,408,737.

### Candidate B — 21 taps, Q15

Групповая задержка: 10 pairs = около1.280 ms. Прирост к исходным 7 pairs: +3 samples = около0.384 ms.

    [184, -266, 259, -889, 304, -2285, 203, -5507, -157, -19958,
         0,
      19958, 157, 5507, -203, 2285, -304, 889, -259, 266, -184]

Maximum absolute magnitude error against the compensation target: **0.050 dB**.

| Input range after att2 | Q15 accumulator bound |
|---|---:|
| ±4096 (att2=2) | 245,858,304 |
| ±16384 (att2=0) | 983,433,216 |
| arbitrary signed int16 history | 1,966,836,420 |

The full-int16 bound is below signed int32 maximum by180,647,227.

### Retained longer least-squares options

The 23-tap and 27-tap least-squares tables remain in rx_hilbert_cic_compensation.py. They are not the first recommendation after the minimax search: 19/21 taps provide better worst-case rejection with fewer pair-products and less delay. The longer tables remain useful comparison points.

## 5. Files and repeatable verification

- reference/rx_hilbert_cic_compensation.py — 17/19/21 minimax and 23/27 least-squares Q15 coefficient sets, compensation target and accumulator bounds.
- reference/test_rx_hilbert_cic_compensation.py — full-chain IRR, delay, target fit and accumulator checks.
- reference/rx_hilbert_cic_sweep.py — repeatable 50-Hz full-chain sweep; prints CSV and minimum IRR for source15 and all candidate families.

Run from temp/reference:

    python rx_hilbert_cic_sweep.py

**Preliminary recommendation:** use 19 taps as the first ESP32 prototype candidate. Keep 21 taps as the higher-margin alternative. This is a recommendation for the next experiment, not a final production choice.

Before replacing source coefficients:
1. уточнить реальные I/Q sample-and-hold offsets and analog acquisition;
2. connect startup ADC sequence and check transition behavior;
3. compare SSB/USB/LSB audio spectra and real analog I/Q mismatch;
4. profile 19/21 tap implementations on ESP32;
5. compare against a measured or otherwise independently verified image-rejection setup.

