# Частичный RX reference pipeline — состав, границы и запуск

**Источник алгоритмов:** PE1NNZ uSDX, commit bf8acd31b8a2506c4e1d203dfb283feecae947e1.  
**Код:** temp/reference/.  
**Статус:** ADC mux/read-previous, I interpolation, CIC, Hilbert/I-delay, AGC/volume, NR и SSB IIR 1..3 соединены в частичную SSB reference chain. Startup ADC timing пока отдельная модель; точная aperture, AVR overflow, AM/FM и аудиовыход ещё впереди.

## 1. Что уже соединено

    analog I/Q values available at each Timer2 event
            |
            v
       RxAdcInputState
       ADMUX next / read previous
       I midpoint interpolation
            |
            | logical I/Q event
            v
       RxCicState
       NEW_RX=1
       8-phase schedule
            |
            | raw CIC I/Q pair
            v
       RxQuadratureState
       att2 scaling
       Q Hilbert FIR
       7-sample I delay
            |
            | -I_delayed - qh
            v
       RxSsbPostState
       fast AGC
       volume
       optional NR EMA
       optional SSB IIR (filt=1..3)
       clamp [-512, 511]
            |
            v
       baseline SSB audio sample

Одна выходная пара формируется после полного восьмифазного цикла исходного RX расписания.

## 2. Файлы и ответственность

| Файл | Роль |
|---|---|
| rx_adc_input.py | MUX для следующей конверсии, чтение предыдущей и I midpoint interpolation |
| rx_cic.py | Восемь активных NEW_RX фаз; отдаёт raw CIC pair до att2 |
| rx_quadrature.py | Применяет att2, вычисляет Hilbert Q, задерживает I на 7 пар |
| rx_ssb_post.py | USB/LSB post: fast AGC, volume, optional NR EMA, optional SSB IIR 1..3, clipping |
| rx_chain.py | Соединяет CIC и Hilbert/I-delay |
| rx_ssb_chain.py | Соединяет CIC, quadrature и базовый SSB post |
| rx_ssb_adc_chain.py | Подключает ADC input adapter к доступной SSB цепочке |
| rx_nr.py / test_rx_nr.py | NR EMA recurrence и integer deadband/state tests |
| rx_iir.py / test_rx_iir.py | Wide SSB IIR recurrence, impulse response и state lifecycle |
| test_*.py | Проверки отдельных блоков и границ между ними |

Важная граница: att2 применяется ровно один раз, в RxQuadratureState, на той же логической границе, где исходный process() масштабирует CIC outputs перед Hilbert.

## 3. Входной формат

Основной вход теперь принимает rx_ssb_adc_chain.py: для каждого Timer2 event передаются analog I и Q values, доступные при старте conversion на выбранном MUX-канале.

RxAdcInputState повторяет исходный порядок:
- I-handler выбирает ADC1/Q для следующей конверсии, затем читает предыдущий ADC0/I result;
- Q-handler выбирает ADC0/I для следующей конверсии, затем читает предыдущий ADC1/Q result;
- I result усредняется с предыдущим I result через truncation toward zero;
- первая операция чтения использует настраиваемый startup_adc_register, поскольку start_rx() не запускает первую конверсию явно.

rx_ssb_chain.py остаётся отдельной нижней обёрткой для случаев, когда логические I/Q events уже подготовлены. rx_ssb_adc_chain.py соединяет ADC input adapter с той же CIC→quadrature→post chain.

## 4. Выход

Параметры nr=0..8 и filt=0..3 передаются через RxSsbReferencePipeline и RxSsbAdcReferencePipeline. По умолчанию nr=0/filt=0, поэтому старое baseline поведение сохраняется. CW filters 4..7 не включены.\n\nКаждый готовый output содержит:
- текущие масштабированные I и Q;
- задержанный I;
- Hilbert Q;
- суммарный SSB audio input;
- финальный sample после fast AGC, volume, выбранных NR/IIR (если включены) и clipping.

Это не полный цифровой аудиовыход uSDX: выходная Comb/integrator interpolation и PWM stage ещё не включены.

## 5. Текущие ограничения

Модель покрывает SSB path с выбранной конфигурацией FAST_AGC compile option disabled. Поддерживаются agc=0/1, nr=0..8 и SSB filt=0..3. По умолчанию agc=1, nr=0, filt=0. NR и IIR recurrence — wide-intermediate models; фактическое AVR-GCC поведение signed overflow ещё не подтверждено. CW IIR filters 4..7 и AM/FM demodulators пока не реализованы.

Пока не поддерживаются:
- точная analog sample-and-hold aperture, ADC acquisition/settling time и jitter внутри Timer2 event;
- startup 25-cycle ADC timing внутри полной event-level chain (есть отдельный rx_adc_timing.py);
- CW IIR filters 4..7;
- AM/FM demodulators;
- audio output interpolator;
- TX;
- физический I2S/ADC/DAC и Si5351 adapters.

Неподдерживаемые режимы в rx_ssb_post.py не имитируются молча: AM/FM и CW filter IDs 4..7 дают NotImplementedError.

## 6. Запуск тестов на Windows

Синхронизировать репозиторий и перейти в:

    C:\github\uSDX-ESP32\temp\reference

Затем:

    python -m unittest -v

Используется стандартная библиотека Python; pip-зависимостей нет.

## 7. Статус проверок

- CIC schedule был сопоставлен с прямым каскадным FIR выражением на детерминированных I/Q потоках во время исследования.
- Для Hilbert рассчитана и внесена импульсная характеристика; в репозитории есть unit test.
- Для I delay проверена задержка ровно 7 decimated I/Q pairs.
- Для baseline AGC/volume добавлены tests, включая sign asymmetry signed right shift.
- Для chain добавлены integration tests: число выходных samples, quadrature→post handoff и output range.
- Для RxAdcInputState добавлены тесты MUX/read-previous канального порядка, startup ADC value и I midpoint interpolation.
- Для rx_ssb_adc_chain добавлены интеграционные тесты от Timer2-event values до SSB audio sample.

Важно: полный запуск unittest из свежего клона репозитория в исследовательской среде не был выполнен — среда не смогла разрешить github.com через DNS. Тестовые файлы сохранены в GitHub, а результаты математических проверок отдельных выражений и CIC scheduler отражены в журнале исследований.

## 8. Следующие расширения

1. Уточнить sample-and-hold aperture и ADC acquisition/settling time на выбранной физической схеме ESP32.
2. Сверить startup_adc_register/startup transient и реальную временную фазу I/Q на исходном AVR.
3. Сверить NR/IIR wide reference outputs с AVR-GCC vectors и завершить int16 range audit.
4. Подключить startup ADC timing к полной event-level chain после определения ISR/aperture offsets.
5. Добавить AM/FM ветви отдельно от SSB.
6. Добавить output CIC interpolator.
7. Только после этого сравнить полную reference chain и подключать ESP32 audio adapter.
## 9. Уточнение входной временной модели

rx_ssb_adc_chain.py использует RxAdcInputState:
- phase 0/I handler selects Q conversion and reads the previous ADC register;
- phase 1/Q handler selects I conversion and reads the previous ADC register;
- the same pattern repeats through the eight-event timer cycle;
- the first ADC register value is supplied as startup_adc_register and is not assumed to be zero by the source;
- I samples are midpoint-interpolated with C/C++ signed division truncation toward zero.

The model treats i_sample_at_tick/q_sample_at_tick as the analog values captured by the conversion started on that timer event. It does not calculate the exact aperture offset after ADSC, input acquisition settling or timer-to-aperture jitter. Those depend on the exact AVR ADC timing and the analog source impedance and remain open.
