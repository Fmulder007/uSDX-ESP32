#pragma once

// ESP32-WROOM-32U hardware adapter for the PE1NNZ uSDX source.
// DSP functions remain in the original source; this file replaces AVR peripherals.

#include <Arduino.h>
#include <Wire.h>
#include <esp_sleep.h>
#include "esp_adc/adc_oneshot.h"
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#if !defined(ARDUINO_ARCH_ESP32)
#error "usdx_esp32_hal.h is only for ESP32 Arduino builds"
#endif

// ESP32 DevKit V4 / ESP32-WROOM-32U initial pin assignment.
// ADC inputs must use ADC1 pins so the radio remains independent of Wi-Fi.
static constexpr uint8_t USDX_PIN_RX_I       = 36; // ADC1_CH0 / VP
static constexpr uint8_t USDX_PIN_RX_Q       = 39; // ADC1_CH3 / VN
static constexpr uint8_t USDX_PIN_MIC        = 34; // ADC1_CH6
static constexpr uint8_t USDX_PIN_AUDIO_PWM  = 25; // audio reconstruction filter
static constexpr uint8_t USDX_PIN_PA_PWM     = 26; // PA bias / envelope
static constexpr uint8_t USDX_PIN_SI5351_SDA = 21;
static constexpr uint8_t USDX_PIN_SI5351_SCL = 22;

// AVR register compatibility: these registers are state placeholders only.
// ADC and timer operations are redirected to ESP32 drivers below.
static volatile uint8_t usdx_avr_admux = 0;
static volatile uint8_t usdx_avr_adcsra = 0;
static volatile uint8_t usdx_avr_adcsrb = 0;
static volatile uint8_t usdx_avr_didr0 = 0;
static volatile uint8_t usdx_avr_adif = 0;
static volatile uint8_t usdx_avr_mcusr = 0;
static volatile uint8_t usdx_avr_wdtcsr = 0;
static volatile uint8_t usdx_avr_prr = 0;
static volatile uint8_t usdx_avr_pcicr = 0;
static volatile uint8_t usdx_avr_pcmsk0 = 0;
static volatile uint8_t usdx_avr_pcmsk1 = 0;
static volatile uint8_t usdx_avr_pcmsk2 = 0;
static volatile uint8_t usdx_avr_timsk0 = 0;
static volatile uint8_t usdx_avr_timsk1 = 0;
static volatile uint8_t usdx_avr_timsk2 = 0;
static volatile uint8_t usdx_avr_assr = 0;
static volatile uint8_t usdx_avr_tccr2a = 0;
static volatile uint8_t usdx_avr_tccr2b = 0;
static volatile uint8_t usdx_avr_tcnt2 = 0;
static volatile uint8_t usdx_avr_ocr2a = 0;
static volatile uint8_t usdx_avr_tccr1b = 0;
static volatile uint8_t usdx_avr_icr1h = 0;
static volatile uint8_t usdx_avr_icr1l = 0;
static volatile uint8_t usdx_avr_ocr1ah = 0;
static volatile uint8_t usdx_avr_ocr1bh = 0;

#define ISR(vector) void vector()
#define TIMER2_COMPA_vect usdx_esp32_timer_compare

#define ADMUX  usdx_avr_admux
#define ADCSRA usdx_avr_adcsra
#define ADCSRB usdx_avr_adcsrb
#define DIDR0 usdx_avr_didr0
#define MCUSR  usdx_avr_mcusr
#define WDTCSR usdx_avr_wdtcsr
#define PRR    usdx_avr_prr
#define PCICR  usdx_avr_pcicr
#define PCMSK0 usdx_avr_pcmsk0
#define PCMSK1 usdx_avr_pcmsk1
#define PCMSK2 usdx_avr_pcmsk2
#define TIMSK0 usdx_avr_timsk0
#define TIMSK1 usdx_avr_timsk1
#define TIMSK2 usdx_avr_timsk2
#define ASSR   usdx_avr_assr
#define TCCR2A usdx_avr_tccr2a
#define TCCR2B usdx_avr_tccr2b
#define TCNT2  usdx_avr_tcnt2
#define OCR2A  usdx_avr_ocr2a
#define TCCR1B usdx_avr_tccr1b
#define ICR1H  usdx_avr_icr1h
#define ICR1L  usdx_avr_icr1l
#define OCR1AH usdx_avr_ocr1ah
#define OCR1BH usdx_avr_ocr1bh

#define ADPS0 0
#define ADPS1 1
#define ADPS2 2
#define ADIF  4
#define ADIE  3
#define ADSC  6
#define ADEN  7
#define ADATE 5
#define REFS0 6
#define REFS1 7
#define WDRF  3
#define AS2   3
#define WGM21 1
#define CS22  2
#define OCIE2A 1
#define COM1A1 7
#define COM1B1 5
#define WGM11  1
#define CS10   0
#define WGM13  4
#define WGM12  3
#define RXEN0  4
#define TXEN0  3
#define WDTO_4S   4000
#define WDTO_15MS 15

// Legacy AVR code expects a handful of port registers. The ESP32 pin API is
// used by the actual board mapping; these placeholders are not connected to GPIO.
static volatile uint8_t usdx_avr_portc = 0;
static volatile uint8_t usdx_avr_portd = 0;
static volatile uint8_t usdx_avr_ddrc = 0;
static volatile uint8_t usdx_avr_ddrd = 0;
static volatile uint8_t usdx_avr_pinc = 0;
static volatile uint8_t usdx_avr_ucsr0b = 0;
#define PORTC usdx_avr_portc
#define PORTD usdx_avr_portd
#define DDRC  usdx_avr_ddrc
#define DDRD  usdx_avr_ddrd
#define PINC  usdx_avr_pinc
#define UCSR0B usdx_avr_ucsr0b

inline uint8_t usdx_esp32_adc_pin(uint8_t logicalChannel) {
  switch (logicalChannel) {
    case 0: return USDX_PIN_RX_Q; // sdr_rx_common_q() selects admux[0]
    case 1: return USDX_PIN_RX_I; // sdr_rx_common_i() selects admux[1]
    case 2: return USDX_PIN_MIC;
    default: return USDX_PIN_MIC;
  }
}

static adc_oneshot_unit_handle_t usdx_adc1_handle = nullptr;

inline adc_channel_t usdx_esp32_adc_channel(uint8_t logicalChannel) {
  // ESP32-WROOM-32U / ESP32: GPIO36=ADC1_CH0, GPIO39=ADC1_CH3,
  // GPIO34=ADC1_CH6. Logical 0=Q, 1=I, 2=MIC matches uSDX selectors.
  switch (logicalChannel) {
    case 0: return ADC_CHANNEL_3;
    case 1: return ADC_CHANNEL_0;
    case 2: return ADC_CHANNEL_6;
    default: return ADC_CHANNEL_6;
  }
}

inline bool usdx_esp32_adc_begin() {
  adc_oneshot_unit_init_cfg_t unitConfig = {};
  unitConfig.unit_id = ADC_UNIT_1;
  unitConfig.ulp_mode = ADC_ULP_MODE_DISABLE;

  esp_err_t err = adc_oneshot_new_unit(&unitConfig, &usdx_adc1_handle);
  if (err != ESP_OK) {
    Serial.printf("ADC1 init failed: %s\\n", esp_err_to_name(err));
    usdx_adc1_handle = nullptr;
    return false;
  }

  adc_oneshot_chan_cfg_t channelConfig = {};
  channelConfig.atten = ADC_ATTEN_DB_12;
  channelConfig.bitwidth = ADC_BITWIDTH_DEFAULT;

  const adc_channel_t channels[] = {
    ADC_CHANNEL_0, ADC_CHANNEL_3, ADC_CHANNEL_6
  };
  for (adc_channel_t channel : channels) {
    err = adc_oneshot_config_channel(usdx_adc1_handle, channel, &channelConfig);
    if (err != ESP_OK) {
      Serial.printf("ADC1 channel config failed: %s\\n", esp_err_to_name(err));
      adc_oneshot_del_unit(usdx_adc1_handle);
      usdx_adc1_handle = nullptr;
      return false;
    }
  }
  return true;
}

inline void usdx_esp32_adc_prepare(uint8_t logicalChannel) {
  // All three ADC1 channels are configured once at startup. This selector
  // remains for compatibility with the original adc_start() call sequence.
  (void)logicalChannel;
}

inline uint16_t usdx_esp32_adc_read() {
  if (usdx_adc1_handle == nullptr) return 512; // safe midscale while ADC is unavailable

  int raw = 0;
  const adc_channel_t channel = usdx_esp32_adc_channel(ADMUX & 0x0f);
  if (adc_oneshot_read(usdx_adc1_handle, channel, &raw) != ESP_OK) {
    return 512;
  }

  // The uSDX arithmetic is written for the original 10-bit 0..1023 scale.
  if (raw <= 0) return 0;
  if (raw >= 4095) return 1023;
  return static_cast<uint16_t>((raw + 2) >> 2);
}
#define ADC usdx_esp32_adc_read()

// LEDC replaces ATmega Timer1 dual PWM outputs.
class UsdxEsp32PwmRegister {
 public:
  explicit UsdxEsp32PwmRegister(uint8_t pin) : pin_(pin), value_(0) {}
  UsdxEsp32PwmRegister& operator=(int value) {
    value_ = static_cast<uint8_t>(constrain(value, 0, 255));
    apply();
    return *this;
  }
  operator uint8_t() const { return value_; }
  void apply() const {
    if (attached_ && enabled_) ledcWrite(pin_, value_);
    else if (attached_) ledcWrite(pin_, 0);
  }
  void setAttached(bool value) { attached_ = value; apply(); }
  void setEnabled(bool value) { enabled_ = value; apply(); }
 private:
  uint8_t pin_;
  uint8_t value_;
  bool attached_ = false;
  bool enabled_ = true;
};

static UsdxEsp32PwmRegister usdx_ocr1al(USDX_PIN_AUDIO_PWM);
static UsdxEsp32PwmRegister usdx_ocr1bl(USDX_PIN_PA_PWM);
#define OCR1AL usdx_ocr1al
#define OCR1BL usdx_ocr1bl

inline void usdx_esp32_apply_pwm_enable(uint8_t control) {
  usdx_ocr1al.setEnabled((control & (1U << COM1A1)) != 0);
  usdx_ocr1bl.setEnabled((control & (1U << COM1B1)) != 0);
}

class UsdxEsp32Timer1Control {
 public:
  UsdxEsp32Timer1Control& operator=(uint8_t value) {
    value_ = value;
    usdx_esp32_apply_pwm_enable(value_);
    return *this;
  }
  UsdxEsp32Timer1Control& operator|=(uint8_t value) {
    value_ |= value;
    usdx_esp32_apply_pwm_enable(value_);
    return *this;
  }
  UsdxEsp32Timer1Control& operator&=(uint8_t value) {
    value_ &= value;
    usdx_esp32_apply_pwm_enable(value_);
    return *this;
  }
  operator uint8_t() const { return value_; }
 private:
  uint8_t value_ = 0;
};
static UsdxEsp32Timer1Control usdx_tccr1a;
#define TCCR1A usdx_tccr1a

inline bool usdx_esp32_pwm_begin(uint32_t frequency) {
  const bool audioOk = ledcAttach(USDX_PIN_AUDIO_PWM, frequency, 8);
  const bool paOk = ledcAttach(USDX_PIN_PA_PWM, frequency, 8);
  usdx_ocr1al.setAttached(audioOk);
  usdx_ocr1bl.setAttached(paOk);
  usdx_ocr1al = 0;
  usdx_ocr1bl = 0;
  if (!audioOk) Serial.printf("LEDC audio attach failed: GPIO%u at %lu Hz\\n", USDX_PIN_AUDIO_PWM, static_cast<unsigned long>(frequency));
  if (!paOk) Serial.printf("LEDC PA attach failed: GPIO%u at %lu Hz\\n", USDX_PIN_PA_PWM, static_cast<unsigned long>(frequency));
  return audioOk && paOk;
}
inline void usdx_esp32_pwm_stop() {
  usdx_ocr1al = 0;
  usdx_ocr1bl = 0;
}

// Timer2 replacement. A hardware timer only wakes a high-priority task;
// DSP and I2C code run in task context, not inside the ESP32 interrupt.
static constexpr uint32_t USDX_TIMER_RESOLUTION_HZ = 10000000;
static hw_timer_t* usdx_sample_timer = nullptr;
static TaskHandle_t usdx_sample_task_handle = nullptr;
static void (*usdx_sample_callback)() = nullptr;
static volatile bool usdx_sample_running = false;
static volatile bool usdx_sample_callback_busy = false;

static void usdx_sample_task(void*) {
  for (;;) {
    const uint32_t pending = ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
    if (!usdx_sample_running || usdx_sample_callback == nullptr) continue;
    for (uint32_t i = 0; i < pending; ++i) {
      // Publish busy before the final running check. timer_stop() can then
      // wait until an already-started callback has completely left DSP code.
      usdx_sample_callback_busy = true;
      if (!usdx_sample_running) {
        usdx_sample_callback_busy = false;
        break;
      }
      usdx_sample_callback();
      usdx_sample_callback_busy = false;
    }
  }
}

static void ARDUINO_ISR_ATTR usdx_sample_timer_isr() {
  BaseType_t higherPriorityTaskWoken = pdFALSE;
  if (usdx_sample_task_handle != nullptr && usdx_sample_running) {
    vTaskNotifyGiveFromISR(usdx_sample_task_handle, &higherPriorityTaskWoken);
  }
  if (higherPriorityTaskWoken == pdTRUE) portYIELD_FROM_ISR();
}

inline bool usdx_esp32_sample_timer_start(uint32_t sampleRate, void (*callback)()) {
  if (sampleRate == 0 || callback == nullptr) return false;
  usdx_sample_callback = callback;
  if (usdx_sample_task_handle == nullptr) {
    const BaseType_t created = xTaskCreatePinnedToCore(
      usdx_sample_task, "uSDX-DSP", 6144, nullptr,
      configMAX_PRIORITIES - 2, &usdx_sample_task_handle, 1);
    if (created != pdPASS) {
      usdx_sample_task_handle = nullptr;
      return false;
    }
  }
  if (usdx_sample_timer == nullptr) {
    usdx_sample_timer = timerBegin(USDX_TIMER_RESOLUTION_HZ);
    if (usdx_sample_timer == nullptr) return false;
    timerAttachInterrupt(usdx_sample_timer, &usdx_sample_timer_isr);
  } else {
    timerStop(usdx_sample_timer);
  }
  usdx_sample_running = true;
  timerWrite(usdx_sample_timer, 0);
  timerAlarm(usdx_sample_timer, USDX_TIMER_RESOLUTION_HZ / sampleRate, true, 0);
  return true;
}

inline void usdx_esp32_sample_timer_stop() {
  usdx_sample_running = false;
  if (usdx_sample_timer != nullptr) timerStop(usdx_sample_timer);
  if (usdx_sample_task_handle != nullptr) {
    xTaskNotifyGive(usdx_sample_task_handle);
    while (usdx_sample_callback_busy) {
      taskYIELD();
    }
  }
}

inline void usdx_esp32_begin() {
  Serial.begin(115200);
  delay(50);
  Serial.println();
  Serial.println("uSDX ESP32 port starting");
  if (!Wire.begin(USDX_PIN_SI5351_SDA, USDX_PIN_SI5351_SCL, 400000)) {
    Serial.println("ERROR: I2C bus initialization failed.");
  } else {
    Serial.println("I2C ready: SDA=21 SCL=22 400kHz");
  }
  if (!usdx_esp32_adc_begin()) {
    Serial.println("ERROR: ADC1 unavailable; RX/TX sample input will remain at midscale.");
  } else {
    Serial.println("ADC1 ready: GPIO36=I, GPIO39=Q, GPIO34=MIC");
  }
}

// AVR watchdog/sleep calls are not part of the ESP32 port.
inline void wdt_disable() {}
inline void wdt_reset() {}
inline void wdt_enable(uint32_t) {}
inline void set_sleep_mode(uint8_t) {}
inline void sleep_enable() {}
inline void sleep_disable() {}
inline void sleep_bod_disable() {}
inline void sleep_cpu() {}
#define SLEEP_MODE_PWR_DOWN 0
