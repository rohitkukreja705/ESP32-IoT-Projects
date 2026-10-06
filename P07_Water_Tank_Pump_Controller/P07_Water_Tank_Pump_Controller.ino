/*
 * P07 — Water Tank Level Monitor & Smart Pump Controller
 * ======================================================
 * Peripherals: HC-SR04 ultrasonic (level), YF-S201 flow sensor,
 *              relay (pump), buzzer
 * Wi-Fi  : Adafruit IO — level %, flow, pump status, AUTO/MANUAL mode,
 *          remote pump switch from the dashboard
 * BLE    : live tank gauge, pump/mode control, tank calibration
 * Logic  : AUTO mode fills between LOW and HIGH thresholds with hysteresis;
 *          protections: dry-run (no flow), overflow, maximum run time;
 *          median filter on distance; litres pumped counter
 */
#include "config.h"
#include "IoTCore.h"
#include "Cloud.h"

cloud::AdafruitIO aio;
const char* SUB_FEEDS[] = { "p07-pump", "p07-mode" };

volatile uint32_t flowPulses = 0;
void IRAM_ATTR onFlowPulse() { flowPulses = flowPulses + 1; }

float distCm = NAN, levelPct = NAN, flowLpm = 0, litres = 0;
bool pumpOn = false, autoMode = true, alarmOn = false;
String fault = "";
uint32_t pumpStart = 0, noFlowSince = 0, lastSample = 0, lastCloud = 0, lastFlowCalc = 0;
float depthCm, fullCm, lowPct, highPct, maxRunMin;

void loadSettings() {
  depthCm   = iot::settingF("depth",  DEF_DEPTH_CM);
  fullCm    = iot::settingF("fullcm", DEF_FULL_CM);
  lowPct    = iot::settingF("low",    DEF_LOW_PCT);
  highPct   = iot::settingF("high",   DEF_HIGH_PCT);
  maxRunMin = iot::settingF("maxrun", DEF_MAXRUN_MIN);
}

float pingOnce() {
  digitalWrite(PIN_TRIG, LOW); delayMicroseconds(3);
  digitalWrite(PIN_TRIG, HIGH); delayMicroseconds(10); digitalWrite(PIN_TRIG, LOW);
  unsigned long us = pulseIn(PIN_ECHO, HIGH, 30000);
  return us ? us * 0.0343 / 2.0 : NAN;
}

// median of 5 pings rejects splashes and stray echoes
float readDistance() {
  float v[5]; int n = 0;
  for (int i = 0; i < 5; i++) { float d = pingOnce(); if (!isnan(d)) v[n++] = d; delay(15); }
  if (n == 0) return NAN;
  for (int i = 0; i < n; i++) for (int j = i + 1; j < n; j++) if (v[j] < v[i]) { float t = v[i]; v[i] = v[j]; v[j] = t; }
  return v[n / 2];
}

void setPump(bool on, const String& why) {
  if (on == pumpOn) return;
  if (on && fault.length()) { iot::sendEvent("pump_blocked", "Clear fault first: " + fault); return; }
  pumpOn = on;
  digitalWrite(PIN_RELAY, (on ^ RELAY_ACTIVE_LOW) ? HIGH : LOW);
  if (on) { pumpStart = millis(); noFlowSince = millis(); }
  iot::sendEvent("pump", String(on ? "ON" : "OFF") + " - " + why);
  aio.publish("p07-pump", on ? "ON" : "OFF");
}

void raiseFault(const String& f) {
  fault = f; alarmOn = true;
  setPump(false, f);
  iot::sendEvent("fault", f);
}

void control() {
  uint32_t now = millis();
  // flow rate once per second
  if (now - lastFlowCalc >= 1000) {
    noInterrupts(); uint32_t p = flowPulses; flowPulses = 0; interrupts();
    float secs = (now - lastFlowCalc) / 1000.0;
    lastFlowCalc = now;
    flowLpm = (p / FLOW_PULSES_PER_LITRE) * 60.0 / secs;
    litres += p / FLOW_PULSES_PER_LITRE;
  }
  if (isnan(levelPct)) return;

  if (levelPct >= 98 && pumpOn) raiseFault("Overflow risk");
  if (pumpOn) {
    if (flowLpm > 0.5) noFlowSince = now;
    if (now - noFlowSince > DRYRUN_S * 1000UL) raiseFault("Dry run - no water flow");
    if (now - pumpStart > maxRunMin * 60000UL) raiseFault("Max run time reached");
  }
  if (autoMode && fault.isEmpty()) {
    if (!pumpOn && levelPct < lowPct)  setPump(true, "level low (auto)");
    if (pumpOn && levelPct >= highPct) setPump(false, "tank full (auto)");
  }
}

void sendBle() {
  JsonDocument d;
  d["lvl"] = iot::rnd(levelPct, 0); d["cm"] = iot::rnd(distCm, 1);
  d["flow"] = iot::rnd(flowLpm, 2); d["lit"] = iot::rnd(litres, 1);
  d["pump"] = pumpOn; d["mode"] = autoMode ? "AUTO" : "MANUAL";
  d["fault"] = fault; d["cloud"] = aio.connected();
  iot::sendData(d);
}

void onFeed(const String& feed, const String& value) {
  if (feed == "p07-pump") setPump(value.equalsIgnoreCase("ON"), "cloud");
  if (feed == "p07-mode") { autoMode = value.equalsIgnoreCase("AUTO"); iot::saveSetting("auto", autoMode ? "1" : "0"); }
}

// Commands: pump:on|off  mode:auto|manual  clear  resetvol
bool onCommand(const String& cmd, const String& arg, bool authed) {
  if (cmd == "setting") { loadSettings(); return true; }
  if (cmd == "pump" || cmd == "mode" || cmd == "clear" || cmd == "resetvol") {
    if (!authed) { iot::emitAck(cmd, false, "send auth:<PIN> first"); return true; }
    if (cmd == "pump") setPump(arg == "on", "BLE");
    if (cmd == "mode") {
      autoMode = arg == "auto"; iot::saveSetting("auto", autoMode ? "1" : "0");
      aio.publish("p07-mode", autoMode ? "AUTO" : "MANUAL");
    }
    if (cmd == "clear") { fault = ""; alarmOn = false; digitalWrite(PIN_BUZZER, LOW); }
    if (cmd == "resetvol") litres = 0;
    iot::emitAck(cmd, true); sendBle();
    return true;
  }
  return false;
}

void setup() {
  pinMode(PIN_TRIG, OUTPUT); pinMode(PIN_ECHO, INPUT);
  pinMode(PIN_RELAY, OUTPUT); pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_FLOW, INPUT);
  digitalWrite(PIN_RELAY, RELAY_ACTIVE_LOW ? HIGH : LOW);      // pump off at boot
  attachInterrupt(digitalPinToInterrupt(PIN_FLOW), onFlowPulse, FALLING);
  iot::begin("P07", onCommand);
  loadSettings();
  autoMode = iot::setting("auto", "1") == "1";
  // false: never switch the pump on from a stale cloud value after a reboot
  aio.begin(onFeed, SUB_FEEDS, 2, false);
  lastFlowCalc = millis();
}

void loop() {
  iot::loop();
  aio.loop();
  control();
  uint32_t now = millis();
  if (alarmOn) digitalWrite(PIN_BUZZER, (now / 300) % 2);
  if (now - lastSample >= SAMPLE_MS) {
    lastSample = now;
    distCm = readDistance();
    if (!isnan(distCm))
      levelPct = constrain((depthCm - distCm) / (depthCm - fullCm) * 100.0, 0, 100);
    sendBle();
  }
  if (aio.connected() && now - lastCloud >= CLOUD_MS && !isnan(levelPct)) {
    lastCloud = now;
    aio.publish("p07-level", levelPct, 0);
    aio.publish("p07-flow", flowLpm, 2);
  }
}
