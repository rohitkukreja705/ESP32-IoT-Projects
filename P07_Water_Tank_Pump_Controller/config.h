#pragma once
// ===== P07 Water Tank Level & Pump Controller — configuration =====
#define WIFI_SSID     ""
#define WIFI_PASS     ""
#define DEVICE_PIN    "1234"
#define AIO_USERNAME  ""
#define AIO_KEY       ""

// ----- pins -----
#define PIN_TRIG      25     // HC-SR04 TRIG (sensor mounted in the tank lid, facing down)
#define PIN_ECHO      34     // ECHO via 1k/2k divider
#define PIN_FLOW      27     // YF-S201 signal via 10k/20k divider
#define PIN_RELAY     26     // pump relay IN
#define RELAY_ACTIVE_LOW true
#define PIN_BUZZER    18

// ----- tank geometry defaults (set:depth=, set:fullcm=) -----
#define DEF_DEPTH_CM   100   // sensor to tank bottom
#define DEF_FULL_CM    15    // sensor to the "100 %" water line
#define DEF_LOW_PCT    25    // auto: pump ON below
#define DEF_HIGH_PCT   90    // auto: pump OFF at/above
#define DEF_MAXRUN_MIN 30    // safety: max continuous run
#define DRYRUN_S       30    // pump ON but no flow for this long -> stop
#define FLOW_PULSES_PER_LITRE 450.0f   // YF-S201: F(Hz) = 7.5 x L/min

#define SAMPLE_MS      1000
#define CLOUD_MS       15000
