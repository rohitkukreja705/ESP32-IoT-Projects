# -*- coding: utf-8 -*-
"""Project specifications P01-P05: hardware, text, DFDs, flowcharts, tests."""

COMMON_PARTS = [
    ("ESP32 DevKit V1 (ESP-WROOM-32, 30-pin)", 1, "Dual-core 240 MHz, Wi-Fi + BLE, 4 MB flash", 350),
    ("Breadboard 830-point + jumper wires (M-M, M-F)", 1, "Prototyping and connections", 150),
    ("Micro-USB data cable", 1, "Power + programming", 60),
]

P01 = dict(
    id="P01", slug="P01_Smart_Weather_Station",
    title="Smart Weather Station with Rain Forecast",
    short="Smart Weather Station",
    cloud="ThingSpeak", level="Intermediate",
    peripherals=["DHT11", "BMP180", "LDR", "FC-37 rain sensor"],
    abstract=(
        "This project builds a low-cost, connected weather station around the ESP32 microcontroller. A DHT11 sensor "
        "measures air temperature and relative humidity, a BMP180 barometer measures atmospheric pressure, a light-"
        "dependent resistor (LDR) measures ambient light and an FC-37 rain plate detects rainfall. The ESP32 derives "
        "heat index and dew point, keeps a three-hour history of pressure and turns the pressure trend into a short-term "
        "forecast, using rules similar to the classical Zambretti forecaster. Readings are uploaded every 20 seconds over "
        "Wi-Fi to ThingSpeak, a free MATLAB-backed IoT cloud that stores the data and draws charts. At the same time the "
        "station acts as a Bluetooth Low Energy (BLE) peripheral, so a phone can show live values, change settings and "
        "configure Wi-Fi without any internet connection. The complete bill of materials costs well under ₹1,000."),
    problem=(
        "Local weather can differ a lot from the city-level forecast shown by phone apps, which matters for farmers, "
        "gardeners, schools and small businesses. Commercial weather stations with data logging and online access "
        "cost several thousand rupees and use closed apps. There is a need for an affordable, open station that measures "
        "the local microclimate, keeps a history, gives a simple rain warning and can be viewed both on site and remotely."),
    objectives=[
        "Measure temperature, humidity, pressure, light intensity and rain with low-cost sensors.",
        "Compute derived values: heat index, dew point and a 3-hour pressure-trend forecast.",
        "Publish all values to a free cloud dashboard (ThingSpeak) for remote monitoring and history.",
        "Provide a BLE interface for live data, Wi-Fi provisioning and configuration without internet.",
        "Raise rain-start and rain-stop events immediately on both channels.",
        "Keep the total hardware cost below ₹1,000 using parts available in the Indian market.",
    ],
    scope=(
        "The station is intended for homes, school labs, terraces, greenhouses and farms. It covers indoor and sheltered "
        "outdoor use; for permanent outdoor use the electronics must be placed in a ventilated radiation shield (Stevenson "
        "screen) with only the rain plate exposed. Wind speed and direction are outside the scope of this version."),
    existing=(
        "Typical hobby weather stations either show values only on a local LCD or upload to the cloud without any local "
        "access, so they become useless when the internet is down and need the Wi-Fi password to be hard-coded into the "
        "firmware. Most also report raw readings only."),
    proposed=[
        "Dual connectivity: BLE for local access and setup, Wi-Fi for cloud logging; each works without the other.",
        "Wi-Fi credentials and the ThingSpeak key are entered from the phone and stored in flash, not in source code.",
        "Value-added data: heat index, dew point and a pressure-trend forecast instead of raw numbers only.",
        "Event-driven upload: an immediate upload when rain starts or stops, in addition to the periodic one.",
    ],
    components=COMMON_PARTS + [
        ("DHT11 temperature & humidity module", 1, "0-50 °C ±2 °C, 20-90 % RH ±5 %", 60),
        ("BMP180 barometric pressure module (GY-68)", 1, "300-1100 hPa, I2C, 3.3 V", 80),
        ("LDR 5 mm + 10 kΩ resistor", 1, "Light-dependent resistor in a divider", 10),
        ("FC-37 / YL-83 rain sensor with LM393 board", 1, "Analog + digital output", 60),
    ],
    circuit=dict(
        title="P01 Smart Weather Station — Circuit Diagram",
        modules=[
            dict(name="LDR + 10 kΩ", sub="Light sensor (voltage divider)",
                 pins=[("LDR end", "3V3"), ("Junction", "G34", "LDR from 3.3 V to GPIO34, 10 kΩ from GPIO34 to GND"), ("10k end", "GND")]),
            dict(name="FC-37 Rain", sub="Rain plate + LM393 board",
                 pins=[("VCC", "3V3"), ("AO", "G35"), ("DO", "G27"), ("GND", "GND")]),
            dict(name="DHT11", sub="Temperature & humidity",
                 pins=[("VCC", "3V3"), ("DATA", "G4"), ("GND", "GND")]),
            dict(name="BMP180", sub="Pressure, I2C address 0x77",
                 pins=[("VIN", "3V3"), ("SDA", "G21"), ("SCL", "G22"), ("GND", "GND")]),
        ],
        notes=["Every module runs from 3.3 V, so no level shifting is needed.",
               "GPIO34/35 are on ADC1, which keeps working while Wi-Fi is active (ADC2 does not).",
               "The on-board LED (GPIO2) shows status: solid = Wi-Fi up, blinking = BLE connected."],
    ),
    principles=[
        ("DHT11", "A capacitive humidity element and an NTC thermistor are read by a small on-board controller that "
                  "sends a 40-bit frame (humidity, temperature, checksum) over a single-wire protocol. The ESP32 starts a "
                  "reading by pulling the line low for 18 ms. The sensor allows one reading per second."),
        ("BMP180", "A piezo-resistive MEMS pressure element with an on-chip ADC and factory calibration coefficients "
                   "stored in EEPROM. The Adafruit library reads the coefficients over I2C and applies Bosch's "
                   "compensation formula to give pressure in pascals; the firmware converts it to hPa."),
        ("LDR", "Cadmium-sulphide resistance falls from about 1 MΩ in darkness to a few kΩ in bright light. With the "
                "LDR on the high side of a 10 kΩ divider, more light raises the voltage at GPIO34, which the 12-bit ADC "
                "reads in millivolts and scales to 0-100 %."),
        ("FC-37 rain sensor", "Interleaved copper tracks act as a variable resistor: water bridges the tracks and "
                              "lowers the resistance. The LM393 board gives an analog voltage (lower = wetter) and a "
                              "digital output that goes LOW above a threshold set by its potentiometer."),
    ],
    working=[
        "After power-up the firmware starts BLE advertising as IOT-P01-xxxx and tries the saved Wi-Fi network. Every two "
        "seconds it reads all sensors, averages 16 ADC samples for the analog channels and calculates heat index "
        "(Rothfusz regression, through the DHT library) and dew point using the Magnus formula: γ = ln(RH/100) + "
        "17.62·T/(243.12+T), Td = 243.12·γ/(17.62−γ).",
        "Every 10 minutes the pressure is stored in a ring buffer of 18 samples (3 hours). The change between the oldest "
        "and newest sample, scaled to three hours, is classified: a fall of 3 hPa or more means storm or heavy rain is "
        "likely, a fall of 1.6 hPa means rain is likely, a steady value means stable weather and a rising value means "
        "improving weather. This is a simplified version of the rules used by barometric forecasters.",
        "The live JSON frame is notified over BLE every two seconds. Every 20 seconds (configurable, minimum 15 s because "
        "of the ThingSpeak free-tier limit) the eight values are sent to ThingSpeak fields 1-8 with the forecast as the "
        "status text. When the rain state changes, an event is sent over BLE and an immediate upload is scheduled.",
    ],
    ble_data=[("t", "Temperature", "°C"), ("h", "Relative humidity", "%"), ("p", "Pressure", "hPa"),
              ("l", "Light level", "%"), ("rn", "Rain wetness", "%"), ("hi", "Heat index", "°C"),
              ("dp", "Dew point", "°C"), ("fc", "Forecast text", "—"), ("wifi", "Wi-Fi connected", "bool")],
    ble_cmds=[("read", "No", "Read the sensors now and send a data frame"),
              ("upload", "No", "Upload to ThingSpeak as soon as the 15 s limit allows")],
    settings=[("tskey", "—", "ThingSpeak Write API Key"), ("tsint", "20", "Upload interval in seconds (≥ 15)"),
              ("rainthr", "30", "Rain threshold in % wetness")],
    cloud_items=[("Field 1", "Temperature (°C)"), ("Field 2", "Humidity (%)"), ("Field 3", "Pressure (hPa)"),
                 ("Field 4", "Light (%)"), ("Field 5", "Rain (%)"), ("Field 6", "Heat index (°C)"),
                 ("Field 7", "Dew point (°C)"), ("Field 8", "Wi-Fi RSSI (dBm)"), ("Status", "Forecast text")],
    dfd=dict(
        sensors="Weather sensors (DHT11, BMP180, LDR, rain plate)", raw="T, RH, pressure, light, rain",
        actuators="Status LED", act="status pattern",
        store3=("D3", "Pressure history (3 h ring buffer)", "pressure every 10 min", "trend"),
        cloud_up="8 fields + forecast every 20 s", cloud_down=None,
        derived="heat index, dew point, forecast",
    ),
    flow=dict(
        nodes=[("s", "start", "Power on"), ("i", "process", "Init BLE, Wi-Fi, DHT11, BMP180, ADC"),
               ("l", "process", "iot::loop(): Wi-Fi reconnect, handle BLE/USB commands"),
               ("d1", "decision", "2 s elapsed?"), ("r", "io", "Read DHT11, BMP180, LDR, rain"),
               ("c", "process", "Compute heat index, dew point"),
               ("rd", "decision", "Rain state changed?"), ("ev", "process", "Send rain event, force upload"),
               ("b", "io", "Notify JSON frame over BLE"),
               ("d2", "decision", "10 min elapsed?"), ("pt", "process", "Store pressure, update forecast"),
               ("d3", "decision", "Upload due and Wi-Fi up?"), ("u", "io", "HTTPS update to ThingSpeak")],
        edges=[("s", "i"), ("i", "l"), ("l", "d1"), ("d1", "r", "yes"), ("d1", "d2", "no"), ("r", "c"),
               ("c", "rd"), ("rd", "ev", "yes"), ("rd", "b", "no"), ("ev", "b"), ("b", "d2"),
               ("d2", "pt", "yes"), ("d2", "d3", "no"), ("pt", "d3"), ("d3", "u", "yes"),
               ("d3", "l", "no", ", constraint=false"), ("u", "l", "", ", constraint=false")],
    ),
    tests=[
        ("Sensor read", "Open Serial Monitor at 115200 and send 'read'", "Plausible T, RH, pressure (≈ 950-1020 hPa in most of India)"),
        ("Light response", "Cover the LDR, then shine a phone torch on it", "Light % drops below 20 then rises above 80"),
        ("Rain detection", "Put a few drops of water on the rain plate", "Rain % rises, 'rain_start' event appears in the app log"),
        ("BLE provisioning", "Connect from the web console, unlock with PIN, save Wi-Fi", "Status shows Wi-Fi connected with an IP address"),
        ("Cloud upload", "Wait 1 minute after Wi-Fi connects", "New entries appear in the ThingSpeak channel charts"),
        ("Offline behaviour", "Switch off the router", "BLE data continues; uploads resume automatically when Wi-Fi returns"),
        ("Wrong PIN", "Send auth:0000 then set:tsint=30", "Device replies 'wrong PIN' and refuses the setting"),
    ],
    advantages=["Very low cost; every part is easily available in India.",
                "Works locally over BLE even with no internet.",
                "No credentials in source code; configured from a phone.",
                "Free cloud storage with charts and a public view option.",
                "Gives a simple forecast, not just raw numbers."],
    limitations=["DHT11 accuracy is ±2 °C / ±5 % RH; a DHT22 or BME280 gives better results.",
                 "The resistive rain plate corrodes over months; a capacitive rain sensor lasts longer.",
                 "The forecast uses pressure trend only and needs at least one hour of data.",
                 "Wind and rainfall quantity (mm) are not measured."],
    future=["Add an anemometer and tipping-bucket rain gauge for wind and rainfall in mm.",
            "Replace DHT11 + BMP180 with a single BME280 for better accuracy.",
            "Run on a solar panel and Li-ion cell with deep sleep between readings.",
            "Use ThingSpeak MATLAB Analysis to send email alerts on heavy-rain prediction."],
    safety=["Keep the ESP32 and DHT11 inside a ventilated, rain-proof enclosure; expose only the rain plate.",
            "Power the rain plate only when reading it (or use a capacitive sensor) to slow corrosion."],
    conclusion=(
        "The Smart Weather Station shows that a useful, connected weather instrument can be built for under ₹1,000. "
        "By combining BLE and Wi-Fi it stays useful when the internet is unavailable, and the derived values and "
        "pressure-trend forecast make the data meaningful to non-technical users. The modular firmware and free cloud "
        "back-end make the system easy to extend with more sensors or a solar power supply."),
    refs=["Aosong, DHT11 Humidity & Temperature Sensor datasheet.",
          "Bosch Sensortec, BMP180 Digital Pressure Sensor datasheet (BST-BMP180-DS000).",
          "Alduchov, O. A. & Eskridge, R. E. (1996), Improved Magnus form approximation of saturation vapor pressure, J. Applied Meteorology.",
          "Rothfusz, L. P. (1990), The Heat Index Equation, NWS Technical Attachment SR 90-23."],
)

P02 = dict(
    id="P02", slug="P02_Smart_Energy_Monitor",
    title="Smart Energy Monitor with Overload Protection",
    short="Smart Energy Monitor",
    cloud="Adafruit IO", level="Advanced",
    peripherals=["ACS712-5A current sensor", "ZMPT101B voltage sensor", "16x2 I2C LCD", "1-channel relay"],
    abstract=(
        "This project measures the electrical consumption of a single AC appliance and protects it from overload. A "
        "ZMPT101B transformer module senses the 230 V mains voltage and an ACS712-5A Hall-effect module senses the load "
        "current. The ESP32 samples both channels together at 10 kHz for ten mains cycles and computes true RMS voltage, "
        "true RMS current, real power, apparent power and power factor, then integrates real power into kilowatt-hours "
        "and an estimated electricity cost in rupees. A 16x2 LCD shows the values locally and a relay can disconnect the "
        "load. The relay trips automatically when power stays above a set limit. Data is published to Adafruit IO over "
        "MQTT, where a dashboard shows gauges and charts and a toggle switches the load remotely. Over BLE the same data, "
        "relay control and a two-point calibration routine are available on a phone."),
    problem=(
        "Households and small shops in India pay slab-based electricity tariffs but have no way to see which appliance "
        "uses how much energy. Faulty or overloaded appliances (heaters, motors, irons) waste energy and can cause fires. "
        "Commercial smart plugs with energy metering are costly, cloud-locked and often inaccurate at low loads."),
    objectives=[
        "Measure true RMS voltage and current of an AC load and compute real power and power factor.",
        "Accumulate energy (kWh) persistently and estimate cost using a configurable tariff.",
        "Switch the load ON/OFF locally (BLE), remotely (Adafruit IO) and automatically on overload.",
        "Display live values on a 16x2 LCD without needing a phone.",
        "Provide an in-field calibration procedure using a reference multimeter.",
    ],
    scope=(
        "Single-phase loads up to about 1 kW (5 A sensor; relay rated 10 A). The design is for education and "
        "monitoring, not for billing. Three-phase systems and bidirectional (solar export) metering are out of scope."),
    existing=(
        "Simple Arduino energy meters usually measure only current and assume a fixed 230 V and unity power factor, "
        "which overestimates the energy of inductive loads such as fans and motors. They rarely include protection or "
        "remote switching, and smart plugs that do are closed products."),
    proposed=[
        "Simultaneous V and I sampling gives real power and power factor, not just V×I.",
        "Overload protection with a 3-second delay to ignore inrush current.",
        "kWh counter saved to flash every 5 minutes so it survives power cuts.",
        "Two-point software calibration from the phone; no code change needed.",
        "Remote switching from the Adafruit IO dashboard and local switching over BLE.",
    ],
    components=COMMON_PARTS + [
        ("ACS712-5A current sensor module", 1, "±5 A, 185 mV/A, Hall-effect, isolated", 120),
        ("ZMPT101B AC voltage sensor module", 1, "0-250 V AC, isolated transformer + op-amp", 140),
        ("16x2 LCD with PCF8574 I2C backpack", 1, "I2C address 0x27 / 0x3F", 180),
        ("1-channel 5 V relay module (10 A)", 1, "Opto-isolated, active-LOW input", 50),
        ("Resistors 10 kΩ + 20 kΩ (2 × 10 kΩ)", 1, "Divider for ACS712 output", 5),
        ("Fuse holder + 5 A fuse, 2-pin socket, plastic enclosure", 1, "Mains safety", 150),
    ],
    circuit=dict(
        title="P02 Smart Energy Monitor — Circuit Diagram (low-voltage side)",
        modules=[
            dict(name="ACS712-5A", sub="Current sensor (in series with load)",
                 pins=[("VCC", "5V"), ("OUT", "G34", "ACS712 OUT -> 10 kΩ -> GPIO34; GPIO34 -> 20 kΩ -> GND (5 V to 3.3 V scaling)"), ("GND", "GND")],
                 outer=["IP+ / IP- in series with the load (mains)"]),
            dict(name="ZMPT101B", sub="Voltage sensor (parallel to mains)",
                 pins=[("VCC", "3V3"), ("OUT", "G35"), ("GND", "GND")],
                 outer=["Screw terminals to L and N (mains)"]),
            dict(name="Relay (1-ch)", sub="Load switch, active LOW",
                 pins=[("VCC", "5V"), ("IN", "G26"), ("GND", "GND")],
                 outer=["COM / NO switch the load's Live wire"]),
            dict(name="LCD 16x2 + I2C", sub="PCF8574 backpack, 0x27",
                 pins=[("VCC", "5V"), ("SDA", "G21"), ("SCL", "G22"), ("GND", "GND")]),
        ],
        notes=["Mains path: Live -> 5 A fuse -> ACS712 IP+ -> IP- -> relay COM -> NO -> load -> Neutral. ZMPT101B input across L and N.",
               "Keep all 230 V wiring inside a closed enclosure, away from the low-voltage side.",
               "Turn the ZMPT101B trimmer so its output does not clip, then calibrate with calv:<multimeter volts>."],
    ),
    principles=[
        ("ACS712-5A", "Current through a copper conductor inside the IC creates a magnetic field that a Hall sensor "
                      "converts to voltage: Vout = 2.5 V + 0.185 V/A × I. The conductor is isolated from the sensing "
                      "circuit (2.1 kV RMS), so the low-voltage side is safe. Because the output can reach 3.4 V, a "
                      "10 kΩ/20 kΩ divider scales it by 2/3 for the 3.3 V ESP32 ADC."),
        ("ZMPT101B", "A small precision current transformer with a series resistor works as a voltage transformer. An "
                     "LM358 op-amp amplifies the secondary signal and centres it at VCC/2. The output is an AC waveform "
                     "proportional to mains voltage; the gain is set with a trimmer and fine-tuned in software."),
        ("Relay module", "An opto-coupler drives a transistor that energises the relay coil. A LOW input switches the "
                         "relay ON (active-LOW), and the contacts (10 A 250 V AC) connect or break the load's live wire."),
        ("I2C LCD", "A PCF8574 I/O expander converts the two-wire I2C bus into the eight data/control lines of an "
                    "HD44780 16x2 character LCD, saving GPIO pins."),
    ],
    working=[
        "Every second the firmware captures 2,000 sample pairs (voltage and current) in 200 ms, i.e. ten full 50 Hz "
        "cycles at a 10 kHz pair rate. The mean of each channel is the DC offset and is subtracted. Then "
        "Vrms = √(Σv²/N), Irms = √(Σi²/N) and real power P = Σ(v·i)/N, each multiplied by its calibration factor. "
        "Apparent power S = Vrms·Irms and power factor PF = P/S.",
        "Energy is integrated as E += P·Δt and stored in NVS every five minutes. Cost = kWh × tariff (default ₹7/kWh). "
        "If P exceeds the limit (default 1,000 W) for three consecutive seconds the relay opens and an 'overload' event "
        "is raised; the short delay avoids false trips from motor inrush current.",
        "Four feeds (voltage, current, power, energy) are published to Adafruit IO every 15 seconds (16 messages per "
        "minute, under the 30/minute free limit). The firmware subscribes to the p02-relay feed, so a toggle block on the "
        "dashboard switches the load. The LCD alternates between a V/A/W page and a PF/kWh/₹ page.",
    ],
    ble_data=[("v", "RMS voltage", "V"), ("i", "RMS current", "A"), ("w", "Real power", "W"),
              ("va", "Apparent power", "VA"), ("pf", "Power factor", "—"), ("kwh", "Energy", "kWh"),
              ("cost", "Cost", "₹"), ("relay", "Relay state", "bool"), ("cloud", "MQTT connected", "bool")],
    ble_cmds=[("relay:on / relay:off", "Yes", "Switch the load"), ("reset", "Yes", "Reset kWh counter"),
              ("calv:<volts>", "Yes", "Calibrate voltage against a multimeter reading"),
              ("cali:<amps>", "Yes", "Calibrate current against a clamp-meter reading")],
    settings=[("aiouser / aiokey", "—", "Adafruit IO username and key"), ("maxw", "1000", "Overload trip limit (W)"),
              ("tariff", "7", "Electricity tariff (₹/kWh)"), ("vcal / ical", "0.70 / 0.00811", "Calibration factors (set by calv/cali)")],
    cloud_items=[("p02-voltage", "Voltage (V) — line chart / gauge"), ("p02-current", "Current (A) — gauge"),
                 ("p02-power", "Real power (W) — line chart"), ("p02-energy", "Energy (kWh) — text block"),
                 ("p02-relay", "Toggle block, ON/OFF values — remote load switch")],
    dfd=dict(
        sensors="Mains sensors (ZMPT101B, ACS712)", raw="voltage & current waveforms",
        actuators="Relay + LCD", act="ON/OFF, display text",
        store3=("D3", "Energy counter (kWh in NVS)", "kWh every 5 min", "saved kWh at boot"),
        cloud_up="V, I, W, kWh feeds", cloud_down="relay toggle",
        derived="Vrms, Irms, P, PF, kWh, cost",
    ),
    flow=dict(
        nodes=[("s", "start", "Power on"), ("i", "process", "Init BLE, Wi-Fi, LCD, relay ON, load kWh"),
               ("l", "process", "Service Wi-Fi, MQTT and BLE commands"),
               ("d1", "decision", "1 s elapsed?"),
               ("m", "io", "Sample V & I 2000 pairs (200 ms)"),
               ("c", "process", "Remove offset; compute Vrms, Irms, P, S, PF; add kWh"),
               ("o", "decision", "P > limit for 3 s?"), ("t", "process", "Open relay, overload event"),
               ("u", "io", "Update LCD, notify BLE"),
               ("d2", "decision", "15 s & MQTT up?"), ("p", "io", "Publish V, I, W, kWh"),
               ("d3", "decision", "5 min elapsed?"), ("sv", "process", "Save kWh to flash")],
        edges=[("s", "i"), ("i", "l"), ("l", "d1"), ("d1", "m", "yes"), ("d1", "d2", "no"), ("m", "c"), ("c", "o"),
               ("o", "t", "yes"), ("o", "u", "no"), ("t", "u"), ("u", "d2"), ("d2", "p", "yes"), ("d2", "d3", "no"),
               ("p", "d3"), ("d3", "sv", "yes"), ("d3", "l", "no", ", constraint=false"), ("sv", "l", "", ", constraint=false")],
    ),
    tests=[
        ("No-load reading", "Power the meter with the load switched off", "Voltage ≈ mains value, current 0 A, power 0 W"),
        ("Calibration", "Measure mains with a multimeter, send calv:<value>", "Displayed voltage matches the multimeter within ±2 %"),
        ("Resistive load", "Connect a 100 W bulb or 1 kW heater", "Power ≈ rated value, PF ≈ 0.95-1.0"),
        ("Inductive load", "Connect a table fan", "PF clearly below 1 (typ. 0.7-0.9)"),
        ("Overload trip", "Set maxw=50 and connect a 100 W load", "Relay opens after ~3 s; 'overload' event shown"),
        ("Remote switch", "Toggle p02-relay on the Adafruit IO dashboard", "Relay follows within ~1 s; BLE event logged"),
        ("Power-cut retention", "Note kWh, unplug for 1 min, re-plug", "kWh resumes from the last saved value (≤ 5 min loss)"),
    ],
    advantages=["Measures real power and power factor, not just current.",
                "Automatic overload protection with remote and local reset.",
                "Calibratable in the field from a phone.",
                "Energy and cost history in a free cloud dashboard.",
                "Low-voltage side is galvanically isolated from mains by both sensors."],
    limitations=["ACS712-5A resolution is about 25 mA after scaling, so loads under ~5 W are not measured well.",
                 "ESP32 ADC is non-linear near 0 V and 3.3 V; accuracy is about ±2-3 % after calibration.",
                 "Single channel, single phase only.",
                 "Adafruit IO free tier keeps data for 30 days."],
    future=["Use a dedicated metering IC (HLW8012, PZEM-004T) for revenue-grade accuracy.",
            "Add scheduling (e.g. geyser only 6-7 AM) and monthly bill prediction.",
            "Monitor several circuits with split-core CT sensors (SCT-013).",
            "Detect appliance type from its power signature (NILM)."],
    safety=["230 V AC can kill. Build only under supervision of a person experienced with mains wiring.",
            "Use a closed plastic enclosure, a 5 A fuse in the live line and proper screw terminals; no breadboard on the mains side.",
            "Never touch the board or sensors while the mains plug is connected; program and test the low-voltage side first.",
            "The ACS712-5A must not carry more than 5 A continuously; size the fuse accordingly."],
    conclusion=(
        "The Smart Energy Monitor measures real power and power factor with two inexpensive isolated sensors and turns the "
        "ESP32 into a connected, protective smart plug. Users can see consumption and cost on an LCD, a phone or a free "
        "cloud dashboard, switch the load from anywhere and rely on automatic overload protection. With its calibration "
        "routine it achieves accuracy suitable for monitoring and energy-saving decisions."),
    refs=["Allegro MicroSystems, ACS712 Fully Integrated Hall-Effect Current Sensor datasheet.",
          "ZMPT101B Current-type Voltage Transformer datasheet, Qingxian Zeming Langxi Electronic.",
          "OpenEnergyMonitor, 'AC Power Theory - Arduino maths', learn.openenergymonitor.org.",
          "Adafruit Industries, Adafruit IO MQTT API documentation, io.adafruit.com/api/docs/mqtt.html."],
)

P03 = dict(
    id="P03", slug="P03_Smart_Home_Automation",
    title="Smart Home Automation with Away-Mode Security",
    short="Smart Home Automation",
    cloud="Adafruit IO", level="Intermediate",
    peripherals=["4-channel relay module", "HC-SR501 PIR sensor", "DHT11", "Active buzzer"],
    abstract=(
        "This project converts four ordinary electrical appliances into smart appliances that can be controlled from a "
        "phone over Bluetooth Low Energy or from anywhere in the world through the Adafruit IO cloud dashboard. A "
        "4-channel relay module switches a light, a fan, a TV socket and a spare plug. A PIR motion sensor and a DHT11 "
        "temperature-humidity sensor enable automation: in AUTO mode the light turns on when someone enters and off after "
        "a period without motion, and the fan follows the room temperature with hysteresis. In AWAY mode the same motion "
        "sensor becomes an intruder detector that sounds a buzzer and publishes an alert. Relay states are saved in flash "
        "and restored after power cuts, and the cloud and BLE views are kept in sync."),
    problem=(
        "Commercial smart switches need Wi-Fi and a vendor cloud; when the internet is down they cannot be operated from "
        "the phone at all. Lights and fans are often left on in empty rooms, wasting energy, and homes left empty during "
        "travel have no low-cost intrusion warning."),
    objectives=[
        "Control four appliances from a phone over BLE (local) and over the internet (Adafruit IO).",
        "Automate the light by occupancy and the fan by temperature.",
        "Provide an AWAY security mode with buzzer and cloud alert on motion.",
        "Restore appliance states after a power failure.",
        "Keep local, cloud and physical states consistent.",
    ],
    scope=(
        "A single room or small flat with up to four loads of up to 10 A each. Voice assistants, energy metering and "
        "multi-room networking are out of scope but can be added through Adafruit IO integrations."),
    existing=(
        "Bluetooth-only relay boards work only within range, while Wi-Fi smart plugs depend on the internet and on the "
        "vendor's servers. Few low-cost systems combine automation rules, security and remote control in one device."),
    proposed=[
        "Hybrid BLE + Wi-Fi control: either path works if the other is down.",
        "Three modes (MANUAL, AUTO, AWAY) selectable from the phone or the dashboard.",
        "Occupancy-based lighting with a configurable timeout and temperature-based fan control with 1 °C hysteresis.",
        "Persistent state in NVS flash and cloud state retrieval after reconnect.",
    ],
    components=COMMON_PARTS + [
        ("4-channel 5 V relay module (10 A)", 1, "Opto-isolated, active-LOW", 170),
        ("HC-SR501 PIR motion sensor", 1, "3-7 m range, adjustable delay", 70),
        ("DHT11 temperature & humidity module", 1, "0-50 °C, 20-90 % RH", 60),
        ("Active buzzer 5 V", 1, "Built-in oscillator, ~85 dB", 15),
        ("5 V 2 A adapter", 1, "Relays draw up to ~300 mA", 150),
    ],
    circuit=dict(
        title="P03 Smart Home Automation — Circuit Diagram",
        modules=[
            dict(name="4-ch Relay", sub="Light / Fan / TV / Plug",
                 pins=[("VCC", "5V"), ("IN1", "G26"), ("IN2", "G27"), ("IN3", "G25"), ("IN4", "G33"), ("GND", "GND")],
                 outer=["COM/NO of each relay switch an appliance's Live wire"]),
            dict(name="HC-SR501 PIR", sub="Motion sensor (3.3 V output)",
                 pins=[("VCC", "5V"), ("OUT", "G13"), ("GND", "GND")]),
            dict(name="DHT11", sub="Temperature & humidity",
                 pins=[("VCC", "3V3"), ("DATA", "G4"), ("GND", "GND")]),
            dict(name="Active buzzer", sub="Alarm",
                 pins=[("+", "G18", "Buzzer + to GPIO18 directly if it draws < 20 mA; otherwise drive it with an NPN transistor (BC547 + 1 kΩ)"), ("-", "GND")]),
        ],
        notes=["Use a 5 V 2 A supply on VIN when all four relays may be ON together.",
               "HC-SR501 runs on 5 V but its output is 3.3 V, safe for the ESP32.",
               "Set the PIR's 'time' trimmer to minimum and jumper to repeat (H) mode; the firmware handles timeouts."],
    ),
    principles=[
        ("Relay module", "Each channel's opto-coupler isolates the ESP32 from the relay coil circuit. A LOW signal turns "
                         "the relay ON, and its changeover contacts switch the appliance's live wire."),
        ("HC-SR501 PIR", "A pyroelectric sensor behind a Fresnel lens detects changes in infrared radiation when a warm "
                         "body moves across its zones. The BISS0001 chip outputs a 3.3 V HIGH pulse while motion continues."),
        ("DHT11", "Measures temperature with an NTC and humidity with a capacitive element, sending a 40-bit digital frame."),
        ("Active buzzer", "Contains its own oscillator, so a DC HIGH level produces a tone; the firmware pulses it at 1 Hz "
                          "for an alarm pattern."),
    ],
    working=[
        "At start-up the firmware restores the last relay states and mode from NVS flash, starts BLE and connects to "
        "Adafruit IO over MQTT/TLS (port 8883). It subscribes to five feeds — p03-light, p03-fan, p03-tv, p03-plug and "
        "p03-mode — and asks the broker for each feed's last value, so changes made on the dashboard while the device was "
        "offline are applied.",
        "In AUTO mode, motion turns the light on immediately; it turns off after 'lightto' seconds (default 60) without "
        "motion. The fan turns on when the temperature reaches 'fanon' (default 30 °C) and off below fanon − 1 °C. In AWAY "
        "mode motion starts a 60-second buzzer pattern, publishes INTRUSION on p03-motion and sends an 'intrusion' event "
        "to the phone. MANUAL mode disables all rules.",
        "Every relay change, from any source, is written to flash and published to its feed. Messages that echo back from "
        "the broker are ignored because the state already matches. Temperature and humidity are published every 30 s.",
    ],
    ble_data=[("t", "Temperature", "°C"), ("h", "Humidity", "%"), ("m", "Motion now", "bool"),
              ("mode", "MANUAL / AUTO / AWAY", "—"), ("alarm", "Alarm sounding", "bool"),
              ("r", "Relay states [light, fan, tv, plug]", "0/1"), ("cloud", "MQTT connected", "bool")],
    ble_cmds=[("r1:on|off|toggle … r4:…", "Yes", "Switch one appliance"), ("all:off / all:on", "Yes", "Switch all four"),
              ("mode:auto|manual|away", "Yes", "Change mode"), ("alarm:off", "Yes", "Silence the alarm")],
    settings=[("aiouser / aiokey", "—", "Adafruit IO credentials"), ("lightto", "60", "Light-off timeout (s)"),
              ("fanon", "30", "Fan-on temperature (°C)")],
    cloud_items=[("p03-light / p03-fan / p03-tv / p03-plug", "Toggle blocks with ON/OFF values"),
                 ("p03-mode", "Text or multi-button block: AUTO, MANUAL, AWAY"),
                 ("p03-temperature, p03-humidity", "Gauge / line chart"),
                 ("p03-motion", "Indicator or stream block (MOTION / CLEAR / INTRUSION)")],
    dfd=dict(
        sensors="PIR + DHT11", raw="motion, temperature, humidity",
        actuators="4-ch relay + buzzer", act="relay ON/OFF, alarm",
        store3=("D3", "Relay & mode state (NVS)", "state on change", "state at boot"),
        cloud_up="relay states, T, RH, motion", cloud_down="toggle & mode commands",
        derived="automation decisions",
    ),
    flow=dict(
        nodes=[("s", "start", "Power on"), ("i", "process", "Restore relays + mode from flash; init BLE, Wi-Fi, MQTT"),
               ("l", "process", "Handle BLE commands and MQTT messages"),
               ("pir", "io", "Read PIR"), ("mo", "decision", "Mode?"),
               ("a1", "decision", "Motion?"), ("on", "process", "Light ON, reset timer"),
               ("to", "decision", "No motion > timeout?"), ("off", "process", "Light OFF"),
               ("fan", "process", "Fan ON if T ≥ set, OFF if T < set − 1"),
               ("aw", "decision", "Motion?"), ("al", "process", "Buzzer + INTRUSION alert"),
               ("pub", "io", "Every 2 s: BLE frame; every 30 s: publish T/RH")],
        edges=[("s", "i"), ("i", "l"), ("l", "pir"), ("pir", "mo"), ("mo", "a1", "AUTO"), ("mo", "aw", "AWAY"),
               ("mo", "pub", "MANUAL"), ("a1", "on", "yes"), ("a1", "to", "no"), ("on", "fan"), ("to", "off", "yes"),
               ("to", "fan", "no"), ("off", "fan"), ("fan", "pub"), ("aw", "al", "yes"), ("aw", "pub", "no"),
               ("al", "pub"), ("pub", "l", "", ", constraint=false")],
    ),
    tests=[
        ("BLE switching", "Unlock, then toggle each switch in the web console", "Correct relay clicks; LED on relay board lights"),
        ("Cloud switching", "Toggle p03-fan on the Adafruit IO dashboard", "Relay 2 follows within ~1 s"),
        ("Occupancy light", "Set lightto=20, walk past the PIR and leave", "Light ON at once, OFF ~20 s after the last motion"),
        ("Fan automation", "Set fanon to 1 °C below room temperature", "Fan turns ON; raise fanon by 2 °C and it turns OFF"),
        ("Away alarm", "Select AWAY and move in front of the PIR", "Buzzer beeps; 'intrusion' event and INTRUSION on p03-motion"),
        ("Power cut", "Turn relays 1 and 3 ON, unplug and re-plug", "Relays 1 and 3 come back ON"),
        ("Internet down", "Disconnect router, control over BLE", "BLE control keeps working; cloud resyncs when back"),
    ],
    advantages=["Works over BLE when the internet is down and over the internet when away.",
                "Saves energy with occupancy and temperature rules.",
                "Adds basic security at no extra cost by reusing the PIR.",
                "State survives power cuts.",
                "Uses a free cloud with a customisable dashboard."],
    limitations=["The PIR cannot detect a person sitting completely still, so the light may switch off.",
                 "Adafruit IO free tier allows 10 feeds in total per account (this project uses 8).",
                 "Relays are not suitable for dimming or fan-speed control.",
                 "No physical wall-switch input in this version."],
    future=["Add wall-switch inputs so manual switches and the app stay in sync.",
            "Add voice control through Adafruit IO's IFTTT / Google Assistant integrations.",
            "Use a triac or TRIAC-based dimmer for light dimming and fan speed control.",
            "Add a camera (ESP32-CAM) snapshot on intrusion."],
    safety=["Appliance wiring is at 230 V AC: use proper screw terminals, insulation and an enclosure.",
            "Do not exceed the relay rating (10 A resistive; derate for motors).",
            "Keep the low-voltage ESP32 wiring physically separated from mains wiring."],
    conclusion=(
        "The system delivers practical smart-home features — remote and local control, occupancy lighting, temperature-"
        "based ventilation and an intrusion alarm — with a ₹1,000 bill of materials. Combining BLE and cloud control "
        "removes the single point of failure of internet-only smart switches, and state persistence makes it dependable "
        "in areas with frequent power cuts."),
    refs=["Murata/BISS0001 PIR controller and HC-SR501 module datasheet.",
          "Aosong, DHT11 datasheet.",
          "Adafruit Industries, Adafruit IO MQTT API — '/get' topic and rate limits.",
          "Songle SRD-05VDC-SL-C relay datasheet."],
)

P04 = dict(
    id="P04", slug="P04_Air_Quality_Monitor",
    title="Indoor Air Quality Monitor with Alarm",
    short="Air Quality Monitor",
    cloud="ThingSpeak", level="Intermediate",
    peripherals=["MQ-135 gas sensor", "DHT11", "0.96\" SSD1306 OLED", "Active buzzer"],
    abstract=(
        "Indoor air in kitchens, classrooms, offices and bedrooms can contain high levels of carbon dioxide, smoke and "
        "volatile organic compounds. This project uses an MQ-135 metal-oxide gas sensor to estimate a CO₂-equivalent "
        "concentration, compensates the sensor reading for temperature and humidity measured by a DHT11, and classifies "
        "air quality into five levels from Good to Hazardous. Values are shown on an OLED display, streamed to a phone "
        "over Bluetooth Low Energy and logged to ThingSpeak for long-term trends. A buzzer warns when the concentration "
        "exceeds an adjustable limit and can be muted from the phone. A one-tap calibration in clean outdoor air stores "
        "the sensor's reference resistance in flash."),
    problem=(
        "Poor ventilation raises CO₂ and pollutant levels, causing headaches, drowsiness and reduced concentration; gas "
        "leaks and smoke can be dangerous. Dedicated NDIR CO₂ monitors cost ₹4,000 or more, so most homes and schools "
        "have no way to know when to open windows or switch on exhaust fans."),
    objectives=[
        "Estimate indoor air quality as a CO₂-equivalent value with a low-cost MQ-135 sensor.",
        "Compensate for temperature and humidity and smooth the readings.",
        "Classify air quality into five levels and alarm above a set threshold.",
        "Display values locally and on a phone, and log them to the cloud.",
        "Allow field calibration and threshold changes without reprogramming.",
    ],
    scope=(
        "Indoor rooms of up to about 30 m². The MQ-135 gives an indicative value, not a certified measurement; it is not "
        "a substitute for a gas-leak detector certified for LPG safety."),
    existing=(
        "Most MQ-135 projects print the raw ADC value or use the library's default reference resistance, which can be "
        "off by a factor of two or more. They ignore humidity, which strongly affects metal-oxide sensors, and do not "
        "handle the sensor's warm-up period."),
    proposed=[
        "Datasheet-based temperature/humidity correction of the sensor resistance.",
        "Calibration against today's outdoor CO₂ (~420 ppm) with R0 saved in flash.",
        "Warm-up handling: no classification or uploads for the first 2 minutes.",
        "Five-level classification with phone notification and mutable buzzer alarm.",
    ],
    components=COMMON_PARTS + [
        ("MQ-135 air quality sensor module", 1, "NH₃, NOx, alcohol, benzene, smoke, CO₂; 5 V heater", 120),
        ("DHT11 temperature & humidity module", 1, "For compensation", 60),
        ("0.96\" SSD1306 OLED 128x64 (I2C)", 1, "Address 0x3C", 170),
        ("Active buzzer 5 V", 1, "Alarm", 15),
        ("Resistors 10 kΩ + 20 kΩ", 1, "Divider for MQ-135 AO", 5),
    ],
    circuit=dict(
        title="P04 Air Quality Monitor — Circuit Diagram",
        modules=[
            dict(name="MQ-135", sub="Gas sensor (5 V heater)",
                 pins=[("VCC", "5V"), ("AO", "G34", "AO -> 10 kΩ -> GPIO34; GPIO34 -> 20 kΩ -> GND (scales 5 V to 3.3 V)"), ("GND", "GND")]),
            dict(name="DHT11", sub="Temperature & humidity",
                 pins=[("VCC", "3V3"), ("DATA", "G4"), ("GND", "GND")]),
            dict(name="SSD1306 OLED", sub="128x64, I2C 0x3C",
                 pins=[("VCC", "3V3"), ("SDA", "G21"), ("SCL", "G22"), ("GND", "GND")]),
            dict(name="Active buzzer", sub="Alarm",
                 pins=[("+", "G18"), ("-", "GND")]),
        ],
        notes=["The MQ-135 heater draws ~150 mA from 5 V; power the board from USB or a 5 V 1 A adapter.",
               "Run a new MQ-135 for 24-48 hours (burn-in) before calibrating."],
    ),
    principles=[
        ("MQ-135", "A tin dioxide (SnO₂) layer heated to about 200-300 °C has low conductivity in clean air. Reducing "
                   "gases react with adsorbed oxygen on the surface and lower its resistance Rs. The module places the "
                   "sensor in series with a load resistor RL, so Vout = Vc·RL/(Rs+RL). The datasheet's log-log curve "
                   "gives ppm = a·(Rs/R0)^−b, with a = 116.6 and b = 2.769 for CO₂."),
        ("Compensation", "Rs falls as temperature and humidity rise. The datasheet curves are approximated by a quadratic "
                         "(below 20 °C) or linear (above 20 °C) correction factor, and Rs is divided by this factor."),
        ("SSD1306 OLED", "A 128x64 monochrome OLED with an on-chip controller and frame buffer, driven over I2C. Each pixel "
                         "emits light, so no backlight is needed and contrast is high."),
        ("DHT11 & buzzer", "The DHT11 supplies temperature and humidity for compensation; the active buzzer sounds short "
                           "beeps while the alarm is active."),
    ],
    working=[
        "Every 2 seconds the firmware reads the DHT11 and averages 32 ADC readings of the MQ-135. The module voltage is "
        "recovered from the divider (×1.5) and Rs = RL·(Vc − Vout)/Vout. Rs is divided by the temperature/humidity "
        "correction factor and the ratio Rs/R0 is converted to ppm with the datasheet curve. An exponential moving "
        "average (α = 0.3) smooths the result.",
        "Levels: Good < 600 ppm, Moderate < 1,000, Poor < 1,500, Unhealthy < 2,500, Hazardous above. When the value "
        "exceeds 'alarmppm' (default 1,500) the buzzer beeps and an 'air_alarm' event is sent; 'mute' silences it for 10 "
        "minutes. The calibration command averages 20 readings in clean air and sets R0 = Rs·(420/116.6)^(1/2.769), so "
        "clean air reads 420 ppm.",
        "Every 20 seconds after warm-up, ppm, temperature, humidity, Rs/R0 and level are uploaded to ThingSpeak with the "
        "level name as status text.",
    ],
    ble_data=[("ppm", "CO₂-equivalent", "ppm"), ("cat", "Level name", "—"), ("lvl", "Level 0-5", "—"),
              ("t", "Temperature", "°C"), ("h", "Humidity", "%"), ("rs", "Sensor resistance", "kΩ"),
              ("r0", "Reference resistance", "kΩ"), ("ratio", "Rs/R0", "—"), ("alarm", "Alarm active", "bool")],
    ble_cmds=[("calibrate", "Yes", "Set R0 in clean outdoor air"), ("mute", "No", "Mute alarm for 10 minutes")],
    settings=[("tskey", "—", "ThingSpeak Write API Key"), ("alarmppm", "1500", "Alarm threshold (ppm)"),
              ("r0", "10", "Reference resistance (set by calibrate)")],
    cloud_items=[("Field 1", "CO₂-equivalent (ppm)"), ("Field 2", "Temperature (°C)"), ("Field 3", "Humidity (%)"),
                 ("Field 4", "Rs/R0"), ("Field 5", "Level (1-5)"), ("Status", "Level name")],
    dfd=dict(
        sensors="MQ-135 + DHT11", raw="sensor voltage, T, RH",
        actuators="OLED + buzzer", act="display, alarm beeps",
        store3=("D3", "Calibration R0 (NVS)", "new R0", "R0 at boot"),
        cloud_up="ppm, T, RH, ratio, level every 20 s", cloud_down=None,
        derived="ppm, AQ level, alarm",
    ),
    flow=dict(
        nodes=[("s", "start", "Power on"), ("i", "process", "Init BLE, Wi-Fi, OLED; load R0 & alarm level"),
               ("l", "process", "Handle commands; buzzer pattern"),
               ("d1", "decision", "2 s elapsed?"), ("r", "io", "Read DHT11, average 32 MQ-135 samples"),
               ("c", "process", "Rs, correction, Rs/R0, ppm, smoothing"),
               ("w", "decision", "Warm-up done?"), ("k", "process", "Classify level"),
               ("a", "decision", "ppm ≥ alarm level?"), ("al", "process", "Alarm ON + event"),
               ("o", "io", "Update OLED, notify BLE"),
               ("u", "decision", "20 s & Wi-Fi & warm?"), ("t", "io", "Upload to ThingSpeak")],
        edges=[("s", "i"), ("i", "l"), ("l", "d1"), ("d1", "r", "yes"), ("d1", "l", "no", ", constraint=false"),
               ("r", "c"), ("c", "w"), ("w", "k", "yes"), ("w", "o", "no"), ("k", "a"), ("a", "al", "yes"),
               ("a", "o", "no"), ("al", "o"), ("o", "u"), ("u", "t", "yes"), ("u", "l", "no", ", constraint=false"),
               ("t", "l", "", ", constraint=false")],
    ),
    tests=[
        ("Warm-up", "Power on and watch the OLED", "'Warm-up' for 2 minutes, then a ppm value"),
        ("Calibration", "Place outdoors for 10 min, send calibrate", "Reading becomes ≈ 420 ppm; new R0 reported"),
        ("Breath test", "Breathe gently towards the sensor", "ppm rises within seconds, then falls back"),
        ("Alcohol test", "Hold a hand-sanitiser cap 10 cm away", "Level rises to Poor/Unhealthy; alarm sounds above threshold"),
        ("Mute", "Send mute during an alarm", "Buzzer stops; OLED shows '(muted)'"),
        ("Cloud", "Check ThingSpeak after 2 minutes", "Five fields updated every 20 s"),
    ],
    advantages=["Very low cost compared with NDIR CO₂ meters.",
                "Temperature/humidity compensation and calibration improve consistency.",
                "Local display, phone alerts and cloud history.",
                "Thresholds adjustable without reprogramming."],
    limitations=["MQ-135 is not selective: alcohol, ammonia and smoke also raise the 'CO₂' value.",
                 "Values are indicative; accuracy is far below an NDIR sensor (e.g. MH-Z19, SCD40).",
                 "Needs burn-in and 2-minute warm-up; heater consumes ~0.75 W.",
                 "Not certified for LPG leak safety."],
    future=["Add a PM2.5 sensor (PMS5003/SDS011) and an NDIR CO₂ sensor for a full AQI.",
            "Automatically switch an exhaust fan through a relay.",
            "Use ThingSpeak React to send alerts when the level stays Poor for 30 minutes.",
            "Battery operation with heater duty-cycling."],
    safety=["The MQ-135 heater gets hot (~50 °C on the case); do not touch it during operation.",
            "Do not rely on this device for life-safety gas detection."],
    conclusion=(
        "The monitor turns a cheap metal-oxide sensor into a practical air-quality indicator by adding calibration, "
        "environmental compensation and smoothing. With a local display, BLE alerts and ThingSpeak logging it helps users "
        "decide when to ventilate, and its modular design allows more accurate sensors to be added later."),
    refs=["Hanwei Electronics, MQ-135 Gas Sensor technical data.",
          "G. Krocker, MQ135 Arduino library (correction-factor coefficients), GitHub.",
          "NOAA Global Monitoring Laboratory, Trends in atmospheric CO₂ (global mean ≈ 420 ppm).",
          "Solomon Systech, SSD1306 OLED driver datasheet."],
)

P05 = dict(
    id="P05", slug="P05_Smart_Parking_System",
    title="Smart Parking System with Automatic Gate",
    short="Smart Parking System",
    cloud="Supabase", level="Intermediate",
    peripherals=["2 × HC-SR04 ultrasonic sensors", "IR obstacle sensor", "SG90 servo motor"],
    abstract=(
        "Finding a free parking slot wastes time and fuel and causes congestion at the entrance of malls, colleges and "
        "apartments. This project monitors each parking slot with an HC-SR04 ultrasonic sensor and controls an entry "
        "barrier with an SG90 servo. An IR sensor detects a car at the gate; the barrier opens only if a slot is free and "
        "closes automatically after the car has passed, otherwise a 'Parking FULL' event is raised. Slot status is "
        "debounced and written to a Supabase PostgreSQL database through its REST API, together with an event log, so "
        "any browser or app can show live availability. A phone connected over BLE shows a live slot map and lets the "
        "attendant open or close the gate manually."),
    problem=(
        "Drivers circle around full parking areas because they cannot see availability in advance, and manual gate "
        "operation needs a full-time attendant. Commercial parking guidance systems are expensive and proprietary."),
    objectives=[
        "Detect occupancy of each slot reliably with ultrasonic distance measurement.",
        "Automate the entry gate based on availability.",
        "Publish live slot status and an event history to a free cloud database (Supabase).",
        "Provide an attendant interface over BLE for manual override.",
        "Make thresholds configurable for model and real-size installations.",
    ],
    scope=(
        "Demonstrated with two slots on a table-top model; the firmware supports more slots by extending two arrays. "
        "Vehicle identification (number-plate recognition) and payments are outside the scope."),
    existing=(
        "Many parking projects show availability only on a local display and use a fixed delay to close the gate, which "
        "can hit a slow vehicle. Cloud versions often push every raw reading, wasting bandwidth and quota."),
    proposed=[
        "Event-driven cloud updates: a slot row is PATCHed only when its state changes (after 3 equal readings).",
        "Gate closes a fixed time after the IR beam is clear, not after a fixed time from opening.",
        "Failed uploads are retried automatically every 2 seconds.",
        "Relational data (slots table + events table + summary view) enables analytics in SQL.",
    ],
    components=COMMON_PARTS + [
        ("HC-SR04 ultrasonic sensor", 2, "2-400 cm, 5 V", 120),
        ("IR obstacle avoidance module", 1, "2-30 cm, adjustable, digital output", 30),
        ("SG90 micro servo", 1, "180°, 1.8 kg·cm, 5 V", 90),
        ("Resistors 1 kΩ + 2 kΩ (×2 sets)", 1, "ECHO level dividers", 5),
    ],
    circuit=dict(
        title="P05 Smart Parking System — Circuit Diagram",
        modules=[
            dict(name="HC-SR04 #1", sub="Slot 1 sensor",
                 pins=[("VCC", "5V"), ("TRIG", "G25"), ("ECHO", "G34", "ECHO -> 1 kΩ -> GPIO; GPIO -> 2 kΩ -> GND (5 V to 3.3 V), for both HC-SR04s"), ("GND", "GND")]),
            dict(name="HC-SR04 #2", sub="Slot 2 sensor",
                 pins=[("VCC", "5V"), ("TRIG", "G26"), ("ECHO", "G35"), ("GND", "GND")]),
            dict(name="IR sensor", sub="Car at gate (LOW = present)",
                 pins=[("VCC", "3V3"), ("OUT", "G27"), ("GND", "GND")]),
            dict(name="SG90 servo", sub="Barrier gate",
                 pins=[("Red +5V", "5V"), ("Orange SIG", "G13"), ("Brown GND", "GND")]),
        ],
        notes=["Mount each HC-SR04 facing down from above the slot (or facing the car from the slot's end wall).",
               "Add a 470 µF capacitor across the servo supply if the ESP32 resets when the servo moves."],
    ),
    principles=[
        ("HC-SR04", "A 10 µs trigger pulse makes the module send eight 40 kHz ultrasonic bursts. The ECHO pin stays HIGH "
                    "until the reflection returns; distance = echo time × 343 m/s ÷ 2 (0.0343 cm/µs ÷ 2)."),
        ("IR obstacle sensor", "An IR LED and photodiode face the same direction; a nearby object reflects IR, and an "
                               "LM393 comparator pulls the output LOW when the reflection exceeds the trimmer threshold."),
        ("SG90 servo", "A DC motor with gearbox and potentiometer feedback; the pulse width of a 50 Hz signal (0.5-2.4 ms) "
                       "sets the shaft angle from 0° to 180°. The ESP32Servo library generates it with the LEDC PWM unit."),
        ("Supabase", "An open-source back-end on PostgreSQL. PostgREST exposes each table as a REST endpoint, and Row "
                     "Level Security policies decide what the device key may read or write."),
    ],
    working=[
        "Every 300 ms both slots are measured (30 ms apart to avoid cross-talk). A slot is occupied when the distance is "
        "below 'occcm' (10 cm for the model, ~60 cm for a real car). A change is accepted only after three consecutive "
        "equal readings, which removes noise and passing objects.",
        "When the IR sensor goes LOW (car at gate) the firmware counts free slots: if at least one is free the servo opens "
        "to 90°, otherwise a 'full' event is raised and a 'full_rejected' row is logged. After the car passes and the IR "
        "beam has been clear for 4 seconds the gate closes.",
        "A confirmed slot change marks the slot as pending. Every 2 seconds pending slots are PATCHed to "
        "/rest/v1/parking_slots?id=eq.N and an event is INSERTed into parking_events. If the request fails the slot stays "
        "pending and is retried. The view parking_summary returns free and total slots for any dashboard.",
    ],
    ble_data=[("s", "Slot states [slot1, slot2]", "0/1"), ("d", "Distances", "cm"), ("free", "Free slots", "count"),
              ("gate", "open / closed", "—"), ("car", "Car at gate", "bool")],
    ble_cmds=[("gate:open / gate:close", "Yes", "Manual barrier control"), ("sync", "No", "Re-upload all slot states")],
    settings=[("sburl / sbkey", "—", "Supabase project URL and publishable key"), ("occcm", "10", "Occupied distance threshold (cm)")],
    cloud_items=[("parking_slots", "One row per slot: occupied, distance_cm, updated_at (PATCH)"),
                 ("parking_events", "slot_occupied / slot_freed / full_rejected with free_slots (INSERT)"),
                 ("parking_summary (view)", "free_slots, total_slots, last_change")],
    dfd=dict(
        sensors="HC-SR04 ×2 + IR sensor", raw="echo times, car-at-gate",
        actuators="Servo barrier", act="open / close angle",
        store3=("D3", "Pending-sync flags (RAM)", "changed slots", "slots to upload"),
        cloud_up="slot PATCH + event INSERT", cloud_down=None,
        derived="slot occupancy, free count, gate decision",
    ),
    flow=dict(
        nodes=[("s", "start", "Power on"), ("i", "process", "Init BLE, Wi-Fi, servo closed, slots pending"),
               ("l", "process", "Handle BLE commands"),
               ("ir", "decision", "Car arrived at gate?"), ("f", "decision", "Free slot?"),
               ("op", "process", "Open gate"), ("full", "process", "'Parking FULL' event + log"),
               ("cl", "decision", "Gate open & IR clear > 4 s?"), ("cg", "process", "Close gate"),
               ("sc", "io", "Every 300 ms: measure both slots"),
               ("db", "decision", "State changed 3× in a row?"), ("pd", "process", "Mark slot pending, BLE event"),
               ("up", "io", "Every 2 s: PATCH pending slots + INSERT event")],
        edges=[("s", "i"), ("i", "l"), ("l", "ir"), ("ir", "f", "yes"), ("ir", "cl", "no"), ("f", "op", "yes"),
               ("f", "full", "no"), ("op", "cl"), ("full", "cl"), ("cl", "cg", "yes"), ("cl", "sc", "no"), ("cg", "sc"),
               ("sc", "db"), ("db", "pd", "yes"), ("db", "up", "no"), ("pd", "up"), ("up", "l", "", ", constraint=false")],
    ),
    tests=[
        ("Distance", "Hold an object 5, 10, 20 cm under each sensor", "Distances shown in the app within ±1 cm"),
        ("Occupancy", "Place a toy car in slot 1", "Slot 1 turns OCCUPIED within ~1 s; row updated in Supabase"),
        ("Gate open", "Block the IR sensor with one slot free", "Gate opens; closes 4 s after the IR is cleared"),
        ("Parking full", "Fill both slots, then block the IR", "Gate stays closed; 'full' event and full_rejected row"),
        ("Manual override", "Unlock and press 'Open gate'", "Gate opens; 'gate OPEN (attendant)' event"),
        ("Offline retry", "Disconnect Wi-Fi, change a slot, reconnect", "Pending change is uploaded after reconnection"),
    ],
    advantages=["Real-time availability visible from anywhere through a standard REST/SQL back-end.",
                "Automatic gate reduces attendant workload.",
                "Debouncing avoids false changes; uploads only on change.",
                "Easily scaled to more slots and analysed with SQL."],
    limitations=["Ultrasonic sensors can be confused by angled or soft surfaces.",
                 "Only the entry is controlled; exits need a second gate or attendant.",
                 "Supabase free projects pause after a week without activity (see setup notes).",
                 "No vehicle identification or billing."],
    future=["Number-plate recognition with ESP32-CAM for entry/exit logs.",
            "Slot reservation from a web page using Supabase Auth.",
            "LED guidance lights above each slot.",
            "LoRa sensors for large outdoor lots."],
    safety=["The servo barrier is a model; a real barrier needs safety sensors so it never closes on a vehicle or person.",
            "Power the servo from 5 V, not 3.3 V; its stall current can brown-out the ESP32."],
    conclusion=(
        "The Smart Parking System combines simple sensors with a relational cloud database to give live, queryable "
        "parking availability and an automatic barrier. Event-driven updates keep cloud usage minimal, and BLE gives the "
        "attendant control even without internet. The design scales naturally to more slots and richer analytics."),
    refs=["Cytron/ElecFreaks, HC-SR04 Ultrasonic Ranging Module user guide.",
          "TowerPro SG90 servo datasheet.",
          "Supabase documentation: REST API (PostgREST) and Row Level Security, supabase.com/docs.",
          "K. Hassan et al., IoT-based smart parking systems: a survey, various journals (background reading)."],
)

PROJECTS_A = [P01, P02, P03, P04, P05]
