# RX SSB — базовая постобработка slow_dsp()

**Источник:** PE1NNZ uSDX, commit bf8acd31b8a2506c4e1d203dfb283feecae947e1.  
**Статус:** базовая USB/LSB/CW ветка описана и вынесена в отдельную host-side модель; NR/IIR/AM/FM не входят.

## 1. Активный базовый путь

Для исходных начальных значений:
- FAST_AGC выключен в usdx_settings.h;
- agc = 1;
- nr = 0;
- filt = 0;
- volume = 12;
- mode первоначально USB, но после setup() может быть загружен из настроек.

В базовой SSB ветке slow_dsp():
1. Вход ac — уже совмещённый -i_delayed - qh.
2. Вызывается process_agc_fast(ac).
3. Результат сдвигается вправо на 16-volume.
4. NR не вызывается, поскольку nr=0.
5. IIR не вызывается, поскольку filt=0.
6. Результат ограничивается диапазоном [-512, 511].

Это минимальный путь, который нужно проверить сразу после Hilbert/I alignment.

Источники: [AGC/NR/slow_dsp](https://github.com/threeme3/usdx/blob/bf8acd31b8/usdx.ino#L2420-L2665), [settings](https://github.com/threeme3/usdx/blob/bf8acd31b8/usdx_settings.h#L1-L60).

## 2. Fast AGC — точная формула

Состояние:
- gain — signed int16, начальное значение 1024.

Функция:

    out = (gain >= 1024) ? (gain >> 10) * in : in;
    accum = 1 - abs(out >> 10);
    if ((INT16_MAX - gain) > accum)
        gain = gain + accum;
    if (gain < 1)
        gain = 1;

Важные свойства:
- обновление gain зависит от каждого входного sample;
- multiplier — целая часть gain >> 10, а не дробный gain;
- при gain=1024 вход проходит с коэффициентом 1;
- gain — 16-bit состояние;
- accum может быть отрицательным, поэтому формула способна уменьшать gain для достаточно сильных отсчётов, хотя комментарий рядом с кодом называет старый AGC алгоритмом, который «only increases gain». Комментарий и выражение не полностью согласуются; при переносе ориентироваться на фактическую формулу и проверить измерениями.

## 3. Signed right shift и знак сигнала

В выражении:

    accum = 1 - abs(out >> 10)

на AVR/GCC с arithmetic right shift:
- +100 >> 10 = 0, поэтому accum = 1;
- -100 >> 10 = -1, поэтому accum = 0.

Таким образом, gain update может быть sign-asymmetric для малых отсчётов, хотя входные амплитуды равны.

Это наблюдаемое следствие signed arithmetic right shift. Оно не является рекомендацией исправить алгоритм. Точное поведение выбранного AVR toolchain следует подтвердить; ESP32 source-compatible модель пока явно использует arithmetic right shift и 16-bit wrap.

В rx_ssb_post.py это свойство проверяется отдельными тестами.

## 4. Volume и output clipping

При agc==1:

    ac = out >> (16-volume)

При volume=12 выполняется сдвиг вправо на 4.

Если agc!=1 при выключенном FAST_AGC:
- volume<=13: ac >>= (13-volume);
- volume>13: ac <<= (volume-13).

В конце:

    ac = min(max(ac, -512), 511)

Для отрицательных значений arithmetic right shift округляет в сторону минус бесконечности: например, -100 >> 4 = -7, а не -6.

В исходном меню VOLUME имеет диапазон -1..16. Значение -1 используется как отдельная команда powerDown, а не как нормальный коэффициент громкости; модель DSP принимает только 0..16.

## 5. Исполняемая модель

- [rx_ssb_post.py](reference/rx_ssb_post.py)
- [test_rx_ssb_post.py](reference/test_rx_ssb_post.py)

Модель поддерживает только:
- USB/LSB/CW passthrough до AGC;
- FAST_AGC compile option выключен;
- agc=1 fast AGC либо ручную volume ветку agc!=1;
- nr=0;
- filt=0;
- clipping.

При включении NR, IIR, AM или FM она выдаёт NotImplementedError, чтобы не создавать ложное впечатление полной поддержки slow_dsp.

## 6. Следующие проверки

- Сравнить состояние gain и выход fast AGC на одинаковом массиве входов AVR reference vs ESP32 model.
- Отдельно проверить +x и -x для малых значений.
- Проверить поведение около порога |out|=1024 и на максимальном сигнале.
- Установить, может ли gain уменьшаться в реальном коде несмотря на комментарий.
- После этого добавить NR и IIR как независимые блоки с отдельными состояниями.
