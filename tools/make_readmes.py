# -*- coding: utf-8 -*-
"""Writes a short README.md into every project folder from the project specs."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from projects_a import PROJECTS_A
from projects_b import PROJECTS_B
from build_reports import LIBS, CONSOLE_URL, SAMPLES

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for P in PROJECTS_A + PROJECTS_B:
    total = sum(c[3] for c in P["components"])
    L = [f"# {P['id']} — {P['title']}", "",
         f"**Cloud:** {P['cloud']} · **Level:** {P['level']} · **Approx. cost:** ₹{total} (incl. ESP32, breadboard, cable)", "",
         P["abstract"], "",
         f"📄 Full report: [`reports/{P['slug']}/{P['slug']}_Report.pdf`](../reports/{P['slug']}/{P['slug']}_Report.pdf) "
         f"(also `.docx`) — circuit diagram, DFD level 0/1, flowchart, setup steps, test cases, source listing.", "",
         "## Wiring", "", "| Module | Pin | ESP32 | Note |", "|---|---|---|---|"]
    for m in P["circuit"]["modules"]:
        for pin in m["pins"]:
            t = {"5V": "5V (VIN)", "3V3": "3V3", "GND": "GND"}.get(pin[1], f"GPIO{pin[1][1:]}")
            L.append(f"| {m['name']} | {pin[0]} | {t} | {pin[2] if len(pin) > 2 else ''} |")
    L += ["", f"![circuit](../reports/{P['slug']}/images/{P['id']}_circuit.png)", "",
          "## Build & flash", "",
          "* Arduino IDE: board **ESP32 Dev Module**, Partition Scheme **Minimal SPIFFS (1.9MB APP with OTA)**.",
          "* Libraries: NimBLE-Arduino 2.x, ArduinoJson 7.x, PubSubClient" + (", " + ", ".join(LIBS[P['id']]) if LIBS[P['id']] else "") + ".",
          f"* Or download `firmware-{P['slug']}` from GitHub **Actions** and flash `*.merged.bin` at `0x0` with https://espressif.github.io/esptool-js/.",
          "", "## Configure over BLE", "",
          f"Open **{CONSOLE_URL}?p={P['id']}** in Chrome (Android/desktop) → Connect → `IOT-{P['id']}-XXXX` → Setup → PIN `1234` → Wi-Fi → cloud keys.", "",
          "| Setting | Default | Meaning |", "|---|---|---|"]
    L += [f"| `{k}` | {d} | {m} |" for k, d, m in P["settings"]]
    L += ["", "| Command | PIN | Action |", "|---|---|---|"]
    L += [f"| `{c}` | {a} | {m} |" for c, a, m in P["ble_cmds"]]
    L += ["", "Example frame:", "", "```json", SAMPLES[P["id"]], "```", "",
          f"## {P['cloud']} objects", "", "| Object | Content |", "|---|---|"]
    L += [f"| {a} | {b} |" for a, b in P["cloud_items"]]
    if P["safety"]:
        L += ["", "## Safety", ""] + [f"* {s}" for s in P["safety"]]
    open(os.path.join(ROOT, P["slug"], "README.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("README", P["id"])
