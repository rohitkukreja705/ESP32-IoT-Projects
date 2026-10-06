/*
 * P09 — Smart Greenhouse with Cloud-Configurable Irrigation
 * =========================================================
 * Peripherals: capacitive soil-moisture sensor v1.2, DHT11, LDR,
 *              2-channel relay (water pump + ventilation fan)
 * Wi-Fi  : Supabase — readings every minute, events log, and thresholds read
 *          from a settings row (change them in the Supabase table editor and
 *          the greenhouse follows within a minute)
 * BLE    : live dashboard, manual pump/fan, AUTO/MANUAL mode, soil calibration
 * Logic  : burst-and-soak watering (prevents over-watering), fan control by
 *          temperature OR humidity with hysteresis, works fully offline with
 *          the last known thresholds
 */
#include "config.h"
#include "IoTCore.h"
#include "Cloud.h"
#include <DHT.h>

DHT dht(PIN_DHT, DHT11);

struct Th { float soilMin, soilMax, tempMax, humMax; } th = { DEF_SOIL_MIN, DEF_SOIL_MAX, DEF_TEMP_MAX, DEF_HUM_MAX };
float soil = NAN, temp = NAN, hum = NAN, light = NAN;
bool pumpOn = false, fanOn = false, autoMode = true;
enum WaterState { IDLE, WATERING, SOAKING } ws = IDLE;
uint32_t stateSince = 0, lastSample = 0, lastUpload = 0, lastSettings = 0;
float dryMv, wetMv;
int pumpCyclesToday = 0;

void setOut(int pin, bool on) { digitalWrite(pin, (on ^ RELAY_ACTIVE_LOW) ? HIGH : LOW); }

void logEvent(const String& ev, const String& detail) {
  iot::sendEvent(ev, detail);
  if (!iot::wifiOK()) return;
  JsonDocument d; d["event"] = ev; d["detail"] = detail; d["device"] = iot::deviceName;
  String s; serializeJson(d, s);
  cloud::supabaseInsert("greenhouse_events", s);
}

void setPump(bool on, const String& why) {
  if (on == pumpOn) return;
  pumpOn = on; setOut(PIN_PUMP, on);
  logEvent(on ? "pump_on" : "pump_off", why);
}
void setFan(bool on, const String& why) {
  if (on == fanOn) return;
  fanOn = on; setOut(PIN_FAN, on);
  logEvent(on ? "fan_on" : "fan_off", why);
}

float avgMv(int pin) {
  uint32_t s = 0; for (int i = 0; i < 16; i++) { s += analogReadMilliVolts(pin); delayMicroseconds(250); }
  return s / 16.0;
}

void sample() {
  float t = dht.readTemperature(), h = dht.readHumidity();
  if (!isnan(t)) temp = t;
  if (!isnan(h)) hum = h;
  // capacitive sensor: lower voltage = wetter soil
  soil = constrain((dryMv - avgMv(PIN_SOIL)) / (dryMv - wetMv) * 100.0, 0, 100);
  light = constrain(avgMv(PIN_LDR) / 3300.0 * 100.0, 0, 100);
}

void automation() {
  if (!autoMode || isnan(soil)) return;
  uint32_t now = millis(), inState = now - stateSince;
  switch (ws) {
    case IDLE:
      if (soil < th.soilMin) { ws = WATERING; stateSince = now; setPump(true, "soil " + String(soil, 0) + "% < " + String(th.soilMin, 0) + "%"); pumpCyclesToday++; }
      break;
    case WATERING:
      if (soil >= th.soilMax) { setPump(false, "target reached"); ws = IDLE; stateSince = now; }
      else if (inState > PUMP_BURST_S * 1000UL) { setPump(false, "burst done, soaking"); ws = SOAKING; stateSince = now; }
      break;
    case SOAKING:
      if (inState > SOAK_S * 1000UL) {
        if (soil < th.soilMax) { ws = WATERING; stateSince = now; setPump(true, "still dry after soak"); }
        else { ws = IDLE; stateSince = now; }
      }
      break;
  }
  if (!isnan(temp) && !isnan(hum)) {
    bool hot = temp > th.tempMax || hum > th.humMax;
    bool cool = temp < th.tempMax - 1.5 && hum < th.humMax - 5;   // hysteresis
    if (hot && !fanOn) setFan(true, "T " + String(temp, 1) + "C / RH " + String(hum, 0) + "%");
    if (cool && fanOn) setFan(false, "climate normal");
  }
}

void fetchCloudSettings() {
  String out;
  if (!cloud::supabaseSelect("greenhouse_settings", "select=*&id=eq.1", out)) return;
  JsonDocument d;
  if (deserializeJson(d, out) || !d.is<JsonArray>() || d.size() == 0) return;
  JsonObject o = d[0];
  Th n = { o["soil_min"] | th.soilMin, o["soil_max"] | th.soilMax, o["temp_max"] | th.tempMax, o["hum_max"] | th.humMax };
  if (n.soilMin != th.soilMin || n.soilMax != th.soilMax || n.tempMax != th.tempMax || n.humMax != th.humMax) {
    th = n;
    iot::saveSetting("th", String(th.soilMin) + "," + String(th.soilMax) + "," + String(th.tempMax) + "," + String(th.humMax));
    iot::sendEvent("thresholds", "Updated from cloud");
  }
  // apply the cloud mode only when it is changed in the table, so a manual
  // override made over BLE is not undone every minute
  static int lastCloudAuto = -1;
  if (!o["auto_mode"].isNull()) {
    int a = o["auto_mode"].as<bool>() ? 1 : 0;
    if (a != lastCloudAuto) { if (lastCloudAuto != -1 || a == 0) autoMode = a; lastCloudAuto = a; }
  }
}

void upload() {
  JsonDocument d;
  d["soil"] = iot::rnd(soil, 0); d["temperature"] = iot::rnd(temp); d["humidity"] = iot::rnd(hum, 0);
  d["light"] = iot::rnd(light, 0); d["pump"] = pumpOn; d["fan"] = fanOn; d["device"] = iot::deviceName;
  String s; serializeJson(d, s);
  cloud::supabaseInsert("greenhouse_readings", s);
}

void sendBle() {
  JsonDocument d;
  d["soil"] = iot::rnd(soil, 0); d["t"] = iot::rnd(temp); d["h"] = iot::rnd(hum, 0); d["l"] = iot::rnd(light, 0);
  d["pump"] = pumpOn; d["fan"] = fanOn; d["mode"] = autoMode ? "AUTO" : "MANUAL";
  d["state"] = ws == IDLE ? "idle" : ws == WATERING ? "watering" : "soaking";
  d["smin"] = th.soilMin; d["smax"] = th.soilMax; d["tmax"] = th.tempMax;
  iot::sendData(d);
}

void loadLocal() {
  dryMv = iot::settingF("soildry", DEF_SOIL_DRY_MV);
  wetMv = iot::settingF("soilwet", DEF_SOIL_WET_MV);
  String s = iot::setting("th", "");
  if (s.length()) sscanf(s.c_str(), "%f,%f,%f,%f", &th.soilMin, &th.soilMax, &th.tempMax, &th.humMax);
}

// Commands: pump:on|off  fan:on|off  mode:auto|manual  caldry  calwet
bool onCommand(const String& cmd, const String& arg, bool authed) {
  if (cmd == "setting") { loadLocal(); return true; }
  if (cmd == "pump" || cmd == "fan" || cmd == "mode" || cmd == "caldry" || cmd == "calwet") {
    if (!authed) { iot::emitAck(cmd, false, "send auth:<PIN> first"); return true; }
    if (cmd == "mode") { autoMode = arg == "auto"; ws = IDLE; setPump(false, "mode change"); }
    if (cmd == "pump") { autoMode = false; setPump(arg == "on", "manual (BLE)"); }
    if (cmd == "fan")  { autoMode = false; setFan(arg == "on", "manual (BLE)"); }
    if (cmd == "caldry") { dryMv = avgMv(PIN_SOIL); iot::saveSetting("soildry", String(dryMv, 0)); }
    if (cmd == "calwet") { wetMv = avgMv(PIN_SOIL); iot::saveSetting("soilwet", String(wetMv, 0)); }
    iot::emitAck(cmd, true, autoMode ? "AUTO" : "MANUAL");
    sendBle();
    return true;
  }
  return false;
}

void setup() {
  pinMode(PIN_PUMP, OUTPUT); pinMode(PIN_FAN, OUTPUT);
  setOut(PIN_PUMP, false); setOut(PIN_FAN, false);
  analogSetAttenuation(ADC_11db);
  iot::begin("P09", onCommand);
  loadLocal();
  dht.begin();
}

void loop() {
  iot::loop();
  uint32_t now = millis();
  if (now - lastSample >= SAMPLE_MS) { lastSample = now; sample(); automation(); sendBle(); }
  if (iot::wifiOK() && (lastSettings == 0 || now - lastSettings >= SETTINGS_MS)) { lastSettings = now; fetchCloudSettings(); }
  if (iot::wifiOK() && now - lastUpload >= UPLOAD_MS && !isnan(soil)) { lastUpload = now; upload(); }
}
