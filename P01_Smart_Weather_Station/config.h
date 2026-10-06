#pragma once
// ===== P01 Smart Weather Station — configuration =====
// Wi-Fi and cloud keys can stay empty here: send them from the BLE web app
// (Setup tab) and they are saved in the ESP32's flash.

#define WIFI_SSID     ""          // optional default
#define WIFI_PASS     ""
#define DEVICE_PIN    "1234"      // PIN the app must send before changing anything
#define TS_WRITE_KEY  ""          // ThingSpeak channel Write API Key (or set:tskey=...)

// ----- pins (ESP32 DevKit V1) -----
#define PIN_DHT       4           // DHT11 data
#define PIN_LDR       34          // LDR divider (ADC1)
#define PIN_RAIN_AO   35          // rain sensor analog out (ADC1)
#define PIN_RAIN_DO   27          // rain sensor digital out (LOW = wet)
#define PIN_LED       2           // on-board LED
// BMP180 uses I2C: SDA = GPIO21, SCL = GPIO22

// ----- timing -----
#define SAMPLE_MS          2000   // read sensors + BLE update
#define TS_INTERVAL_S      20     // ThingSpeak upload period (free tier minimum 15 s)
#define TREND_SAMPLE_MS    600000 // store pressure every 10 min for the 3-hour trend
