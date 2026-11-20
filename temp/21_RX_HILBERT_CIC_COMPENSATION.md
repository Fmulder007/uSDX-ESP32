# Hilbert FIR, компенсирующий I midpoint interpolation и CIC

**Статус:** два Q15-кандидата рассчитаны и проверены на полной steady-state RX chain-модели. Исходный FIR не заменён. Это новые варианты именно под сочетание I midpoint average + CIC + Hilbert, а не плоские Hilbert transformers.

## 1. Почему предыдущие «плоские» кандидаты оказались неверным сравнением

В sdr_rx_common_i() исходник усредняет соседние I conversions:

    I_aligned[n] = (I[n] + I[n-1]) / 2

I stream имеет 31 250 samples/s. Для синусоиды частоты f такое среднее имеет амплитудный коэффициент:

    A_I(f) = cos(pi*f/31250)

Q branch этой двухточечной коррекции не получает. Поэтому перед Hilbert:

    A_Q(f) / A_I(f) = 1 / cos(pi*f/31250)

Между 650 и 3400 Hz отношение Q/I растёт примерно от 1.0028 до 1.0620. CIC имеет одинаковую magnitude response по I и Q, поэтому сам по себе это отношение не устраняет.

Исходный Hilbert FIR не является плоским по амплитуде: его roll-off частично компенсирует дисбаланс I/Q, созданный midpoint average. Плоские Remez-кандидаты из 20_RX_HILBERT_CANDIDATES.md эту компенсацию убирают и **не являются drop-in заменой**.

## 2. Исправленная цель проектирования

Чтобы уравнять ветви, Hilbert magnitude должна приближать:

    |H_target(f)| = cos(pi*f/31250)

при сохранении нужной quadrature phase и source polarity. Групповая задержка Q FIR компенсируется такой же задержкой I.

Коэффициенты ниже получены least-squares fit к этой compensation target по полосе 650…3400 Hz с Type-III antisymmetric constraint и симметричным Q15 quantization. Это не обычный flat-gain Hilbert.

## 3. Полная проверка: ADC midpoint → CIC → candidate Hilbert

Использована steady-state chain из тех же reference blocks:

1. RxAdcInputState: I/Q ADC mux/read-previous и I midpoint interpolation;
2. RxCicState: исходная восьмифазная CIC;
3. RxHilbertCandidateState: Q15 candidate и соответствующая I delay.

На каждом Timer2 event подаются:

    I = round(511*cos(2*pi*f*n/62500))
    Q = round(±511*sin(2*pi*f*n/62500))

Сравнивается RMS выход для двух Q полярностей. att2=2, отброс первых128 decimated outputs, далее 2048 output pairs. Это идеальная модель без реального ADC aperture, analog settling и I/Q analog mismatch.

| Частота | Source 15 taps | Compensated 23 taps | Compensated 27 taps |
|---:|---:|---:|---:|
| 650 Hz | 50.6 dB | **71.4 dB** | 69.0 dB |
| 1000 Hz | 58.0 dB | 68.3 dB | 68.6 dB |
| 1500 Hz | 46.6 dB | 69.0 dB | 68.8 dB |
| 2000 Hz | 39.8 dB | 65.2 dB | 66.0 dB |
| 2500 Hz | 38.0 dB | 60.9 dB | 69.5 dB |
| 2750 Hz | 38.6 dB | 60.3 dB | 63.9 dB |
| 3000 Hz | 32.6 dB | 59.6 dB | 63.2 dB |
| 3200 Hz | 31.2 dB | 59.5 dB | 61.9 dB |
| 3400 Hz | 37.4 dB | **46.3 dB** | **53.2 dB** |

Дополнительный sweep с шагом 50 Hz по всей полосе 650…3400 Hz:

- source 15 taps: minimum около 30.67 dB на 3150 Hz;
- compensated 23 taps: minimum около 46.29 dB на 3400 Hz;
- compensated 27 taps: minimum около 53.20 dB на 3400 Hz.

Итак, **23-tap compensated filter — минимальный по вычислительной стоимости проверенный вариант, который сохраняет более 43 dB на всей частотной сетке sweep**. 27 taps добавляют около 7 dB верхнеполосного запаса.

## 4. Coefficients и delay

### Candidate A — 23 taps, Q15

Групповая задержка: 11 I/Q pairs = около 1.408 ms. Прирост к исходным 7 pairs: +4 samples, +0.512 ms.

    [-122, 21, -445, 31, -1152, 12, -2570, -72, -5729, -324, -20042,
         0,
      20042, 324, 5729, 72, 2570, -12, 1152, -31, 445, -21, 122]

Maximum absolute error of Q15 magnitude against target over 650…3400 Hz: **0.085 dB**.

Accumulator bounds using antisymmetry:

| Input range after att2 | Bound |
|---|---:|
| ±4096 (att2=2) | 250,019,840 |
| ±16384 (att2=0) | 1,000,079,360 |
| arbitrary signed int16 history | 2,000,128,200 |

All are below signed int32 maximum 2,147,483,647.

### Candidate B — 27 taps, Q15

Групповая задержка: 13 pairs = около 1.664 ms. Прирост к исходным 7 pairs: +6 samples, +0.768 ms.

    [-57, 11, -222, 20, -597, 19, -1338, -10, -2753, -96, -5864, -340, -20092,
         0,
      20092, 340, 5864, 96, 2753, 10, 1338, -19, 597, -20, 222, -11, 57]

Maximum absolute error of Q15 magnitude against target: **0.037 dB**.

| Input range after att2 | Bound |
|---|---:|
| ±4096 (att2=2) | 257,384,448 |
| ±16384 (att2=0) | 1,029,537,792 |
| arbitrary signed int16 history | 2,059,044,165 |

All fit signed int32.

## 5. Файлы и следующий шаг

Добавлены:

- reference/rx_hilbert_cic_compensation.py — два compensation coefficient sets, Q15 response target и accumulator bound.
- reference/test_rx_hilbert_cic_compensation.py — full-chain image rejection, delay, coefficient target and accumulator safety tests.

**Предварительная рекомендация для дальнейшего исследования:** взять 23 taps как основной кандидат на следующий этап — он обеспечивает около 46.3 dB minimum в текущей full-chain ideal model при меньшей вычислительной нагрузке. 27 taps сохранить как вариант с более высоким запасом.

Но активные коэффициенты PE1NNZ пока не заменять. Перед окончательным выбором нужно:
1. уточнить реальные I/Q sample-and-hold offsets и analog acquisition;
2. подключить startup ADC sequence и проверить переходный процесс;
3. проверить входной диапазон CIC и реальный fixed-point scaling;
4. сравнить SSB/USB/LSB audio spectra;
5. собрать и профилировать оба варианта на ESP32.
