#pragma once
// ===== P10 Vehicle Tracking & Accident Alert — configuration =====
#define WIFI_SSID     ""     // phone hotspot in the vehicle
#define WIFI_PASS     ""
#define DEVICE_PIN    "1234"
#define SUPABASE_URL  ""
#define SUPABASE_KEY  ""

// ----- pins -----
#define PIN_GPS_RX    16     // ESP32 RX2  <- NEO-6M TX
#define PIN_GPS_TX    17     // ESP32 TX2  -> NEO-6M RX
#define PIN_BUZZER    18
#define PIN_BUTTON    13     // push button to GND (cancel alert / hold 3 s = SOS)
// MPU6050: SDA 21, SCL 22

// ----- behaviour (set:crashg= set:tilt= set:fence=lat,lng,metres) -----
#define DEF_CRASH_G      2.5   // impact threshold in g
#define DEF_TILT_DEG     60    // rollover threshold
#define TILT_HOLD_MS     3000
#define CANCEL_WINDOW_S  15    // driver can cancel a false alarm
#define MOVING_LOG_MS    30000 // log every 30 s while moving
#define PARKED_LOG_MS    300000// every 5 min while parked
#define MOVING_KMPH      3.0
