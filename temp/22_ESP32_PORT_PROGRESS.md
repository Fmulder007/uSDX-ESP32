# Портирование uSDX на ESP32 — рабочий журнал

Дата: 2026-11-21

## Цель

Прямой перенос прошивки PE1NNZ uSDX 1.02x на ESP32-WROOM-32U с сохранением оригинальных RX/TX DSP-функций. Работа идёт в firmware/uSDX_ESP32/; неизменённый upstream snapshot сохранён в firmware/reference/PE1NNZ_bf8acd31b8/.

Исходник: threeme3/usdx, commit bf8acd31b8a2506c4e1d203dfb283feecae947e1.

## Что уже перенесено

1. Импортированы основной скетч, usdx_filter.h, usdx_settings.h, ina219.h; точные исходные копии хранятся отдельно.
2. Основной скетч переименован в uSDX_ESP32.ino, создан отдельный sketch-folder.
3. Добавлен usdx_esp32_hal.h с ESP32 ветвями аппаратного слоя:
   - ADC1 через ESP-IDF one-shot driver; 12-bit raw scaled to original 10-bit range;
   - AVR-совместимый EEPROM block API поверх 4096-byte ESP32 EEPROM emulation;
   - LEDC PWM для двух исходных PWM-каналов;
   - GPTimer 80 MHz, уведомляющий высокоприоритетную FreeRTOS DSP task;
   - стартовая GPIO-карта и обслуживание Si5351 I²C через Wire.
4. Оригинальные RX/TX DSP-функции и фильтры оставлены в основном скетче без намеренной замены алгоритмов.
5. SI5351 I²C адаптер поддерживает register write/read, в том числе двухбайтовое чтение для необязательного INA219; расширитель LPF использует прямой Wire interface.
6. AVR Timer1 PWM заменён на LEDC GPIO25 (audio/sidetone) и GPIO26 (PA envelope), 8 bit.
7. AVR Timer2 sample cadence заменён на GPTimer с разрешением 10 MHz: RX 62.5 kHz соответствует 1280 тикам (16 мкс), TX 4.8 kHz — 16667 тикам (около 0,002% ошибки). Период округляется до ближайшего целого тика. ISR только уведомляет задачу; DSP + ADC + I²C выполняются в task context.
8. В sample timer stop добавлено ожидание окончания текущего callback перед переключением RX/TX.
9. Энкодер PCINT заменён на GPIO interrupts GPIO18/19.
10. В первом headless профиле отключены DIAG, CAT, CW decoder и LCD fonts; RX, SSB TX, keyer и основной radio state machine оставлены.
11. Добавлен GitHub Actions workflow для компиляции Arduino-ESP32 Core 3.3.13 / ESP32 Dev Module.
12. Настройки uSDX сохраняют старый binary layout через eeprom_read_block() / eeprom_write_block() wrappers. Для EEPROM emulation выделено 4096 байт; запись каждого блока завершается EEPROM.commit().

## ADC I/Q pipeline — важная деталь

Оригинал не читает тот канал, который только что записал в MUX. RX helper выставляет MUX для следующего timer event, запускает конверсию и читает результат предыдущей конверсии. Поэтому HAL хранит current и previous MUX отдельно.

- selector 0 соответствует I: GPIO36 / ADC1_CH0;
- selector 1 соответствует Q: GPIO39 / ADC1_CH3;
- selector 2 соответствует MIC: GPIO34 / ADC1_CH6.

sdr_rx_common_q() выставляет selector 0 для следующего события, но получает предыдущую конверсию selector 1 (Q). sdr_rx_common_i() выставляет selector 1, но получает предыдущую конверсию selector 0 (I). В режиме TX эта задержанная схема не применяется: dsp_tx() должен читать свежие MIC samples; VOX helper также читает MIC напрямую.

## Стартовая распиновка

| Сигнал | GPIO ESP32 | Назначение |
|---|---:|---|
| RX I | 36 | ADC1_CH0 |
| RX Q | 39 | ADC1_CH3 |
| MIC | 34 | ADC1_CH6 |
| Audio PWM | 25 | LEDC |
| PA envelope PWM | 26 | LEDC |
| Si5351 SDA/SCL | 21 / 22 | I²C 400 kHz |
| RX/TX control | 27 | GPIO |
| DIT / DAH | 32 / 33 | key inputs |
| Rotary A / B | 18 / 19 | encoder interrupts |
| Button | 23 | input pulldown, active high |
| Signal output | 4 | GPIO |

Распиновка предварительная. GPIO ESP32 не 5V tolerant. Старую аналоговую плату uSDX нельзя подключать напрямую без проверки максимального напряжения и DC bias на I/Q и MIC входах. Перед подключением PA отдельно проверить GPIO26, управление разрешением и аппаратный уровень.

## Что не подтверждено

- Arduino-ESP32 build ещё не получен. В контейнере нет Arduino CLI и Xtensa toolchain; GitHub Actions workflow добавлен, но результат его выполнения не получен.
- ADC one-shot throughput на 62.5k events/s не измерен. adc_oneshot_read() — polling API и не должен вызываться в ISR, поэтому он вызывается из задачи; успевает ли он стабильно уложиться в 16 мкс вместе с DSP, ещё нужно проверить на устройстве.
- Джиттер GPTimer→task, накопление task notifications и отсутствие потерянных/задержанных событий не измерены.
- PWM waveform / carrier and PA envelope not checked on the oscilloscope.
- Si5351 PLL update timing and full SSB TX spectrum not checked on hardware.
- Аналоговая входная схема и уровни пока не согласованы с фактической схемой радиоплаты.

## Следующая работа

1. Получить реальную сборку ESP32 и исправлять компиляторные ошибки по факту.
2. На плате проверить старт ADC, последовательность I/Q и callback execution budget.
3. Если one-shot ADC/task path не выдержит 16 мкс, перенести acquisition на continuous ADC/DMA, сохранив те же DSP interfaces.
4. Проверить два PWM выхода и Si5351, затем проводить RX/TX bring-up поэтапно.

**Текущий статус:** начальный аппаратный порт написан, но ещё не подтверждён компиляцией и работой на плате. Называть его готовым нельзя.


17. Планировщик sample task больше не воспроизводит накопившиеся timer notifications пачкой: при задержке исполняется один callback, а пропущенные таймерные события учитываются отдельно. В Serial раз в 2 секунды выводятся cumulative callback count и dropped timer events. Это позволяет измерить, выдерживает ли система исходную частоту, без искажения времени искусственным догоняющим burst.
18. GPTimer переведён на 80 MHz; period ticks округляется: RX 1280 тиков / 16 мкс (точно), TX 16667 тиков / 208,3375 мкс (около 0,002% отклонения от 4800 Гц).


15. RX ADC pipeline is now explicitly buffered: after each MUX update, ESP32 acquires the selected channel into a pending sample and returns the result acquired at the preceding timer callback. First result after RX start is midscale warm-up. TX bypasses the delayed path and reads MIC directly.
