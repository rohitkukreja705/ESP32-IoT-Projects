/*
 * P04 — Indoor Air Quality Monitor with Alarm
 * ===========================================
 * Peripherals: MQ-135 gas sensor, DHT11, 0.96" SSD1306 OLED, active buzzer
 * Wi-Fi  : ThingSpeak — ppm, temperature, humidity, Rs/R0, level every 20 s
 * BLE    : live values, one-tap clean-air calibration, alarm mute
 * Extras : temperature/humidity compensation of the MQ-135 resistance,
 *          exponential smoothing, 5-level air quality classification,
 *          warm-up handling, R0 calibration saved to flash
 *
 * NOTE: MQ-135 gives an *indicative* CO2-equivalent value (it also reacts to
 * NH3, alcohol, smoke, benzene). It is not a certified AQI instrument.
 */
#include "config.h"
#include "IoTCore.h"
#include "Cloud.h"
#include <Wire.h>
#include <DHT.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

DHT dht(PIN_DHT, DHT11);
Adafruit_SSD1306 oled(128, 64, &Wire, -1);
bool oledOK = false;

// MQ-135 curve for CO2 (from datasheet log-log fit)
const float PARA = 116.6020682, PARB = 2.769034857;
const float ATMOCO2 = 420.0;                        // outdoor CO2 today, ppm

float temp = NAN, hum = NAN, rs = NAN, r0 = 10.0, ratio = NAN, ppm = NAN;
int level = 0; bool muted = false, alarmOn = false;
uint32_t lastSample = 0, lastUpload = 0, alarmMuteUntil = 0;
float alarmPpm = DEF_ALARM_PPM;
const char* LEVELS[] = { "Warming up", "Good", "Moderate", "Poor", "Unhealthy", "Hazardous" };

// Correction factor for temperature and humidity (MQ-135 datasheet curves)
float correction(float t, float h) {
  if (isnan(t) || isnan(h)) return 1.0;
  if (t < 20) return 0.00035 * t * t - 0.02718 * t + 1.39538 - (h - 33.) * 0.0018;
  return -0.003333333 * t + -0.001923077 * h + 1.130128205;
}

// Sensor resistance in kOhm. RL value cancels out in Rs/R0, so 10 k is used.
float readRs() {
  uint32_t s = 0;
  for (int i = 0; i < 32; i++) { s += analogReadMilliVolts(PIN_MQ135); delayMicroseconds(300); }
  float vout = (s / 32.0) * DIVIDER_RATIO;
  if (vout < 1) vout = 1;
  float rsRaw = 10.0 * (MQ_VCC_MV - vout) / vout;
  return rsRaw / correction(temp, hum);
}

int classify(float p) {
  if (millis() < WARMUP_S * 1000UL) return 0;
  if (p < 600) return 1;
  if (p < 1000) return 2;
  if (p < 1500) return 3;
  if (p < 2500) return 4;
  return 5;
}

void sample() {
  float t = dht.readTemperature(), h = dht.readHumidity();
  if (!isnan(t)) temp = t;
  if (!isnan(h)) hum = h;
  rs = readRs();
  ratio = rs / r0;
  float p = PARA * pow(ratio, -PARB);
  ppm = isnan(ppm) ? p : ppm * 0.7 + p * 0.3;      // exponential smoothing
  level = classify(ppm);

  bool alarmNow = level > 0 && ppm >= alarmPpm;
  if (alarmNow && !alarmOn) iot::sendEvent("air_alarm", "Air quality " + String(LEVELS[level]) + ", " + String(ppm, 0) + " ppm");
  if (!alarmNow && alarmOn) iot::sendEvent("air_ok", "Air quality back to normal");
  alarmOn = alarmNow;
}

void drawOled() {
  if (!oledOK) return;
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);
  oled.setTextSize(1); oled.setCursor(0, 0);
  oled.print("AIR QUALITY  ");
  oled.print(iot::wifiOK() ? "W" : "-"); oled.print(iot::bleConnected() ? " B" : " -");
  oled.setTextSize(3); oled.setCursor(0, 14);
  if (level == 0) { oled.setTextSize(2); oled.print("Warm-up"); }
  else oled.print((int)ppm);
  oled.setTextSize(1); oled.setCursor(98, 28); if (level) oled.print("ppm");
  oled.setCursor(0, 42); oled.print(LEVELS[level]);
  if (alarmOn) oled.print(muted ? " (muted)" : " !ALARM");
  oled.setCursor(0, 54);
  oled.printf("%.1fC  %.0f%%RH  R%.2f", temp, hum, ratio);
  oled.display();
}

void buzzer() {
  bool sound = alarmOn && millis() > alarmMuteUntil;
  digitalWrite(PIN_BUZZER, sound && (millis() / 250) % 4 == 0);   // short beeps
  muted = alarmOn && !sound;
}

void sendBle() {
  JsonDocument d;
  d["ppm"] = iot::rnd(ppm, 0); d["t"] = iot::rnd(temp); d["h"] = iot::rnd(hum, 0);
  d["rs"] = iot::rnd(rs, 2); d["r0"] = iot::rnd(r0, 2); d["ratio"] = iot::rnd(ratio, 3);
  d["lvl"] = level; d["cat"] = LEVELS[level]; d["alarm"] = alarmOn;
  iot::sendData(d);
}

// Commands: calibrate (in clean outdoor air), mute
bool onCommand(const String& cmd, const String& arg, bool authed) {
  if (cmd == "setting") { alarmPpm = iot::settingF("alarmppm", DEF_ALARM_PPM); return true; }
  if (cmd == "mute") { alarmMuteUntil = millis() + 10 * 60000UL; iot::emitAck(cmd, true, "muted 10 min"); return true; }
  if (cmd == "calibrate") {
    if (!authed) { iot::emitAck(cmd, false, "send auth:<PIN> first"); return true; }
    float sum = 0;
    for (int i = 0; i < 20; i++) { sum += readRs(); delay(100); }
    float rsAvg = sum / 20;
    r0 = rsAvg * pow(ATMOCO2 / PARA, 1.0 / PARB);    // R0 such that clean air = ATMOCO2 ppm
    iot::saveSetting("r0", String(r0, 3));
    ppm = NAN;
    iot::emitAck(cmd, true, "R0=" + String(r0, 2) + " kOhm");
    return true;
  }
  return false;
}

void setup() {
  pinMode(PIN_BUZZER, OUTPUT);
  analogSetAttenuation(ADC_11db);
  iot::begin("P04", onCommand);
  r0 = iot::settingF("r0", 10.0);
  alarmPpm = iot::settingF("alarmppm", DEF_ALARM_PPM);
  dht.begin();
  Wire.begin(21, 22);
  oledOK = oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR);
  if (!oledOK) Serial.println("[OLED] not found");
}

void loop() {
  iot::loop();
  buzzer();
  uint32_t now = millis();
  if (now - lastSample >= SAMPLE_MS) {
    lastSample = now;
    sample();
    drawOled();
    sendBle();
  }
  if (iot::wifiOK() && level > 0 && now - lastUpload >= TS_INTERVAL_S * 1000UL) {
    lastUpload = now;
    float f[5] = { ppm, temp, hum, ratio, (float)level };
    cloud::thingSpeakUpdate(f, 5, LEVELS[level]);
  }
}
