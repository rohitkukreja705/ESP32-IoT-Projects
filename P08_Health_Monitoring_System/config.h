#pragma once
// ===== P08 Health Monitoring System — configuration =====
#define WIFI_SSID     ""
#define WIFI_PASS     ""
#define DEVICE_PIN    "1234"
#define TS_WRITE_KEY  ""

// ----- pins -----
// MAX30102 + SSD1306 share I2C: SDA 21, SCL 22 (MAX30102 0x57, OLED 0x3C)
#define PIN_DS18B20   4      // DS18B20 data + 4.7k pull-up to 3.3 V
#define PIN_BUZZER    18
#define OLED_ADDR     0x3C

// ----- alert thresholds (set:hrlow= set:hrhigh= set:spo2low= set:templow/temphigh=) -----
#define DEF_HR_LOW     50
#define DEF_HR_HIGH    120
#define DEF_SPO2_LOW   92
#define DEF_TEMP_HIGH  38.0
#define FINGER_IR_MIN  50000  // IR level that means a finger is on the sensor
#define TS_INTERVAL_S  20
