# Эталонные модели DSP (рабочие)

Здесь будут небольшие исполняемые модели отдельных участков DSP, которые можно запускать на ПК без ESP32 и без Arduino Core.

## Текущая модель

- `rx_cic.py` — активный восьмифазный RX CIC из NEW_RX=1; выдаёт сырые пары до att2.
- `test_rx_cic.py` — проверка расписания функций против прямой каскадной формулы.
- `rx_quadrature.py` — активный Hilbert FIR и 7-sample I delay; применяет att2.
- `test_rx_quadrature.py` — импульсная характеристика, задержка I и знак SSB-суммы.
- `rx_chain.py` — объединяет CIC и quadrature в частичный RX pipeline.
- `test_rx_chain.py` — проверка стыка и однократного применения att2.
- `rx_ssb_post.py` — базовый SSB slow_dsp post-processing: fast AGC, volume, clipping.
- `test_rx_ssb_post.py` — тесты AGC state, signed shift, volume и clipping.

## Запуск на Windows

Из каталога `temp\reference`:

    python -m unittest -v

Используются только стандартные модули Python. Ничего устанавливать через pip не требуется.

## Ограничение текущей модели

Частичный сквозной RX pipeline CIC → Hilbert/I-delay уже соединён в rx_chain.py. Он принимает выборки, уже распределённые по логическим I/Q-каналам. Пока не моделируются:
- переключение ADMUX и конвейер ADC register read;
- интерполяция I из соседних ADC отсчётов;
- slow_dsp(): demod, AGC, NR и IIR;
- выходная аудио-интерполяция.

Модель намеренно ограничена одним блоком: CIC. Для CIC выполнено сравнение восьмифазного расписания с прямой двухступенчатой формулой. Для Hilbert/I-delay есть impulse и delay tests. Частичный CIC→Hilbert pipeline соединён; полный RX pipeline пока не готов.
