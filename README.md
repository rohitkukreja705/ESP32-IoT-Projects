# ESP32 IoT Projects — 10 complete BLE + Wi-Fi projects

Ten intermediate/advanced IoT projects built on a single **ESP32 DevKit V1** (≈ ₹350). Every project:

* uses **2–4 low-cost peripherals** that are easy to buy in India (Robu.in, Amazon.in, local markets);
* runs **BLE and Wi-Fi at the same time** — BLE for local control and setup, Wi-Fi for the cloud;
* uses only **free cloud tiers**: ThingSpeak, Adafruit IO or Supabase;
* comes with a **full project report** (`.docx` + `.pdf`): block diagram, circuit diagram, pin table, DFD level 0 and 1, flowchart, BLE protocol, cloud and app setup, test cases, troubleshooting and full source listing;
* is configured from a phone through one shared **Web Bluetooth console** — no Wi-Fi password or API key is ever written into the code.

| # | Project | Peripherals | Cloud | Report |
|---|---|---|---|---|
| P01 | [Smart Weather Station with Rain Forecast](P01_Smart_Weather_Station) | DHT11, BMP180, LDR, FC-37 rain sensor | ThingSpeak | [PDF](reports/P01_Smart_Weather_Station/P01_Smart_Weather_Station_Report.pdf) |
| P02 | [Smart Energy Monitor with Overload Protection](P02_Smart_Energy_Monitor) | ACS712-5A, ZMPT101B, 16x2 I2C LCD, relay | Adafruit IO | [PDF](reports/P02_Smart_Energy_Monitor/P02_Smart_Energy_Monitor_Report.pdf) |
| P03 | [Smart Home Automation with Away-Mode Security](P03_Smart_Home_Automation) | 4-ch relay, PIR, DHT11, buzzer | Adafruit IO | [PDF](reports/P03_Smart_Home_Automation/P03_Smart_Home_Automation_Report.pdf) |
| P04 | [Indoor Air Quality Monitor with Alarm](P04_Air_Quality_Monitor) | MQ-135, DHT11, SSD1306 OLED, buzzer | ThingSpeak | [PDF](reports/P04_Air_Quality_Monitor/P04_Air_Quality_Monitor_Report.pdf) |
| P05 | [Smart Parking System with Automatic Gate](P05_Smart_Parking_System) | 2× HC-SR04, IR sensor, SG90 servo | Supabase | [PDF](reports/P05_Smart_Parking_System/P05_Smart_Parking_System_Report.pdf) |
| P06 | [RFID Attendance System with Offline Queue](P06_RFID_Attendance_System) | MFRC522, SSD1306 OLED, buzzer, LEDs | Supabase | [PDF](reports/P06_RFID_Attendance_System/P06_RFID_Attendance_System_Report.pdf) |
| P07 | [Water Tank Level Monitor & Smart Pump Controller](P07_Water_Tank_Pump_Controller) | HC-SR04, YF-S201 flow, relay, buzzer | Adafruit IO | [PDF](reports/P07_Water_Tank_Pump_Controller/P07_Water_Tank_Pump_Controller_Report.pdf) |
| P08 | [Health Monitoring System (HR, SpO₂, Temp)](P08_Health_Monitoring_System) | MAX30102, DS18B20, SSD1306 OLED, buzzer | ThingSpeak | [PDF](reports/P08_Health_Monitoring_System/P08_Health_Monitoring_System_Report.pdf) |
| P09 | [Smart Greenhouse with Cloud-Configurable Irrigation](P09_Smart_Greenhouse) | Capacitive soil sensor, DHT11, LDR, 2-ch relay | Supabase | [PDF](reports/P09_Smart_Greenhouse/P09_Smart_Greenhouse_Report.pdf) |
| P10 | [Vehicle Tracking & Accident Alert](P10_Vehicle_Tracker_Accident_Alert) | NEO-6M GPS, MPU6050, buzzer, button | Supabase | [PDF](reports/P10_Vehicle_Tracker_Accident_Alert/P10_Vehicle_Tracker_Accident_Alert_Report.pdf) |

## Repository layout

```
common/            IoTCore.h (Wi-Fi + BLE + commands + settings) and Cloud.h (ThingSpeak / Adafruit IO / Supabase)
P01_… … P10_…/     one Arduino sketch per project (config.h, .ino, copies of the common headers, README)
docs/index.html    Web Bluetooth console (the BLE "app"), served by GitHub Pages
cloud/             supabase_schema.sql — tables, views and RLS for P05, P06, P09, P10
reports/           <project>/<project>_Report.docx + .pdf + images (circuit, DFDs, flowchart, block diagram)
tools/             generators for the diagrams and reports (Python + Graphviz + docx-js)
.github/workflows/ build.yml — compiles all 10 projects and publishes flashable firmware
```

## Quick start (no software installation needed)

1. **Firmware** — open the **Actions** tab → latest *Build firmware* run → download `firmware-<project>` → unzip.
   In Chrome on a computer open <https://espressif.github.io/esptool-js/>, *Connect*, flash `*.merged.bin` at address **0x0**.
   (Arduino IDE users: board *ESP32 Dev Module*, Partition Scheme *Minimal SPIFFS (1.9MB APP with OTA)*.)
2. **BLE app** — enable GitHub Pages (*Settings → Pages → Deploy from branch → main → /docs*), then open
   `https://rohitkukreja705.github.io/esp32-iot-projects/` in Chrome on Android (Bluefy on iPhone).
   Tap **Connect** → `IOT-Pxx-XXXX` → **Setup** → PIN `1234` → Wi-Fi → cloud keys.
3. **Cloud** — follow chapter 7.3 of the project's report:
   * ThingSpeak: create a channel, copy the Write API Key → `tskey`.
   * Adafruit IO: copy username + key → `aiouser`, `aiokey` (feeds auto-create).
   * Supabase: run `cloud/supabase_schema.sql` in the SQL editor, copy Project URL + publishable key → `sburl`, `sbkey`.

## BLE protocol (all projects)

Nordic UART Service `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` · write commands to RX `…0002` · notifications on TX `…0003`.
Works with the web console and with **nRF Connect** / **Serial Bluetooth Terminal**.

| Command | Purpose |
|---|---|
| `auth:1234` | unlock this connection (change with `set:pin=XXXX`) |
| `status` | Wi-Fi, IP, RSSI, heap, uptime, time |
| `wifi:SSID,PASSWORD` | save Wi-Fi and connect |
| `set:key=value` / `get:key` | settings: cloud keys, thresholds, calibration |
| `reboot` · `forget` | restart · erase settings |

The device replies with one JSON object per line (`{"type":"data",…}`, `"event"`, `"ack"`, `"err"`, `"status"`).

## Free-tier limits to keep in mind

| Service | Free limits (2026) | Used by |
|---|---|---|
| ThingSpeak | 3 M messages/year, 4 channels, 1 update / 15 s per channel | P01, P04, P08 |
| Adafruit IO | 30 data points/min, 10 feeds, 5 dashboards, 30 days history | P02, P03, P07 — one account cannot hold all three projects' feeds at once (17 feeds) |
| Supabase | 500 MB DB, 2 active projects, paused after 1 week idle | P05, P06, P09, P10 — one project holds all four |

## Safety

P02, P03 and P07 can switch 230 V mains loads. Build them in a closed enclosure with a fuse and get help from someone qualified;
test the low-voltage side first. P08 is an educational prototype, not a medical device.

## Rebuilding the reports

```bash
pip install matplotlib pillow     # plus graphviz, LibreOffice, poppler-utils, node + docx
python3 tools/build_reports.py    # or: python3 tools/build_reports.py P03 P07
python3 tools/make_readmes.py
```

Firmware verified to compile with ESP32 Arduino core 3.3.12, NimBLE-Arduino 2.5.1 and ArduinoJson 7.4.2.
