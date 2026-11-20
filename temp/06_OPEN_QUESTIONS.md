# Открытые вопросы и следующие задачи

Документ живой: вопросы закрываются по мере проверки и сопровождаются ссылкой на результат. Непроверенный вариант не считается решением.

## 1. Подтверждено

- [x] Зафиксирован исходный commit PE1NNZ: bf8acd31b8a2506c4e1d203dfb283feecae947e1.
- [x] Активная RX-ветка: NEW_RX=1, SIMPLE_RX выключен.
- [x] Восстановлена последовательность sdr_rx_00...sdr_rx_07.
- [x] Частоты: 62,5 kHz timer events, 31,25 kS/s на I и Q, 7,8125 kS/s пары.
- [x] Найдена коррекция временного сдвига I через усреднение соседних отсчётов.
- [x] Восстановлена активная Hilbert-обработка и I delay.
- [x] Определены основные блоки slow_dsp() и filt_var().
- [x] Восстановлен SSB TX путь ssb() → phase delta/amplitude → аппаратный выход.
- [x] Определён риск ширины int: AVR 16-bit vs ESP32 32-bit.
- [x] Среда ESP32 установлена; тест OLED успешно собран и прошит.
- [x] Разложены восемь фаз активного CIC и выведена эквивалентная R=4/N=3 передаточная функция.
- [x] Рассчитаны номинальные ADC prescaler и conversion timing.
- [x] Рассчитаны реальные частоты Timer2/Timer1 с учётом F_CPU override и округления OCR.
- [x] Учтена 25-тактовая первая ADC-конверсия после ADEN: доказано, что она не готова к следующему Timer2 событию; добавлены startup timing model и тесты: temp/16_RX_ADC_STARTUP_TIMING.md.

## 2. RX — вопросы

- [x] Развернуть все восемь фаз CIC в таблицу входов/регистров/выходов: temp/08_RX_CIC_PHASES.md.
- [x] Сверить коэффициентный масштаб CIC: raw DC gain 32, после default att2=2 — 8; smeter() использует R*8=32. Комментарий 12 dB не является общим DC scaling коэффициентом; авторский смысл комментария остаётся неустановленным.
- [x] Смоделировать логическую привязку I/Q к timer event, first ADC register read и read-previous/start-next pipeline: temp/reference/rx_adc_input.py.
- [ ] Уточнить абсолютную sample-and-hold привязку к Timer2 и разницу задержек I/Q ISR до ADSC; затем отдельно измерить acquisition/settling и jitter.
- [x] Зафиксировать наблюдаемое source reset поведение CIC/Hilbert/AGC/IIR при cold start и TX→RX: temp/12_STATE_LIFECYCLE.md.
- [ ] Проверить переходные процессы cold start, TX→RX и повторного TX на эталонных сигналах.
- [x] Доказать диапазоны активной CIC для ADC domain [-511,512]: raw output [-16352,16384], без int16 overflow; DC gain 32 до att2 и 8 при default att2=2. См. temp/17_RX_NUMERIC_RANGE.md.
- [ ] Установить фактическое AVR-GCC поведение signed overflow в Hilbert: full-scale 650 Hz test при att2=2 создаёт третий числитель 34915; сравнить AVR disassembly/output с wide и wrap кандидатами.
- [x] Подготовлена отдельная reference-модель базового SSB slow_dsp (fast AGC/volume/clipping, nr=0/filt=0): temp/reference/rx_ssb_post.py.
- [x] Выделить process_nr() в отдельную stateful EMA-модель и проверить integer deadband/state freeze: temp/reference/rx_nr.py и test_rx_nr.py.
- [x] Восстановить SSB filt_var() equations, добавить wide recurrence и impulse/lifecycle tests: temp/reference/rx_iir.py и test_rx_iir.py. Линейная response рассчитана; AVR width audit ещё открыт.
- [x] Подключить NR и SSB filt=1..3 к rx_ssb_post.py, rx_ssb_chain.py и rx_ssb_adc_chain.py; default nr=0/filt=0 unchanged, CW/AM/FM остаются unsupported.
- [x] Соединить CIC → Hilbert/I delay → базовый SSB slow_dsp в частичный stateful pipeline: temp/reference/rx_ssb_chain.py.
- [x] Подключить ADC mux/read-previous порядок и midpoint interpolation I к SSB chain: temp/reference/rx_ssb_adc_chain.py.
- [ ] Получить эталонный результат на синусе/двухтональном тесте.
- [ ] Проверить полярность USB/LSB и измерить подавление нежелательной боковой полосы.
- [ ] Определить спецификацию выхода RX DSP: sample rate, format, latency.
- [ ] Сравнить IIR response с AVR-GCC на fixed vectors, выполнить int16 range audit и измерить transient после переключения filt, bypass/re-enable и mode; static IIR histories не сбрасываются фильтровым обработчиком.

## 3. TX — вопросы

- [ ] Проследить полный pipeline из четырёх ADC readings в _adc и следующий ssb() вызов.
- [x] Рассчитать номинальное ADC conversion timing из adc_start() и prescaler.
- [ ] Проверить фактическую sample-and-hold привязку и интервалы чтения ADC; в MULTI_ADC чтения разнесены по времени PLL I2C и вычислениями.
- [ ] Проверить диапазоны I/Q Hilbert, magnitude approximation, atan approximation и phase delta.
- [x] Вывести таблицу _UA/MAX_DP и зафиксировать phase slew limiter с переносом остатка: temp/13_TX_PHASE_SCALING.md.
- [ ] Измерить спектральное влияние MAX_DP и проверить знак/alias поведение dp около полного оборота.
- [ ] Подготовить эталонные входы mic и выходы df/amp.
- [ ] Отделить численный результат df от передачи PLL-регистров.
- [ ] Уточнить допустимую задержку между вычислением и применением Si5351.
- [ ] Сверить _F_SAMP_TX=4800 с реальной частотой Timer2 TX около 4809,375 Hz при стандартных настройках исходника.

## 4. Архитектура ESP32 — вопросы

- [ ] Выбрать окончательный RX input API: чередующиеся ADC events, массивы I/Q или выровненные пары.
- [ ] Проверить способы получения аналоговых I/Q без нарушения временного согласования.
- [ ] Выбрать ISR/DMA/block/task организацию по измеренному времени.
- [ ] Определить размеры блоков и верхнюю границу задержки.
- [x] Подготовлен черновик структур RxDspState и TxDspState: temp/10_DSP_INTERFACE_DRAFT.md.
- [ ] Утвердить структуры после reference tests.
- [ ] Определить интерфейс RF adapter для frequency_delta и amplitude.

## 5. Следующие задачи по порядку

1. Завершить state inventory: назначение, момент обновления и reset/lifecycle каждой переменной.
2. Закрыть временную модель ADC: определить ISR-to-ADSC offsets, ADC prescaler phase и I/Q aperture; analog acquisition/settling — отдельным измерением.
3. Установить фактическую AVR-GCC арифметику Hilbert на overrange vector: получить точные flags/disassembly и сравнить реальный результат с wide и wrap кандидатами.
4. Подключить startup timing model к полному RX reference harness и подготовить фиксированные синусоидальные/двухтональные векторы с промежуточными контрольными точками.
5. Сверить NR/IIR wide models с AVR fixed vectors и выполнить int16 range audit; затем добавить AM/FM branches.
6. Подготовить аналогичную модель SSB TX, включая integer atan2 macro semantics, MAX_DP и ADC pipeline.
7. Проверить и уточнить API из temp/10_DSP_INTERFACE_DRAFT.md по результатам reference harness.
8. Только после этого начинать перенос на ESP32.

## 6. Варианты, которые нужно сохранить для сравнения

- RX input: исходные чередующиеся ADC events / отдельные I[] и Q[] / source-aligned I/Q pairs.
- Processing: sample-by-sample ISR / DMA blocks / hybrid ISR+ring buffer+DSP task.
- Numerics: wide intermediate math / AVR-compatible arithmetic / documented fixed-point design.

Ни один из вариантов пока не объявлен окончательным.
