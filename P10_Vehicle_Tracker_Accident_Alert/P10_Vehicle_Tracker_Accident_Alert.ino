/*
 * P10 — Vehicle Tracking & Accident Alert System
 * ==============================================
 * Peripherals: NEO-6M GPS, MPU6050 accelerometer/gyro, buzzer, push button
 * Wi-Fi  : Supabase (through the driver's phone hotspot) — location trail
 *          and accident / SOS / geofence alerts with a Google Maps link
 * BLE    : live position, speed, g-force and tilt on the phone; alert
 *          notifications even without internet
 * Logic  : impact (> crash g) or rollover (> tilt for 3 s) starts a 15 s
 *          countdown with buzzer; the driver can cancel with the button;
 *          otherwise the alert is sent. Holding the button 3 s = manual SOS.
 *          Adaptive logging (30 s moving / 5 min parked), offline buffer,
 *          geofence exit alert.
 */
#include "config.h"
#include "IoTCore.h"
#include "Cloud.h"
#include <TinyGPSPlus.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

TinyGPSPlus gps;
HardwareSerial gpsSerial(2);
Adafruit_MPU6050 mpu;
bool mpuOK = false;

float gNow = 0, gPeak = 0, pitch = 0, roll = 0;
float crashG, tiltDeg;
double fenceLat = 0, fenceLng = 0; float fenceR = 0; bool outsideFence = false;

enum AlertState { NORMAL, COUNTDOWN, SENT } st = NORMAL;
String alertType, alertDetail; float alertG = 0;
bool alertDelivered = true; uint32_t lastAlertTry = 0;
uint32_t countdownStart = 0, tiltSince = 0, lastLog = 0, lastBle = 0, lastImu = 0, btnDownAt = 0;

struct Fix { double lat, lng; float spd, hdg; int sats; String ts; };
Fix buf[20]; int bufN = 0;          // offline buffer (newest kept)

void loadSettings() {
  crashG = iot::settingF("crashg", DEF_CRASH_G);
  tiltDeg = iot::settingF("tilt", DEF_TILT_DEG);
  String f = iot::setting("fence", "");
  if (f.length()) sscanf(f.c_str(), "%lf,%lf,%f", &fenceLat, &fenceLng, &fenceR);
}

String mapsLink(double lat, double lng) {
  return "https://maps.google.com/?q=" + String(lat, 6) + "," + String(lng, 6);
}

bool sendAlert(const String& type, const String& detail) {
  JsonDocument d;
  bool fix = gps.location.isValid();
  d["type"] = type; d["detail"] = detail; d["device"] = iot::deviceName;
  d["g_force"] = iot::rnd(alertG, 2);
  if (fix) { d["lat"] = gps.location.lat(); d["lng"] = gps.location.lng(); d["maps_url"] = mapsLink(gps.location.lat(), gps.location.lng()); }
  d["speed_kmph"] = gps.speed.isValid() ? iot::rnd(gps.speed.kmph()) : 0;
  String s; serializeJson(d, s);
  iot::sendEvent(type, detail + (fix ? " " + mapsLink(gps.location.lat(), gps.location.lng()) : " (no GPS fix)"));
  return cloud::supabaseInsert("vehicle_alerts", s);
}

void readImu() {
  if (!mpuOK || millis() - lastImu < 20) return;          // 50 Hz
  lastImu = millis();
  sensors_event_t a, g, t;
  mpu.getEvent(&a, &g, &t);
  float ax = a.acceleration.x / 9.80665, ay = a.acceleration.y / 9.80665, az = a.acceleration.z / 9.80665;
  gNow = sqrt(ax * ax + ay * ay + az * az);
  if (gNow > gPeak) gPeak = gNow;
  pitch = atan2(-ax, sqrt(ay * ay + az * az)) * 57.2958;
  roll  = atan2(ay, az) * 57.2958;

  if (st != NORMAL) return;
  if (gNow > crashG) { alertType = "accident_impact"; alertG = gNow; st = COUNTDOWN; countdownStart = millis(); }
  bool tilted = fabs(pitch) > tiltDeg || fabs(roll) > tiltDeg;
  if (!tilted) tiltSince = 0;
  else if (!tiltSince) tiltSince = millis();
  else if (millis() - tiltSince > TILT_HOLD_MS) { alertType = "accident_rollover"; alertG = gNow; st = COUNTDOWN; countdownStart = millis(); }
  if (st == COUNTDOWN) iot::sendEvent("countdown", alertType + " - press the button within " + String(CANCEL_WINDOW_S) + " s to cancel");
}

void handleButton() {
  bool down = digitalRead(PIN_BUTTON) == LOW;
  uint32_t now = millis();
  if (down && !btnDownAt) btnDownAt = now;
  if (!down && btnDownAt) {
    uint32_t held = now - btnDownAt; btnDownAt = 0;
    if (held > 50 && held < 3000 && st != NORMAL) {
      st = NORMAL; tiltSince = 0; digitalWrite(PIN_BUZZER, LOW);
      iot::sendEvent("cancelled", "Driver cancelled the alert (false alarm)");
    }
  }
  if (down && btnDownAt && now - btnDownAt >= 3000 && st == NORMAL) {
    btnDownAt = 0; alertType = "sos"; alertG = gNow;
    st = SENT; sendAlert("sos", "Manual SOS from driver");
  }
}

void alertLogic() {
  uint32_t now = millis();
  if (st == COUNTDOWN) {
    digitalWrite(PIN_BUZZER, (now / 250) % 2);
    if (now - countdownStart > CANCEL_WINDOW_S * 1000UL) {
      st = SENT;
      alertDetail = "Possible accident, peak " + String(alertG, 1) + " g";
      alertDelivered = sendAlert(alertType, alertDetail);
      lastAlertTry = now;
      if (!alertDelivered) iot::sendEvent("alert_pending", "No internet - alert shown on BLE, retrying every 30 s");
    }
  } else if (st == SENT) {
    if (!alertDelivered && iot::wifiOK() && now - lastAlertTry > 30000) {
      lastAlertTry = now;
      alertDelivered = sendAlert(alertType, alertDetail + " (delayed)");
    }
    digitalWrite(PIN_BUZZER, (now / 1000) % 2 == 0 && (now % 1000) < 150);   // slow chirp
  } else digitalWrite(PIN_BUZZER, LOW);
}

void checkFence() {
  if (fenceR <= 0 || !gps.location.isValid()) return;
  double d = TinyGPSPlus::distanceBetween(gps.location.lat(), gps.location.lng(), fenceLat, fenceLng);
  bool out = d > fenceR;
  if (out != outsideFence) {
    outsideFence = out;
    alertG = 0;
    sendAlert(out ? "geofence_exit" : "geofence_enter", String(d, 0) + " m from home");
  }
}

void logLocation() {
  if (!gps.location.isValid()) return;
  float spd = gps.speed.isValid() ? gps.speed.kmph() : 0;
  uint32_t period = spd > MOVING_KMPH ? MOVING_LOG_MS : PARKED_LOG_MS;
  if (lastLog && millis() - lastLog < period) return;
  lastLog = millis();
  Fix f = { gps.location.lat(), gps.location.lng(), spd, (float)gps.course.deg(), (int)gps.satellites.value(), iot::timestamp() };
  if (bufN == 20) { for (int i = 1; i < 20; i++) buf[i - 1] = buf[i]; bufN = 19; }   // drop oldest
  buf[bufN++] = f;
  if (!iot::wifiOK()) return;
  // flush the whole buffer in one request
  JsonDocument d; JsonArray arr = d.to<JsonArray>();
  for (int i = 0; i < bufN; i++) {
    JsonObject o = arr.add<JsonObject>();
    o["lat"] = buf[i].lat; o["lng"] = buf[i].lng; o["speed_kmph"] = iot::rnd(buf[i].spd);
    o["heading"] = iot::rnd(buf[i].hdg, 0); o["satellites"] = buf[i].sats; o["device"] = iot::deviceName;
    if (buf[i].ts.startsWith("20")) o["recorded_at"] = buf[i].ts; else o["recorded_at"] = nullptr;
  }
  String s; serializeJson(d, s);
  if (cloud::supabaseInsert("vehicle_locations", s)) bufN = 0;
}

void sendBle() {
  JsonDocument d;
  bool fix = gps.location.isValid();
  d["fix"] = fix;
  if (fix) { d["lat"] = serialized(String(gps.location.lat(), 6)); d["lng"] = serialized(String(gps.location.lng(), 6)); }
  d["spd"] = gps.speed.isValid() ? iot::rnd(gps.speed.kmph()) : 0;
  d["sat"] = gps.satellites.value();
  d["g"] = iot::rnd(gPeak, 2); d["pitch"] = iot::rnd(pitch, 0); d["roll"] = iot::rnd(roll, 0);
  d["state"] = st == NORMAL ? "normal" : st == COUNTDOWN ? "countdown" : "alert";
  d["buf"] = bufN;
  iot::sendData(d);
  gPeak = gNow;
}

// Commands: reset (clear alert), sos, fencehere:<metres>
bool onCommand(const String& cmd, const String& arg, bool authed) {
  if (cmd == "setting") { loadSettings(); return true; }
  if (cmd == "reset") { st = NORMAL; tiltSince = 0; iot::emitAck(cmd, true, "alert cleared"); return true; }
  if (cmd == "sos") { alertG = gNow; st = SENT; sendAlert("sos", "SOS from phone app"); iot::emitAck(cmd, true); return true; }
  if (cmd == "fencehere") {
    if (!authed) { iot::emitAck(cmd, false, "send auth:<PIN> first"); return true; }
    if (!gps.location.isValid()) { iot::emitAck(cmd, false, "no GPS fix yet"); return true; }
    String f = String(gps.location.lat(), 6) + "," + String(gps.location.lng(), 6) + "," + (arg.length() ? arg : String("300"));
    iot::saveSetting("fence", f); loadSettings(); outsideFence = false;
    iot::emitAck(cmd, true, "fence " + f);
    return true;
  }
  return false;
}

void setup() {
  pinMode(PIN_BUZZER, OUTPUT); pinMode(PIN_BUTTON, INPUT_PULLUP);
  iot::begin("P10", onCommand);
  loadSettings();
  gpsSerial.begin(9600, SERIAL_8N1, PIN_GPS_RX, PIN_GPS_TX);
  Wire.begin(21, 22);
  mpuOK = mpu.begin();
  if (mpuOK) { mpu.setAccelerometerRange(MPU6050_RANGE_8_G); mpu.setFilterBandwidth(MPU6050_BAND_21_HZ); }
  else Serial.println("[MPU6050] not found");
}

void loop() {
  iot::loop();
  while (gpsSerial.available()) gps.encode(gpsSerial.read());
  readImu();
  handleButton();
  alertLogic();
  uint32_t now = millis();
  if (now - lastBle >= 1000) { lastBle = now; sendBle(); checkFence(); }
  logLocation();
}
