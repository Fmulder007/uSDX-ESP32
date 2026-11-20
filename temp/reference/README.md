# Эталонные модели DSP (рабочие)

Здесь будут небольшие исполняемые модели отдельных участков DSP, которые можно запускать на ПК без ESP32 и без Arduino Core.

## Текущая модель

- `rx_adc_input.py` — упрощённый MUX/read-previous pipeline для установившегося I/Q режима и midpoint interpolation I (не точная startup-модель после ADEN).
- `rx_adc_timing.py` — цикл-тактовая модель ADC startup: первая 25-тактовая конверсия, обычные 13-тактовые конверсии, sample-and-hold timestamps и момент обновления ADC data register.
- `test_rx_adc_input.py` — тесты логического канального порядка, начального регистра и интерполяции.
- `test_rx_adc_timing.py` — тесты задержки первой конверсии, двух стартовых чтений старого ADC register, первого Q результата в I slot и sample-and-hold offsets.
- `rx_numeric_audit.py` — диапазоны промежуточных значений Hilbert и кандидаты проверки signed int16.
- `test_rx_numeric_audit.py` — CIC DC gain/границы и воспроизводимый full-scale 650 Hz Hilbert overrange test. Также проверяются SSB IIR prefilter/feedback intermediate width на фиксированных синусоидальных vectors.
- `rx_nr.py` — integer EMA smoother, используемый в slow_dsp() при NR=1…8.
- `test_rx_nr.py` — тесты passthrough, EMA step response, truncation deadband и persistent NR state.
- `rx_iir.py` — wide-intermediate SSB filters 1..3 recurrence model; не AVR bit-exact и не CW.
- `test_rx_iir.py` — impulse golden vectors, zero-input stability, bypass freeze и state carry-over.
- `avr_hilbert_probe.cpp` / `avr_hilbert_probe.md` — standalone probe для фактического AVR-GCC результата signed-overflow expression и wide comparison.
- `avr_iir_probe.cpp` / `avr_iir_probe.md` — сравнение source-style AVR 16-bit SSB IIR filters 1..3 с int32 wide variants на фиксированном 2.5-kHz vector.
- `avr_nr_probe.cpp` / `avr_nr_probe.md` — сравнение source-style NR integer recurrence с int32 wide variant на full-range transition vector.
- `rx_cic.py` — активный восьмифазный RX CIC из NEW_RX=1; выдаёт сырые пары до att2.
- `test_rx_cic.py` — проверка расписания функций против прямой каскадной формулы.
- `rx_quadrature.py` — активный Hilbert FIR и 7-sample I delay; применяет att2.
- `test_rx_quadrature.py` — импульсная характеристика, задержка I и знак SSB-суммы.
- `test_rx_hilbert_image_rejection.py` — isolated FIR test без ADC/CIC: сравнение двух квадратурных orientations на 650 и 3400 Hz; не использовать его как полный RX image-rejection результат.
- `rx_hilbert_candidates.py` / `test_rx_hilbert_candidates.py` — experimental 19/23-tap Q15 Hilbert FIRs, group-delay and image-rejection tests; baseline coefficients unchanged.
- `rx_hilbert_cic_compensation.py` / `test_rx_hilbert_cic_compensation.py` — 23/27-tap Q15 FIRs fitted to the I-midpoint amplitude compensation and tested through ADC input + CIC + Hilbert.
- `rx_hilbert_cic_sweep.py` — repeatable 650…3400 Hz / 50 Hz full-chain sweep of source15, compensated23 and compensated27 candidates.
- `rx_chain.py` — объединяет CIC и quadrature в частичный RX pipeline.
- `test_rx_chain.py` — проверка стыка и однократного применения att2.
- `rx_ssb_chain.py` — объединяет CIC, Hilbert/I-delay и базовый SSB post-processing.
- `test_rx_ssb_chain.py` — интеграционные проверки SSB subset.
- `rx_ssb_adc_chain.py` — подключает ADC mux/read-previous и I interpolation перед всей доступной SSB-цепочкой.
- `test_rx_ssb_adc_chain.py` — интеграционные проверки входного ADC pipeline.
- `rx_ssb_post.py` — SSB post-processing: fast AGC, volume, optional NR EMA, optional SSB IIR 1..3, clipping.
- `test_rx_ssb_post.py` — тесты AGC state, signed shift, volume, NR/IIR integration и clipping.


## Запуск на Windows

Из каталога `temp\reference`:

    python -m unittest -v

Используются только стандартные модули Python. Ничего устанавливать через pip не требуется.

## Ограничение текущей модели

Частичный сквозной RX SSB pipeline с ADC MUX/read-previous, I midpoint interpolation, CIC, Hilbert/I-delay, AGC/volume, optional NR и SSB IIR 1..3 соединён в rx_ssb_adc_chain.py. Отдельный image-rejection harness также прогоняет альтернативный Hilbert через ADC mux/input model → CIC → quadrature. Параметры nr=0..8 и filt=0..3 передаются через цепочку; defaults nr=0/filt=0 сохраняют прежнее поведение. Пока не моделируются:
- точный sample-and-hold aperture и acquisition/settling time внутри conversion;
- startup 25-cycle ADC conversion timing внутри полной event-level chain (есть отдельный rx_adc_timing.py);
- фактическое AVR-GCC поведение signed-overflow в Hilbert/IIR/NR; rx_quadrature.py и rx_iir.py остаются wide-intermediate baselines;
- CW IIR filters 4..7;
- AM/FM demodulation;
- выходная аудио-интерполяция.

Набор содержит несколько отдельных моделей и одну сквозную частичную SSB-цепочку. Для CIC есть сравнение расписания с прямой двухступенчатой формулой; для Hilbert/I-delay — impulse/delay tests; для ADC input — MUX/read-previous и I interpolation tests; для NR — EMA/deadband/state tests; для SSB IIR — impulse, bypass и state-carry-over tests; для slow_dsp — AGC/volume/clipping tests. Эти поддерживаемые ступени соединены в rx_ssb_adc_chain.py. Полный AVR-GCC golden comparison, startup aperture, аудио-интерполятор, CW/AM/FM и спектральные тесты ещё не завершены.

## Startup timing caveat

rx_adc_timing.py выявляет startup-последовательность после ADEN. rx_adc_input.py и rx_ssb_adc_chain.py пока остаются абстракцией установившегося логического потока и не используют эту startup-модель. Точная задержка ISR до ADSC, фаза ADC prescaler и analog acquisition/settling требуют отдельного уточнения. См. ../16_RX_ADC_STARTUP_TIMING.md.
