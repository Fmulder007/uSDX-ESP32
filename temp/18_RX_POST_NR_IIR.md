# RX post-processing: NR smoother и переключаемые IIR-фильтры

**Источник:** PE1NNZ uSDX snapshot bf8acd31b8a2506c4e1d203dfb283feecae947e1, usdx.ino и usdx_filter.h.
**Статус:** source flow, NR recurrence и SSB IIR recurrences разобраны; NR/IIR wide reference models с tests подключены к частичной SSB event chain. Для SSB IIR вычислена линейная transfer response и добавлен первый input-dependent int16 range audit; фактическое AVR integer overflow и cold-start/filter-switch golden tests ещё требуют проверки.

## 1. Порядок обработки в slow_dsp()

Для SSB/CW основной scalar audio path:

1. На входе slow_dsp(ac) ведётся накопление abs(ac) для S-meter.
2. При AM/FM ac заменяется результатом отдельного детектора. Для USB/LSB/CW исходный ac сохраняется.
3. AGC и volume:
   - при agc==1 выполняется process_agc_fast(ac), затем ac >>= (16-volume);
   - при agc==0 volume работает без AGC: справа сдвиг до volume=13, выше — левый сдвиг.
   - ветка agc==2 с process_agc() включается только если собран FAST_AGC.
4. При nr!=0 вызывается process_nr(ac).
5. При filt!=0 вызывается filt_var(ac).
6. В конце результат ограничивается диапазоном [-512,511].

Исходные значения из выбранной конфигурации: mode=USB, agc=1, nr=0, filt=0, volume=12; FAST_AGC выключен в usdx_settings.h. Поэтому по умолчанию NR и IIR выключены, работает process_agc_fast, затем volume shift на 4 бита, затем финальный clip. prev_filt[] = {0,4} сохраняет Full для LSB/USB и CW filter 500 Hz для CW.

## 2. NR — фактический алгоритм

Реальная активная функция:

    static int16_t ea1;
    ea1 = EA(ea1, in, 1 << (nr-1));
    return ea1;

Макрос:

    #define EA(y,x,N) (y) = (y) + ((x) - (y)) / (N)

Это однополюсный EMA low-pass smoother, а не спектральный/адаптивный noise reducer. Для уровня nr:

    N = 2^(nr-1)
    y[n] = y[n-1] + trunc0((x[n] - y[n-1]) / N)

trunc0 — целочисленное деление C/C++ с округлением к нулю.

| NR | N | alpha=1/N | Аналитическая -3 dB частота при 7812.5 samples/s |
|---:|---:|---:|---:|
| 0 | bypass | — | — |
| 1 | 1 | 1.0000 | нет сглаживания (точный passthrough) |
| 2 | 2 | 0.5000 | 898.65 Hz |
| 3 | 4 | 0.2500 | 360.20 Hz |
| 4 | 8 | 0.1250 | 166.28 Hz |
| 5 | 16 | 0.0625 | 80.27 Hz |
| 6 | 32 | 0.03125 | 39.48 Hz |
| 7 | 64 | 0.015625 | 19.58 Hz |
| 8 | 128 | 0.0078125 | 9.75 Hz |

Частоты рассчитаны для линейного EMA в wide arithmetic и частоты вызова process_nr() 7812.5 Hz. Это аналитические номиналы, а не измеренная характеристика AVR integer implementation.

### Целочисленная deadband — важнее номинальной частоты

Деление округляется к нулю. Если abs(input - ea1) < N, обновление равно нулю и состояние больше не движется. Поэтому:

- NR=2 может остановиться с остатком ±1;
- NR=8 может остановиться с остатком до ±127;
- при NR=8 сигнал или изменение амплитуды величиной 127 counts от текущего состояния не изменит output вообще.

Это не обычный бесконечно точный EMA с малой alpha: quantization создаёт неподвижные зоны. Для слабого аудио это способно подавлять не только шум, но и полезные малые изменения.

### Состояние и переключение уровня

ea1 — один static int16_t внутри process_nr(), общий для всех уровней NR. Ветка NR=0 просто пропускает вызов: состояние замораживается, а не сбрасывается. При повторном включении NR старое состояние используется дальше. При входе в CW код присваивает nr=0, но ea1 не очищает.

Старые функции process_nr_old() и process_nr_old2() в текущем активном пути не вызываются. Не переносить их вместо process_nr().

## 3. Исполняемая NR reference model

Добавлены:

- reference/rx_nr.py — точная recurrence и truncation toward zero; состояние одно для всех уровней.
- reference/test_rx_nr.py — passthrough NR=1, response NR=2, deadband NR=8, отрицательное деление, заморозка состояния при NR=0 и повторное использование при смене уровня.

Это модель арифметики recurrence в bounded рабочем диапазоне, но не доказательство всего AVR int16_t overflow для произвольных входов. NR включается после AGC/volume; полный range audit должен учитывать именно этот сигнал. NR state передаётся в общий RxSsbPostState и потому работает внутри rx_ssb_chain.py/rx_ssb_adc_chain.py, но отдельная rx_adc_timing.py startup scheduler пока не подключена к этой цепочке.

## 4. IIR — границы ветвей

filt_var() находится в usdx_filter.h. Вызов выполняется только при filt!=0.

### SSB (filt=1..3)

Путь содержит:
1. Общую входную секцию с историей zz1/zz2:

       zz2 = zz1
       zz1 = za0
       za0 = (30*(za0-zz2) + 25*zz1) >> 5

   Комментарий источника называет её 300-Hz stage. Поскольку zz2 и zz1 обновляются до вычисления, на этой строке zz2 — предыдущий вход x[n-1], а zz1 — текущий x[n]. Поэтому линейная форма:

       p[n] = (55*x[n] - 30*x[n-1]) / 32

   DC gain равен 25/32 = 0.78125 (-2.14 dB), Nyquist gain — 85/32 = 2.65625 (+8.49 dB). Это high-shelf-like секция, а не DC-block с нулём на 0 Hz. Комментарий “300-Hz” не является достаточным определением её cutoff.

2. Первую Direct Form I biquad секцию с состояниями za1/za2 (input history) и zb1/zb2 (output history):

   - filt=1: zb0=((za0+2*za1+za2)>>1)-((13*zb1+11*zb2)>>4)
   - filt=2: zb0=((za0+2*za1+za2)>>1)-((2*zb1+8*zb2)>>4)
   - filt=3: zb0=((za0+2*za1+za2)>>1)-((0*zb1+4*zb2)>>4)

3. Вторую biquad секцию zc0, со своими zc1/zc2:

   - filt=1: zc0=((zb0+2*zb1+zb2)>>1)-((18*zc1+11*zc2)>>4)
   - filt=2: zc0=((zb0+2*zb1+zb2)>>2)-((4*zc1+8*zc2)>>4)
   - filt=3: zc0=((zb0+2*zb1+zb2)>>2)-((0*zc1+4*zc2)>>4)

Затем histories сдвигаются, функция возвращает zc0. UI labels в конфигурации F_MCU>16 MHz: Full, 3000, 2400, 1800; для другого F_MCU: Full, 2400, 2000, 1500. Это программные labels, не подтверждённые здесь измеренные -3 dB bandwidths.

### Линеаризованная частотная характеристика (пока не AVR bit-exact)

Из этих difference equations получаются следующие transfer functions при fs=7812.5 Hz. Учитывается порядок обновления zz1/zz2; целочисленные округления и overflow пока исключены. Пик и границы ниже — расчётная линейная характеристика, не результат измерения прошивки на радио.

| filt | Peak frequency | Peak gain | Относительная полоса -3 dB |
|---:|---:|---:|---:|
| 1 | 2593 Hz | 5.493 (14.80 dB) | 2360–2794 Hz |
| 2 | 1984 Hz | 3.412 (10.66 dB) | 1621–2239 Hz |
| 3 | 1556 Hz | 2.193 (6.82 dB) | 838–2034 Hz |

Получается выраженная peaking/band-pass-like характеристика, а не монотонный low-pass с одним cutoff. Это подтверждено отдельной длинной sinus simulation на wide integer recurrence при амплитуде 100: измеренные коэффициенты совпали с аналитическим расчётом с малой ошибкой квантования. Перед тем как считать эти числа эталоном, требуется сравнить AVR-GCC fixed-vector output: исходные SSB IIR выражения также используют 16-bit int промежуточные значения на AVR.


### CW (filt=4..7)

CW branch использует другую пару biquad секций, затем возвращает zc0 >> 3 для компенсации заявленного front-end gain 64x. В выбранном usdx_settings.h FILTER_700HZ выключен (определение закомментировано), поэтому работает основной блок с коэффициентами, подписанными как варианты 600 Hz ±250/100/50/18 Hz. Menu labels: 500, 200, 100, 50; они не совпадают буквально с названиями комментариев в коде и должны рассматриваться как UI labels, а не точная measured bandwidth.

## 5. IIR state lifecycle и риск переходных процессов

Все IIR history variables объявлены static внутри filt_var(). Внутри функции нет ветви reset по _init, mode или изменению filt. Переключение filter вызывает _init=true в обработчике меню, но это состояние сбрасывает аудио/feedback state в других функциях, а не эти IIR histories. Когда filt=0, функция вообще не вызывается, поэтому histories остаются замороженными.

Следствие: после смены filter, обхода фильтра или переключения SSB/CW старые za*, zb*, zc*, zz* могут попасть в новый filter path. Не следует считать смену filter equivalent к запуску нового filter с нулевыми history. Это требует отдельного transient/reset test. В то же время автоматически обнулять все histories при каждом sample или менять исходное поведение при переносе нельзя.

## 6. Первый SSB IIR intermediate range audit

Для дополнительной проверки вход подавался непосредственно на вход filt_var(), то есть после AGC и volume. Модель считает широкие математические промежуточные значения, не имитируя AVR overflow.

**Вектор A:** синус 2,5 kHz, 7812,5 samples/s, амплитуда 512, 5000 samples.

| Промежуточная величина | filt=1 | filt=2 | filt=3 |
|---|---:|---:|---:|
| max abs prefilter sum | **37315** | **37315** | **37315** |
| max abs stage-1 feedback sum | 29175 | 7834 | 3120 |
| max abs stage-2 feedback term 1 | **46980** | 2568 | 0 |
| max abs stage-2 feedback sum | **43357** | 5068 | 1468 |

У всех трёх ветвей общая prefilter sum выходит за signed int16. У filt=1 ещё до сложения feedback terms произведение 18*zc1 достигает **46980**; сама stage-2 feedback sum достигает **43357**. Это reachable в wide recurrence на конкретном векторе, но после первого переполнения фактическая AVR state trajectory может разойтись с wide baseline.

**Вектор B:** синус 3,9 kHz, амплитуда 128, 5000 samples. Для всех трёх фильтров ни один из перечисленных промежуточных узлов не вышел за signed int16. Это лишь контрольный вектор, не глобальная гарантия диапазона.

Риск важен, потому что filt_var() вызывается **до** финального slow_dsp() clipping [-512,511]. Настройки volume допускают 0…16; при agc=1, volume=16 нет финального right shift перед IIR, а при agc!=1, volume=16 исходный код выполняет left shift на три бита. Значит, нельзя считать, что только финальный audio clip ограничивает внутреннюю IIR арифметику.

Добавлены audit_ssb_iir_intermediates() в reference/rx_numeric_audit.py; теперь он проверяет не только суммы, но и отдельные произведения до сложения. Два теста в test_rx_numeric_audit.py покрывают overrange и low-amplitude control vectors. Это range warning по wide trajectory, не утверждение о точном AVR результате.

Для проверки целевого компилятора подготовлены reference/avr_iir_probe.c и avr_iir_probe.md. Probe прогоняет source-style 16-bit и int32 wide реализации всех трёх SSB-фильтров на том же 2.5-kHz vector и сохраняет checksums/final states. Компиляция и выполнение AVR-GCC ещё не проведены: AVR toolchain отсутствует в исследовательской среде.

## 7. Исполняемые IIR reference model

Добавлены:

- reference/rx_iir.py — wide-intermediate модель SSB filters 1..3, сохраняющая порядок обновления history и arithmetic right shifts; filt=0 bypass не меняет состояния.
- reference/test_rx_iir.py — zero-input stability, импульсные golden vectors по каждому SSB filter, frozen state в bypass, state carry-over при смене фильтра и явный отказ от неподдержанных CW IDs.

Шесть focused recurrence/lifecycle assertions проверены. Модель не воспроизводит AVR signed overflow и не реализует CW filters 4..7.

## 8. Открытые численные вопросы

- Требуется получить AVR-GCC golden values для Hilbert/NR/IIR overflow vectors; нынешний IIR range audit — математический wide trajectory.
- Для NR in-ea1 должен быть проверен на AVR signed-int overflow при крайних внутренних уровнях.
- Линейная SSB transfer response уже рассчитана; нужно получить AVR integer response с truncation/overflow и отдельно разобрать CW filters 4..7.
- Проверить скачок/звон после переключения filt, bypass/re-enable и mode.
- Проверить, влияет ли 600 Hz CW active branch / disabled 700 Hz alternative на желаемую конфигурацию переноса. При FILTER_700HZ выключенном условная ветка cw_tone==0 исключается препроцессором, поэтому в filt_var() основной 600-Hz block выполняется независимо от cw_tone.

## 9. Исходные участки кода

- process_nr(), slow_dsp() и EA() macro:
  https://github.com/threeme3/usdx/blob/bf8acd31b8/usdx.ino#L2156-L2157
  https://github.com/threeme3/usdx/blob/bf8acd31b8/usdx.ino#L2510-L2655
- Default RX settings, AGC/NR/ATT2:
  https://github.com/threeme3/usdx/blob/bf8acd31b8/usdx.ino#L2427-L2445
- Filter states/equations:
  https://github.com/threeme3/usdx/blob/bf8acd31b8/usdx_filter.h
- Filter/NR menu ranges:
  https://github.com/threeme3/usdx/blob/bf8acd31b8/usdx.ino#L4058-L4080
- Filter state menu transition:
  https://github.com/threeme3/usdx/blob/bf8acd31b8/usdx.ino#L5273-L5305

## 9. Интеграция в partial SSB chain

RxSsbPostState теперь вызывает stages в source order: AGC/volume → NR EMA → selected SSB IIR → final clip. RxSsbReferencePipeline и RxSsbAdcReferencePipeline передают nr и filt параметры до post stage. При nr=0/filt=0 прежний baseline remains unchanged. Поддерживаемый диапазон пока USB/LSB common SSB filter branch: NR 0..8 и filt 0..3. CW IIR 4..7, AM/FM и AVR signed-overflow emulation не входят в эту модель. Startup ADC timing analysis остаётся отдельной моделью; полный event chain пока использует идеализированную steady-state ADC input abstraction.
