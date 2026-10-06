#pragma once
// ===== P05 Smart Parking System — configuration =====
#define WIFI_SSID     ""
#define WIFI_PASS     ""
#define DEVICE_PIN    "1234"
#define SUPABASE_URL  ""     // https://<project-ref>.supabase.co  (or set:sburl=...)
#define SUPABASE_KEY  ""     // publishable / anon key             (or set:sbkey=...)

// ----- pins -----
#define PIN_TRIG1     25     // slot 1 HC-SR04 TRIG
#define PIN_ECHO1     34     // slot 1 ECHO via 1k/2k divider (5 V -> 3.3 V)
#define PIN_TRIG2     26     // slot 2 TRIG
#define PIN_ECHO2     35     // slot 2 ECHO via divider
#define PIN_IR        27     // IR obstacle sensor at the gate (LOW = car present)
#define PIN_SERVO     13     // SG90 signal (servo powered from 5 V)

#define NUM_SLOTS     2
#define GATE_CLOSED_DEG  0
#define GATE_OPEN_DEG    90

// ----- behaviour -----
#define DEF_OCCUPIED_CM  10   // set:occcm=...  (10 cm for a table-top model, ~60 cm real car)
#define GATE_HOLD_MS     4000 // keep gate open this long after the car has passed
#define SCAN_MS          300
