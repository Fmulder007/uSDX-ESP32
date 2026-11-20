/*
 * AVR diagnostic probe for PE1NNZ uSDX process_nr().
 *
 * process_nr() is defined before the source Ofast pragma, so this probe has
 * no local Ofast pragma and uses the normal translation-unit optimization.
 *
 * Build for ATmega328P:
 *   avr-g++ --version
 *   avr-g++ -mmcu=atmega328p -std=gnu++11 -Os -flto -Wall -Wextra \
 *       -o avr_nr_probe.elf avr_nr_probe.cpp
 *   avr-objdump -d -S avr_nr_probe.elf > avr_nr_probe.lst
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

typedef struct {
    int16_t ea1;
} SourceState;

typedef struct {
    int32_t ea1;
} WideState;

volatile uint32_t probe_source_checksum[8];
volatile uint32_t probe_wide_checksum[8];
volatile int16_t probe_source_final_state[8];
volatile int32_t probe_wide_final_state[8];

__attribute__((noinline))
static int16_t source_style_nr_step(SourceState *s, int16_t input, uint8_t nr)
{
    /* Same recurrence and expression width as EA(ea1, in, 1 << (nr-1)). */
    s->ea1 = s->ea1 + (input - s->ea1) / (1 << (nr - 1));
    return s->ea1;
}

__attribute__((noinline))
static int32_t wide_nr_step(WideState *s, int16_t input, uint8_t nr)
{
    const int32_t divisor = 1L << (nr - 1);
    const int32_t delta = (int32_t)input - s->ea1;
    s->ea1 += delta / divisor;
    return s->ea1;
}

int main(void)
{
    for (uint8_t level_index = 0; level_index < 8; ++level_index) {
        const uint8_t nr = level_index + 1;
        SourceState source = {0};
        WideState wide = {0};
        uint32_t source_checksum = 0;
        uint32_t wide_checksum = 0;

        for (uint16_t n = 0; n < SAMPLE_COUNT; ++n) {
            const int16_t input = (n & 1) ? 32767 : -32767;
            const int16_t source_out = source_style_nr_step(&source, input, nr);
            const int32_t wide_out = wide_nr_step(&wide, input, nr);

            source_checksum = source_checksum * 33UL + (uint16_t)source_out;
            wide_checksum = wide_checksum * 33UL + (uint16_t)wide_out;
        }

        probe_source_checksum[level_index] = source_checksum;
        probe_wide_checksum[level_index] = wide_checksum;
        probe_source_final_state[level_index] = source.ea1;
        probe_wide_final_state[level_index] = wide.ea1;
    }

    for (;;) {
        /* Inspect volatile globals through an AVR debugger/simulator. */
    }
}
