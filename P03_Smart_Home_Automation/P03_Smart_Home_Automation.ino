/*
 * P03 — Smart Home Automation with Away-Mode Security
 * ===================================================
 * Peripherals: 4-channel relay module, HC-SR501 PIR, DHT11, active buzzer
 * Wi-Fi  : Adafruit IO (MQTT) — 4 toggle feeds control the relays from the
 *          dashboard / phone; temperature, humidity and motion are published
 * BLE    : local control when the internet is down, live status, mode change
 * Modes  : MANUAL - relays only change by command
 *          AUTO   - PIR switches the light, temperature switches the fan
 *          AWAY   - any motion sounds the buzzer and raises an intrusion alert
 * Extras : relay states survive power cuts (saved in flash), fan hysteresis,
 *          cloud <-> BLE state stays in sync
 */
#include "config.h"
#include "IoTCore.h"
#include "Cloud.h"
#include <DHT.h>

DHT dht(PIN_DHT, DHT11);
cloud::AdafruitIO aio;

const int RELAY_PINS[4] = { PIN_RELAY1, PIN_RELAY2, PIN_RELAY3, PIN_RELAY4 };
const char* RELAY_NAMES[4] = { "Light", "Fan", "TV", "Plug" };
const char* RELAY_FEEDS[4] = { "p03-light", "p03-fan", "p03-tv", "p03-plug" };
const char* SUB_FEEDS[] = { "p03-light", "p03-fan", "p03-tv", "p03-plug", "p03-mode" };

enum Mode { MANUAL, AUTO, AWAY };
const char* MODE_NAMES[] = { "MANUAL", "AUTO", "AWAY" };
Mode mode = AUTO;

bool relay[4] = { false, false, false, false };
bool motion = false, alarmOn = false;
float temp = NAN, hum = NAN;
uint32_t lastMotion = 0, lastSensor = 0, lastCloud = 0, alarmStart = 0;
uint32_t lightTimeoutMs = DEF_LIGHT_TIMEOUT_S * 1000UL;
float fanOnC = DEF_FAN_ON_C;

void loadSettings() {
  lightTimeoutMs = iot::settingF("lightto", DEF_LIGHT_TIMEOUT_S) * 1000UL;
  fanOnC = iot::settingF("fanon", DEF_FAN_ON_C);
}

void applyRelay(int i) {
  digitalWrite(RELAY_PINS[i], (relay[i] ^ RELAY_ACTIVE_LOW) ? HIGH : LOW);
}

void setRelay(int i, bool on, const char* source, bool publish = true) {
  if (i < 0 || i > 3 || relay[i] == on) return;
  relay[i] = on;
  applyRelay(i);
  iot::saveSetting(("r" + String(i + 1)).c_str(), on ? "1" : "0");
  iot::sendEvent("relay", String(RELAY_NAMES[i]) + (on ? " ON" : " OFF") + " (" + source + ")");
  if (publish) aio.publish(RELAY_FEEDS[i], on ? "ON" : "OFF");
}

void setMode(Mode m, const char* source) {
  mode = m;
  iot::saveSetting("mode", String((int)m));
  if (m != AWAY) { alarmOn = false; digitalWrite(PIN_BUZZER, LOW); }
  iot::sendEvent("mode", String(MODE_NAMES[m]) + " (" + source + ")");
  aio.publish("p03-mode", MODE_NAMES[m]);
}

void automation() {
  uint32_t now = millis();
  if (mode == AUTO) {
    if (motion && !relay[0]) setRelay(0, true, "motion");
    if (!motion && relay[0] && now - lastMotion > lightTimeoutMs) setRelay(0, false, "no motion");
    if (!isnan(temp)) {
      if (temp >= fanOnC && !relay[1]) setRelay(1, true, "temperature");
      if (temp < fanOnC - 1.0 && relay[1]) setRelay(1, false, "temperature");   // 1 °C hysteresis
    }
  }
  if (mode == AWAY && motion && !alarmOn) {
    alarmOn = true; alarmStart = now;
    iot::sendEvent("intrusion", "Motion detected while AWAY");
    aio.publish("p03-motion", "INTRUSION");
  }
  // buzzer pattern: 1 Hz beeping for up to 60 s
  if (alarmOn) {
    digitalWrite(PIN_BUZZER, ((now - alarmStart) / 500) % 2);
    if (now - alarmStart > 60000) { alarmOn = false; digitalWrite(PIN_BUZZER, LOW); }
  }
}

void sendBle() {
  JsonDocument d;
  d["t"] = iot::rnd(temp); d["h"] = iot::rnd(hum, 0);
  d["m"] = motion; d["mode"] = MODE_NAMES[mode]; d["alarm"] = alarmOn;
  JsonArray r = d["r"].to<JsonArray>();
  for (int i = 0; i < 4; i++) r.add(relay[i] ? 1 : 0);
  d["cloud"] = aio.connected();
  iot::sendData(d);
}

void onFeed(const String& feed, const String& value) {
  bool on = value.equalsIgnoreCase("ON") || value == "1";
  for (int i = 0; i < 4; i++)
    if (feed == RELAY_FEEDS[i]) { setRelay(i, on, "cloud", false); sendBle(); return; }
  if (feed == "p03-mode") {
    for (int m = 0; m < 3; m++)
      if (value.equalsIgnoreCase(MODE_NAMES[m]) && mode != m) { mode = (Mode)m; setMode(mode, "cloud"); }
  }
}

// Commands: r1:on  r2:off  r3:toggle  all:off  mode:auto|manual|away  alarm:off
bool onCommand(const String& cmd, const String& arg, bool authed) {
  if (cmd == "setting") { loadSettings(); return true; }
  bool isRelay = cmd.length() == 2 && cmd[0] == 'r' && cmd[1] >= '1' && cmd[1] <= '4';
  if (!(isRelay || cmd == "all" || cmd == "mode" || cmd == "alarm")) return false;
  if (!authed) { iot::emitAck(cmd, false, "send auth:<PIN> first"); return true; }
  if (isRelay) {
    int i = cmd[1] - '1';
    bool on = arg == "on" ? true : arg == "off" ? false : !relay[i];
    setRelay(i, on, "BLE");
  } else if (cmd == "all") {
    for (int i = 0; i < 4; i++) setRelay(i, arg == "on", "BLE");
  } else if (cmd == "mode") {
    String a = arg; a.toUpperCase();
    for (int m = 0; m < 3; m++) if (a == MODE_NAMES[m]) setMode((Mode)m, "BLE");
  } else if (cmd == "alarm") {
    alarmOn = false; digitalWrite(PIN_BUZZER, LOW);
  }
  iot::emitAck(cmd, true);
  sendBle();
  return true;
}

void setup() {
  for (int i = 0; i < 4; i++) { pinMode(RELAY_PINS[i], OUTPUT); }
  pinMode(PIN_PIR, INPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  iot::begin("P03", onCommand);
  // restore last relay states and mode after a power cut
  for (int i = 0; i < 4; i++) { relay[i] = iot::setting(("r" + String(i + 1)).c_str(), "0") == "1"; applyRelay(i); }
  mode = (Mode)constrain((int)iot::settingF("mode", AUTO), 0, 2);
  loadSettings();
  dht.begin();
  // On every (re)connect the library asks Adafruit IO for the last value of
  // each subscribed feed, so changes made on the dashboard while the board
  // was offline are applied (the cloud is the source of truth).
  aio.begin(onFeed, SUB_FEEDS, 5);
}

void loop() {
  iot::loop();
  aio.loop();
  uint32_t now = millis();

  bool m = digitalRead(PIN_PIR) == HIGH;
  if (m) lastMotion = now;
  if (m != motion) {
    motion = m;
    if (mode != AWAY) aio.publish("p03-motion", m ? "MOTION" : "CLEAR");
    sendBle();
  }
  automation();

  if (now - lastSensor >= SENSOR_MS) {
    lastSensor = now;
    float t = dht.readTemperature(), h = dht.readHumidity();
    if (!isnan(t)) temp = t;
    if (!isnan(h)) hum = h;
    sendBle();
  }
  if (aio.connected() && now - lastCloud >= CLOUD_MS && !isnan(temp)) {
    lastCloud = now;
    aio.publish("p03-temperature", temp, 1);
    aio.publish("p03-humidity", hum, 0);
  }
}
