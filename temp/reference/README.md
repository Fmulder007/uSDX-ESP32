# Эталонные модели DSP (рабочие)

Здесь будут небольшие исполняемые модели отдельных участков DSP, которые можно запускать на ПК без ESP32 и без Arduino Core.

## Текущая модель

- `rx_adc_input.py` — MUX/read-previous ADC pipeline и midpoint interpolation I.
- `test_rx_adc_input.py` — тесты канального порядка, стартового значения и интерполяции.
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
- `rx_ssb_post.py` — базовый SSB slow_dsp post-processing: fast AGC, volume, clipping.
- `test_rx_ssb_post.py` — тесты AGC state, signed shift, volume и clipping.

## Запуск на Windows

Из каталога `temp\reference`:

    python -m unittest -v

Используются только стандартные модули Python. Ничего устанавливать через pip не требуется.

## Ограничение текущей модели

Частичный сквозной RX SSB pipeline с ADC MUX/read-previous и I midpoint interpolation соединён в rx_ssb_adc_chain.py. Вход — аналоговые I/Q значения, доступные для старта conversion на каждом Timer2 event. Пока не моделируются:
- точный sample-and-hold aperture и acquisition/settling time внутри conversion;
- NR и IIR ветви;
- AM/FM demodulation;
- выходная аудио-интерполяция.

Модель намеренно ограничена одним блоком: CIC. Для CIC выполнено сравнение восьмифазного расписания с прямой двухступенчатой формулой. Для Hilbert/I-delay есть impulse и delay tests. Для ADC MUX/read-previous и I interpolation есть отдельные тесты канального порядка. Для базового SSB post есть AGC/volume/clipping tests. Все доступные ступени соединены в частичный RX SSB pipeline; аудио-интерполятор и спектральные тесты пока не готовы.
