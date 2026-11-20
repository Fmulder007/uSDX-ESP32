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

## 2. RX — вопросы

- [x] Развернуть все восемь фаз CIC в таблицу входов/регистров/выходов: temp/08_RX_CIC_PHASES.md.
- [ ] Сверить комментарий исходника о 12 dB CIC gain с коэффициентным масштабом активной реализации и att2.
- [ ] Зафиксировать временную привязку каждого I/Q отсчёта к таймерному событию, включая first-conversion startup transient и read-previous/start-next pipeline.
- [x] Зафиксировать наблюдаемое source reset поведение CIC/Hilbert/AGC/IIR при cold start и TX→RX: temp/12_STATE_LIFECYCLE.md.
- [ ] Проверить переходные процессы cold start, TX→RX и повторного TX на эталонных сигналах.
- [ ] Проверить диапазон промежуточных значений CIC и Hilbert.
- [ ] Получить эталонный результат на синусе/двухтональном тесте.
- [ ] Проверить полярность USB/LSB и измерить подавление нежелательной боковой полосы.
- [ ] Определить спецификацию выхода RX DSP: sample rate, format, latency.

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
2. Закрыть временную модель ADC: pipeline, sample-and-hold и I/Q aperture.
3. Разобрать и проверить масштабирование CIC, включая комментарий о 12 dB gain.
4. Расширить host-side RX reference model: ADC mux pipeline → I interpolation → CIC → Hilbert/I delay.
5. Добавить slow_dsp: demod, AGC, NR и IIR с отдельными состояниями.
6. Подготовить аналогичную модель SSB TX, включая integer atan2 macro semantics, MAX_DP и ADC pipeline.
7. Проверить и уточнить API из temp/10_DSP_INTERFACE_DRAFT.md по результатам reference harness.
8. Только после этого начинать перенос на ESP32.

## 6. Варианты, которые нужно сохранить для сравнения

- RX input: исходные чередующиеся ADC events / отдельные I[] и Q[] / source-aligned I/Q pairs.
- Processing: sample-by-sample ISR / DMA blocks / hybrid ISR+ring buffer+DSP task.
- Numerics: wide intermediate math / AVR-compatible arithmetic / documented fixed-point design.

Ни один из вариантов пока не объявлен окончательным.
