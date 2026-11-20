/*
 * AVR diagnostic probe for the PE1NNZ uSDX SSB filt_var() branches 1..3.
 *
 * Build for ATmega328P:
 *   avr-g++ --version
 *   avr-g++ -mmcu=atmega328p -std=gnu++11 -Os -flto -Wall -Wextra \
 *       -o avr_iir_probe.elf avr_iir_probe.cpppppp
 *   avr-objdump -d -S avr_iir_probe.elf > avr_iir_probe.lst
 *
 * Inspect probe_source_checksum[], probe_wide_checksum[], and the final
 * state arrays in a debugger/simulator. This file is a diagnostic only.
 */

#include <stdint.h>
#include <limits.h>

#if !defined(__AVR__)
#error "This probe must be compiled for an AVR target"
#endif

#if INT_MAX != 32767
#error "Expected 16-bit AVR int"
#endif

#define SAMPLE_COUNT 5000
#define SINE_LENGTH 25

/* Один период 2.5 kHz tone при fs=7812.5 samples/s, amplitude 512. */
static const int16_t sine_25[SINE_LENGTH] = {
       0,  463, -395, -127,  503,
    -301, -247,  511, -188, -350,
     487,  -64, -432,  432,   64,
    -487,  350,  188, -511,  247,
     301, -503,  127,  395, -463
};

typedef struct {
    int16_t zz1, zz2;
    int16_t za1, za2;
    int16_t zb1, zb2;
    int16_t zc1, zc2;
} SourceState;

typedef struct {
    int32_t zz1, zz2;
    int32_t za1, za2;
    int32_t zb1, zb2;
    int32_t zc1, zc2;
} WideState;

/* Результаты доступны в debugger после выхода main в бесконечный цикл. */
volatile uint32_t probe_source_checksum[3];
volatile uint32_t probe_wide_checksum[3];

volatile int16_t probe_source_final_state[3][8];
volatile int32_t probe_wide_final_state[3][8];

/* filt_var() is defined before the source pragma at usdx.ino:2712.
 * Do not add Ofast here: use the translation unit's normal -Os flags. */
__attribute__((noinline))
static int16_t source_style_step(SourceState *s, int16_t input, uint8_t filt)
{
    int16_t za0 = input;
    int16_t zb0;
    int16_t zc0;

    /* Порядок обновления входной pre-section — как в filt_var(). */
    s->zz2 = s->zz1;
    s->zz1 = za0;
    za0 = (30 * (za0 - s->zz2) + 25 * s->zz1) >> 5;

    if (filt == 1) {
        zb0 = ((za0 + 2 * s->za1 + s->za2) >> 1)
            - ((13 * s->zb1 + 11 * s->zb2) >> 4);
        zc0 = ((zb0 + 2 * s->zb1 + s->zb2) >> 1)
            - ((18 * s->zc1 + 11 * s->zc2) >> 4);
    } else if (filt == 2) {
        zb0 = ((za0 + 2 * s->za1 + s->za2) >> 1)
            - ((2 * s->zb1 + 8 * s->zb2) >> 4);
        zc0 = ((zb0 + 2 * s->zb1 + s->zb2) >> 2)
            - ((4 * s->zc1 + 8 * s->zc2) >> 4);
    } else {
        zb0 = ((za0 + 2 * s->za1 + s->za2) >> 1)
            - ((0 * s->zb1 + 4 * s->zb2) >> 4);
        zc0 = ((zb0 + 2 * s->zb1 + s->zb2) >> 2)
            - ((0 * s->zc1 + 4 * s->zc2) >> 4);
    }

    s->zc2 = s->zc1;
    s->zc1 = zc0;
    s->zb2 = s->zb1;
    s->zb1 = zb0;
    s->za2 = s->za1;
    s->za1 = za0;

    return zc0;
}


__attribute__((noinline))
static int32_t wide_step(WideState *s, int16_t input, uint8_t filt)
{
    int32_t za0 = input;
    int32_t zb0;
    int32_t zc0;

    s->zz2 = s->zz1;
    s->zz1 = za0;
    za0 = (30L * (za0 - s->zz2) + 25L * s->zz1) >> 5;

    if (filt == 1) {
        zb0 = ((za0 + 2L * s->za1 + s->za2) >> 1)
            - ((13L * s->zb1 + 11L * s->zb2) >> 4);
        zc0 = ((zb0 + 2L * s->zb1 + s->zb2) >> 1)
            - ((18L * s->zc1 + 11L * s->zc2) >> 4);
    } else if (filt == 2) {
        zb0 = ((za0 + 2L * s->za1 + s->za2) >> 1)
            - ((2L * s->zb1 + 8L * s->zb2) >> 4);
        zc0 = ((zb0 + 2L * s->zb1 + s->zb2) >> 2)
            - ((4L * s->zc1 + 8L * s->zc2) >> 4);
    } else {
        zb0 = ((za0 + 2L * s->za1 + s->za2) >> 1)
            - ((0L * s->zb1 + 4L * s->zb2) >> 4);
        zc0 = ((zb0 + 2L * s->zb1 + s->zb2) >> 2)
            - ((0L * s->zc1 + 4L * s->zc2) >> 4);
    }

    s->zc2 = s->zc1;
    s->zc1 = zc0;
    s->zb2 = s->zb1;
    s->zb1 = zb0;
    s->za2 = s->za1;
    s->za1 = za0;

    return zc0;
}

int main(void)
{
    for (uint8_t filter_index = 0; filter_index < 3; ++filter_index) {
        const uint8_t filt = filter_index + 1;
        SourceState source = {0};
        WideState wide = {0};
        uint32_t source_checksum = 0;
        uint32_t wide_checksum = 0;

        for (uint16_t n = 0; n < SAMPLE_COUNT; ++n) {
            const int16_t sample = sine_25[n % SINE_LENGTH];
            const int16_t source_out = source_style_step(&source, sample, filt);
            const int32_t wide_out = wide_step(&wide, sample, filt);

            source_checksum = source_checksum * 33UL + (uint16_t)source_out;
            wide_checksum = wide_checksum * 33UL + (uint16_t)wide_out;
        }

        probe_source_checksum[filter_index] = source_checksum;
        probe_wide_checksum[filter_index] = wide_checksum;

        probe_source_final_state[filter_index][0] = source.zz1;
        probe_source_final_state[filter_index][1] = source.zz2;
        probe_source_final_state[filter_index][2] = source.za1;
        probe_source_final_state[filter_index][3] = source.za2;
        probe_source_final_state[filter_index][4] = source.zb1;
        probe_source_final_state[filter_index][5] = source.zb2;
        probe_source_final_state[filter_index][6] = source.zc1;
        probe_source_final_state[filter_index][7] = source.zc2;

        probe_wide_final_state[filter_index][0] = wide.zz1;
        probe_wide_final_state[filter_index][1] = wide.zz2;
        probe_wide_final_state[filter_index][2] = wide.za1;
        probe_wide_final_state[filter_index][3] = wide.za2;
        probe_wide_final_state[filter_index][4] = wide.zb1;
        probe_wide_final_state[filter_index][5] = wide.zb2;
        probe_wide_final_state[filter_index][6] = wide.zc1;
        probe_wide_final_state[filter_index][7] = wide.zc2;
    }

    for (;;) {
        /* Исследовать volatile globals через debugger/simulator. */
    }
}
