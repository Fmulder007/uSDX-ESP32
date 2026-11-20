# Журнал исследований

## 2026-11-20 — исходный снимок и первый DSP-разбор

### Исходная база
- Репозиторий PE1NNZ: https://github.com/threeme3/usdx
- Commit: bf8acd31b8a2506c4e1d203dfb283feecae947e1
- Версия в исходнике: 1.02x
- Файлы: usdx.ino, usdx_filter.h, usdx_settings.h.

### RX
- Подтверждён NEW_RX=1, AF_OUT=1.
- SIMPLE_RX не определён; OLD_RX неактивна.
- Активное расписание проходит через sdr_rx_00...sdr_rx_07.
- Один ADC переключается между I/Q; I-ветвь усредняет предыдущий и текущий отсчёты для временного выравнивания.
- Частоты: timer 62,5 kHz; по 31,25 kS/s на канал; 7,8125 kS/s для пар I/Q.
- Активный Hilbert: буфер Q 14 значений и задержка I 7 значений.
- slow_dsp() выполняется на частоте пар, затем Comb/интеграторная секция формирует поток к PWM.

### TX
- F_SAMP_TX=4800, _UA=600.
- Активны MULTI_ADC и MORE_MIC_GAIN.
- SSB использует mic filter, Hilbert, magnitude approximation, approximate atan2, phase delta и MAX_DP.
- dsp_tx() конвейерно готовит управляющие значения и взаимодействует с Si5351/PWM.
- Требуется уточнить точную ADC временную модель и hardware latency.

### Перенос
- Зафиксирован риск ширины int: AVR 16-bit vs ESP32 32-bit.
- Созданы рабочие документы RX, TX, состояния/тайминга, вариантов архитектуры и численной совместимости.
- Портирование не начато.
### Углубление RX CIC и ADC — 2026-11-20
- Расписаны все восемь фаз активной RX-последовательности.
- Выведена эквивалентность двух decimate-by-2 FIR ступеней с коэффициентами [1,3,3,1] к CIC N=3, R=4; эквивалентная импульсная последовательность [1,3,6,10,12,12,10,6,3,1].
- Зафиксировано, что итоговый I результат вызывается на фазе 0, Q result формируется на фазе 7 и используется следующим вызовом process().
- Рассчитаны номинальные ADC divider/conversion timings для F_MCU=20 MHz.
- Найдено требующее проверки расхождение: комментарий исходника к R=4 говорит 12 dB gain, тогда как прямой подсчёт коэффициентов активной CIC-ветви даёт raw gain 32 до att2 и 8 после att2=2.

### Фактические timer rates — 2026-11-20
- Проверено: исходник требует Arduino build с F_CPU=16 MHz, затем переопределяет F_CPU на 20 007 000 Hz.
- Timer2 использует целочисленную формулу OCR2A=((F_CPU/64)/fs)-1.
- При RX target 62 500 Hz получается OCR2A=4 и фактическая частота около 62 521,875 Hz.
- При TX target 4 800 Hz получается OCR2A=64 и фактическая частота около 4 809,375 Hz.
- Timer1 PWM при target 78 125 Hz ограничивает top до 255; фактическая carrier около 78 152,344 Hz.
- _F_SAMP_TX при стандартном F_MCU=20 MHz остаётся 4 800, поэтому требуется отдельно проверить расхождение с реальным TX timer rate; не менять исходную шкалу до тестов.

### Черновик границы DSP-ядра — 2026-11-20
- Подготовлен temp/10_DSP_INTERFACE_DRAFT.md.
- Рассмотрены три RX input формы: raw alternating ADC events, массивы I/Q, source-aligned I/Q pairs.
- Предложено сохранить одну последовательную sample state machine и добавить block wrapper поверх неё, чтобы sample/block processing сравнивались одинаково.
- Предложен выход DSP_TX как пара frequency_delta + amplitude; Si5351/PWM остаются в RF adapter.
- API не утверждён: окончательные типы и границы зависят от reference harness и численной проверки.

### Уточнение ADC pipeline — 2026-11-20
- RX common_i/common_q сначала выбирают ADMUX для следующей конверсии и запускают её, затем читают результат предыдущей конверсии.
- В active schedule common_i ставит admux[1] (следующий канал ADC1), но читает предыдущий результат ADC0 (I); common_q ставит admux[0], но читает предыдущий результат ADC1 (Q).
- После cold start первая выборка может быть startup transient: start_rx() конфигурирует ADC, но не запускает явную первую конверсию до старта таймера.
- TX MULTI_ADC усредняет четыре чтения, но они неравномерны: между первым и вторым чтением выполняется PLL bulk I2C transfer (~88 us по комментарию исходника); далее идут ssb() и freq_calc_fast().
- Этот порядок должен быть воспроизведён в reference model; нельзя заменять его синхронным I/Q или равномерным 4x oversampling без измерений.

### Первая исполняемая reference-модель — RX CIC — 2026-11-20
- Добавлена папка temp/reference/.
- rx_cic.py воспроизводит активную восьмифазную последовательность NEW_RX=1 на уже разделённых I/Q выборках.
- test_rx_cic.py сравнивает фазовое расписание с прямой двухступенчатой CIC формулой и проверяет задержку Q в паре.
- Эквивалентная модель была проверена на детерминированных псевдослучайных I/Q потоках длиной 4, 8, 32, 128, 256 и 1024 samples; выходы scheduler совпали с прямой формулой с учётом Q фазового смещения.
- Скрипты используют только стандартную библиотеку Python; это ещё не полный AVR reference и не тест Hilbert/демодуляции.

### Вторая исполняемая RX reference-модель — Hilbert/I delay — 2026-11-20
- Добавлен temp/reference/rx_quadrature.py.
- Перенесена активная формула qh с сохранением четырёх отдельных signed integer divisions (truncation toward zero).
- Добавлен 14-value Q history и 7-value I delay.
- Unit tests проверяют 15-точечную impulse response: [-2,0,-8,0,-21,0,-79,0,79,0,21,0,8,0,2], задержку I ровно на 7 I/Q pairs и знак SSB audio input.
- Модель возвращает также текущие undelayed I/Q значения для AM/FM ветвей; slow_dsp пока не входит в неё.

### Соединение RX CIC и Hilbert reference blocks — 2026-11-20
- Граница блоков уточнена: RxCicState выдаёт raw I/Q после CIC, но до att2; RxQuadratureState выполняет att2 и затем Hilbert/I delay, как исходная граница process().
- Добавлена обёртка temp/reference/rx_chain.py, соединяющая оба блока на упорядоченном потоке I,Q,I,Q,...
- Добавлены integration tests на частоту выдачи пары, начальное q_ac2 и однократное применение att2.
- Это частичный RX pipeline; ADC mux/read-previous pipeline, I midpoint interpolation, slow_dsp и audio interpolator пока не реализованы.

### Базовый SSB slow_dsp reference — 2026-11-20
- Добавлены temp/reference/rx_ssb_post.py и test_rx_ssb_post.py.
- Модель воспроизводит default USB/LSB/CW path при FAST_AGC выключенном, agc=1, nr=0, filt=0; также покрывает ручную volume ветку agc!=1 и финальный clamp [-512,511].
- Зафиксирован signed arithmetic shift: +100>>10=0, -100>>10=-1; gain update может быть sign-asymmetric.
- AM/FM, NR и IIR намеренно не моделируются и вызывают NotImplementedError.
- В исходном меню VOLUME имеет диапазон -1..16; -1 — команда powerDown, рабочая модель принимает 0..16.
### ADC input adapter и сквозная timer-event SSB chain — 2026-11-20
- Добавлен temp/reference/rx_adc_input.py: на каждом Timer2 event он выбирает MUX для следующей конверсии, возвращает результат предыдущей, повторяет I midpoint interpolation с signed division truncation toward zero.
- Startup ADC register value вынесен в параметр: исходник после start_rx() явно не запускает первую конверсию, поэтому значение первого ADC read не гарантируется нулём.
- Добавлены тесты канального порядка I/Q, startup register value и midpoint I interpolation.
- Добавлен temp/reference/rx_ssb_adc_chain.py, который соединяет ADC input adapter → CIC → att2/Hilbert/I delay → baseline SSB fast AGC/volume/clipping.
- Полная программная timer-event модель теперь начинается с analog I/Q values, доступных для conversion start на каждом событии; точное sample-and-hold aperture, acquisition settling и jitter внутри conversion пока не моделируются.
- Исправлен integration test ожидания i_s0za1: на фазе 6 обновляется odd history, а последнее i_s0za1 было записано на фазе 4.


### RX ADC: первая конверсия после ADEN — 2026-11-20
- Повторно проверен adc_start() и подтверждено: ADEN включается, но ADSC в функции закомментирован; первая конверсия начинается только из первого Timer2 RX ISR.
- Для RX исходник выбирает ADC prescaler=16: ADC clock ≈1,2504375 MHz. Timer2 интервал — 320 CPU cycles ≈15,9944 мкс.
- По datasheet ATmega328P первая конверсия после ADEN занимает 25 ADC cycles (400 CPU cycles ≈19,993 мкс), обычная — 13 cycles (208 CPU cycles ≈10,396 мкс). Sample-and-hold: 13,5 cycles для первой, 1,5 для обычной.
- Следствие: event 1 приходит, пока первый conversion ещё выполняется; ADSC повторно устанавливается при уже активной конверсии, а ADC register ещё содержит старое значение. Event 2 получает первый готовый результат ADC1/Q в логическом I slot. На event 4 настоящая I выборка ещё усредняется с предыдущим ошибочно назначенным Q; при стабильной работе I midpoint возвращается к правильной последовательности на следующем I slot.
- Добавлены temp/reference/rx_adc_timing.py и test_rx_adc_timing.py: четыре теста подтверждают startup stall, назначение первого Q результата, восстановление I/Q cadence и sample-and-hold offsets.
- Прежняя rx_adc_input.py оставлена как упрощённая логическая модель установившегося режима; сквозная rx_ssb_adc_chain.py пока не подключена к startup timing model.
- Открыто: точный цикл ISR от входа в обработчик до ADSC, фаза свободного ADC prescaler относительно Timer2, фактический I/Q aperture skew, analog acquisition/settling и эффективная разрядность при ADC clock выше 1 MHz.
- Подробный разбор: temp/16_RX_ADC_STARTUP_TIMING.md. Использован Microchip ATmega328P datasheet DS40002061A, разделы 24.4–24.5.


### RX numeric range audit: CIC gain и Hilbert intermediates — 2026-11-20
- Проверена граница ADC path: ADC-511 даёт [-511,512]; I midpoint average остаётся в том же диапазоне.
- Коэффициентная граница активной CIC: первая FIR [1,3,3,1] даёт [-4088,4096], после M_SR=1 — [-2044,2048]; вторая ступень даёт raw [-16352,16384]. Все значения помещаются в signed int16.
- DC gain: первая ступень 8/2=4, вторая 8, raw total=32; при default att2=2 перед Hilbert остаётся gain8. В source smeter() компенсирует att2 и использует R*8=32, что независимо согласуется с raw CIC gain.
- Комментарий рядом с R=4 ("providing 12dB gain") не описывает полный коэффициентный DC gain active NEW_RX; смысл комментария точно не установлен, его нельзя использовать для scaling.
- Проверка Hilbert выявила достижимый full-scale Q sine 650 Hz при 31.25 kS/s и att2=2: произведение на 5 равно 38790, третий числитель 34915. Это выше signed int16. Математическая wide модель даёт qh=3890; условный modulo-16-bit candidate даёт 3379 на том же примере.
- Signed overflow в C/C++ не определён стандартом; фактический AVR-GCC результат нужно проверить на точной версии компилятора, флагах и disassembly/runtime vector. До этого не назначать wrap или int32 как bit-exact решение.
- Добавлены temp/reference/rx_numeric_audit.py и test_rx_numeric_audit.py. Три focused tests прошли на host-side validation copy: CIC DC bounds/gain, full-scale 650Hz overflow vector, wide-vs-wrap illustration.
- Полный разбор: temp/17_RX_NUMERIC_RANGE.md.


### RX post-processing: NR recurrence и IIR state — 2026-11-20
- Проверен активный slow_dsp() порядок: detector branch для AM/FM, AGC/volume, NR, optional filt_var(), final clamp [-512,511].
- Snapshot defaults: mode=USB, volume=12, filt=0, nr=0, agc=1. FAST_AGC выключен в usdx_settings.h, следовательно используется process_agc_fast; volume после него выполняет >>4. NR и IIR по умолчанию bypass.
- NR=1..8 использует EA(ea1,in,1<<(nr-1)), то есть first-order EMA с N=1…128. NR=1 является passthrough, NR=8 — nominal alpha=1/128 и linear -3 dB frequency около9.75Hz при 7812.5 SPS.
- Целочисленное деление C-style truncation-to-zero создаёт deadband: при NR=8 разница input-state менее128 не изменяет ea1; NR=2 — разница менее2. NR=0 не вызывает функцию, поэтому static ea1 freeze-ится, а не сбрасывается. Одна переменная ea1 общая для всех NR levels.
- Добавлены temp/reference/rx_nr.py и test_rx_nr.py. Шесть focused assertions проверены на recurrence: NR1 passthrough, NR2 step response, NR8 deadband, отрицательное truncation, NR0 freeze/level reuse, range validation.
- IIR карта: filt=0 bypass; SSB filt1..3 — общая 300-Hz pre-section и две Direct Form I biquad sections; CW filt4..7 — отдельные biquad coefficients, zc0>>3 output. UI labels не считать измеренной полосой пропускания.
- Все histories filt_var() объявлены static; filter menu выставляет _init, но сами фильтровые histories не reset-ятся. При filt=0 фильтр не вызывается и его histories заморожены. Это потенциальный источник transient при смене filter/mode.
- Подробный разбор: temp/18_RX_POST_NR_IIR.md. Добавлены wide-intermediate модели rx_nr.py/rx_iir.py и подключены через rx_ssb_post.py → rx_ssb_chain.py → rx_ssb_adc_chain.py. Default nr=0/filt=0 сохраняет прежний baseline. Полный AVR-GCC width comparison и CW/AM/FM ещё открыты.


### RX SSB chain integration: NR/IIR — 2026-11-20
- Расширен RxSsbPostState: добавлены persistent RxNrState и RxSsbIirState после AGC/volume, перед final clip.
- RxSsbReferencePipeline и RxSsbAdcReferencePipeline теперь принимают nr=0..8 и SSB filt=0..3 и передают параметры в post stage.
- При defaults nr=0/filt=0 прежнее поведение остаётся прежним; filt=0 не изменяет stored IIR histories, NR=0 не изменяет ema state.
- CW filters 4..7 и AM/FM не аппроксимируются: остаются явным NotImplementedError.
- Добавлены post integration tests и full-chain config test. В этом исследовательском окружении полный unittest suite не запускался; отдельные NR/IIR recurrence and post-stage assertions проверены вручную по тем же формулам.
- Полная карта и ограничения: temp/15_RX_REFERENCE_PIPELINE.md; NR/IIR детали: temp/18_RX_POST_NR_IIR.md.


### RX SSB IIR range audit — 2026-11-20
- Добавлена wide-intermediate диагностика audit_ssb_iir_intermediates() в temp/reference/rx_numeric_audit.py; она повторяет source recurrence SSB filt=1..3 и записывает максимум каждого промежуточного узла, а также первый индекс превышения signed int16.
- Вектор: 2.5 kHz sine, fs=7812.5 Hz, amplitude512, 5000 samples. Общий prefilter sum достигает37315 во всех трёх фильтрах; filt=1 отдельный множитель 18*zc1 достигает46980, stage-2 feedback sum достигает43357. Все три значения выше 32767.
- Контрольный vector: 3.9 kHz, amplitude128, 5000 samples — все перечисленные промежуточные значения остаются в signed int16 для filt1..3.
- SSB IIR вызывается до финального clip [-512,511]; volume range допускает отсутствие attenuation (agc=1,volume=16) или left shift при agc!=1,volume=14..16. Поэтому итоговый output clip не гарантирует безопасные intermediate values.
- Добавлены два test cases в test_rx_numeric_audit.py: reachable wide-trajectory overrange и low-amplitude in-range vector.
- Это анализ mathematical wide trajectory. После первого signed overflow фактический AVR-GCC state/output может разойтись; AVR probe/golden values пока не получены.
- Подробный отчёт: temp/18_RX_POST_NR_IIR.md; общая численная карта: temp/17_RX_NUMERIC_RANGE.md.


### AVR IIR probe подготовлен — 2026-11-20
- Добавлены temp/reference/avr_iir_probe.cpp и avr_iir_probe.md.
- Probe содержит 25-sample periodic table для 2.5 kHz / amplitude512 / fs7812.5Hz; запускает по 5000 samples для каждого SSB filter 1..3.
- Сравнивает source-style int16 state/expressions под pragma GCC optimize("Ofast") и explicit int32 wide model; выводит volatile checksum и конечные state arrays.
- Probe не собирался: AVR-GCC в текущем исследовательском окружении отсутствует. На будущее требуется сохранить `avr-gcc --version`, flags, disassembly и значения всех checksum/state.
