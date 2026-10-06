#pragma once
// ===== P09 Smart Greenhouse / Irrigation — configuration =====
#define WIFI_SSID     ""
#define WIFI_PASS     ""
#define DEVICE_PIN    "1234"
#define SUPABASE_URL  ""
#define SUPABASE_KEY  ""

// ----- pins -----
#define PIN_SOIL      34     // capacitive soil moisture v1.2 AOUT (powered 3.3 V)
#define PIN_LDR       35     // LDR divider
#define PIN_DHT       4      // DHT11
#define PIN_PUMP      26     // relay CH1 -> 5 V mini pump
#define PIN_FAN       27     // relay CH2 -> 5 V/12 V fan
#define RELAY_ACTIVE_LOW true

// ----- defaults; the live values come from the Supabase "greenhouse_settings" row -----
#define DEF_SOIL_MIN   35    // % : start watering below
#define DEF_SOIL_MAX   60    // % : stop watering at
#define DEF_TEMP_MAX   32    // °C: fan on above
#define DEF_HUM_MAX    85    // %RH: fan on above
#define DEF_SOIL_DRY_MV 2800 // sensor in dry air   (set:soildry=)
#define DEF_SOIL_WET_MV 1200 // sensor in water     (set:soilwet=)
#define PUMP_BURST_S   15    // water in short bursts...
#define SOAK_S         120   // ...then wait for water to spread before re-checking

#define SAMPLE_MS      2000
#define UPLOAD_MS      60000
#define SETTINGS_MS    60000
