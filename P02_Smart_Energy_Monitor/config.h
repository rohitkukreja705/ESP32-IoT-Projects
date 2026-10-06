#pragma once
// ===== P02 Smart Energy Monitor — configuration =====
#define WIFI_SSID     ""
#define WIFI_PASS     ""
#define DEVICE_PIN    "1234"
#define AIO_USERNAME  ""     // Adafruit IO username (or set:aiouser=...)
#define AIO_KEY       ""     // Adafruit IO key      (or set:aiokey=...)

// ----- pins -----
#define PIN_CURRENT   34     // ACS712-5A OUT through 10k/20k divider (ADC1)
#define PIN_VOLTAGE   35     // ZMPT101B OUT (module powered from 3.3 V)
#define PIN_RELAY     26     // relay module IN
#define RELAY_ACTIVE_LOW true
// LCD 16x2 with PCF8574 backpack: SDA = 21, SCL = 22, address 0x27 (try 0x3F)
#define LCD_ADDR      0x27

// ----- calibration defaults (fine-tune with calv:<V> and cali:<A>) -----
#define DEF_V_PER_MV  0.70f   // mains volts per ADC millivolt RMS (ZMPT pot dependent)
#define DEF_A_PER_MV  0.00811f// 1 / (185 mV/A * 2/3 divider) = 0.00811 A per mV
#define NOISE_AMPS    0.05f   // readings below this are treated as 0 A

// ----- behaviour -----
#define SAMPLE_MS        1000    // measure + BLE + LCD
#define CLOUD_MS         15000   // Adafruit IO publish (4 feeds -> 16 msg/min)
#define DEF_MAX_WATTS    1000    // overload trip (set:maxw=...)
#define DEF_TARIFF       7.0     // Rs per kWh   (set:tariff=...)
