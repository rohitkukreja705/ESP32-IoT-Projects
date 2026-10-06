/*
 * P01 — Smart Weather Station with Rain Forecast
 * ===============================================
 * Sensors : DHT11 (temperature, humidity), BMP180 (pressure),
 *           LDR (light), FC-37 rain sensor
 * Wi-Fi   : uploads 8 fields to ThingSpeak every 20 s (charts + public view)
 * BLE     : live readings every 2 s to the Web Bluetooth dashboard
 * Extras  : heat index, dew point, 3-hour pressure trend -> short-term forecast,
 *           rain-start / rain-stop events
 *
 * Board: ESP32 Dev Module | Partition: Minimal SPIFFS (1.9MB APP with OTA)
 * Libraries: NimBLE-Arduino 2.x, ArduinoJson 7, PubSubClient,
 *            DHT sensor library, Adafruit BMP085 Library
 */
#include "config.h"
#include "IoTCore.h"
#include "Cloud.h"
#include <Wire.h>
#include <DHT.h>
#include <Adafruit_BMP085.h>

DHT dht(PIN_DHT, DHT11);
Adafruit_BMP085 bmp;
bool bmpOK = false;

struct Reading {
  float temp = NAN, hum = NAN, pres = NAN, light = NAN, rain = NAN;
  float heatIndex = NAN, dewPoint = NAN;
  bool raining = false;
} r;

// pressure history for trend (18 samples x 10 min = 3 h)
float presHist[18]; int presCount = 0, presIdx = 0;
String forecast = "Collecting data";
uint32_t lastSample = 0, lastUpload = 0, lastTrend = 0;
uint32_t uploadPeriod = TS_INTERVAL_S * 1000UL;
bool forceUpload = false;

// Average several ADC readings (in millivolts) to reduce noise.
float readMilliVolts(int pin, int n = 16) {
  uint32_t s = 0;
  for (int i = 0; i < n; i++) { s += analogReadMilliVolts(pin); delayMicroseconds(200); }
  return s / (float)n;
}

// Magnus formula, valid -45..60 °C
float dewPointC(float t, float h) {
  if (isnan(t) || isnan(h) || h <= 0) return NAN;
  const float a = 17.62, b = 243.12;
  float g = log(h / 100.0) + a * t / (b + t);
  return b * g / (a - g);
}

// Very small Zambretti-style rule set based on 3-hour pressure change.
void updateForecast() {
  if (presCount < 6) { forecast = "Collecting data"; return; }   // need >= 1 h
  int oldest = (presIdx - presCount + 18) % 18;
  float trend = presHist[(presIdx - 1 + 18) % 18] - presHist[oldest];
  // scale to a 3-hour change
  trend = trend * 18.0 / presCount;
  float p = r.pres;
  if (trend <= -3.0)       forecast = "Storm / heavy rain likely";
  else if (trend <= -1.6)  forecast = "Rain likely";
  else if (trend < -0.5)   forecast = "Clouds increasing";
  else if (trend < 0.5)    forecast = (p > 1015) ? "Fair, stable" : "Unsettled, stable";
  else if (trend < 1.6)    forecast = "Improving";
  else                     forecast = "Clearing, fair weather";
}

void readSensors() {
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  if (!isnan(t)) r.temp = t;
  if (!isnan(h)) r.hum = h;
  if (bmpOK) r.pres = bmp.readPressure() / 100.0;          // Pa -> hPa
  // LDR on high side: more light -> higher voltage
  r.light = constrain(readMilliVolts(PIN_LDR) / 3300.0 * 100.0, 0, 100);
  // Rain plate: dry ~3300 mV, wet -> lower voltage
  float rainMv = readMilliVolts(PIN_RAIN_AO);
  r.rain = constrain((3300.0 - rainMv) / 3300.0 * 100.0, 0, 100);
  r.heatIndex = (isnan(r.temp) || isnan(r.hum)) ? NAN : dht.computeHeatIndex(r.temp, r.hum, false);
  r.dewPoint = dewPointC(r.temp, r.hum);

  bool wet = digitalRead(PIN_RAIN_DO) == LOW || r.rain > iot::settingF("rainthr", 30);
  if (wet != r.raining) {
    r.raining = wet;
    iot::sendEvent(wet ? "rain_start" : "rain_stop", wet ? "Rain detected" : "Rain stopped");
    forceUpload = true;
  }
}

void sendBle() {
  JsonDocument d;
  d["t"]  = iot::rnd(r.temp);
  d["h"]  = iot::rnd(r.hum, 0);
  d["p"]  = iot::rnd(r.pres);
  d["l"]  = iot::rnd(r.light, 0);
  d["rn"] = iot::rnd(r.rain, 0);
  d["hi"] = iot::rnd(r.heatIndex);
  d["dp"] = iot::rnd(r.dewPoint);
  d["fc"] = forecast;
  d["wifi"] = iot::wifiOK();
  iot::sendData(d);
}

void upload() {
  float f[8] = { r.temp, r.hum, r.pres, r.light, r.rain, r.heatIndex, r.dewPoint,
                 (float)WiFi.RSSI() };
  bool ok = cloud::thingSpeakUpdate(f, 8, forecast);
  if (!ok) iot::sendEvent("upload_failed", "ThingSpeak upload failed");
}

// Project-specific commands (everything else is handled by IoTCore)
bool onCommand(const String& cmd, const String& arg, bool authed) {
  if (cmd == "read")   { readSensors(); sendBle(); return true; }
  if (cmd == "upload") { forceUpload = true; iot::emitAck(cmd, true, "queued"); return true; }
  if (cmd == "setting") return true;   // a threshold changed: read live via settingF()
  return false;
}

void setup() {
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_RAIN_DO, INPUT);
  analogSetAttenuation(ADC_11db);           // full 0-3.3 V range
  iot::begin("P01", onCommand);
  dht.begin();
  Wire.begin(21, 22);
  bmpOK = bmp.begin();
  if (!bmpOK) Serial.println("[BMP180] not found - check SDA/SCL wiring");
}

void loop() {
  iot::loop();
  uint32_t now = millis();

  if (now - lastSample >= SAMPLE_MS) {
    lastSample = now;
    readSensors();
    sendBle();
    uploadPeriod = max(15, (int)iot::settingF("tsint", TS_INTERVAL_S)) * 1000UL;
  }
  if (bmpOK && (now - lastTrend >= TREND_SAMPLE_MS || presCount == 0) && !isnan(r.pres)) {
    lastTrend = now;
    presHist[presIdx] = r.pres;
    presIdx = (presIdx + 1) % 18;
    if (presCount < 18) presCount++;
    updateForecast();
  }
  if ((now - lastUpload >= uploadPeriod || forceUpload) && iot::wifiOK() && now - lastUpload > 15500) {
    lastUpload = now;
    forceUpload = false;
    upload();
  }
  // LED: solid = Wi-Fi up, slow blink = BLE connected, off = offline
  digitalWrite(PIN_LED, iot::wifiOK() ? HIGH : (iot::bleConnected() ? (now / 500) % 2 : LOW));
}
