# Эталонные модели DSP (рабочие)

Здесь будут небольшие исполняемые модели отдельных участков DSP, которые можно запускать на ПК без ESP32 и без Arduino Core.

## Текущая модель

- `rx_adc_input.py` — упрощённый MUX/read-previous pipeline для установившегося I/Q режима и midpoint interpolation I (не точная startup-модель после ADEN).
- `rx_adc_timing.py` — цикл-тактовая модель ADC startup: первая 25-тактовая конверсия, обычные 13-тактовые конверсии, sample-and-hold timestamps и момент обновления ADC data register.
- `test_rx_adc_input.py` — тесты логического канального порядка, начального регистра и интерполяции.
- `test_rx_adc_timing.py` — тесты задержки первой конверсии, двух стартовых чтений старого ADC register, первого Q результата в I slot и sample-and-hold offsets.
- `rx_numeric_audit.py` — диапазоны промежуточных значений Hilbert и кандидаты проверки signed int16.
- `test_rx_numeric_audit.py` — CIC DC gain/границы и воспроизводимый full-scale 650 Hz Hilbert overrange test.
- `rx_nr.py` — integer EMA smoother, используемый в slow_dsp() при NR=1…8.
- `test_rx_nr.py` — тесты passthrough, EMA step response, truncation deadband и persistent NR state.
- `rx_iir.py` — wide-intermediate SSB filters 1..3 recurrence model; не AVR bit-exact и не CW.
- `test_rx_iir.py` — impulse golden vectors, zero-input stability, bypass freeze и state carry-over.
- `avr_hilbert_probe.c` / `avr_hilbert_probe.md` — standalone probe для фактического AVR-GCC результата signed-overflow expression и wide comparison.
- `rx_cic.py` — активный восьмифазный RX CIC из NEW_RX=1; выдаёт сырые пары до att2.
- `test_rx_cic.py` — проверка расписания функций против прямой каскадной формулы.
- `rx_quadrature.py` — активный Hilbert FIR и 7-sample I delay; применяет att2.
- `test_rx_quadrature.py` — импульсная характеристика, задержка I и знак SSB-суммы.
- `rx_chain.py` — объединяет CIC и quadrature в частичный RX pipeline.
- `test_rx_chain.py` — проверка стыка и однократного применения att2.
- `rx_ssb_chain.py` — объединяет CIC, Hilbert/I-delay и базовый SSB post-processing.
- `test_rx_ssb_chain.py` — интеграционные проверки SSB subset.
- `rx_ssb_adc_chain.py` — подключает ADC mux/read-previous и I interpolation перед всей доступной SSB-цепочкой.
- `test_rx_ssb_adc_chain.py` — интеграционные проверки входного ADC pipeline.
- `rx_ssb_post.py` — baseline SSB post-processing: fast AGC, volume, clipping.
- `test_rx_ssb_post.py` — тесты AGC state, signed shift, volume и clipping.


## Запуск на Windows

Из каталога `temp\reference`:

    python -m unittest -v

Используются только стандартные модули Python. Ничего устанавливать через pip не требуется.

## Ограничение текущей модели

Частичный сквозной RX SSB pipeline с ADC MUX/read-previous и I midpoint interpolation соединён в rx_ssb_adc_chain.py. Вход — аналоговые I/Q значения, доступные для старта conversion на каждом Timer2 event. Пока не моделируются:
- точный sample-and-hold aperture и acquisition/settling time внутри conversion;
- фактическое AVR-GCC поведение signed-overflow в Hilbert; rx_quadrature.py остаётся wide-intermediate mathematical baseline;
- NR и IIR ветви;
- AM/FM demodulation;
- выходная аудио-интерполяция.

Набор содержит несколько отдельных моделей и одну сквозную частичную SSB-цепочку. Для CIC расписание сверяется с прямой двухступенчатой формулой; для Hilbert/I-delay есть impulse/delay tests; для ADC input есть MUX/read-previous и I interpolation tests; для slow_dsp есть AGC/volume/clipping tests. Все эти ступени соединены в rx_ssb_adc_chain.py. Аудио-интерполятор, NR/IIR, AM/FM и спектральные тесты пока не готовы.

## Startup timing caveat

rx_adc_timing.py выявляет startup-последовательность после ADEN. rx_adc_input.py и rx_ssb_adc_chain.py пока остаются абстракцией установившегося логического потока и не используют эту startup-модель. Точная задержка ISR до ADSC, фаза ADC prescaler и analog acquisition/settling требуют отдельного уточнения. См. ../16_RX_ADC_STARTUP_TIMING.md.
