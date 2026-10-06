#pragma once
// ===== P06 RFID Attendance System — configuration =====
#define WIFI_SSID     ""
#define WIFI_PASS     ""
#define DEVICE_PIN    "1234"
#define SUPABASE_URL  ""
#define SUPABASE_KEY  ""

// ----- pins -----
// MFRC522 (3.3 V ONLY!): SDA/SS 5, SCK 18, MOSI 23, MISO 19, RST 4
#define PIN_RC522_SS  5
#define PIN_RC522_RST 4
#define PIN_BUZZER    25
#define PIN_LED_OK    26     // green LED + 220R
#define PIN_LED_ERR   27     // red LED + 220R
// SSD1306 OLED: SDA 21, SCL 22
#define OLED_ADDR     0x3C

// ----- behaviour -----
#define REPEAT_BLOCK_MS   10000   // ignore the same card for 10 s
#define MEMBER_SYNC_MS    600000  // refresh member list from Supabase every 10 min
#define MAX_MEMBERS       200
