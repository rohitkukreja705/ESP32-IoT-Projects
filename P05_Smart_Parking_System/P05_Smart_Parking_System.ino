/*
 * P05 — Smart Parking System with Automatic Gate
 * ==============================================
 * Peripherals: 2 x HC-SR04 ultrasonic (one per slot), IR obstacle sensor
 *              (gate), SG90 servo (barrier)
 * Wi-Fi  : Supabase — live slot table (PATCH) + event log (INSERT); any
 *          browser can show free slots through the Supabase REST API
 * BLE    : live slot map, manual gate open/close for the attendant
 * Logic  : car at gate -> gate opens only if a slot is free, closes after the
 *          car has passed; "Parking FULL" event otherwise. Slot changes are
 *          debounced (3 equal readings) and uploaded; failed uploads retry.
 */
#include "config.h"
#include "IoTCore.h"
#include "Cloud.h"
#include <ESP32Servo.h>

Servo gate;
const int TRIG[NUM_SLOTS] = { PIN_TRIG1, PIN_TRIG2 };
const int ECHO[NUM_SLOTS] = { PIN_ECHO1, PIN_ECHO2 };

float distCm[NUM_SLOTS];
bool occupied[NUM_SLOTS], pendingSync[NUM_SLOTS];
int  sameCount[NUM_SLOTS];
bool gateOpen = false, carAtGate = false, fullNotified = false;
uint32_t lastScan = 0, gateClearSince = 0, lastRetry = 0;
float occupiedCm = DEF_OCCUPIED_CM;

float readDistance(int i) {
  digitalWrite(TRIG[i], LOW); delayMicroseconds(3);
  digitalWrite(TRIG[i], HIGH); delayMicroseconds(10);
  digitalWrite(TRIG[i], LOW);
  unsigned long us = pulseIn(ECHO[i], HIGH, 25000);        // 25 ms ~ 4 m
  if (us == 0) return 400;                                  // nothing in range
  return us * 0.0343 / 2.0;
}

int freeSlots() { int f = 0; for (int i = 0; i < NUM_SLOTS; i++) if (!occupied[i]) f++; return f; }

void logEvent(const String& ev, int slot) {
  JsonDocument d;
  d["event"] = ev; d["slot"] = slot; d["free_slots"] = freeSlots(); d["device"] = iot::deviceName;
  String s; serializeJson(d, s);
  cloud::supabaseInsert("parking_events", s);
}

bool syncSlot(int i) {
  JsonDocument d;
  d["occupied"] = occupied[i]; d["distance_cm"] = iot::rnd(distCm[i], 0);
  String t = iot::timestamp();
  if (t.startsWith("20")) d["updated_at"] = t;        // only once NTP time is known
  String s; serializeJson(d, s);
  return cloud::supabaseUpdate("parking_slots", "id=eq." + String(i + 1), s);
}

void moveGate(bool open, const char* why) {
  if (open == gateOpen) return;
  gateOpen = open;
  gate.write(open ? GATE_OPEN_DEG : GATE_CLOSED_DEG);
  iot::sendEvent("gate", String(open ? "OPEN" : "CLOSED") + " (" + why + ")");
}

void scanSlots() {
  for (int i = 0; i < NUM_SLOTS; i++) {
    distCm[i] = readDistance(i);
    bool occ = distCm[i] < occupiedCm;
    if (occ != occupied[i]) {
      if (++sameCount[i] >= 3) {                            // debounce
        occupied[i] = occ; sameCount[i] = 0;
        iot::sendEvent("slot", "Slot " + String(i + 1) + (occ ? " occupied" : " free"));
        pendingSync[i] = true;
      }
    } else sameCount[i] = 0;
    delay(30);                                              // avoid echo cross-talk
  }
}

void gateLogic() {
  bool car = digitalRead(PIN_IR) == LOW;
  uint32_t now = millis();
  if (car && !carAtGate) {                                  // a car just arrived
    if (freeSlots() > 0) { moveGate(true, "car arrived"); fullNotified = false; }
    else if (!fullNotified) {
      fullNotified = true;
      iot::sendEvent("full", "Parking FULL - gate stays closed");
      if (iot::wifiOK()) logEvent("full_rejected", 0);
    }
  }
  if (!car && carAtGate) gateClearSince = now;
  if (gateOpen && !car && now - gateClearSince > GATE_HOLD_MS) moveGate(false, "car passed");
  carAtGate = car;
}

void uploadPending() {
  if (!iot::wifiOK()) return;
  for (int i = 0; i < NUM_SLOTS; i++) {
    if (!pendingSync[i]) continue;
    if (syncSlot(i)) {
      pendingSync[i] = false;
      logEvent(occupied[i] ? "slot_occupied" : "slot_freed", i + 1);
    }
  }
}

void sendBle() {
  JsonDocument d;
  JsonArray s = d["s"].to<JsonArray>();
  JsonArray ds = d["d"].to<JsonArray>();
  for (int i = 0; i < NUM_SLOTS; i++) { s.add(occupied[i] ? 1 : 0); ds.add(iot::rnd(distCm[i], 0)); }
  d["free"] = freeSlots(); d["gate"] = gateOpen ? "open" : "closed"; d["car"] = carAtGate;
  iot::sendData(d);
}

// Commands: gate:open | gate:close
bool onCommand(const String& cmd, const String& arg, bool authed) {
  if (cmd == "setting") { occupiedCm = iot::settingF("occcm", DEF_OCCUPIED_CM); return true; }
  if (cmd == "gate") {
    if (!authed) { iot::emitAck(cmd, false, "send auth:<PIN> first"); return true; }
    moveGate(arg == "open", "attendant");
    if (arg == "open") gateClearSince = millis();
    iot::emitAck(cmd, true, gateOpen ? "open" : "closed");
    return true;
  }
  if (cmd == "sync") { for (int i = 0; i < NUM_SLOTS; i++) pendingSync[i] = true; iot::emitAck(cmd, true); return true; }
  return false;
}

void setup() {
  for (int i = 0; i < NUM_SLOTS; i++) {
    pinMode(TRIG[i], OUTPUT); pinMode(ECHO[i], INPUT);
    occupied[i] = false; pendingSync[i] = true; sameCount[i] = 0; distCm[i] = 0;
  }
  pinMode(PIN_IR, INPUT);
  iot::begin("P05", onCommand);
  occupiedCm = iot::settingF("occcm", DEF_OCCUPIED_CM);
  gate.setPeriodHertz(50);
  gate.attach(PIN_SERVO, 500, 2400);
  gate.write(GATE_CLOSED_DEG);
}

void loop() {
  iot::loop();
  gateLogic();
  uint32_t now = millis();
  if (now - lastScan >= SCAN_MS) {
    lastScan = now;
    scanSlots();
    sendBle();
  }
  if (now - lastRetry >= 2000) { lastRetry = now; uploadPending(); }
}
