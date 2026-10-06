# -*- coding: utf-8 -*-
"""
build_reports.py — generates, for every project:
  reports/<slug>/images/*.png   circuit, block diagram, DFD L0/L1, flowchart
  reports/<slug>/<slug>_Report.docx and .pdf
Run from the repo root:  python3 tools/build_reports.py [P01 P02 ...]
Needs: matplotlib, graphviz (dot), node + docx, LibreOffice, poppler-utils.
"""
import json, os, re, subprocess, sys, shutil
sys.path.insert(0, os.path.dirname(__file__))
import circuit, graphs
from projects_a import PROJECTS_A
from projects_b import PROJECTS_B

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO_URL = "https://github.com/rohitkukreja705/esp32-iot-projects"
CONSOLE_URL = "https://rohitkukreja705.github.io/esp32-iot-projects/"
DATE = "October 2026"

LIBS = {
    "P01": ["DHT sensor library (Adafruit)", "Adafruit Unified Sensor", "Adafruit BMP085 Library"],
    "P02": ["LiquidCrystal I2C (Frank de Brabander / johnrickman)"],
    "P03": ["DHT sensor library (Adafruit)", "Adafruit Unified Sensor"],
    "P04": ["DHT sensor library (Adafruit)", "Adafruit Unified Sensor", "Adafruit SSD1306", "Adafruit GFX Library"],
    "P05": ["ESP32Servo"],
    "P06": ["MFRC522 (GithubCommunity / miguelbalboa)", "Adafruit SSD1306", "Adafruit GFX Library"],
    "P07": [],
    "P08": ["SparkFun MAX3010x Pulse and Proximity Sensor Library", "OneWire", "DallasTemperature",
            "Adafruit SSD1306", "Adafruit GFX Library"],
    "P09": ["DHT sensor library (Adafruit)", "Adafruit Unified Sensor"],
    "P10": ["TinyGPSPlus", "Adafruit MPU6050", "Adafruit Unified Sensor"],
}

SAMPLES = {
    "P01": '{"t":29.4,"h":62,"p":1004.6,"l":71,"rn":0,"hi":31.9,"dp":21.4,"fc":"Fair, stable","wifi":true,"type":"data"}',
    "P02": '{"v":231.4,"i":0.412,"w":88.6,"va":95.3,"pf":0.93,"kwh":1.274,"cost":8.92,"relay":true,"cloud":true,"type":"data"}',
    "P03": '{"t":30.1,"h":58,"m":true,"mode":"AUTO","alarm":false,"r":[1,1,0,0],"cloud":true,"type":"data"}',
    "P04": '{"ppm":684,"t":27.9,"h":55,"rs":38.12,"r0":52.4,"ratio":0.727,"lvl":2,"cat":"Moderate","alarm":false,"type":"data"}',
    "P05": '{"s":[1,0],"d":[6,38],"free":1,"gate":"closed","car":false,"type":"data"}',
    "P06": '{"type":"scan","uid":"A1B2C3D4","name":"Rohit","dir":"IN","cloud":true}',
    "P07": '{"lvl":64,"cm":45.2,"flow":3.12,"lit":12.4,"pump":true,"mode":"AUTO","fault":"","cloud":true,"type":"data"}',
    "P08": '{"hr":76,"spo2":98,"temp":36.6,"finger":true,"alert":false,"type":"data"}',
    "P09": '{"soil":41,"t":31.2,"h":67,"l":82,"pump":false,"fan":true,"mode":"AUTO","state":"soaking","smin":35,"smax":60,"tmax":32,"type":"data"}',
    "P10": '{"fix":true,"lat":23.259933,"lng":77.412613,"spd":34.5,"sat":8,"g":1.07,"pitch":3,"roll":-2,"state":"normal","buf":0,"type":"data"}',
}


# ===================================================================== helpers
class Model:
    def __init__(self):
        self.blocks, self.fig, self.tab, self.toc = [], 0, 0, []

    def h1(self, text, nobreak=False):
        self.blocks.append({"t": "h1", "text": text, "nobreak": nobreak}); self.toc.append((1, text))

    def h2(self, text):
        self.blocks.append({"t": "h2", "text": text}); self.toc.append((2, text))

    def h3(self, text):
        self.blocks.append({"t": "h3", "text": text})

    def p(self, text):
        self.blocks.append({"t": "p", "text": text})

    def bullets(self, items):
        self.blocks.append({"t": "bullets", "items": list(items)})

    def numbers(self, items):
        self.blocks.append({"t": "numbers", "items": list(items)})

    def table(self, header, rows, widths, cap):
        self.tab += 1
        self.blocks.append({"t": "table", "header": header, "rows": [[str(c) for c in r] for r in rows],
                            "widths": widths, "caption": f"Table {self.tab}: {cap}"})
        return self.tab

    def img(self, path, cap, w=6.3, maxh=8.6):
        self.fig += 1
        self.blocks.append({"t": "img", "path": path, "caption": f"Figure {self.fig}: {cap}", "w": w, "maxh": maxh})
        return self.fig

    def code(self, lines, title=None):
        self.blocks.append({"t": "code", "lines": lines, "title": title})

    def note(self, text, kind="info"):
        self.blocks.append({"t": "note", "text": text, "kind": kind})

    def pb(self):
        self.blocks.append({"t": "pb"})


def service_short(cloud):
    return {"ThingSpeak": "ts", "Adafruit IO": "aio", "Supabase": "sb"}[cloud]


# ===================================================================== diagrams
def make_images(P, d):
    os.makedirs(d, exist_ok=True)
    img = {k: os.path.join(d, f"{P['id']}_{k}.png") for k in ("circuit", "block", "dfd0", "dfd1", "flow")}
    circuit.draw(json.loads(json.dumps(P["circuit"])), img["circuit"])

    D = P["dfd"]
    inputs = [m["name"] for m in P["circuit"]["modules"] if m["name"] not in D["actuators"]]
    sens, outs = [], []
    for m in P["circuit"]["modules"]:
        n = m["name"]
        is_out = any(w in n.lower() for w in ("relay", "buzzer", "servo", "lcd", "oled", "led"))
        (outs if is_out else sens).append(f"{n}\n{m.get('sub', '')}")
    links = [("Phone — Web Bluetooth console", "BLE (NUS)"), (f"{P['cloud']} cloud", "Wi-Fi HTTPS/MQTT")]
    graphs.block(f"ESP32\\nDevKit V1\\n({P['id']})", [s.replace("\n", "\\n") for s in sens],
                 [o.replace("\n", "\\n") for o in outs], links, img["block"])

    ents0 = [(D["sensors"], D["raw"], None),
             ("User with phone (BLE web console)", "commands, PIN, Wi-Fi & cloud keys", "live data, events, acks"),
             (D["actuators"], None, D["act"]),
             (f"{P['cloud']} cloud platform", D["cloud_down"], D["cloud_up"])]
    graphs.dfd0(P["short"], ents0, img["dfd0"])

    procs = [("1.0", "Acquire sensor data"), ("2.0", "Process & decide"), ("3.0", "Actuate & alert"),
             ("4.0", "BLE communication"), ("5.0", "Cloud sync")]
    sid, sname, s_in, s_out = D["store3"]
    stores = [("D1", "Settings (NVS flash)"), ("D2", sname)]
    ents = [("E1", D["sensors"]), ("E2", "User / BLE app"), ("E3", D["actuators"]), ("E4", f"{P['cloud']} cloud")]
    flows = [("E1", "1.0", D["raw"]), ("1.0", "2.0", "readings"), ("D1", "2.0", "thresholds, calibration"),
             ("2.0", "3.0", "control decisions"), ("3.0", "E3", D["act"]), ("2.0", "4.0", "data frames, events"),
             ("4.0", "E2", "live JSON, events"), ("E2", "4.0", "commands, Wi-Fi, keys"), ("4.0", "D1", "new settings"),
             ("4.0", "2.0", "user commands"), ("2.0", "5.0", D["derived"]), ("5.0", "E4", D["cloud_up"]),
             ("D1", "5.0", "Wi-Fi & cloud keys"), ("2.0", "D2", s_in), ("D2", "2.0", s_out)]
    if D["cloud_down"]:
        flows += [("E4", "5.0", D["cloud_down"]), ("5.0", "2.0", "remote commands")]
    graphs.dfd1(procs, stores, ents, flows, img["dfd1"])

    F = P["flow"]
    graphs.flowchart(F["nodes"], F["edges"], img["flow"])
    return img


# ===================================================================== content
def cloud_setup_steps(P):
    c = P["cloud"]
    if c == "ThingSpeak":
        return [
            "Go to **thingspeak.mathworks.com** and sign up with a free MathWorks account (choose the free, non-commercial licence).",
            f"Open **Channels → My Channels → New Channel**. Name it '{P['short']}'.",
            "Tick and name the fields exactly as listed in the table below, then click **Save Channel**.",
            "Open the **API Keys** tab and copy the **Write API Key** (16 characters).",
            "In the BLE web console open **Setup**, unlock with the PIN and save the key in the `tskey` field "
            "(equivalent command: `set:tskey=YOURKEY`).",
            "Open **Private View** to see live charts. Add Gauge or Numeric Display widgets with **Add Widgets**, and use "
            "**Sharing → Share channel view with everyone** if you want a public link.",
        ]
    if c == "Adafruit IO":
        return [
            "Go to **io.adafruit.com** and create a free account.",
            "Click the yellow **key icon (My Key / Adafruit IO Key)** and copy your **Username** and **Active Key**.",
            "In the BLE web console open **Setup**, unlock and save them in `aiouser` and `aiokey` "
            "(commands: `set:aiouser=NAME`, `set:aiokey=aio_xxxx`).",
            "Power the device: feeds are created automatically on the first publish. You can also create them first in "
            "**Feeds → New Feed** using the exact keys in the table below.",
            "Open **Dashboards → New Dashboard**, then **+ (Create New Block)**. Use Toggle blocks for switch feeds with "
            "button-on text `ON` and button-off text `OFF` (or `AUTO`/`MANUAL` for mode feeds), Gauge blocks for levels "
            "and Line Chart blocks for history.",
            "Free tier: 30 data points per minute, 10 feeds, 5 dashboards and 30 days of history per account. Projects on "
            "the same account share these limits, so delete feeds of projects you are not running or use separate accounts.",
        ]
    return [
        "Go to **supabase.com**, sign in (GitHub sign-in works) and click **New project**. Choose region **Mumbai "
        "(ap-south-1)** for the lowest latency and set a database password.",
        "Open **SQL Editor → New query**, paste the whole file `cloud/supabase_schema.sql` from the repository and click "
        "**Run**. It creates the tables, views and Row Level Security policies for all four Supabase projects (P05, P06, "
        "P09, P10), so one Supabase project can serve all of them.",
        "Click **Connect** at the top of the dashboard (or **Project Settings → API Keys**) and copy the **Project URL** "
        "(https://xxxx.supabase.co) and the **publishable key** (`sb_publishable_…`; the legacy `anon` key also works).",
        "In the BLE web console open **Setup**, unlock and save them in `sburl` and `sbkey`.",
        "Open **Table Editor** to watch rows arrive. Use the **SQL Editor** for reports, e.g. the views created by the "
        "schema, and **Export to CSV** for spreadsheets.",
        "Free tier: 500 MB database and 2 active projects. Free projects are **paused after one week of inactivity** "
        "— open the dashboard and click **Restore** if that happens.",
    ]


def build_model(P, img):
    M = Model()
    pid, cloud = P["id"], P["cloud"]
    M.blocks.append({"t": "title", "title": P["title"],
                     "subtitle": f"IoT project using ESP32 with Bluetooth Low Energy and Wi-Fi ({cloud})",
                     "img": img["block"],
                     "fields": [("Project", f"{pid} · {P['level']} level"),
                                ("Peripherals", ", ".join(P["peripherals"])),
                                ("Submitted by", "______________________________"),
                                ("Under the guidance of", "______________________________"),
                                ("Department / Institution", "______________________________")],
                     "date": DATE})

    # certificate + acknowledgement templates
    M.blocks.append({"t": "h1", "text": "Certificate", "nobreak": False})
    M.p(f"This is to certify that the project report entitled **“{P['title']}”** is a bonafide record of the work "
        "carried out by ______________________ (Roll No. ________) in partial fulfilment of the requirements for the award "
        "of ______________________ in ______________________ during the academic year ________.")
    M.p(" ")
    M.p("Project Guide: ______________________          Head of Department: ______________________")
    M.p("Date: ____________          Place: ____________")
    M.blocks.append({"t": "h1", "text": "Acknowledgement", "nobreak": False})
    M.p("I express my sincere gratitude to my project guide ______________________ for continuous guidance and support, "
        "to the Head of the Department ______________________, and to all faculty members and friends who helped me "
        "complete this project successfully.")

    toc_index = len(M.blocks)
    M.blocks.append({"t": "toc", "entries": []})

    # ---------------- Abstract
    M.h1("Abstract")
    M.p(P["abstract"])
    M.p("**Keywords:** ESP32, Internet of Things, Bluetooth Low Energy, Wi-Fi, " + cloud + ", " +
        ", ".join(P["peripherals"]) + ".")

    # ---------------- 1 Introduction
    M.h1("1. Introduction")
    M.p("The Internet of Things (IoT) connects physical devices — sensors and actuators — to networks so that data can "
        "be collected, analysed and acted on automatically. The ESP32 from Espressif Systems has made IoT affordable: a "
        "single ₹350 board combines a dual-core 240 MHz processor, Wi-Fi and Bluetooth Low Energy. This project uses "
        f"both radios at once: BLE for direct, local interaction with a phone and Wi-Fi for cloud connectivity through "
        f"{cloud}, a free IoT/cloud platform.")
    M.h2("1.1 Problem Statement"); M.p(P["problem"])
    M.h2("1.2 Objectives"); M.numbers(P["objectives"])
    M.h2("1.3 Scope of the Project"); M.p(P["scope"])
    M.h2("1.4 Organisation of the Report")
    M.p("Chapter 2 reviews existing approaches and describes the proposed system. Chapter 3 covers system design and "
        "components, Chapter 4 the circuit, Chapter 5 the data flow diagrams, Chapter 6 the software, Chapter 7 the "
        "step-by-step setup of hardware, cloud and app, Chapter 8 testing, Chapter 9 discussion and Chapter 10 the "
        "conclusion. Complete source code is given in the appendices.")

    # ---------------- 2 Literature
    M.h1("2. Existing System and Proposed System")
    M.h2("2.1 Existing Systems"); M.p(P["existing"])
    M.h2("2.2 Proposed System"); M.p("The proposed system improves on these in the following ways:"); M.bullets(P["proposed"])
    M.h2("2.3 Why Both BLE and Wi-Fi?")
    M.p("Wi-Fi gives the device internet access for remote monitoring, history and control from anywhere, but it depends "
        "on a router and an internet connection, and the device needs the Wi-Fi password before it can connect. BLE needs "
        "no infrastructure: any modern phone can connect directly within about 10-30 m. Using both gives:")
    M.bullets(["**Provisioning** — Wi-Fi credentials and cloud keys are sent from the phone over BLE and stored in flash; "
               "nothing secret is hard-coded or uploaded to GitHub.",
               "**Resilience** — local monitoring and control keep working when the internet or router is down.",
               "**Remote access** — the cloud dashboard works from anywhere when the internet is available.",
               "**Low cost** — no extra hardware; both radios are built into the ESP32."])
    M.p("The ESP32 shares one 2.4 GHz radio between Wi-Fi and Bluetooth by time-division coexistence. For this to work "
        "the Wi-Fi modem-sleep mode must stay enabled, which the firmware ensures. NimBLE, a lightweight BLE stack, is "
        "used instead of the default Bluedroid stack to leave more RAM for TLS (HTTPS/MQTTS) connections.")

    # ---------------- 3 System design
    M.h1("3. System Design")
    M.h2("3.1 Block Diagram")
    M.img(img["block"], f"Block diagram of the {P['short']}", w=6.3, maxh=4.2)
    M.p("The ESP32 is the central controller. Input devices (blue) feed measurements to it, output devices (amber) are "
        "driven by it, and two communication links (green) connect it to the user's phone over BLE and to the "
        f"{cloud} cloud over Wi-Fi. The board is powered from 5 V through its USB connector or VIN pin.")
    M.h2("3.2 System Architecture")
    M.p("The system follows the standard three-layer IoT architecture:")
    M.bullets([f"**Perception layer** — {', '.join(P['peripherals'])} connected to the ESP32 GPIO, ADC, I2C, SPI or UART.",
               "**Network layer** — BLE 4.2 GATT server (Nordic UART Service) and Wi-Fi 802.11 b/g/n with TLS-encrypted "
               f"{'MQTT' if cloud == 'Adafruit IO' else 'HTTPS REST'} to {cloud}.",
               f"**Application layer** — the Web Bluetooth console on the phone and the {cloud} dashboard / database."])
    M.h2("3.3 Hardware Components and Cost")
    rows, total = [], 0
    for i, (name, qty, spec, price) in enumerate(P["components"], 1):
        total += price
        rows.append([i, name, qty, spec, f"₹{price}"])
    rows.append(["", "**Total (approx.)**", "", "", f"**₹{total}**"])
    M.table(["#", "Component", "Qty", "Specification", "Cost"], rows, [0.4, 2.6, 0.45, 2.4, 0.75],
            "Bill of materials with approximate Indian prices (Robu.in / Amazon.in / local market, 2026)")
    M.note(f"Prices are indicative and vary by seller. The breadboard, cable and ESP32 can be reused across all ten "
           f"projects, so the incremental cost of this project is about ₹{total - 560}.")
    M.h2("3.4 ESP32 DevKit V1")
    M.table(["Feature", "Value"], [
        ["Module", "ESP-WROOM-32 (ESP32-D0WD), dual-core Xtensa LX6 up to 240 MHz"],
        ["Memory", "520 KB SRAM, 4 MB SPI flash"],
        ["Wireless", "Wi-Fi 802.11 b/g/n 2.4 GHz; Bluetooth 4.2 BR/EDR + BLE"],
        ["I/O", "25 usable GPIO on the 30-pin board, 12-bit ADC (ADC1: GPIO32-39), 2 × DAC, PWM on any output"],
        ["Interfaces", "3 × UART, 2 × I2C, 3 × SPI, I2S, touch, RMT"],
        ["Supply", "5 V via USB/VIN, on-board 3.3 V regulator (AMS1117)"],
        ["Logic level", "3.3 V — inputs are NOT 5 V tolerant"],
    ], [1.6, 4.6], "Key specifications of the ESP32 DevKit V1")
    M.h2("3.5 Working Principle of Components")
    for name, text in P["principles"]:
        M.h3(name); M.p(text)

    # ---------------- 4 Circuit
    M.h1("4. Circuit Design")
    M.h2("4.1 Circuit Diagram")
    M.img(img["circuit"], f"Circuit diagram of the {P['short']}", w=6.6, maxh=8.4)
    M.h2("4.2 Pin Connections")
    rows = []
    for m in P["circuit"]["modules"]:
        for pin in m["pins"]:
            tgt = pin[1]
            tgt_txt = {"5V": "5V rail (VIN)", "3V3": "3.3 V (3V3 pin)", "GND": "GND"}.get(tgt, f"GPIO{tgt[1:]}")
            rows.append([m["name"], pin[0], tgt_txt, pin[2] if len(pin) > 2 else ""])
    M.table(["Module", "Module pin", "ESP32 connection", "Notes"], rows, [1.5, 1.2, 1.4, 2.6], "Pin connection table")
    M.h2("4.3 Interfacing and Power Notes")
    M.bullets(P["circuit"]["notes"] + [
        "Only ADC1 pins (GPIO32-39) are used for analog inputs, because ADC2 cannot be read while Wi-Fi is active.",
        "Strapping pins GPIO0, 2, 12 and 15 are avoided for inputs so the board always boots normally.",
        "All grounds are common. 5 V signals are reduced to 3.3 V with resistor dividers before reaching the ESP32."])

    # ---------------- 5 DFD
    M.h1("5. Data Flow Diagrams")
    M.p("Data flow diagrams (DFDs) show how data moves through the system without showing control logic or timing. "
        "External entities are drawn as rectangles, processes as numbered circles, data stores as open boxes and data "
        "flows as labelled arrows.")
    M.h2("5.1 DFD Level 0 (Context Diagram)")
    M.img(img["dfd0"], "DFD Level 0 — context diagram", w=6.4, maxh=5.0)
    M.p(f"At level 0 the whole {P['short']} is a single process. It receives {P['dfd']['raw']} from the "
        f"{P['dfd']['sensors']}, commands and configuration from the user's phone, and "
        f"{'commands from ' + cloud if P['dfd']['cloud_down'] else 'no commands from the cloud'}. It sends "
        f"{P['dfd']['act']} to the {P['dfd']['actuators']}, live data to the phone and {P['dfd']['cloud_up']} to {cloud}.")
    M.h2("5.2 DFD Level 1")
    M.img(img["dfd1"], "DFD Level 1 — main processes and data stores", w=6.6, maxh=6.2)
    D = P["dfd"]
    M.table(["Process / store", "Description"], [
        ["1.0 Acquire sensor data", f"Reads {D['raw']} from the {D['sensors']}; filters/averages the raw values."],
        ["2.0 Process & decide", f"Computes {D['derived']}; applies thresholds and rules; generates events."],
        ["3.0 Actuate & alert", f"Drives the {D['actuators']} ({D['act']})."],
        ["4.0 BLE communication", "Sends JSON frames and events to the phone; receives and authenticates commands."],
        ["5.0 Cloud sync", f"Sends {D['cloud_up']} to {cloud}" + (f"; receives {D['cloud_down']}." if D['cloud_down'] else ".")],
        ["D1 Settings (NVS)", "Wi-Fi credentials, cloud keys, PIN, thresholds — survive reboots."],
        [f"D2 {D['store3'][1]}", f"Stores {D['store3'][2]}; returns {D['store3'][3]}."],
    ], [1.9, 4.6], "Description of level-1 processes and data stores")
    M.h2("5.3 Data Dictionary")
    M.table(["Field", "Meaning", "Unit"], [list(x) for x in P["ble_data"]], [1.4, 3.8, 1.2],
            "BLE data frame fields")
    M.table(["Cloud object", "Content / usage"], [list(x) for x in P["cloud_items"]], [2.2, 4.3],
            f"{cloud} data objects")

    # ---------------- 6 Software
    M.h1("6. Software Design and Implementation")
    M.h2("6.1 Development Environment")
    M.table(["Item", "Details"], [
        ["IDE / build", "Arduino IDE 2.x or arduino-cli; GitHub Actions builds firmware in the cloud"],
        ["Board package", "esp32 by Espressif Systems 3.x (tested with 3.3.12)"],
        ["Board settings", "ESP32 Dev Module, Partition Scheme: Minimal SPIFFS (1.9MB APP with OTA/190KB SPIFFS)"],
        ["Common libraries", "NimBLE-Arduino 2.x, ArduinoJson 7.x, PubSubClient 2.8"],
        ["Project libraries", ", ".join(LIBS[pid]) if LIBS[pid] else "none beyond the common ones"],
        ["Phone app", "Web Bluetooth console (Chrome on Android / desktop, Bluefy on iPhone); nRF Connect as alternative"],
        ["Cloud", f"{cloud} (free tier)"],
    ], [1.6, 4.9], "Software tools")
    M.note("The default 1.2 MB app partition is too small for BLE + Wi-Fi + TLS. Select **Minimal SPIFFS (1.9MB APP)** "
           "in Tools → Partition Scheme, otherwise the upload fails with 'Sketch too big'.", "warn")
    M.h2("6.2 Firmware Architecture")
    M.p("The firmware is split into three layers so that the ten projects share tested code:")
    M.bullets(["**IoTCore.h** (shared) — Wi-Fi station with auto-reconnect, NimBLE GATT server with the Nordic UART "
               "Service, line-based command parser shared by BLE and USB serial, PIN authentication, settings in NVS "
               "(Preferences), NTP time in IST, JSON helpers.",
               "**Cloud.h** (shared) — ThingSpeak HTTPS client, Adafruit IO MQTT/TLS client with a 28 messages/minute "
               "rate limiter, Supabase PostgREST client (insert, update, select).",
               f"**{P['slug']}.ino** — sensor drivers, algorithms, automation rules and the project's own commands."])
    M.p("The main loop is non-blocking: every task is scheduled with millis() timers, BLE writes are queued from the BLE "
        "callback into a FreeRTOS queue and executed in loop(), so the BLE stack never waits for slow operations such as "
        "HTTPS requests.")
    M.h2("6.3 Working of the System")
    for t in P["working"]:
        M.p(t)
    M.h2("6.4 Flowchart")
    M.img(img["flow"], "Firmware flowchart", w=5.6, maxh=8.6)
    M.h2("6.5 BLE Communication Protocol")
    M.p("The device is a BLE peripheral named **IOT-" + pid + "-XXXX** (XXXX = last bytes of the MAC address). It exposes "
        "the Nordic UART Service, which most BLE apps understand:")
    M.table(["Item", "UUID", "Properties"], [
        ["Service (NUS)", "6E400001-B5A3-F393-E0A9-E50E24DCCA9E", "Primary"],
        ["RX — phone → ESP32", "6E400002-B5A3-F393-E0A9-E50E24DCCA9E", "Write, Write without response"],
        ["TX — ESP32 → phone", "6E400003-B5A3-F393-E0A9-E50E24DCCA9E", "Notify, Read"],
    ], [1.7, 3.3, 1.6], "GATT service and characteristics")
    M.p("Commands are plain text lines (`command:argument`). Replies are one JSON object per line ending in a newline; "
        "long lines are split into MTU-sized notifications and re-joined by the app. Commands that change anything "
        "require `auth:<PIN>` first on each connection (default PIN 1234, change it with `set:pin=XXXX`).")
    M.table(["Command", "PIN needed", "Action"], [
        ["auth:<PIN>", "—", "Unlock for this connection"], ["status", "No", "Status JSON: Wi-Fi, IP, RSSI, heap, uptime, time"],
        ["wifi:<SSID>,<password>", "Yes", "Save Wi-Fi credentials and connect"],
        ["set:<key>=<value>", "Yes", "Save a setting (cloud keys, thresholds)"], ["get:<key>", "Yes", "Read a setting (secrets masked)"],
        ["reboot / forget", "Yes", "Restart / erase all settings"]] + [list(c) for c in P["ble_cmds"]],
        [2.1, 0.9, 3.5], "BLE commands (common commands first, then project commands)")
    M.code([SAMPLES[pid]], "Example data frame sent by the device:")
    M.h2(f"6.6 Cloud Integration ({cloud})")
    if cloud == "ThingSpeak":
        M.p("Data is sent with an HTTPS GET request: `https://api.thingspeak.com/update?api_key=KEY&field1=…&status=…`. "
            "ThingSpeak returns the new entry number, or 0 if the update was rejected (for example when sent within 15 s "
            "of the previous one). The free licence allows 3 million messages per year and one update every 15 s per "
            "channel, so a 20 s interval leaves a safety margin.")
    elif cloud == "Adafruit IO":
        M.p("The device keeps a persistent MQTT connection to io.adafruit.com on port 8883 (TLS) using the account "
            "username and key. Values are published to `username/feeds/<feed-key>`, and control feeds are subscribed so "
            "dashboard changes arrive within about a second. A built-in limiter keeps the device below Adafruit IO's free "
            "limit of 30 data points per minute.")
    else:
        M.p("Supabase exposes every Postgres table through a REST API (PostgREST). The device sends HTTPS requests to "
            "`https://<project>.supabase.co/rest/v1/<table>` with the `apikey` and `Authorization: Bearer` headers: POST to "
            "insert rows, PATCH with a filter such as `?id=eq.1` to update and GET with `?select=` to read. Row Level "
            "Security policies (in cloud/supabase_schema.sql) allow the device key to do only what the project needs.")
    M.table(["Object", "Content"], [list(x) for x in P["cloud_items"]], [2.4, 4.1], f"{cloud} configuration")
    M.h2("6.7 Configurable Settings")
    M.table(["Key", "Default", "Meaning"], [list(x) for x in P["settings"]] +
            [["ssid / pass", "—", "Wi-Fi network (set with the wifi: command)"], ["pin", "1234", "BLE PIN"]],
            [1.6, 1.3, 3.6], "Settings stored in flash (change with set:key=value)")

    # ---------------- 7 Setup guide
    M.h1("7. Setup and Deployment Guide")
    M.h2("7.1 Hardware Assembly")
    M.numbers(["Place the ESP32 DevKit across the centre gap of the breadboard so both pin rows are free.",
               "Connect the ESP32 3V3 pin to one breadboard power rail (3.3 V), VIN to the other rail (5 V) and both GND "
               "pins to the ground rails.",
               "Wire each module exactly as in the pin connection table (section 4.2), including the resistor dividers "
               "marked with [n] in the circuit diagram.",
               "Check every connection against the circuit diagram before powering on. Make sure no 5 V signal reaches "
               "an ESP32 pin directly.",
               "Connect the USB cable to a computer (for flashing) or a 5 V adapter (for normal use)."])
    M.h2("7.2 Flashing the Firmware")
    M.h3("Option A — Arduino IDE")
    M.numbers(["Install Arduino IDE 2.x from arduino.cc.",
               "File → Preferences → Additional boards manager URLs: "
               "`https://espressif.github.io/arduino-esp32/package_esp32_index.json`.",
               "Tools → Board → Boards Manager: install **esp32 by Espressif Systems** (version 3.x).",
               "Sketch → Include Library → Manage Libraries: install **NimBLE-Arduino** (2.x), **ArduinoJson** (7.x), "
               "**PubSubClient**" + (", " + ", ".join(f"**{l}**" for l in LIBS[pid]) if LIBS[pid] else "") + ".",
               f"Download the repository and open the folder **{P['slug']}** (it already contains IoTCore.h, Cloud.h and config.h).",
               "Tools: Board **ESP32 Dev Module**, Partition Scheme **Minimal SPIFFS (1.9MB APP with OTA/190KB SPIFFS)**, "
               "Upload Speed 921600, and the correct COM port.",
               "Click Upload. If it stays at 'Connecting…', hold the BOOT button on the ESP32 until upload starts.",
               "Open Serial Monitor at 115200 baud and type `status` to check the device."])
    M.h3("Option B — no software installation (GitHub Actions + browser flasher)")
    M.numbers([f"Open the repository {REPO_URL} → **Actions** → latest **Build firmware** run.",
               f"Download the artifact **firmware-{P['slug']}** and unzip it to get `{P['slug']}.ino.merged.bin`.",
               "Open **https://espressif.github.io/esptool-js/** in Chrome or Edge on a computer, click **Connect** and "
               "select the ESP32's serial port.",
               "Set Flash Address **0x0**, choose the merged .bin file and click **Program**. Press the EN (reset) button "
               "when done."])
    M.h2(f"7.3 Cloud Setup ({cloud})")
    M.numbers(cloud_setup_steps(P))
    M.table(["Field / feed / table", "Content"], [list(x) for x in P["cloud_items"]], [2.4, 4.1],
            f"Items to create in {cloud}")
    M.h2("7.4 BLE App Setup (Web Bluetooth Console)")
    M.p("No app installation is needed. The console is a web page hosted free on GitHub Pages; Chrome talks to the ESP32 "
        "directly through the Web Bluetooth API.")
    M.numbers(["On an Android phone turn on **Bluetooth** and **Location** (Android requires location for BLE scanning).",
               f"Open **{CONSOLE_URL}?p={pid}** in **Chrome**. (On iPhone use the free **Bluefy** browser; on a laptop use "
               "Chrome or Edge.)",
               f"Tap **Connect** and choose **IOT-{pid}-XXXX** in the pop-up list. The dot turns green and the Live tab "
               "starts updating.",
               "Open **Setup**, enter the PIN (default **1234**) and tap **Unlock**.",
               "Enter your 2.4 GHz Wi-Fi name and password and tap **Save Wi-Fi**. After a few seconds the status line shows "
               "the IP address.",
               f"Enter the {cloud} keys from section 7.3 and tap **Save** next to each.",
               "Use the **Control** tab for commands and the **Log** tab to see every event and acknowledgement."])
    M.h3("Alternative: nRF Connect app")
    M.numbers(["Install **nRF Connect for Mobile** (Nordic Semiconductor, free) and scan.",
               f"Connect to **IOT-{pid}-XXXX** and open **Nordic UART Service**.",
               "Enable notifications on the **TX** characteristic (6E400003…).",
               "Write UTF-8 text to the **RX** characteristic (6E400002…), e.g. `auth:1234`, then `status`."])
    M.note("To host the console yourself: in the GitHub repository open Settings → Pages, choose 'Deploy from a branch', "
           "branch main, folder /docs. Web Bluetooth only works on HTTPS pages, which GitHub Pages provides.")
    M.h2("7.5 First-Run Checklist")
    M.bullets(["Serial Monitor shows '[BLE] advertising as IOT-" + pid + "-XXXX'.",
               "Status in the console shows wifi: true and an IP address.",
               f"Data appears in {cloud} within a minute.",
               "All sensor values in the Live tab are plausible (no '—')."])

    # ---------------- 8 Testing
    M.h1("8. Testing and Results")
    M.p("The following test cases verify each function. Record the observed result and mark Pass/Fail while testing "
        "your build.")
    M.table(["#", "Test", "Procedure", "Expected result", "Observed"],
            [[f"T{i}", t[0], t[1], t[2], ""] for i, t in enumerate(P["tests"], 1)],
            [0.4, 1.2, 2.1, 2.1, 0.8], "Test cases")
    M.h2("8.1 Expected Output")
    M.p("A typical data frame received in the console's Log tab looks like this (values will differ):")
    M.code([SAMPLES[pid]])
    M.p("Serial Monitor (115200 baud) prints the same lines along with connection messages such as `[WiFi] connected`, "
        "`[BLE] connected` and the HTTP or MQTT result of each cloud upload, which helps in troubleshooting.")
    M.h2("8.2 Troubleshooting")
    M.table(["Symptom", "Likely cause and fix"], [
        ["Device not in the Connect list", "Bluetooth/Location off on the phone, or the page is not opened in Chrome over HTTPS."],
        ["'Sketch too big' on upload", "Select Partition Scheme 'Minimal SPIFFS (1.9MB APP with OTA)'."],
        ["Wi-Fi never connects", "ESP32 supports only 2.4 GHz networks; check the SSID/password (case-sensitive)."],
        ["Settings refused", "Send auth:<PIN> first; the unlock is per BLE connection."],
        ["Sensor shows null / —", "Check wiring and supply voltage; see the Serial Monitor for 'not found' messages."],
        ["Board resets randomly", "Weak USB supply or servo/relay current; use a 5 V 2 A adapter and add a 470 µF capacitor."],
        [f"No data in {cloud}", {"ThingSpeak": "Wrong Write API Key or interval below 15 s.",
                                 "Adafruit IO": "Wrong username/key, rate limit exceeded or 10-feed limit reached.",
                                 "Supabase": "Wrong URL/key, schema not run, or project paused after inactivity."}[cloud]],
    ], [2.0, 4.5], "Troubleshooting guide")

    # ---------------- 9 Discussion
    M.h1("9. Discussion")
    M.h2("9.1 Advantages"); M.bullets(P["advantages"])
    M.h2("9.2 Limitations"); M.bullets(P["limitations"])
    M.h2("9.3 Safety Precautions"); M.bullets(P["safety"])
    M.h2("9.4 Security Considerations")
    M.bullets(["Secrets (Wi-Fi password, cloud keys) are stored in the ESP32's NVS flash, not in source code.",
               "BLE commands that change the device require a PIN; change the default PIN after setup.",
               "Cloud traffic is TLS-encrypted. Certificate verification is disabled (setInsecure) for simplicity; for "
               "production, pin the server's root certificate with setCACert().",
               "Use a dedicated cloud account/project for the device and rotate keys if the device is lost."])
    M.h2("9.5 Future Scope"); M.bullets(P["future"])

    # ---------------- 10 Conclusion
    M.h1("10. Conclusion")
    M.p(P["conclusion"])
    M.p("All design goals listed in Chapter 1 are met with low-cost parts available in the Indian market, free cloud "
        "services and open-source software. The shared firmware core and the single Web Bluetooth console make the "
        "project easy to reproduce and extend.")

    # ---------------- References
    M.h1("References")
    refs = P["refs"] + [
        "Espressif Systems, ESP32 Series Datasheet and ESP32 Technical Reference Manual, espressif.com.",
        "Espressif Systems, Arduino-ESP32 documentation, docs.espressif.com/projects/arduino-esp32.",
        "H2zero, NimBLE-Arduino library documentation, github.com/h2zero/NimBLE-Arduino.",
        "Bluetooth SIG, Bluetooth Core Specification 4.2 — Generic Attribute Profile (GATT).",
        "W3C Web Bluetooth Community Group, Web Bluetooth specification, webbluetoothcg.github.io/web-bluetooth.",
        "B. Blanchon, ArduinoJson 7 documentation, arduinojson.org.",
        {"ThingSpeak": "MathWorks, ThingSpeak documentation — Write data with REST API, mathworks.com/help/thingspeak.",
         "Adafruit IO": "Adafruit Industries, Adafruit IO documentation and MQTT API, io.adafruit.com/api/docs.",
         "Supabase": "Supabase Inc., Supabase documentation — REST API and Row Level Security, supabase.com/docs."}[cloud],
    ]
    M.numbers(refs)

    # ---------------- Appendices
    M.h1("Appendix A: Project Source Code")
    M.p(f"The complete code is in the repository folder **{P['slug']}** ({REPO_URL}).")
    for fn in ("config.h", f"{P['slug']}.ino"):
        M.code(open(os.path.join(ROOT, P["slug"], fn), encoding="utf-8").read().rstrip("\n").split("\n"), fn)
    M.h1("Appendix B: Shared Library Code")
    M.p("These two headers are identical in every project folder (master copies in /common).")
    for fn in ("IoTCore.h", "Cloud.h"):
        M.code(open(os.path.join(ROOT, "common", fn), encoding="utf-8").read().rstrip("\n").split("\n"), fn)
    return M, toc_index


# ===================================================================== build
def render(M, toc_index, P, out_docx, pages=None):
    entries = [{"level": lvl, "text": txt, "page": (pages or {}).get(i, "")} for i, (lvl, txt) in enumerate(M.toc)]
    M.blocks[toc_index] = {"t": "toc", "entries": entries}
    model = {"meta": {"title": P["title"], "description": P["abstract"][:200], "author": "ESP32 IoT Projects",
                      "header": f"{P['id']} · {P['title']}", "headerRight": "ESP32 IoT Projects"},
             "blocks": M.blocks}
    mp = out_docx.replace(".docx", ".model.json")
    json.dump(model, open(mp, "w", encoding="utf-8"), ensure_ascii=False)
    subprocess.run(["node", os.path.join(ROOT, "tools", "build_docx.js"), mp, out_docx], check=True,
                   stdout=subprocess.DEVNULL)
    os.remove(mp)


def to_pdf(docx, outdir):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", outdir, docx], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return docx.replace(".docx", ".pdf")


def find_pages(pdf, toc):
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
    texts = []
    for pg in range(1, n + 1):
        t = subprocess.run(["pdftotext", "-f", str(pg), "-l", str(pg), "-layout", pdf, "-"], capture_output=True, text=True).stdout
        texts.append(re.sub(r"\s+", " ", t))
    norm = lambda s: re.sub(r"\s+", " ", s).strip()
    pages, start = {}, 0
    # skip title, certificate and contents pages: start after the page whose text has "Contents"
    for i, t in enumerate(texts):
        if "Contents" in t[:200]:
            start = i + 1
    while start < n and "Abstract" not in texts[start][:300]:
        start += 1
    cur = start
    for idx, (lvl, txt) in enumerate(toc):
        key = norm(txt)[:38]
        for pg in range(cur, n):
            if key in texts[pg]:
                pages[idx] = pg + 1; cur = pg; break
    return pages


def build(P):
    out = os.path.join(ROOT, "reports", P["slug"])
    imgdir = os.path.join(out, "images")
    img = make_images(P, imgdir)
    M, toc_index = build_model(P, img)
    docx = os.path.join(out, f"{P['slug']}_Report.docx")
    render(M, toc_index, P, docx)                      # pass 1 (no page numbers)
    pdf = to_pdf(docx, out)
    pages = find_pages(pdf, M.toc)
    render(M, toc_index, P, docx, pages)               # pass 2 with page numbers
    pdf = to_pdf(docx, out)
    missing = [M.toc[i][1] for i in range(len(M.toc)) if i not in pages]
    print(f"{P['id']}: {docx}  pages found {len(pages)}/{len(M.toc)}" + (f" missing {missing}" if missing else ""))


if __name__ == "__main__":
    want = set(sys.argv[1:])
    for P in PROJECTS_A + PROJECTS_B:
        if not want or P["id"] in want:
            build(P)
