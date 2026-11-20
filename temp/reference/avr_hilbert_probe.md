# AVR Hilbert arithmetic probe

Этот маленький C-файл нужен только для проверки численной семантики исходной Hilbert-формулы на реальном AVR toolchain. Он не подключается к ESP32-проекту и не меняет firmware.

## Входной вектор

Сохранён в массиве probe_v и scalar probe_q. Он получен из full-scale 650 Hz Q-синуса после активной CIC и att2=2. Для него wide-intermediate baseline даёт 3890, а простая modulo-16-bit гипотеза — 3379.

## Сборка

Нужен AVR-GCC для ATmega328P. В каталоге с файлом:

    avr-gcc --version
    avr-gcc -mmcu=atmega328p -std=gnu11 -Os -Wall -Wextra -o avr_hilbert_probe.elf avr_hilbert_probe.c
    avr-objdump -d -S avr_hilbert_probe.elf > avr_hilbert_probe.lst

В source_style_hilbert намеренно оставлена исходная запись выражения и pragma GCC optimize("Ofast"). Функция возвращает int16_t. wide_hilbert делает явное расширение операндов до int32_t до арифметики и сохраняет отдельные целочисленные деления исходной формулы.

## Что смотреть

- probe_source_result — фактический результат source-style выражения, сформированного этим AVR-GCC.
- probe_wide_result — wide result, ожидается 3890.
- В avr_hilbert_probe.lst — какие разрядности и инструкции реально использованы в source_style_hilbert.

Для получения probe_source_result нужен AVR debugger/simulator или чтение RAM в отладчике. Одна только дизассемблированная последовательность помогает понять разрядность, но окончательный golden value лучше также получить исполнением бинарного файла.

Важно: source expression вызывает signed overflow в C при данном векторе, поэтому стандарт C не обещает конкретного результата. Этот probe фиксирует поведение конкретной версии AVR-GCC и конкретных flags, а не доказывает переносимость такого поведения на другие компиляторы.
