/*
 * Stand-alone arithmetic probe for the active PE1NNZ uSDX NEW_RX Hilbert.
 *
 * Build for ATmega328P, not for a 32-bit host:
 *   avr-g++ -mmcu=atmega328p -std=gnu++11 -Os -flto -o avr_hilbert_probe.elf avr_hilbert_probe.cpp
 *   avr-objdump -d -S avr_hilbert_probe.elf > avr_hilbert_probe.lst
 *
 * Inspect probe_source_result and probe_wide_result in a debugger/simulator.
 * This is a diagnostic only; it does not modify or replace firmware code.
 */

#include <stdint.h>
#include <limits.h>

#if !defined(__AVR__)
#error "This probe must be compiled for an AVR target"
#endif

#if INT_MAX != 32767
#error "Expected 16-bit AVR int"
#endif

volatile int16_t probe_v[14] = {
    0, 123, 1311, 2973, 3879, 3752, 2622,
    791, -1253, -2961, -3879, -3761, -2638, -813
};
volatile int16_t probe_q = 1231;

volatile int16_t probe_source_result;
volatile int32_t probe_wide_result;

#pragma GCC push_options
#pragma GCC optimize ("Ofast")

__attribute__((noinline))
int16_t source_style_hilbert(const volatile int16_t *v, int16_t q)
{
    int16_t qh;
    qh = ((v[0] - q) + (v[2] - v[12]) * 4) / 64
       + ((v[4] - v[10]) + (v[6] - v[8])) / 8
       + ((v[4] - v[10]) * 5 - (v[6] - v[8])) / 128
       + (v[6] - v[8]) / 2;
    return qh;
}

#pragma GCC pop_options

__attribute__((noinline))
int32_t wide_hilbert(const volatile int16_t *v, int16_t q)
{
    int32_t d0 = (int32_t)v[0] - q;
    int32_t d1 = (int32_t)v[2] - v[12];
    int32_t d2 = (int32_t)v[4] - v[10];
    int32_t d3 = (int32_t)v[6] - v[8];

    return (d0 + d1 * 4) / 64
         + (d2 + d3) / 8
         + (d2 * 5 - d3) / 128
         + d3 / 2;
}

int main(void)
{
    probe_source_result = source_style_hilbert(probe_v, probe_q);
    probe_wide_result = wide_hilbert(probe_v, probe_q);

    for (;;) {
        /* Inspect the two volatile result symbols in a debugger/simulator. */
    }
}
