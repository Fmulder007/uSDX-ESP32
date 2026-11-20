# AVR SSB IIR arithmetic probe

Этот standalone probe сравнивает две реализации одних и тех же SSB filters 1..3:

- source_style_step(): состояние и промежуточные выражения используют исходную 16-bit AVR int арифметику; функция собрана под pragma GCC optimize("Ofast");
- wide_step(): состояние и вычисления явно расширены до int32_t до умножений и сложений.

## Вход

В файле зашит один период 25 samples синусоиды 2.5 kHz при fs=7812.5 samples/s, amplitude512. Он повторяется 5000 раз. Это тот же вектор, на котором host-side range audit обнаружил prefilter sum 37315 и filt=1 multiplication 18*zc1 до 46980.

## Сборка AVR

    avr-gcc --version
    avr-gcc -mmcu=atmega328p -std=gnu11 -Os -Wall -Wextra -o avr_iir_probe.elf avr_iir_probe.c
    avr-objdump -d -S avr_iir_probe.elf > avr_iir_probe.lst

Запускать в AVR debugger/simulator. После выполнения main заполнены volatile globals:

- probe_source_checksum[0..2] — source-style checksum фильтров 1, 2, 3;
- probe_wide_checksum[0..2] — wide checksum;
- probe_source_final_state[filter][0..7] — конечные состояния source-style;
- probe_wide_final_state[filter][0..7] — конечные состояния wide.

Индексы final state: zz1, zz2, za1, za2, zb1, zb2, zc1, zc2.

## Интерпретация

Различие source и wide checksum/final states докажет, что фактическая AVR сборка даёт другую траекторию на этом vector. Это не доказывает, что modulo-wrap на каждом выражении — верная абстракция; следует также изучить avr_iir_probe.lst и сохранить точную версию compiler/flags.

Файл является исследовательским probe, не частью firmware и не готовым исправлением IIR. Signed overflow остаётся неопределённым по стандарту C; цель — измерить поведение конкретного toolchain и проверить, насколько оно воспроизводимо.
