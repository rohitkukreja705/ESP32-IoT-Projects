#pragma once
// ===== P04 Air Quality Monitor — configuration =====
#define WIFI_SSID     ""
#define WIFI_PASS     ""
#define DEVICE_PIN    "1234"
#define TS_WRITE_KEY  ""

// ----- pins -----
#define PIN_MQ135     34     // MQ-135 AO through 10k/20k divider (5 V -> 3.3 V)
#define PIN_DHT       4
#define PIN_BUZZER    18
// SSD1306 128x64 OLED: SDA 21, SCL 22, address 0x3C
#define OLED_ADDR     0x3C

#define DIVIDER_RATIO 1.5f   // module AO = ADC voltage x 1.5 (10k top, 20k bottom)
#define MQ_VCC_MV     5000.0f

// ----- behaviour -----
#define WARMUP_S        120   // heater warm-up after each power-on
#define DEF_ALARM_PPM   1500  // set:alarmppm=...
#define SAMPLE_MS       2000
#define TS_INTERVAL_S   20
