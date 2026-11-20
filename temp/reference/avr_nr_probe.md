# AVR NR arithmetic probe

Probe для process_nr() — отдельной NR recurrence из slow_dsp().

## Почему обычные flags, без Ofast

В исходнике process_nr() расположен до строки #pragma GCC optimize("Ofast") (usdx.ino около 2712). Поэтому source-style probe не получает локальный Ofast pragma и использует стандартный translation-unit optimization. Исходный sketch компилируется как C++, поэтому файл также .cpp и команда использует avr-g++.

## Входной вектор

5000 samples попеременно -32767 и +32767. Для NR=8 уже первый переход после начального sample даёт математическую разность 33022; для NR=1 — 65534. Обе величины не помещаются в signed 16-bit int на AVR до целочисленного деления. Это worst-case range probe, а не утверждение о типовом эфирном сигнале.

## Сборка

    avr-g++ --version
    avr-g++ -mmcu=atmega328p -std=gnu++11 -Os -flto -Wall -Wextra -o avr_nr_probe.elf avr_nr_probe.cpp
    avr-objdump -d -S avr_nr_probe.elf > avr_nr_probe.lst

После запуска main исследовать:

- probe_source_checksum[0..7], probe_wide_checksum[0..7];
- probe_source_final_state[0..7], probe_wide_final_state[0..7].

Индекс 0 соответствует NR=1, индекс 7 — NR=8. Для полного воспроизведения нужно сохранить версию AVR-GCC и реальные флаги AVR-сборки. Probe не заменяет компиляцию исходного sketch и не задаёт переносимую семантику signed overflow.
