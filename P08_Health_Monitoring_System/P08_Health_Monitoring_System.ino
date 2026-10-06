/*
 * P08 — IoT Health Monitoring System (Heart Rate, SpO2, Body Temperature)
 * =======================================================================
 * Peripherals: MAX30102 pulse-oximeter, DS18B20 temperature probe,
 *              SSD1306 OLED, buzzer
 * Wi-Fi  : ThingSpeak — HR, SpO2, temperature, alert flag every 20 s
 *          (only while a finger is on the sensor and readings are valid)
 * BLE    : live vitals on the phone, alert events, configurable limits
 * Extras : non-blocking 25 Hz sampling with a sliding 4-second window,
 *          Maxim SpO2/HR algorithm, finger detection, averaged HR,
 *          non-blocking DS18B20 conversion
 *
 * DISCLAIMER: educational project, NOT a medical device. Do not use it for
 * diagnosis or treatment decisions.
 */
#include "config.h"
#include "IoTCore.h"
#include "Cloud.h"
#include <Wire.h>
#include <MAX30105.h>
#include <spo2_algorithm.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

MAX30105 pox;
OneWire oneWire(PIN_DS18B20);
DallasTemperature ds(&oneWire);
Adafruit_SSD1306 oled(128, 64, &Wire, -1);
bool poxOK = false, oledOK = false;

const int BUF = 100;                    // 4 s at 25 samples/s
uint32_t irBuf[BUF], redBuf[BUF];
int filled = 0, newSamples = 0;
bool finger = false;

float hr = NAN, spo2 = NAN, bodyTemp = NAN;
float hrHist[4]; int hrN = 0, hrI = 0;
bool alertOn = false; String alertMsg = "";
uint32_t lastTempReq = 0, lastUpload = 0, lastUi = 0;
float hrLow, hrHigh, spo2Low, tempHigh;

void loadSettings() {
  hrLow = iot::settingF("hrlow", DEF_HR_LOW);   hrHigh = iot::settingF("hrhigh", DEF_HR_HIGH);
  spo2Low = iot::settingF("spo2low", DEF_SPO2_LOW); tempHigh = iot::settingF("temphigh", DEF_TEMP_HIGH);
}

void processWindow() {
  int32_t s, h; int8_t sv, hv;
  maxim_heart_rate_and_oxygen_saturation(irBuf, BUF, redBuf, &s, &sv, &h, &hv);
  if (hv && h > 30 && h < 220) {
    hrHist[hrI] = h; hrI = (hrI + 1) % 4; if (hrN < 4) hrN++;
    float sum = 0; for (int i = 0; i < hrN; i++) sum += hrHist[i];
    hr = sum / hrN;
  }
  if (sv && s > 70 && s <= 100) spo2 = s;
}

void readPox() {
  if (!poxOK) return;
  pox.check();
  while (pox.available()) {
    uint32_t red = pox.getFIFORed(), ir = pox.getFIFOIR();
    pox.nextSample();
    bool f = ir > FINGER_IR_MIN;
    if (f != finger) {
      finger = f; filled = 0; newSamples = 0; hrN = 0;
      if (!f) { hr = NAN; spo2 = NAN; }
      iot::sendEvent("finger", f ? "Finger detected - hold still" : "Finger removed");
    }
    if (!finger) continue;
    if (filled < BUF) { irBuf[filled] = ir; redBuf[filled] = red; filled++; }
    else {                               // slide the window by one sample
      memmove(irBuf, irBuf + 1, (BUF - 1) * sizeof(uint32_t));
      memmove(redBuf, redBuf + 1, (BUF - 1) * sizeof(uint32_t));
      irBuf[BUF - 1] = ir; redBuf[BUF - 1] = red;
    }
    if (filled == BUF && ++newSamples >= 25) { newSamples = 0; processWindow(); }   // every 1 s
  }
}

void readTemp() {
  if (millis() - lastTempReq < 1000) return;
  float t = ds.getTempCByIndex(0);
  if (t > -50 && t < 85) bodyTemp = t;   // -127 = sensor missing
  ds.requestTemperatures();              // non-blocking; read on next call
  lastTempReq = millis();
}

void checkAlerts() {
  String m = "";
  if (finger && !isnan(hr) && (hr < hrLow || hr > hrHigh)) m += "HR " + String(hr, 0) + " bpm. ";
  if (finger && !isnan(spo2) && spo2 < spo2Low) m += "SpO2 " + String(spo2, 0) + "%. ";
  if (!isnan(bodyTemp) && bodyTemp > tempHigh) m += "Temp " + String(bodyTemp, 1) + "C. ";
  bool a = m.length() > 0;
  if (a && (!alertOn || m != alertMsg)) iot::sendEvent("vital_alert", m);
  alertOn = a; alertMsg = m;
  digitalWrite(PIN_BUZZER, alertOn && (millis() / 200) % 5 == 0);
}

void drawOled() {
  if (!oledOK) return;
  oled.clearDisplay(); oled.setTextColor(SSD1306_WHITE);
  oled.setTextSize(1); oled.setCursor(0, 0);
  oled.printf("HEALTH %s %s", iot::wifiOK() ? "WiFi" : "----", iot::bleConnected() ? "BLE" : "");
  if (!finger) { oled.setCursor(0, 24); oled.setTextSize(2); oled.print("Place"); oled.setCursor(0, 42); oled.print("finger"); }
  else {
    oled.setTextSize(2); oled.setCursor(0, 14);
    oled.print(isnan(hr) ? String("--") : String(hr, 0)); oled.setTextSize(1); oled.print(" bpm");
    if ((millis() / 400) % 2) oled.fillCircle(118, 20, 4, SSD1306_WHITE);   // heartbeat dot
    oled.setTextSize(2); oled.setCursor(0, 34);
    oled.print(isnan(spo2) ? String("--") : String(spo2, 0)); oled.setTextSize(1); oled.print(" %SpO2");
  }
  oled.setTextSize(1); oled.setCursor(0, 56);
  oled.print(isnan(bodyTemp) ? String("Temp --") : "Temp " + String(bodyTemp, 1) + "C");
  if (alertOn) oled.print("  ALERT");
  oled.display();
}

void sendBle() {
  JsonDocument d;
  d["hr"] = iot::rnd(hr, 0); d["spo2"] = iot::rnd(spo2, 0); d["temp"] = iot::rnd(bodyTemp);
  d["finger"] = finger; d["alert"] = alertOn;
  if (alertOn) d["msg"] = alertMsg;
  iot::sendData(d);
}

bool onCommand(const String& cmd, const String& arg, bool authed) {
  if (cmd == "setting") { loadSettings(); return true; }
  return false;
}

void setup() {
  pinMode(PIN_BUZZER, OUTPUT);
  iot::begin("P08", onCommand);
  loadSettings();
  Wire.begin(21, 22);
  poxOK = pox.begin(Wire, I2C_SPEED_FAST);
  if (poxOK) pox.setup(60, 4, 2, 100, 411, 4096);   // brightness, avg, Red+IR, 100 sps, 411 us, range
  else Serial.println("[MAX30102] not found");
  ds.begin(); ds.setWaitForConversion(false); ds.requestTemperatures();
  oledOK = oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR);
}

void loop() {
  iot::loop();
  readPox();
  readTemp();
  checkAlerts();
  uint32_t now = millis();
  if (now - lastUi >= 1000) { lastUi = now; drawOled(); sendBle(); }
  if (iot::wifiOK() && finger && !isnan(hr) && now - lastUpload >= TS_INTERVAL_S * 1000UL) {
    lastUpload = now;
    float f[4] = { hr, spo2, bodyTemp, alertOn ? 1.0f : 0.0f };
    cloud::thingSpeakUpdate(f, 4, alertOn ? alertMsg : "normal");
  }
}
