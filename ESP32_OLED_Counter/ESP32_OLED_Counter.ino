#include <Wire.h>
#include <stdio.h>
#include <string.h>

// ESP32 DevKit V4 / ESP32-WROOM-32U
// OLED 128x64, SSD1306 I2C, default address 0x3C.
// SDA = GPIO 21, SCL = GPIO 22.

static const uint8_t OLED_ADDR = 0x3C;
static const int OLED_SDA = 21;
static const int OLED_SCL = 22;

static const int OLED_WIDTH = 128;
static const int OLED_HEIGHT = 64;
static const size_t OLED_BUFFER_SIZE = OLED_WIDTH * OLED_HEIGHT / 8;

static uint8_t framebuffer[OLED_BUFFER_SIZE];
static bool oledReady = false;
static uint32_t secondsCounter = 0;
static uint32_t lastTick = 0;

// 5x7 column font: bit 0 is the top pixel.
static bool getGlyph(char ch, uint8_t glyph[5]) {
  memset(glyph, 0, 5);

  switch (ch) {
    case '0': { const uint8_t g[5] = {0x3E, 0x51, 0x49, 0x45, 0x3E}; memcpy(glyph, g, 5); return true; }
    case '1': { const uint8_t g[5] = {0x00, 0x42, 0x7F, 0x40, 0x00}; memcpy(glyph, g, 5); return true; }
    case '2': { const uint8_t g[5] = {0x42, 0x61, 0x51, 0x49, 0x46}; memcpy(glyph, g, 5); return true; }
    case '3': { const uint8_t g[5] = {0x21, 0x41, 0x45, 0x4B, 0x31}; memcpy(glyph, g, 5); return true; }
    case '4': { const uint8_t g[5] = {0x18, 0x14, 0x12, 0x7F, 0x10}; memcpy(glyph, g, 5); return true; }
    case '5': { const uint8_t g[5] = {0x27, 0x45, 0x45, 0x45, 0x39}; memcpy(glyph, g, 5); return true; }
    case '6': { const uint8_t g[5] = {0x3C, 0x4A, 0x49, 0x49, 0x30}; memcpy(glyph, g, 5); return true; }
    case '7': { const uint8_t g[5] = {0x01, 0x71, 0x09, 0x05, 0x03}; memcpy(glyph, g, 5); return true; }
    case '8': { const uint8_t g[5] = {0x36, 0x49, 0x49, 0x49, 0x36}; memcpy(glyph, g, 5); return true; }
    case '9': { const uint8_t g[5] = {0x06, 0x49, 0x49, 0x29, 0x1E}; memcpy(glyph, g, 5); return true; }

    case 'C': { const uint8_t g[5] = {0x3E, 0x41, 0x41, 0x41, 0x22}; memcpy(glyph, g, 5); return true; }
    case 'D': { const uint8_t g[5] = {0x7F, 0x41, 0x41, 0x22, 0x1C}; memcpy(glyph, g, 5); return true; }
    case 'E': { const uint8_t g[5] = {0x7F, 0x49, 0x49, 0x49, 0x41}; memcpy(glyph, g, 5); return true; }
    case 'N': { const uint8_t g[5] = {0x7F, 0x02, 0x04, 0x08, 0x7F}; memcpy(glyph, g, 5); return true; }
    case 'O': { const uint8_t g[5] = {0x3E, 0x41, 0x41, 0x41, 0x3E}; memcpy(glyph, g, 5); return true; }
    case 'P': { const uint8_t g[5] = {0x7F, 0x09, 0x09, 0x09, 0x06}; memcpy(glyph, g, 5); return true; }
    case 'S': { const uint8_t g[5] = {0x46, 0x49, 0x49, 0x49, 0x31}; memcpy(glyph, g, 5); return true; }
    case 'T': { const uint8_t g[5] = {0x01, 0x01, 0x7F, 0x01, 0x01}; memcpy(glyph, g, 5); return true; }
    case ' ': return true;
    default: return false;
  }
}

static bool oledWriteCommands(const uint8_t *commands, size_t count) {
  Wire.beginTransmission(OLED_ADDR);
  Wire.write(0x00);  // Co = 0, D/C# = 0: command stream
  for (size_t i = 0; i < count; ++i) {
    Wire.write(commands[i]);
  }
  return Wire.endTransmission() == 0;
}

static bool oledSendFramebuffer() {
  // SSD1306 page-addressing mode: send one 128-byte page at a time.
  for (uint8_t page = 0; page < 8; ++page) {
    const uint8_t pageCommands[] = {
      static_cast<uint8_t>(0xB0 | page),  // Select page 0..7
      0x00,                               // Column low nibble
      0x10                                // Column high nibble
    };
    if (!oledWriteCommands(pageCommands, sizeof(pageCommands))) {
      return false;
    }

    const size_t pageOffset = static_cast<size_t>(page) * OLED_WIDTH;
    for (uint8_t column = 0; column < OLED_WIDTH; column += 16) {
      Wire.beginTransmission(OLED_ADDR);
      Wire.write(0x40);  // Data stream
      for (uint8_t i = 0; i < 16; ++i) {
        Wire.write(framebuffer[pageOffset + column + i]);
      }
      if (Wire.endTransmission() != 0) {
        return false;
      }
    }
  }
  return true;
}

static bool oledBegin() {
  Wire.begin(OLED_SDA, OLED_SCL);
  Wire.setClock(400000);

  // Check whether a device acknowledges the configured I2C address.
  Wire.beginTransmission(OLED_ADDR);
  if (Wire.endTransmission() != 0) {
    return false;
  }

  const uint8_t initCommands[] = {
    0xAE,       // Display OFF
    0xD5, 0x80, // Display clock divide
    0xA8, 0x3F, // Multiplex ratio: 1/64
    0xD3, 0x00, // Display offset
    0x40,       // Start line = 0
    0x8D, 0x14, // Enable charge pump
    0x20, 0x02, // Page addressing mode
    0xA1,       // Segment remap
    0xC8,       // COM scan direction
    0xDA, 0x12, // COM pins for 128x64
    0x81, 0x7F, // Contrast
    0xD9, 0xF1, // Pre-charge period
    0xDB, 0x40, // VCOMH deselect level
    0xA4,       // Display follows RAM
    0xA6,       // Normal (not inverted)
    0xAF        // Display ON
  };

  if (!oledWriteCommands(initCommands, sizeof(initCommands))) {
    return false;
  }

  memset(framebuffer, 0, sizeof(framebuffer));
  return oledSendFramebuffer();
}

static void clearScreen() {
  memset(framebuffer, 0, sizeof(framebuffer));
}

static void drawPixel(int x, int y) {
  if (x < 0 || x >= OLED_WIDTH || y < 0 || y >= OLED_HEIGHT) {
    return;
  }
  const size_t index = static_cast<size_t>(y >> 3) * OLED_WIDTH + x;
  framebuffer[index] |= static_cast<uint8_t>(1U << (y & 7));
}

static void drawCharacter(char ch, int x, int y, uint8_t scale) {
  uint8_t glyph[5];
  if (!getGlyph(ch, glyph)) {
    return;
  }

  for (int column = 0; column < 5; ++column) {
    for (int row = 0; row < 7; ++row) {
      if ((glyph[column] & (1U << row)) == 0) {
        continue;
      }
      for (uint8_t dx = 0; dx < scale; ++dx) {
        for (uint8_t dy = 0; dy < scale; ++dy) {
          drawPixel(x + column * scale + dx, y + row * scale + dy);
        }
      }
    }
  }
}

static int textWidth(const char *text, uint8_t scale) {
  const size_t length = strlen(text);
  if (length == 0) {
    return 0;
  }
  return static_cast<int>(length * 6 * scale - scale);
}

static void drawCenteredText(const char *text, int y, uint8_t scale) {
  int x = (OLED_WIDTH - textWidth(text, scale)) / 2;
  while (*text != '\0') {
    drawCharacter(*text++, x, y, scale);
    x += 6 * scale;
  }
}

static bool renderCounter() {
  char value[11];
  snprintf(value, sizeof(value), "%lu", static_cast<unsigned long>(secondsCounter));

  const size_t digits = strlen(value);
  uint8_t scale = 1;
  if (digits <= 2) {
    scale = 5;
  } else if (digits == 3) {
    scale = 4;
  } else if (digits == 4) {
    scale = 3;
  } else if (digits <= 6) {
    scale = 2;
  }

  clearScreen();
  drawCenteredText("ESP32 TEST", 1, 1);
  const int valueY = (OLED_HEIGHT - 7 * scale) / 2;
  drawCenteredText(value, valueY, scale);
  drawCenteredText("SECONDS", 56, 1);

  return oledSendFramebuffer();
}

void setup() {
  Serial.begin(115200);
  delay(200);

  Serial.println();
  Serial.println("ESP32 + OLED counter test");
  Serial.println("I2C: SDA=GPIO21, SCL=GPIO22, address=0x3C");

  oledReady = oledBegin();
  if (!oledReady) {
    Serial.println("OLED not detected or I2C communication failed.");
    Serial.println("Check wiring and OLED address (0x3C / 0x3D).");
  } else {
    Serial.println("OLED initialized.");
    renderCounter();
  }

  lastTick = millis();
}

void loop() {
  const uint32_t now = millis();
  bool changed = false;

  // Unsigned subtraction keeps the timing correct across millis() rollover.
  while (static_cast<uint32_t>(now - lastTick) >= 1000U) {
    lastTick += 1000U;
    ++secondsCounter;
    changed = true;
  }

  if (changed) {
    Serial.print("Seconds: ");
    Serial.println(static_cast<unsigned long>(secondsCounter));

    if (oledReady && !renderCounter()) {
      Serial.println("OLED update failed; check I2C connection.");
      oledReady = false;
    }
  }
}
