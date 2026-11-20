# Частичный RX reference pipeline — состав, границы и запуск

**Источник алгоритмов:** PE1NNZ uSDX, commit bf8acd31b8a2506c4e1d203dfb283feecae947e1.  
**Код:** temp/reference/.  
**Статус:** ADC mux/read-previous, I interpolation, CIC, Hilbert/I-delay и базовая SSB post-processing соединены; точная sample-and-hold aperture, NR/IIR/AM/FM и аудиовыход ещё впереди.

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
| rx_ssb_post.py | Базовая USB/LSB/CW постобработка, fast AGC, volume, clipping |
| rx_chain.py | Соединяет CIC и Hilbert/I-delay |
| rx_ssb_chain.py | Соединяет CIC, quadrature и базовый SSB post |
| rx_ssb_adc_chain.py | Подключает ADC input adapter к доступной SSB цепочке |
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

Каждый готовый output содержит:
- текущие масштабированные I и Q;
- задержанный I;
- Hilbert Q;
- суммарный SSB audio input;
- финальный sample после базового fast AGC, volume и clipping.

Это не полный цифровой аудиовыход uSDX: выходная Comb/integrator interpolation и PWM stage ещё не включены.

## 5. Текущие ограничения

Модель покрывает только базовый SSB:
- FAST_AGC compile option выключен;
- agc=1;
- nr=0;
- filt=0;
- USB/LSB/CW common audio path.

Пока не поддерживаются:
- точная analog sample-and-hold aperture, ADC acquisition/settling time и jitter внутри Timer2 event;
- NR;
- IIR filters;
- AM/FM demodulators;
- audio output interpolator;
- TX;
- физический I2S/ADC/DAC и Si5351 adapters.

Неподдерживаемые режимы в rx_ssb_post.py не имитируются молча: модель выдаёт NotImplementedError.

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
3. Добавить NR и каждый IIR filter отдельно.
4. Добавить AM/FM ветви отдельно от базовой SSB.
5. Добавить output CIC interpolator.
6. Только после этого сравнить полную reference chain и подключать ESP32 audio adapter.
## 9. Уточнение входной временной модели

rx_ssb_adc_chain.py использует RxAdcInputState:
- phase 0/I handler selects Q conversion and reads the previous ADC register;
- phase 1/Q handler selects I conversion and reads the previous ADC register;
- the same pattern repeats through the eight-event timer cycle;
- the first ADC register value is supplied as startup_adc_register and is not assumed to be zero by the source;
- I samples are midpoint-interpolated with C/C++ signed division truncation toward zero.

The model treats i_sample_at_tick/q_sample_at_tick as the analog values captured by the conversion started on that timer event. It does not calculate the exact aperture offset after ADSC, input acquisition settling or timer-to-aperture jitter. Those depend on the exact AVR ADC timing and the analog source impedance and remain open.
