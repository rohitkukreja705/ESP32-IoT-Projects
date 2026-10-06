/*
 * P02 — Smart Energy Monitor with Overload Protection
 * ====================================================
 * Peripherals: ACS712-5A current sensor, ZMPT101B voltage sensor,
 *              16x2 I2C LCD, 1-channel relay
 * Wi-Fi  : Adafruit IO over MQTT — voltage, current, power, energy feeds and
 *          a "relay" toggle feed for remote ON/OFF from the dashboard
 * BLE    : live V / I / W / PF / kWh / cost, relay control, calibration
 * Extras : true RMS + real power + power factor from simultaneous sampling,
 *          kWh counter saved to flash, overload auto-trip
 *
 * !!! SAFETY: the ZMPT101B and the relay connect to 230 V AC mains. Build it
 * inside a closed plastic enclosure, use a fuse, never touch the board while
 * plugged in, and get help from someone experienced with mains wiring. !!!
 *
 * Libraries: NimBLE-Arduino 2.x, ArduinoJson 7, PubSubClient, LiquidCrystal_I2C
 */
#include "config.h"
#include "IoTCore.h"
#include "Cloud.h"
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(LCD_ADDR, 16, 2);
cloud::AdafruitIO aio;
const char* SUB_FEEDS[] = { "p02-relay" };

struct Meter {
  float vrms = 0, irms = 0, realW = 0, va = 0, pf = 0;
  double kwh = 0;
} m;

float vPerMv, aPerMv, maxWatts, tariff;
bool relayOn = true;
int overCount = 0;
uint32_t lastSample = 0, lastCloud = 0, lastSave = 0, lastMeasure = 0;
int lcdPage = 0;
// raw RMS of the last measurement (mV at the ADC) - used for calibration
float rawVmv = 0, rawImv = 0;

void loadSettings() {
  vPerMv   = iot::settingF("vcal", DEF_V_PER_MV);
  aPerMv   = iot::settingF("ical", DEF_A_PER_MV);
  maxWatts = iot::settingF("maxw", DEF_MAX_WATTS);
  tariff   = iot::settingF("tariff", DEF_TARIFF);
}

void setRelay(bool on, const char* source) {
  relayOn = on;
  digitalWrite(PIN_RELAY, (on ^ RELAY_ACTIVE_LOW) ? HIGH : LOW);
  iot::sendEvent("relay", String(on ? "ON" : "OFF") + " by " + source);
  aio.publish("p02-relay", on ? "ON" : "OFF");
}

/*
 * Sample both channels ~2000 times across 200 ms (10 mains cycles at 50 Hz).
 * The DC offset (mean) is removed, then:
 *   Vrms = sqrt(mean(v^2)), Irms = sqrt(mean(i^2)), P = mean(v*i)
 */
void measure() {
  const int N = 2000;
  static int16_t vs[N], is[N];
  uint32_t t0 = micros();
  for (int k = 0; k < N; k++) {
    vs[k] = analogRead(PIN_VOLTAGE);
    is[k] = analogRead(PIN_CURRENT);
    while (micros() - t0 < (uint32_t)(k + 1) * 100) { }   // 10 kHz pair rate
  }
  double vMean = 0, iMean = 0;
  for (int k = 0; k < N; k++) { vMean += vs[k]; iMean += is[k]; }
  vMean /= N; iMean /= N;
  double vv = 0, ii = 0, vi = 0;
  for (int k = 0; k < N; k++) {
    double v = vs[k] - vMean, i = is[k] - iMean;
    vv += v * v; ii += i * i; vi += v * i;
  }
  const double mvPerCount = 3300.0 / 4095.0;              // approx. with 11 dB attenuation
  rawVmv = sqrt(vv / N) * mvPerCount;
  rawImv = sqrt(ii / N) * mvPerCount;
  m.vrms = rawVmv * vPerMv;
  m.irms = rawImv * aPerMv;
  if (m.vrms < 20) m.vrms = 0;                            // mains not present
  if (m.irms < NOISE_AMPS) m.irms = 0;
  double p = (vi / N) * mvPerCount * mvPerCount * vPerMv * aPerMv;
  m.va = m.vrms * m.irms;
  m.realW = (m.irms == 0) ? 0 : fabs(p);
  if (m.realW > m.va) m.realW = m.va;
  m.pf = m.va > 1 ? m.realW / m.va : 0;

  uint32_t now = millis();
  if (lastMeasure) m.kwh += m.realW * (now - lastMeasure) / 3600000.0 / 1000.0;
  lastMeasure = now;
}

void protect() {
  if (relayOn && m.realW > maxWatts) {
    if (++overCount >= 3) {                               // 3 s above the limit
      setRelay(false, "overload");
      iot::sendEvent("overload", "Load " + String(m.realW, 0) + " W > limit " + String(maxWatts, 0) + " W");
      overCount = 0;
    }
  } else overCount = 0;
}

void showLcd() {
  char l1[17], l2[17];
  if (lcdPage < 3) {
    snprintf(l1, 17, "%5.1fV %6.3fA", m.vrms, m.irms);
    snprintf(l2, 17, "%6.1fW %s %s", m.realW, relayOn ? "ON " : "OFF", iot::wifiOK() ? "W" : "-");
  } else {
    snprintf(l1, 17, "PF %.2f %6.0fVA", m.pf, m.va);
    snprintf(l2, 17, "%.3fkWh Rs%.1f", m.kwh, m.kwh * tariff);
  }
  lcd.setCursor(0, 0); lcd.print(l1); for (int i = strlen(l1); i < 16; i++) lcd.print(' ');
  lcd.setCursor(0, 1); lcd.print(l2); for (int i = strlen(l2); i < 16; i++) lcd.print(' ');
  lcdPage = (lcdPage + 1) % 5;                            // 3 s page 1, 2 s page 2
}

void sendBle() {
  JsonDocument d;
  d["v"] = iot::rnd(m.vrms); d["i"] = iot::rnd(m.irms, 3);
  d["w"] = iot::rnd(m.realW); d["va"] = iot::rnd(m.va);
  d["pf"] = iot::rnd(m.pf, 2); d["kwh"] = iot::rnd(m.kwh, 3);
  d["cost"] = iot::rnd(m.kwh * tariff, 2);
  d["relay"] = relayOn; d["cloud"] = aio.connected();
  iot::sendData(d);
}

void onFeed(const String& feed, const String& value) {
  Serial.printf("[AIO] %s = %s\n", feed.c_str(), value.c_str());
  if (feed == "p02-relay") {
    bool on = value.equalsIgnoreCase("ON") || value == "1";
    if (on != relayOn) setRelay(on, "cloud");
  }
}

bool onCommand(const String& cmd, const String& arg, bool authed) {
  if (cmd == "setting") { loadSettings(); return true; }
  if (cmd == "relay" || cmd == "reset" || cmd == "calv" || cmd == "cali") {
    if (!authed) { iot::emitAck(cmd, false, "send auth:<PIN> first"); return true; }
    if (cmd == "relay") {
      bool on = arg == "on" ? true : arg == "off" ? false : !relayOn;
      setRelay(on, "BLE"); iot::emitAck(cmd, true, on ? "ON" : "OFF");
    } else if (cmd == "reset") {
      m.kwh = 0; iot::saveSetting("kwh", "0"); iot::emitAck(cmd, true, "energy reset");
    } else if (cmd == "calv") {                // calv:<voltage shown by a multimeter>
      if (rawVmv < 1) { iot::emitAck(cmd, false, "no voltage signal"); return true; }
      vPerMv = arg.toFloat() / rawVmv; iot::saveSetting("vcal", String(vPerMv, 5));
      iot::emitAck(cmd, true, "vcal=" + String(vPerMv, 5));
    } else if (cmd == "cali") {                // cali:<amps shown by a clamp meter>
      if (rawImv < 1) { iot::emitAck(cmd, false, "no current signal"); return true; }
      aPerMv = arg.toFloat() / rawImv; iot::saveSetting("ical", String(aPerMv, 6));
      iot::emitAck(cmd, true, "ical=" + String(aPerMv, 6));
    }
    return true;
  }
  return false;
}

void setup() {
  pinMode(PIN_RELAY, OUTPUT);
  analogSetAttenuation(ADC_11db);
  iot::begin("P02", onCommand);
  loadSettings();
  m.kwh = iot::settingF("kwh", 0);
  setRelay(true, "boot");
  Wire.begin(21, 22);
  lcd.init(); lcd.backlight();
  lcd.print("Energy Monitor"); lcd.setCursor(0, 1); lcd.print("starting...");
  aio.begin(onFeed, SUB_FEEDS, 1);
}

void loop() {
  iot::loop();
  aio.loop();
  uint32_t now = millis();
  if (now - lastSample >= SAMPLE_MS) {
    lastSample = now;
    measure();
    protect();
    showLcd();
    sendBle();
  }
  if (now - lastCloud >= CLOUD_MS && aio.connected()) {
    lastCloud = now;
    aio.publish("p02-voltage", m.vrms, 1);
    aio.publish("p02-current", m.irms, 3);
    aio.publish("p02-power", m.realW, 1);
    aio.publish("p02-energy", (float)m.kwh, 3);
  }
  if (now - lastSave >= 300000) {                          // save kWh every 5 min
    lastSave = now;
    iot::saveSetting("kwh", String(m.kwh, 4));
  }
}
