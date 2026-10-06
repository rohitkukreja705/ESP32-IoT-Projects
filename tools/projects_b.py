# -*- coding: utf-8 -*-
"""Project specifications P06-P10."""
from projects_a import COMMON_PARTS

P06 = dict(
    id="P06", slug="P06_RFID_Attendance_System",
    title="RFID Attendance System with Offline Queue",
    short="RFID Attendance System",
    cloud="Supabase", level="Advanced",
    peripherals=["MFRC522 RFID reader", "SSD1306 OLED", "Buzzer", "Green/red LEDs"],
    abstract=(
        "Paper registers and roll-calls waste class and work time and are easy to falsify. This project records "
        "attendance with 13.56 MHz RFID cards read by an MFRC522 module. Each tap is matched against a member list, "
        "toggled between IN and OUT, confirmed with an OLED message, a beep and an LED, and stored in a Supabase "
        "PostgreSQL table with a timestamp. The member list is cached in the ESP32's flash so the reader keeps working "
        "without internet; offline scans are queued in a LittleFS file and uploaded automatically when Wi-Fi returns. An "
        "administrator enrols new cards from a phone over BLE by typing a name and tapping the card. A SQL view produces "
        "the day's first-in and last-out times per member."),
    problem=(
        "Manual attendance is slow, error-prone and allows proxy attendance. Biometric systems are costly and raise "
        "hygiene and privacy concerns, while many low-cost RFID projects lose data when the network fails and need the "
        "card list hard-coded in firmware."),
    objectives=[
        "Identify members by RFID card UID and record IN/OUT attendance with timestamps.",
        "Store attendance in a cloud database that can be queried and exported.",
        "Keep working during internet outages without losing any scan.",
        "Enrol and delete cards from a phone without reprogramming.",
        "Give clear feedback at the reader (display, sound, LED).",
    ],
    scope=(
        "Classrooms, labs, small offices and clubs with up to ~200 members per reader. Multi-reader sites can share one "
        "Supabase project. Payroll and leave management are outside the scope."),
    existing=(
        "Common RFID attendance projects compare UIDs against an array in the source code and send each scan straight to "
        "a spreadsheet; if Wi-Fi is down the scan is lost, and adding a member means re-flashing the board."),
    proposed=[
        "Member list in the cloud, cached in NVS flash and refreshed every 10 minutes.",
        "Store-and-forward queue in LittleFS: zero data loss during outages; offline rows keep their real scan time.",
        "BLE administration: enrol (upsert) and delete cards from a phone.",
        "Automatic IN/OUT toggling and duplicate-tap protection (10 s).",
    ],
    components=COMMON_PARTS + [
        ("MFRC522 RFID reader kit (with 1 card + 1 key-tag)", 1, "13.56 MHz, ISO 14443A, SPI, 3.3 V", 110),
        ("Extra MIFARE Classic 1K cards", 5, "One per member", 75),
        ("0.96\" SSD1306 OLED 128x64 (I2C)", 1, "Address 0x3C", 170),
        ("Active buzzer 5 V", 1, "Feedback", 15),
        ("LEDs (green, red) + 220 Ω resistors", 2, "Status indication", 5),
    ],
    circuit=dict(
        title="P06 RFID Attendance System — Circuit Diagram",
        modules=[
            dict(name="MFRC522", sub="RFID reader, SPI (3.3 V ONLY)",
                 pins=[("3.3V", "3V3"), ("SDA/SS", "G5"), ("SCK", "G18"), ("MOSI", "G23"), ("MISO", "G19"), ("RST", "G4"), ("GND", "GND")]),
            dict(name="SSD1306 OLED", sub="128x64, I2C 0x3C",
                 pins=[("VCC", "3V3"), ("SDA", "G21"), ("SCL", "G22"), ("GND", "GND")]),
            dict(name="Buzzer + LEDs", sub="Feedback",
                 pins=[("BZ +", "G25"), ("LED G", "G26", "Each LED: GPIO -> 220 Ω -> LED anode, cathode -> GND"), ("LED R", "G27"), ("GND", "GND")]),
        ],
        notes=["Never connect the MFRC522 to 5 V; it is a 3.3 V device.",
               "The MFRC522 IRQ pin is not used."],
    ),
    principles=[
        ("RFID (ISO 14443A)", "The MFRC522 drives a 13.56 MHz field through its PCB antenna. A passive card harvests "
                              "energy from this field and answers by load modulation. During anti-collision the card "
                              "sends its 4- or 7-byte UID, which the firmware uses as the member ID."),
        ("SPI interface", "The ESP32 talks to the MFRC522 over SPI (SCK 18, MOSI 23, MISO 19, SS 5) at up to 10 MHz; RST "
                          "on GPIO4 resets the chip at start-up. The firmware checks the version register (0x91/0x92) to "
                          "detect wiring faults."),
        ("LittleFS queue", "LittleFS is a power-fail-safe flash file system. Each offline scan is appended as one JSON "
                           "line to /queue.jsonl; after a successful upload the file is rewritten without that line."),
        ("Supabase", "Two tables — members(uid, name) and attendance(uid, name, direction, scanned_at, offline) — plus an "
                     "attendance_today view. The device inserts rows through the REST API using the publishable key."),
    ],
    working=[
        "On boot the firmware mounts LittleFS, counts queued rows, initialises the reader and OLED and, once Wi-Fi is up, "
        "downloads the member list (uid, name) from Supabase into the 'cards' NVS namespace.",
        "When a card is presented the UID is read as upper-case hex. A repeated tap within 10 s is ignored. If the UID "
        "is unknown the red LED and a long beep signal 'ACCESS DENIED' and an 'unknown_card' event is sent over BLE. "
        "Otherwise the IN/OUT flag for that UID in NVS is toggled, the OLED greets the member and a row is built with "
        "uid, name, direction, device and (if NTP time is known) scanned_at.",
        "If Wi-Fi is up and the queue is empty the row is inserted directly; otherwise it is appended to the queue with "
        "offline=true. Every 15 s the queue is flushed row by row; the first failure stops the flush so order is kept. "
        "In enrolment mode (enroll:<name>) the next card is stored locally and upserted into members with "
        "'Prefer: resolution=merge-duplicates'.",
    ],
    ble_data=[("today", "Scans since boot", "count"), ("queued", "Rows waiting to upload", "count"),
              ("enrol", "Enrol mode active", "bool"), ("wifi", "Wi-Fi connected", "bool"),
              ("type=scan", "Per tap: uid, name, dir, cloud", "line")],
    ble_cmds=[("enroll:<name>", "Yes", "Next card tapped (within 30 s) is enrolled as <name>"),
              ("delete:<UID>", "Yes", "Remove a card locally and from the cloud"),
              ("cancel", "Yes", "Leave enrol mode"), ("syncnow", "Yes", "Refresh members and flush the queue now")],
    settings=[("sburl / sbkey", "—", "Supabase project URL and publishable key")],
    cloud_items=[("members", "uid (PK, upper-case hex), name, role"),
                 ("attendance", "uid, name, direction IN/OUT, device, offline, scanned_at"),
                 ("attendance_today (view)", "first_in, last_out and scans per member for today (IST)")],
    dfd=dict(
        sensors="RFID card + MFRC522", raw="card UID",
        actuators="OLED, buzzer, LEDs", act="greeting / denied feedback",
        store3=("D3", "Offline queue (LittleFS) + member cache (NVS)", "queued scans, members", "rows to flush, names"),
        cloud_up="attendance rows, enrolments", cloud_down="member list",
        derived="member name, IN/OUT direction",
    ),
    flow=dict(
        nodes=[("s", "start", "Power on"), ("i", "process", "Mount LittleFS, init RC522, OLED, BLE, Wi-Fi"),
               ("l", "process", "Handle BLE admin commands"),
               ("c", "decision", "Card present?"), ("u", "io", "Read UID"),
               ("dup", "decision", "Same card < 10 s?"), ("en", "decision", "Enrol mode?"),
               ("enr", "process", "Save name, upsert members"),
               ("k", "decision", "UID known?"), ("deny", "process", "Red LED, long beep, 'unknown_card'"),
               ("t", "process", "Toggle IN/OUT, greet on OLED, beep"),
               ("w", "decision", "Wi-Fi up and queue empty?"), ("ins", "io", "INSERT attendance row"),
               ("q", "process", "Append row to queue file"),
               ("p", "process", "Every 15 s: flush queue; every 10 min: sync members")],
        edges=[("s", "i"), ("i", "l"), ("l", "c"), ("c", "u", "yes"), ("c", "p", "no"), ("u", "dup"),
               ("dup", "p", "yes"), ("dup", "en", "no"), ("en", "enr", "yes"), ("en", "k", "no"), ("enr", "p"),
               ("k", "deny", "no"), ("k", "t", "yes"), ("deny", "p"), ("t", "w"), ("w", "ins", "yes"),
               ("w", "q", "no"), ("ins", "p"), ("q", "p"), ("p", "l", "", ", constraint=false")],
    ),
    tests=[
        ("Reader detection", "Open Serial Monitor at boot", "'[RC522] version 0x92 OK' (or 0x91)"),
        ("Enrolment", "Unlock, send enroll:Rohit, tap a card", "OLED 'ENROLLED'; row appears in members table"),
        ("IN / OUT", "Tap the card, wait 11 s, tap again", "Rows with direction IN then OUT in attendance"),
        ("Unknown card", "Tap a card that is not enrolled", "'ACCESS DENIED', red LED, long beep"),
        ("Duplicate tap", "Tap the same card twice within 5 s", "Only one row recorded"),
        ("Offline queue", "Disconnect Wi-Fi, tap 3 times, reconnect", "OLED shows Q:3, then rows uploaded with offline=true"),
        ("Daily report", "Run 'select * from attendance_today' in SQL editor", "One line per member with first IN and last OUT"),
    ],
    advantages=["No data loss during network outages (store-and-forward).",
                "Cards managed from a phone; no reprogramming.",
                "Standard SQL database: easy reports, CSV export, integration.",
                "Fast (< 1 s per tap) and contactless."],
    limitations=["Cards can be lent to others (proxy) — RFID identifies the card, not the person.",
                 "MIFARE Classic UIDs can be cloned with special tools; use for low-security attendance only.",
                 "Scans made before NTP sync get the upload time instead of the real time.",
                 "The publishable key with permissive RLS is suitable for trusted environments only."],
    future=["Add a fingerprint sensor (R307) or face check for two-factor attendance.",
            "Web dashboard with Supabase Auth for teachers/managers and CSV export.",
            "Real-time push notifications to parents/managers using Supabase Realtime.",
            "Battery backup and RTC module (DS3231) for accurate offline timestamps."],
    safety=["Store only the minimum personal data (name, card UID) and inform members how it is used.",
            "Restrict Supabase table access with RLS and rotate the key if a device is lost."],
    conclusion=(
        "The RFID Attendance System replaces paper registers with a fast, contactless and reliable system. Caching the "
        "member list and queuing scans in flash makes it robust against internet outages, while Supabase provides a real "
        "relational database for reports. Phone-based enrolment over BLE keeps administration simple."),
    refs=["NXP Semiconductors, MFRC522 Standard performance MIFARE and NTAG frontend datasheet.",
          "M. Balboa, Arduino RFID library for MFRC522, GitHub (miguelbalboa/rfid).",
          "ISO/IEC 14443-3: Identification cards — Proximity cards — Initialization and anticollision.",
          "Supabase documentation: Upsert with PostgREST (Prefer: resolution=merge-duplicates)."],
)

P07 = dict(
    id="P07", slug="P07_Water_Tank_Pump_Controller",
    title="Water Tank Level Monitor and Smart Pump Controller",
    short="Water Tank & Pump Controller",
    cloud="Adafruit IO", level="Advanced",
    peripherals=["HC-SR04 ultrasonic sensor", "YF-S201 flow sensor", "Relay module", "Active buzzer"],
    abstract=(
        "Overhead water tanks in Indian homes either overflow because the motor is left on or run dry because nobody "
        "notices. This project measures the water level with an ultrasonic sensor in the tank lid and the actual water "
        "flow with a YF-S201 Hall-effect flow sensor, and switches the pump through a relay. In AUTO mode the pump starts "
        "below a low threshold and stops at a high threshold. Three protections stop the pump: dry-run (pump on but no "
        "flow for 30 s), overflow (level above 98 %) and maximum run time. Level, flow and pump state are published to "
        "Adafruit IO, where the dashboard can also switch the pump and change the mode. A phone connected over BLE shows "
        "a live tank gauge and allows calibration of the tank dimensions."),
    problem=(
        "Manual pump control wastes water and electricity through overflow and damages pumps through dry running when "
        "the supply line is empty. Float switches are mechanical, wear out and give no remote information."),
    objectives=[
        "Measure tank level without contact and show it as a percentage.",
        "Control the pump automatically with hysteresis between low and high levels.",
        "Detect dry running using a flow sensor and stop the pump.",
        "Prevent overflow and limit continuous run time.",
        "Monitor and control remotely (Adafruit IO) and locally (BLE).",
    ],
    scope=(
        "Domestic overhead tanks up to about 3 m deep with single-phase pumps up to 1 HP switched through a suitable "
        "contactor. The demo uses a 5 V mini pump and a bucket."),
    existing=(
        "Typical water-level controllers use probes or float switches and only switch the pump on level; they do not "
        "detect dry running and offer no remote monitoring. Many ultrasonic projects use single readings that jump "
        "because of ripples."),
    proposed=[
        "Median-of-5 filtering of ultrasonic readings.",
        "Flow-based dry-run protection and maximum run-time protection.",
        "Fault latch: the pump cannot restart until the fault is cleared by the user.",
        "Pump never switches on from a stale cloud value after a reboot.",
    ],
    components=COMMON_PARTS + [
        ("HC-SR04 ultrasonic sensor (or JSN-SR04T waterproof)", 1, "2-400 cm", 60),
        ("YF-S201 water flow sensor", 1, "1-30 L/min, ½-inch, Hall-effect", 180),
        ("1-channel 5 V relay module (10 A)", 1, "Pump switching", 50),
        ("Active buzzer 5 V", 1, "Fault alarm", 15),
        ("5 V mini submersible pump + 1 m tube (demo)", 1, "Demo load", 90),
        ("Resistors 1 kΩ/2 kΩ and 10 kΩ/20 kΩ", 1, "Level dividers", 5),
    ],
    circuit=dict(
        title="P07 Water Tank & Pump Controller — Circuit Diagram",
        modules=[
            dict(name="HC-SR04", sub="In tank lid, facing down",
                 pins=[("VCC", "5V"), ("TRIG", "G25"), ("ECHO", "G34", "ECHO -> 1 kΩ -> GPIO34; GPIO34 -> 2 kΩ -> GND"), ("GND", "GND")]),
            dict(name="YF-S201", sub="Flow sensor in pump outlet",
                 pins=[("Red 5V", "5V"), ("Yellow SIG", "G27", "SIG -> 10 kΩ -> GPIO27; GPIO27 -> 20 kΩ -> GND"), ("Black GND", "GND")]),
            dict(name="Relay (1-ch)", sub="Pump, active LOW",
                 pins=[("VCC", "5V"), ("IN", "G26"), ("GND", "GND")],
                 outer=["COM/NO switch the pump (via contactor for big pumps)"]),
            dict(name="Active buzzer", sub="Fault alarm",
                 pins=[("+", "G18"), ("-", "GND")]),
        ],
        notes=["For a real tank use the waterproof JSN-SR04T (same TRIG/ECHO wiring).",
               "Motors above ~0.5 HP must be switched through a contactor driven by this relay, never directly."],
    ),
    principles=[
        ("Ultrasonic level", "The sensor measures the distance d from the lid to the water surface. With D = distance to "
                             "the tank bottom and F = distance to the full line, level % = (D − d) / (D − F) × 100."),
        ("YF-S201", "Water turns a small rotor with a magnet; a Hall-effect sensor gives one pulse per magnet pass. The "
                    "datasheet relation is f (Hz) = 7.5 × Q (L/min), i.e. about 450 pulses per litre. Pulses are counted "
                    "in an interrupt service routine."),
        ("Relay", "Opto-isolated relay switches the pump (or the coil of a contactor for large pumps)."),
        ("Adafruit IO", "MQTT broker and dashboards; feeds hold time-series values and blocks (gauge, toggle) display "
                        "or change them."),
    ],
    working=[
        "Every second the firmware takes five ultrasonic readings 15 ms apart and uses the median, converts it to a "
        "level percentage using the stored tank geometry, and computes flow rate from the pulses counted in the last "
        "second. Total litres pumped are accumulated.",
        "AUTO mode switches the pump ON when level < 'low' (25 %) and OFF when level ≥ 'high' (90 %). While the pump is "
        "ON, flow must exceed 0.5 L/min within 30 s, otherwise a 'Dry run' fault is raised. Level ≥ 98 % raises an "
        "'Overflow risk' fault and run time > 'maxrun' minutes raises 'Max run time reached'. A fault turns the pump off, "
        "sounds the buzzer and blocks restarts until 'clear' is sent.",
        "Level and flow are published every 15 s; the pump feed is updated on every change. The device subscribes to "
        "p07-pump and p07-mode but does not request their last value after reconnecting, so a stale ON can never start "
        "the pump unexpectedly.",
    ],
    ble_data=[("lvl", "Tank level", "%"), ("cm", "Measured distance", "cm"), ("flow", "Flow rate", "L/min"),
              ("lit", "Litres pumped", "L"), ("pump", "Pump ON", "bool"), ("mode", "AUTO / MANUAL", "—"),
              ("fault", "Active fault text", "—"), ("cloud", "MQTT connected", "bool")],
    ble_cmds=[("pump:on / pump:off", "Yes", "Manual pump control"), ("mode:auto / mode:manual", "Yes", "Select mode"),
              ("clear", "Yes", "Clear fault and silence buzzer"), ("resetvol", "Yes", "Reset litres counter")],
    settings=[("aiouser / aiokey", "—", "Adafruit IO credentials"), ("depth", "100", "Sensor to tank bottom (cm)"),
              ("fullcm", "15", "Sensor to full line (cm)"), ("low / high", "25 / 90", "AUTO thresholds (%)"),
              ("maxrun", "30", "Maximum continuous run (min)")],
    cloud_items=[("p07-level", "Gauge 0-100 %"), ("p07-flow", "Line chart, L/min"),
                 ("p07-pump", "Toggle block ON/OFF (remote pump switch)"), ("p07-mode", "Toggle block AUTO/MANUAL")],
    dfd=dict(
        sensors="HC-SR04 + YF-S201", raw="echo time, flow pulses",
        actuators="Pump relay + buzzer", act="pump ON/OFF, fault alarm",
        store3=("D3", "Tank geometry & thresholds (NVS)", "calibration values", "depth, full, low, high"),
        cloud_up="level, flow, pump state", cloud_down="pump & mode commands",
        derived="level %, L/min, faults",
    ),
    flow=dict(
        nodes=[("s", "start", "Power on"), ("i", "process", "Pump OFF; load settings; init BLE, Wi-Fi, MQTT, flow ISR"),
               ("l", "process", "Handle commands; compute flow every 1 s"),
               ("m", "io", "Every 1 s: median of 5 pings -> level %"),
               ("of", "decision", "Level ≥ 98 % & pump ON?"), ("dr", "decision", "Pump ON & no flow 30 s?"),
               ("mr", "decision", "Run time > max?"), ("f", "process", "Fault: pump OFF, buzzer, event"),
               ("am", "decision", "AUTO & no fault?"), ("lo", "decision", "Level < low?"), ("on", "process", "Pump ON"),
               ("hi", "decision", "Level ≥ high?"), ("off", "process", "Pump OFF"),
               ("p", "io", "BLE frame; publish level/flow every 15 s")],
        edges=[("s", "i"), ("i", "l"), ("l", "m"), ("m", "of"), ("of", "f", "yes"), ("of", "dr", "no"),
               ("dr", "f", "yes"), ("dr", "mr", "no"), ("mr", "f", "yes"), ("mr", "am", "no"), ("f", "p"),
               ("am", "lo", "yes"), ("am", "p", "no"), ("lo", "on", "yes"), ("lo", "hi", "no"), ("on", "p"),
               ("hi", "off", "yes"), ("hi", "p", "no"), ("off", "p"), ("p", "l", "", ", constraint=false")],
    ),
    tests=[
        ("Level calibration", "Set depth to bucket depth, fullcm to sensor-to-brim minus 2 cm", "Empty ≈ 0 %, full ≈ 100 %"),
        ("Auto fill", "Lower the water below 25 %", "Pump starts; stops at 90 %"),
        ("Dry run", "Lift the pump out of the water while it runs", "Pump stops after ~30 s; 'Dry run' fault + buzzer"),
        ("Fault latch", "Try pump:on while a fault is active", "'pump_blocked' event; pump stays OFF until 'clear'"),
        ("Remote control", "Switch p07-mode to MANUAL and toggle p07-pump", "Pump follows dashboard"),
        ("Reboot safety", "Leave p07-pump ON in the cloud, reboot the ESP32", "Pump stays OFF after boot"),
        ("Flow accuracy", "Pump into a 1 L measuring jug", "Litres counter ≈ 1.0 L (±10 %)"),
    ],
    advantages=["Prevents overflow and protects the pump from dry running.",
                "Non-contact level measurement — no corroding probes in the water.",
                "Remote visibility of tank level and water usage.",
                "Safe defaults: fault latch and no auto-start from stale cloud data."],
    limitations=["HC-SR04 is not waterproof; condensation inside a tank shortens its life (use JSN-SR04T).",
                 "YF-S201 accuracy is about ±10 % and needs a minimum flow of ~1 L/min.",
                 "Large pumps need a contactor and motor-protection relay.",
                 "Adafruit IO free tier keeps 30 days of history."],
    future=["Add a sump-tank level sensor so the pump never starts when the sump is empty.",
            "Daily water-usage report and leak detection (flow with pump off).",
            "Solar-powered remote tank node using ESP-NOW or LoRa.",
            "Voltage monitoring to protect the motor from low-voltage starts."],
    safety=["The pump is a mains appliance: use a contactor, fuse and proper enclosure; follow electrical codes.",
            "Seal the electronics against humidity; mount the controller outside the tank."],
    conclusion=(
        "The controller automates tank filling while protecting both the tank and the pump, using a flow sensor to detect "
        "dry running that level-only controllers miss. Remote monitoring through Adafruit IO and local control over BLE "
        "make it convenient, and conservative defaults make it safe to leave unattended."),
    refs=["Seeed/YF-S201 Water Flow Sensor datasheet (F = 7.5·Q).",
          "ElecFreaks, HC-SR04 user guide; JSN-SR04T waterproof module datasheet.",
          "Adafruit IO MQTT API documentation.",
          "Bureau of Indian Standards, IS 732: Code of practice for electrical wiring installations (safety reference)."],
)

P08 = dict(
    id="P08", slug="P08_Health_Monitoring_System",
    title="IoT Health Monitoring System (Heart Rate, SpO₂, Body Temperature)",
    short="Health Monitoring System",
    cloud="ThingSpeak", level="Advanced",
    peripherals=["MAX30102 pulse oximeter", "DS18B20 temperature probe", "SSD1306 OLED", "Active buzzer"],
    abstract=(
        "This project measures three basic vital signs — heart rate, blood-oxygen saturation (SpO₂) and body temperature "
        "— and makes them available locally and remotely. A MAX30102 optical sensor captures red and infrared "
        "photoplethysmography (PPG) signals from a fingertip; the ESP32 samples them without blocking at 25 Hz into a "
        "sliding four-second window and runs Maxim's reference algorithm every second to estimate heart rate and SpO₂. A "
        "waterproof DS18B20 probe measures temperature. Readings appear on an OLED, stream to a phone over BLE and are "
        "uploaded to ThingSpeak every 20 seconds while a finger is on the sensor. Configurable limits trigger a buzzer and "
        "a phone alert. The system is an educational prototype and not a medical device."),
    problem=(
        "Elderly people, patients recovering at home and people in rural areas often need periodic monitoring of pulse, "
        "oxygen and temperature, and caregivers may be far away. Clinical monitors are expensive, and stand-alone finger "
        "oximeters do not share or log their readings."),
    objectives=[
        "Measure heart rate and SpO₂ from PPG signals with a MAX30102.",
        "Measure body temperature with a DS18B20 probe.",
        "Detect finger presence and produce stable, averaged readings.",
        "Alert locally and on a phone when values leave configurable limits.",
        "Log readings to ThingSpeak so caregivers can view trends remotely.",
    ],
    scope=(
        "Spot checks and short monitoring sessions at rest, for education and awareness. Continuous wearable use, motion "
        "tolerance and clinical accuracy are out of scope."),
    existing=(
        "Many MAX30102 projects use blocking loops that freeze the microcontroller for four seconds per reading, which "
        "breaks Wi-Fi/BLE responsiveness; others compute heart rate only. Results are rarely logged with finger detection, "
        "so empty readings pollute the data."),
    proposed=[
        "Non-blocking FIFO reading with a sliding window: a new estimate every second.",
        "Finger detection by IR level; uploads only valid readings.",
        "Four-sample moving average of heart rate.",
        "Configurable alert limits stored in flash and changed from the phone.",
    ],
    components=COMMON_PARTS + [
        ("MAX30102 pulse oximeter & heart-rate module", 1, "Red + IR LEDs, 18-bit ADC, I2C 0x57", 150),
        ("DS18B20 waterproof temperature probe", 1, "−55 to +125 °C, ±0.5 °C, 1-Wire", 90),
        ("4.7 kΩ resistor", 1, "1-Wire pull-up", 2),
        ("0.96\" SSD1306 OLED 128x64 (I2C)", 1, "Address 0x3C", 170),
        ("Active buzzer 5 V", 1, "Alert", 15),
    ],
    circuit=dict(
        title="P08 Health Monitoring System — Circuit Diagram",
        modules=[
            dict(name="MAX30102", sub="PPG sensor, I2C 0x57",
                 pins=[("VIN", "3V3"), ("SDA", "G21"), ("SCL", "G22"), ("GND", "GND")]),
            dict(name="SSD1306 OLED", sub="Shares the I2C bus, 0x3C",
                 pins=[("VCC", "3V3"), ("SDA", "G21"), ("SCL", "G22"), ("GND", "GND")]),
            dict(name="DS18B20 probe", sub="Red / Yellow / Black",
                 pins=[("Red VDD", "3V3"), ("Yellow DQ", "G4", "4.7 kΩ pull-up between DQ (GPIO4) and 3.3 V"), ("Black GND", "GND")]),
            dict(name="Active buzzer", sub="Alert",
                 pins=[("+", "G18"), ("-", "GND")]),
        ],
        notes=["MAX30102 and OLED share SDA/SCL (different addresses, 0x57 and 0x3C).",
               "Some purple MAX30102 boards need the 1.8 V/3.3 V solder jumper set to 3.3 V for I2C pull-ups."],
    ),
    principles=[
        ("Photoplethysmography", "Arterial blood volume in the fingertip changes with every heartbeat, which changes how "
                                 "much light is absorbed. The MAX30102 shines red (660 nm) and infrared (880 nm) light and "
                                 "measures the reflected light. The periodic (AC) part gives the pulse; the time between "
                                 "peaks gives heart rate."),
        ("SpO₂ ratio", "Oxygenated haemoglobin absorbs more IR and less red light than deoxygenated haemoglobin. The "
                       "ratio R = (AC_red/DC_red)/(AC_IR/DC_IR) is mapped to SpO₂ with an empirical curve; Maxim's "
                       "algorithm uses SpO₂ ≈ −45.06·R² + 30.354·R + 94.845 via a lookup table."),
        ("DS18B20", "A digital thermometer on Dallas 1-Wire: one data line with a 4.7 kΩ pull-up. A 12-bit conversion "
                    "takes 750 ms; the firmware requests a conversion and reads the result on the next pass instead of "
                    "waiting."),
        ("OLED & buzzer", "The OLED shows bpm, SpO₂, temperature and a blinking heartbeat dot; the buzzer chirps while an "
                          "alert is active."),
    ],
    working=[
        "The MAX30102 is configured for 100 samples/s with 4-sample averaging (25 effective samples/s), 411 µs pulse width "
        "and an 18-bit range. In every loop pass the firmware drains the sensor FIFO. IR above 50,000 counts means a "
        "finger is present; removing the finger resets the buffers.",
        "Samples enter a 100-sample (4 s) window. Once full, every 25 new samples (1 s) the window is passed to "
        "maxim_heart_rate_and_oxygen_saturation(). Valid heart rates (30-220 bpm) are averaged over the last four "
        "estimates; valid SpO₂ values (70-100 %) are shown directly. The DS18B20 is read once per second without "
        "blocking.",
        "Alerts compare the values with hrlow/hrhigh, spo2low and temphigh. An alert sends a 'vital_alert' event and "
        "chirps the buzzer. Every 20 s, if a finger is present and heart rate is valid, HR, SpO₂, temperature and the "
        "alert flag are uploaded to ThingSpeak.",
    ],
    ble_data=[("hr", "Heart rate", "bpm"), ("spo2", "Oxygen saturation", "%"), ("temp", "Body temperature", "°C"),
              ("finger", "Finger detected", "bool"), ("alert", "Alert active", "bool"), ("msg", "Alert details", "—")],
    ble_cmds=[("status", "No", "Device status (the project has no actuator commands)")],
    settings=[("tskey", "—", "ThingSpeak Write API Key"), ("hrlow / hrhigh", "50 / 120", "Heart-rate limits (bpm)"),
              ("spo2low", "92", "SpO₂ lower limit (%)"), ("temphigh", "38", "Temperature upper limit (°C)")],
    cloud_items=[("Field 1", "Heart rate (bpm)"), ("Field 2", "SpO₂ (%)"), ("Field 3", "Temperature (°C)"),
                 ("Field 4", "Alert flag (0/1)"), ("Status", "Alert text or 'normal'")],
    dfd=dict(
        sensors="Patient (fingertip, skin)", raw="PPG red/IR, temperature",
        actuators="OLED + buzzer", act="vitals display, alert chirp",
        store3=("D3", "PPG sample window (RAM) & limits (NVS)", "100 red/IR samples", "window, limits"),
        cloud_up="HR, SpO₂, temp, alert every 20 s", cloud_down=None,
        derived="HR, SpO₂, alerts",
    ),
    flow=dict(
        nodes=[("s", "start", "Power on"), ("i", "process", "Init BLE, Wi-Fi, MAX30102 (100 sps, avg 4), DS18B20, OLED"),
               ("l", "process", "Handle commands"),
               ("f", "io", "Drain MAX30102 FIFO"), ("fp", "decision", "IR > 50k (finger)?"),
               ("rs", "process", "Reset window, clear HR/SpO₂"), ("w", "process", "Push sample into 4 s window"),
               ("n", "decision", "Window full & 25 new samples?"), ("a", "process", "Run Maxim HR/SpO₂ algorithm; average HR"),
               ("t", "io", "Read DS18B20, request next"), ("al", "decision", "Outside limits?"),
               ("b", "process", "Buzzer + vital_alert event"),
               ("u", "io", "Every 1 s: OLED + BLE; every 20 s: ThingSpeak (if finger & valid)")],
        edges=[("s", "i"), ("i", "l"), ("l", "f"), ("f", "fp"), ("fp", "w", "yes"), ("fp", "rs", "no"), ("rs", "t"),
               ("w", "n"), ("n", "a", "yes"), ("n", "t", "no"), ("a", "t"), ("t", "al"), ("al", "b", "yes"),
               ("al", "u", "no"), ("b", "u"), ("u", "l", "", ", constraint=false")],
    ),
    tests=[
        ("Sensor detection", "Boot with Serial Monitor open", "No '[MAX30102] not found' message"),
        ("Finger detection", "Place and remove a finger", "'Finger detected' / 'Finger removed' events"),
        ("Heart rate", "Rest finger 15 s; compare with a commercial oximeter or manual pulse count", "Within ±5 bpm"),
        ("SpO₂", "Compare with a commercial finger oximeter at rest", "Within ±2-3 % (typical 95-99 %)"),
        ("Temperature", "Hold probe under the arm for 3 minutes; compare with a clinical thermometer", "Within ±0.5 °C"),
        ("Alert", "Set hrhigh=60 over BLE", "Buzzer chirps and 'vital_alert' event appears"),
        ("Cloud", "Keep finger on sensor for 1 minute", "ThingSpeak fields 1-4 update every 20 s"),
    ],
    advantages=["Three vitals in one low-cost device with remote logging.",
                "Responsive: non-blocking design keeps BLE and Wi-Fi working while measuring.",
                "Uploads only valid data (finger present).",
                "Limits are configurable per patient."],
    limitations=["Not a medical device; accuracy depends on finger pressure, motion, ambient light and skin tone.",
                 "Maxim's reference algorithm is sensitive to motion; readings at rest only.",
                 "FIFO samples may be lost during the 1-2 s HTTPS upload, briefly delaying the next estimate.",
                 "ThingSpeak data should not hold identifiable patient information."],
    future=["Use a better algorithm (bandpass filter + peak detection, or Maxim's SpO₂ calibration) and a finger clip.",
            "Add ECG (AD8232) and blood pressure estimation from PTT.",
            "Send SMS/email to caregivers via ThingSpeak React + ThingHTTP.",
            "Wearable version with a LiPo battery and wrist-worn sensor."],
    safety=["Educational prototype only — never use it to diagnose, treat or replace professional medical equipment.",
            "Use a USB power bank or isolated adapter; never connect a person to a device powered from a non-isolated supply.",
            "Clean the sensor and probe between users."],
    conclusion=(
        "The Health Monitoring System demonstrates how optical PPG and digital temperature sensing can be combined on an "
        "ESP32 into a connected vital-signs monitor. Its non-blocking design keeps BLE and Wi-Fi responsive, finger "
        "detection keeps cloud data clean, and configurable alerts make it a useful learning platform for biomedical IoT."),
    refs=["Maxim Integrated (Analog Devices), MAX30102 datasheet and reference design (RD117) algorithm.",
          "SparkFun Electronics, SparkFun MAX3010x Sensor Library, GitHub.",
          "Maxim Integrated, DS18B20 Programmable Resolution 1-Wire Digital Thermometer datasheet.",
          "J. Allen (2007), Photoplethysmography and its application in clinical physiological measurement, Physiol. Meas. 28."],
)

P09 = dict(
    id="P09", slug="P09_Smart_Greenhouse",
    title="Smart Greenhouse with Cloud-Configurable Irrigation",
    short="Smart Greenhouse",
    cloud="Supabase", level="Advanced",
    peripherals=["Capacitive soil moisture sensor v1.2", "DHT11", "LDR", "2-channel relay (pump + fan)"],
    abstract=(
        "Irrigation by fixed timers wastes water and stresses plants, and greenhouses overheat quickly on sunny days. This "
        "project monitors soil moisture with a corrosion-resistant capacitive sensor, air temperature and humidity with a "
        "DHT11 and light with an LDR, and controls a water pump and a ventilation fan through a two-channel relay. "
        "Irrigation uses a burst-and-soak strategy: the pump runs in short bursts and waits for water to spread before "
        "measuring again, which prevents over-watering. The fan runs when temperature or humidity is too high. All "
        "readings and actions are logged to Supabase, and the thresholds are read from a settings row in the database, "
        "so they can be changed from anywhere in the Supabase table editor. BLE gives local monitoring, manual control "
        "and two-point soil calibration."),
    problem=(
        "Small farmers and home gardeners either over-water (wasting water, causing root rot) or under-water (yield "
        "loss). Greenhouses need ventilation at the right time. Commercial controllers are expensive and need the "
        "operator on site to change settings."),
    objectives=[
        "Measure soil moisture, temperature, humidity and light.",
        "Irrigate automatically using burst-and-soak control between two moisture thresholds.",
        "Ventilate automatically on high temperature or humidity with hysteresis.",
        "Log readings and events to Supabase and read thresholds from the cloud.",
        "Allow manual override and calibration from a phone over BLE.",
    ],
    scope=(
        "One greenhouse zone or a group of pots/beds with similar water needs, a 5-12 V pump or solenoid valve and a "
        "fan. Multi-zone control and fertigation are outside the scope."),
    existing=(
        "Most soil-moisture projects use cheap resistive probes that corrode in weeks and switch the pump on until the "
        "sensor reads wet — but water takes time to spread, so the soil ends up over-watered. Thresholds are hard-coded."),
    proposed=[
        "Capacitive sensor (no exposed metal) with two-point calibration stored in flash.",
        "Burst-and-soak state machine (15 s water, 120 s soak) to avoid overshoot.",
        "Thresholds stored in a Supabase table and fetched every minute; last values kept offline.",
        "Fan control by temperature OR humidity with hysteresis.",
    ],
    components=COMMON_PARTS + [
        ("Capacitive soil moisture sensor v1.2", 1, "Analog, 3.3-5 V, corrosion resistant", 70),
        ("DHT11 temperature & humidity module", 1, "0-50 °C, 20-90 % RH", 60),
        ("LDR 5 mm + 10 kΩ resistor", 1, "Light level", 10),
        ("2-channel 5 V relay module", 1, "Pump + fan", 80),
        ("5 V mini submersible pump + tube", 1, "Irrigation (demo)", 90),
        ("5 V / 12 V DC fan", 1, "Ventilation (demo)", 60),
    ],
    circuit=dict(
        title="P09 Smart Greenhouse — Circuit Diagram",
        modules=[
            dict(name="Soil sensor v1.2", sub="Capacitive, analog",
                 pins=[("VCC", "3V3"), ("AOUT", "G34"), ("GND", "GND")]),
            dict(name="LDR + 10 kΩ", sub="Light (divider)",
                 pins=[("LDR end", "3V3"), ("Junction", "G35", "LDR from 3.3 V to GPIO35, 10 kΩ from GPIO35 to GND"), ("10k end", "GND")]),
            dict(name="DHT11", sub="Air temperature & humidity",
                 pins=[("VCC", "3V3"), ("DATA", "G4"), ("GND", "GND")]),
            dict(name="2-ch Relay", sub="CH1 pump, CH2 fan (active LOW)",
                 pins=[("VCC", "5V"), ("IN1", "G26"), ("IN2", "G27"), ("GND", "GND")],
                 outer=["COM/NO switch pump & fan supply (+)"]),
        ],
        notes=["Power the soil sensor from 3.3 V so its output never exceeds the ADC range.",
               "Use a separate supply for a 12 V fan or pump; only the relay contacts carry that current."],
    ),
    principles=[
        ("Capacitive soil sensor", "The probe forms a capacitor whose dielectric is the surrounding soil. Water has a "
                                   "high dielectric constant (~80) compared with dry soil (~4), so wetter soil increases "
                                   "capacitance. A 555 timer oscillator and RC filter turn this into a DC voltage that falls "
                                   "as moisture rises. No metal touches the soil, so it does not corrode."),
        ("Two-point calibration", "Moisture % = (V_dry − V) / (V_dry − V_wet) × 100, where V_dry is measured with the "
                                  "probe in air and V_wet with it in water (caldry / calwet commands)."),
        ("DHT11 & LDR", "The DHT11 measures air temperature and humidity; the LDR divider measures light for logging "
                        "and future shading control."),
        ("Supabase settings row", "A single-row table greenhouse_settings (id = 1) holds soil_min, soil_max, temp_max, "
                                  "hum_max and auto_mode. Editing it in the Supabase dashboard changes the controller's "
                                  "behaviour within a minute."),
    ],
    working=[
        "Every 2 s the controller reads all sensors (16-sample ADC averages) and runs the automation. The irrigation "
        "state machine has three states. IDLE → WATERING when soil < soil_min; WATERING → IDLE when soil ≥ soil_max, or "
        "→ SOAKING after a 15 s burst; SOAKING → WATERING after 120 s if soil is still below soil_max, else IDLE.",
        "The fan turns on when temperature > temp_max or humidity > hum_max and off only when temperature < temp_max − "
        "1.5 °C and humidity < hum_max − 5 %. Every pump/fan change is inserted into greenhouse_events with its reason.",
        "Every 60 s a reading row is inserted into greenhouse_readings and the settings row is fetched; changed thresholds "
        "are saved in NVS so the greenhouse keeps working with the last values when offline. The auto_mode column is "
        "applied only when it changes, so a manual override from BLE is not undone every minute.",
    ],
    ble_data=[("soil", "Soil moisture", "%"), ("t", "Temperature", "°C"), ("h", "Humidity", "%"), ("l", "Light", "%"),
              ("pump / fan", "Output states", "bool"), ("mode", "AUTO / MANUAL", "—"),
              ("state", "idle / watering / soaking", "—"), ("smin, smax, tmax", "Active thresholds", "% / °C")],
    ble_cmds=[("mode:auto / mode:manual", "Yes", "Select mode (pump turns off on change)"),
              ("pump:on|off, fan:on|off", "Yes", "Manual control (switches to MANUAL)"),
              ("caldry / calwet", "Yes", "Store current soil reading as dry / wet reference")],
    settings=[("sburl / sbkey", "—", "Supabase URL and publishable key"),
              ("soildry / soilwet", "2800 / 1200", "Soil calibration (mV)")],
    cloud_items=[("greenhouse_readings", "soil, temperature, humidity, light, pump, fan every 60 s"),
                 ("greenhouse_events", "pump_on/off, fan_on/off with reason"),
                 ("greenhouse_settings", "Row id=1: soil_min, soil_max, temp_max, hum_max, auto_mode (edit to tune)")],
    dfd=dict(
        sensors="Soil, DHT11, LDR", raw="moisture, T, RH, light",
        actuators="Pump + fan relays", act="irrigate / ventilate",
        store3=("D3", "Thresholds & calibration (NVS)", "thresholds from cloud", "last thresholds offline"),
        cloud_up="readings + events", cloud_down="threshold settings row",
        derived="moisture %, watering state, fan decision",
    ),
    flow=dict(
        nodes=[("s", "start", "Power on"), ("i", "process", "Outputs OFF; load calibration & thresholds; init BLE, Wi-Fi"),
               ("l", "process", "Handle BLE commands"),
               ("r", "io", "Every 2 s: read soil, DHT11, LDR"), ("am", "decision", "AUTO?"),
               ("st", "decision", "Water state"), ("i1", "decision", "soil < min?"), ("w1", "decision", "soil ≥ max?"),
               ("w2", "decision", "burst > 15 s?"), ("s1", "decision", "soak > 120 s?"),
               ("pon", "process", "Pump ON → WATERING"), ("poff", "process", "Pump OFF → IDLE"),
               ("soak", "process", "Pump OFF → SOAKING"),
               ("fan", "process", "Fan ON if T/RH high; OFF when both normal"),
               ("c", "io", "Every 60 s: fetch settings row, INSERT reading")],
        edges=[("s", "i"), ("i", "l"), ("l", "r"), ("r", "am"), ("am", "st", "yes"), ("am", "c", "no"),
               ("st", "i1", "IDLE"), ("st", "w1", "WATERING"), ("st", "s1", "SOAKING"),
               ("i1", "pon", "yes"), ("i1", "fan", "no"), ("w1", "poff", "yes"), ("w1", "w2", "no"),
               ("w2", "soak", "yes"), ("w2", "fan", "no"), ("s1", "pon", "yes, still dry"), ("s1", "fan", "no"),
               ("pon", "fan"), ("poff", "fan"), ("soak", "fan"), ("fan", "c"), ("c", "l", "", ", constraint=false")],
    ),
    tests=[
        ("Calibration", "Probe in air: caldry; probe in water: calwet", "Air ≈ 0 %, water ≈ 100 %"),
        ("Burst-and-soak", "Put probe in dry soil (AUTO)", "Pump 15 s ON, 120 s OFF, repeats until soil ≥ max"),
        ("Fan", "Set temp_max 2 °C below room temperature in Supabase", "Within 1 min the fan turns ON; 'fan_on' event"),
        ("Cloud thresholds", "Change soil_min in greenhouse_settings", "BLE shows new smin within 60 s"),
        ("Manual override", "Send pump:on over BLE", "Pump ON, mode MANUAL; cloud does not revert it"),
        ("Offline", "Disconnect Wi-Fi for 10 min", "Control continues with last thresholds; logging resumes after"),
    ],
    advantages=["Saves water through burst-and-soak irrigation.",
                "Corrosion-free capacitive sensing.",
                "Thresholds changeable from anywhere without reflashing.",
                "Full history of readings and actions in a SQL database."],
    limitations=["One moisture sensor represents the whole zone.",
                 "DHT11 has limited accuracy and range (0-50 °C).",
                 "Capacitive sensor readings vary with soil type; calibrate in the actual soil for best results.",
                 "Supabase free projects pause after a week without activity."],
    future=["Multiple zones with solenoid valves and one sensor per zone.",
            "Use weather forecast (rain probability) to skip irrigation.",
            "Shade-net motor control using the LDR reading.",
            "Web dashboard with charts using Supabase JS client."],
    safety=["Keep electronics in an IP65 box; route pump and fan wiring with drip loops.",
            "Use low-voltage pumps/fans where possible; mains pumps need a contactor and RCCB."],
    conclusion=(
        "The Smart Greenhouse automates irrigation and ventilation using inexpensive sensors and a robust control "
        "strategy. Burst-and-soak watering avoids the overshoot of simple threshold controllers, and storing thresholds in "
        "Supabase lets growers tune the system remotely, while BLE and offline thresholds keep it working without "
        "internet."),
    refs=["DFRobot, Capacitive Soil Moisture Sensor v1.2 (SEN0193) wiki.",
          "FAO Irrigation and Drainage Paper 56 — Crop evapotranspiration (background on irrigation scheduling).",
          "Aosong, DHT11 datasheet.",
          "Supabase documentation — Database, Table Editor and REST API."],
)

P10 = dict(
    id="P10", slug="P10_Vehicle_Tracker_Accident_Alert",
    title="Vehicle Tracking and Accident Alert System",
    short="Vehicle Tracker & Accident Alert",
    cloud="Supabase", level="Advanced",
    peripherals=["NEO-6M GPS module", "MPU6050 accelerometer/gyro", "Active buzzer", "Push button"],
    abstract=(
        "Road accidents in India claim lakhs of lives every year, and delayed help is a major cause. This project "
        "tracks a vehicle with a NEO-6M GPS receiver and detects possible accidents with an MPU6050 accelerometer: a "
        "sudden impact above a g-force threshold or a rollover (tilt above 60° for 3 seconds) starts a 15-second "
        "countdown with a buzzer. If the driver does not cancel with the button, an alert with the GPS location and a "
        "Google Maps link is inserted into a Supabase database through the driver's phone hotspot. Holding the button for "
        "three seconds sends a manual SOS. The location trail is logged every 30 seconds while moving and every 5 minutes "
        "when parked, buffered when offline, and a home geofence raises exit/enter alerts. A phone connected over BLE shows "
        "live position, speed and g-force."),
    problem=(
        "After an accident, victims may be unconscious or unable to call for help, and bystanders may not know the exact "
        "location. Fleet owners and families also want to know where a vehicle is. Commercial trackers need SIM "
        "subscriptions and closed apps."),
    objectives=[
        "Track vehicle position, speed and heading with GPS and log it to the cloud.",
        "Detect impacts and rollovers with an accelerometer.",
        "Give the driver a cancel window to avoid false alarms.",
        "Send accident/SOS alerts with a map link to a cloud database.",
        "Provide geofence alerts and live data over BLE.",
    ],
    scope=(
        "Two-wheelers and cars, using the driver's phone hotspot for internet. Automatic calling/SMS (GSM) and CAN-bus "
        "data are outside the scope but listed as future work."),
    existing=(
        "Basic GPS trackers log location only; accident-detection projects often trigger on any bump and have no cancel "
        "window, causing frequent false alarms. Many rely on a GSM module and paid SMS."),
    proposed=[
        "Two detection criteria: peak g-force and sustained tilt (rollover).",
        "15-second cancel window with buzzer, plus a manual SOS button.",
        "Adaptive logging interval and an offline buffer of 20 positions.",
        "Undelivered alerts are retried every 30 s; BLE alert works without internet.",
        "Geofence around a home location set from the phone.",
    ],
    components=COMMON_PARTS + [
        ("NEO-6M GPS module with ceramic antenna (GY-NEO6MV2)", 1, "UART 9600 baud, 2.5 m CEP", 300),
        ("MPU6050 accelerometer + gyroscope (GY-521)", 1, "±2-16 g, I2C 0x68", 120),
        ("Active buzzer 5 V", 1, "Countdown / alert", 15),
        ("Push button (tactile, 12 mm)", 1, "Cancel / SOS", 5),
        ("12 V-to-5 V USB car charger / power bank", 1, "Vehicle power", 150),
    ],
    circuit=dict(
        title="P10 Vehicle Tracker & Accident Alert — Circuit Diagram",
        modules=[
            dict(name="NEO-6M GPS", sub="UART 9600 baud",
                 pins=[("VCC", "3V3"), ("TX", "G16"), ("RX", "G17"), ("GND", "GND")]),
            dict(name="MPU6050", sub="GY-521, I2C 0x68",
                 pins=[("VCC", "3V3"), ("SDA", "G21"), ("SCL", "G22"), ("GND", "GND")]),
            dict(name="Active buzzer", sub="Countdown / alert",
                 pins=[("+", "G18"), ("-", "GND")]),
            dict(name="Push button", sub="Cancel (short) / SOS (3 s)",
                 pins=[("Pin 1", "G13", "Internal pull-up enabled; button pulls GPIO13 to GND when pressed"), ("Pin 2", "GND")]),
        ],
        notes=["GPS TX goes to ESP32 RX2 (GPIO16) and GPS RX to TX2 (GPIO17) — crossed.",
               "Mount the MPU6050 rigidly to the vehicle body, not on a rubber mount; place the GPS antenna facing the sky."],
    ),
    principles=[
        ("GPS (NEO-6M)", "The receiver tracks signals from several satellites, measures the travel time of each, and "
                         "solves for position and time (trilateration). It outputs NMEA sentences ($GPRMC, $GPGGA) at "
                         "9600 baud; TinyGPSPlus parses latitude, longitude, speed, course and satellite count."),
        ("MPU6050", "A MEMS accelerometer measures acceleration on three axes. At rest it reads 1 g (gravity). The total "
                    "magnitude |a| = √(ax² + ay² + az²) jumps above 2-3 g in a crash. Gravity's direction gives pitch = "
                    "atan2(−ax, √(ay²+az²)) and roll = atan2(ay, az)."),
        ("Cancel window", "Speed bumps and potholes can exceed the threshold. The 15 s buzzer countdown lets a conscious "
                          "driver cancel; an unconscious driver cannot, so the alert is sent."),
        ("Geofence", "TinyGPSPlus::distanceBetween() uses the haversine formula to compute the distance from home; "
                     "crossing the radius raises geofence_exit / geofence_enter alerts."),
    ],
    working=[
        "The firmware parses GPS characters continuously and reads the MPU6050 at 50 Hz with an 8 g range and a 21 Hz "
        "low-pass filter. Peak g is tracked per second for the BLE display.",
        "If |a| exceeds crashg (default 2.5 g), or pitch/roll exceed tilt (60°) for 3 s, the state changes to COUNTDOWN "
        "and the buzzer beeps for 15 s. A short button press cancels. After 15 s the alert (type, g-force, lat, lng, "
        "Google Maps URL, speed) is inserted into vehicle_alerts; if there is no internet it is retried every 30 s and "
        "shown immediately over BLE. Holding the button 3 s sends 'sos'.",
        "A position is logged every 30 s when speed > 3 km/h and every 5 minutes otherwise. Points go into a 20-entry "
        "buffer, and the whole buffer is inserted in one request when online, so short coverage gaps lose nothing.",
    ],
    ble_data=[("fix", "GPS fix valid", "bool"), ("lat / lng", "Position", "degrees"), ("spd", "Speed", "km/h"),
              ("sat", "Satellites used", "count"), ("g", "Peak g in last second", "g"), ("pitch / roll", "Tilt", "°"),
              ("state", "normal / countdown / alert", "—"), ("buf", "Unsent positions", "count")],
    ble_cmds=[("reset", "No", "Clear an alert state"), ("sos", "No", "Send an SOS alert from the phone"),
              ("fencehere:<metres>", "Yes", "Set the home geofence at the current position")],
    settings=[("sburl / sbkey", "—", "Supabase URL and publishable key"), ("crashg", "2.5", "Impact threshold (g)"),
              ("tilt", "60", "Rollover angle (°)"), ("fence", "—", "lat,lng,radius (set by fencehere)")],
    cloud_items=[("vehicle_locations", "lat, lng, speed_kmph, heading, satellites, recorded_at"),
                 ("vehicle_alerts", "type, detail, g_force, lat, lng, maps_url, speed_kmph")],
    dfd=dict(
        sensors="GPS satellites + MPU6050", raw="NMEA sentences, acceleration",
        actuators="Driver (buzzer + button)", act="countdown beeps",
        store3=("D3", "Offline position buffer (RAM) & geofence (NVS)", "positions", "batch to upload"),
        cloud_up="location batches, alerts", cloud_down=None,
        derived="position, speed, g-force, tilt, alerts",
    ),
    flow=dict(
        nodes=[("s", "start", "Power on"), ("i", "process", "Init BLE, Wi-Fi (hotspot), GPS UART, MPU6050"),
               ("l", "process", "Parse GPS characters; handle BLE commands"),
               ("m", "io", "Every 20 ms: read MPU6050, compute g, pitch, roll"),
               ("st", "decision", "State NORMAL?"), ("cr", "decision", "g > crashg OR tilt > 60° for 3 s?"),
               ("cd", "process", "COUNTDOWN: beep 15 s"), ("bt", "decision", "Button pressed?"),
               ("cn", "process", "Cancel → NORMAL"), ("tm", "decision", "15 s over?"),
               ("al", "io", "INSERT alert with map link (retry if offline)"),
               ("lg", "decision", "Log interval reached?"), ("lp", "io", "Buffer position; INSERT batch if online"),
               ("b", "io", "Every 1 s: BLE frame, geofence check")],
        edges=[("s", "i"), ("i", "l"), ("l", "m"), ("m", "st"), ("st", "cr", "yes"), ("st", "bt", "no"),
               ("cr", "cd", "yes"), ("cr", "lg", "no"), ("cd", "bt"), ("bt", "cn", "yes"), ("bt", "tm", "no"),
               ("cn", "lg"), ("tm", "al", "yes"), ("tm", "lg", "no"), ("al", "lg"), ("lg", "lp", "yes"),
               ("lg", "b", "no"), ("lp", "b"), ("b", "l", "", ", constraint=false")],
    ),
    tests=[
        ("GPS fix", "Place outdoors with clear sky, wait 1-5 min (cold start)", "fix=true, 4+ satellites, position matches Google Maps"),
        ("Tracking", "Drive/walk with the device for 5 minutes", "Rows every ~30 s while moving in vehicle_locations"),
        ("Impact", "Set crashg=1.5 and tap the board sharply", "Countdown starts and buzzer beeps"),
        ("Cancel", "Press the button during countdown", "'cancelled' event; no alert row"),
        ("Accident alert", "Let the countdown expire", "Row in vehicle_alerts with maps_url; BLE event"),
        ("Rollover", "Tilt the board 90° for 4 s", "accident_rollover countdown"),
        ("SOS", "Hold the button 3 s", "sos row in vehicle_alerts"),
        ("Geofence", "fencehere:50 then move > 50 m away", "geofence_exit alert"),
    ],
    advantages=["Automatic alert with exact map location even if the driver is unconscious.",
                "Cancel window reduces false alarms.",
                "No SIM card or paid SMS needed (uses phone hotspot).",
                "Location history and alerts in a queryable database."],
    limitations=["Depends on the phone hotspot for internet; no alert if the phone is damaged or out of coverage.",
                 "Threshold-based detection can miss low-speed crashes or trigger on severe potholes.",
                 "NEO-6M needs open sky; cold start can take several minutes.",
                 "Alerts are stored in the database; notification to family needs an extra step (see future work)."],
    future=["Add a SIM800L/A7670 GSM module for direct SMS and calls.",
            "Supabase Edge Function or database webhook to send Telegram/email notifications on new alerts.",
            "Machine-learning crash classifier using gyro + accelerometer patterns.",
            "Web map of the trail using Leaflet and the Supabase JS client."],
    safety=["Do not operate the phone/app while driving.",
            "Fix the device securely; a loose device can cause false impacts and distract the driver.",
            "The system supplements, not replaces, calling emergency services (112)."],
    conclusion=(
        "The Vehicle Tracking and Accident Alert System combines GPS, inertial sensing and a cloud database to provide "
        "tracking, geofencing and automatic accident alerts with location links at very low cost. The cancel window and "
        "dual detection criteria keep false alarms low, while offline buffering and retries make it dependable on "
        "Indian roads with patchy mobile coverage."),
    refs=["u-blox, NEO-6 GPS Modules data sheet (GPS.G6-HW-09005).",
          "InvenSense (TDK), MPU-6000/MPU-6050 Product Specification.",
          "M. Hart, TinyGPSPlus library documentation, arduiniana.org.",
          "Ministry of Road Transport & Highways, Road Accidents in India (annual report)."],
)

PROJECTS_B = [P06, P07, P08, P09, P10]
