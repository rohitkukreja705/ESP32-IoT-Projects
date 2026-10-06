#pragma once
// ===== P03 Smart Home Automation — configuration =====
#define WIFI_SSID     ""
#define WIFI_PASS     ""
#define DEVICE_PIN    "1234"
#define AIO_USERNAME  ""
#define AIO_KEY       ""

// ----- pins -----
#define PIN_RELAY1    26     // Light
#define PIN_RELAY2    27     // Fan
#define PIN_RELAY3    25     // TV / Socket
#define PIN_RELAY4    33     // Spare plug
#define RELAY_ACTIVE_LOW true   // most blue 4-channel modules switch ON with LOW
#define PIN_PIR       13     // HC-SR501 OUT
#define PIN_DHT       4      // DHT11 data
#define PIN_BUZZER    18     // active buzzer (+) via NPN or directly (< 20 mA)

// ----- automation defaults (change over BLE with set:key=value) -----
#define DEF_LIGHT_TIMEOUT_S  60   // lightto : light off after no motion
#define DEF_FAN_ON_C         30   // fanon   : fan on above this temperature
#define SENSOR_MS            2000
#define CLOUD_MS             30000
