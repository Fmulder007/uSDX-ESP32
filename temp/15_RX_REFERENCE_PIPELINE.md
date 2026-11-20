# Частичный RX reference pipeline — состав, границы и запуск

**Источник алгоритмов:** PE1NNZ uSDX, commit bf8acd31b8a2506c4e1d203dfb283feecae947e1.  
**Код:** temp/reference/.  
**Статус:** три базовые SSB стадии соединены; физический ADC input и полный RX ещё впереди.

## 1. Что уже соединено

    logical I/Q input events
            |
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
| rx_cic.py | Восемь активных NEW_RX фаз; отдаёт raw CIC pair до att2 |
| rx_quadrature.py | Применяет att2, вычисляет Hilbert Q, задерживает I на 7 пар |
| rx_ssb_post.py | Базовая USB/LSB/CW постобработка, fast AGC, volume, clipping |
| rx_chain.py | Соединяет CIC и Hilbert/I-delay |
| rx_ssb_chain.py | Соединяет CIC, quadrature и базовый SSB post |
| test_*.py | Проверки отдельных блоков и границ между ними |

Важная граница: att2 применяется ровно один раз, в RxQuadratureState, на той же логической границе, где исходный process() масштабирует CIC outputs перед Hilbert.

## 3. Входной формат

rx_ssb_chain.py получает уже демультиплексированные события логических каналов:

    I, Q, I, Q, I, Q, I, Q, ...

Каждое событие — пара:
- channel: "I" или "Q";
- sample: signed ADC value после смещения и назначения канала.

Модель пока не управляет физическим ADC и не повторяет ADMUX pipeline. Она также не делает исходную midpoint interpolation I. Эти операции должны быть добавлены на входной границе до CIC либо в отдельном source-compatible input adapter.

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
- ADMUX/read-previous ADC pipeline;
- I midpoint interpolation;
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

Важно: полный запуск unittest из свежего клона репозитория в исследовательской среде не был выполнен — среда не смогла разрешить github.com через DNS. Тестовые файлы сохранены в GitHub, а результаты математических проверок отдельных выражений и CIC scheduler отражены в журнале исследований.

## 8. Следующие расширения

1. Добавить RxAdcInputState: ADMUX pipeline, read-previous semantics, первая conversion и channel mapping.
2. Добавить source-compatible I midpoint interpolation.
3. Сверить выход CIC после подключения ADC model с исходной временной фазой.
4. После этого добавить NR и каждый IIR filter отдельно.
5. Добавить AM/FM ветви отдельно от базовой SSB.
6. Добавить output CIC interpolator и только после сравнения подключать ESP32 audio adapter.
