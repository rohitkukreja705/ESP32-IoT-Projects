/*
 * P06 — RFID Attendance System with Offline Queue
 * ===============================================
 * Peripherals: MFRC522 RFID reader (13.56 MHz cards/tags), SSD1306 OLED,
 *              buzzer, green/red status LEDs
 * Wi-Fi  : Supabase — "members" table (who owns which card) and
 *          "attendance" table (IN/OUT log with timestamps)
 * BLE    : admin enrolment (enroll:<name>, then tap the card), delete cards,
 *          live scan feed on the phone
 * Extras : works without internet — members are cached in flash and scans
 *          are queued in LittleFS, then flushed when Wi-Fi returns;
 *          automatic IN/OUT toggling; duplicate-tap protection
 */
#include "config.h"
#include "IoTCore.h"
#include "Cloud.h"
#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <LittleFS.h>

MFRC522 rfid(PIN_RC522_SS, PIN_RC522_RST);
Adafruit_SSD1306 oled(128, 64, &Wire, -1);
Preferences cards;     // uid -> name   (namespace "cards")
Preferences inout;     // uid -> "1" when currently IN (namespace "inout")
bool oledOK = false, fsOK = false;

String enrollName = "";            // non-empty while waiting for a card to enrol
uint32_t enrollUntil = 0;
String lastUid; uint32_t lastUidAt = 0;
uint32_t lastMemberSync = 0, lastFlush = 0, screenUntil = 0;
int scansToday = 0, queued = 0;

String uidHex(const MFRC522::Uid& u) {
  String s;
  for (byte i = 0; i < u.size; i++) { if (u.uidByte[i] < 0x10) s += "0"; s += String(u.uidByte[i], HEX); }
  s.toUpperCase();
  return s;
}

void beep(int times, int ms) {
  for (int i = 0; i < times; i++) { digitalWrite(PIN_BUZZER, HIGH); delay(ms); digitalWrite(PIN_BUZZER, LOW); delay(80); }
}

void show(const String& l1, const String& l2, const String& l3, uint32_t holdMs = 3000) {
  if (!oledOK) return;
  oled.clearDisplay(); oled.setTextColor(SSD1306_WHITE);
  oled.setTextSize(1); oled.setCursor(0, 0); oled.print(l1);
  oled.setTextSize(2); oled.setCursor(0, 16); oled.print(l2.substring(0, 10));
  oled.setTextSize(1); oled.setCursor(0, 44); oled.print(l3);
  oled.setCursor(0, 56);
  oled.printf("%s %s Q:%d", iot::wifiOK() ? "WiFi" : "----", iot::bleConnected() ? "BLE" : "---", queued);
  oled.display();
  screenUntil = holdMs ? millis() + holdMs : 0;
}

void idleScreen() {
  String t = iot::timestamp();
  show("RFID ATTENDANCE", "Tap card", t.length() > 16 ? t.substring(11, 16) + "  scans:" + String(scansToday) : "time not synced", 0);
}

// ------------------------------------------------------------ offline queue
void queueRecord(const String& json) {
  if (!fsOK) return;
  File f = LittleFS.open("/queue.jsonl", FILE_APPEND);
  if (f) { f.println(json); f.close(); queued++; }
}

void countQueue() {
  queued = 0;
  if (!fsOK || !LittleFS.exists("/queue.jsonl")) return;
  File f = LittleFS.open("/queue.jsonl", FILE_READ);
  while (f && f.available()) { if (f.readStringUntil('\n').length() > 2) queued++; }
  if (f) f.close();
}

void flushQueue() {
  if (!fsOK || !iot::wifiOK() || queued == 0) return;
  File f = LittleFS.open("/queue.jsonl", FILE_READ);
  if (!f) return;
  // Rows are posted one by one (offline rows may differ in their keys).
  // Stop at the first failure and keep that row and the rest for later.
  String rest; int sent = 0; bool failed = false;
  while (f.available()) {
    String line = f.readStringUntil('\n'); line.trim();
    if (line.length() < 3) continue;
    if (!failed && sent < 20 && cloud::supabaseInsert("attendance", line)) { sent++; continue; }
    failed = true;
    rest += line + "\n";
  }
  f.close();
  File w = LittleFS.open("/queue.jsonl", FILE_WRITE);
  if (w) { w.print(rest); w.close(); }
  countQueue();
  if (sent) iot::sendEvent("sync", "Uploaded " + String(sent) + " offline scans");
}

// ------------------------------------------------------------ members
void syncMembers() {
  String out;
  if (!cloud::supabaseSelect("members", "select=uid,name&limit=" + String(MAX_MEMBERS), out)) return;
  JsonDocument d;
  if (deserializeJson(d, out)) return;
  int n = 0;
  for (JsonObject m : d.as<JsonArray>()) {
    String uid = m["uid"] | ""; String name = m["name"] | "";
    if (uid.length() && uid.length() <= 15 && cards.getString(uid.c_str(), "") != name) cards.putString(uid.c_str(), name);
    n++;
  }
  Serial.printf("[MEMBERS] %d members synced\n", n);
}

void enrolCard(const String& uid) {
  cards.putString(uid.c_str(), enrollName);
  JsonDocument d; d["uid"] = uid; d["name"] = enrollName;
  String s; serializeJson(d, s);
  // upsert so re-enrolling the same card renames it
  int c = cloud::supabaseRequest("POST", "/rest/v1/members", s, nullptr,
                                 "resolution=merge-duplicates,return=minimal");
  iot::sendEvent("enrolled", enrollName + " -> " + uid + (c >= 200 && c < 300 ? " (cloud ok)" : " (saved locally)"));
  show("ENROLLED", enrollName, uid);
  beep(2, 80);
  enrollName = "";
}

void handleScan(const String& uid) {
  uint32_t now = millis();
  if (uid == lastUid && now - lastUidAt < REPEAT_BLOCK_MS) return;   // double tap
  lastUid = uid; lastUidAt = now;

  if (enrollName.length()) { enrolCard(uid); return; }

  String name = cards.getString(uid.c_str(), "");
  if (name.isEmpty()) {
    digitalWrite(PIN_LED_ERR, HIGH); beep(1, 600); digitalWrite(PIN_LED_ERR, LOW);
    show("ACCESS DENIED", "Unknown", uid);
    iot::sendEvent("unknown_card", uid);
    return;
  }
  bool wasIn = inout.getString(uid.c_str(), "0") == "1";
  const char* dir = wasIn ? "OUT" : "IN";
  inout.putString(uid.c_str(), wasIn ? "0" : "1");
  scansToday++;

  digitalWrite(PIN_LED_OK, HIGH); beep(1, 120); digitalWrite(PIN_LED_OK, LOW);
  String t = iot::timestamp();
  show(String(dir) == "IN" ? "WELCOME" : "GOODBYE", name, String(dir) + "  " + (t.length() > 16 ? t.substring(11, 19) : ""));

  JsonDocument d;
  d["uid"] = uid; d["name"] = name; d["direction"] = dir; d["device"] = iot::deviceName;
  if (t.startsWith("20")) d["scanned_at"] = t;   // keep the real scan time for offline rows
  String row; serializeJson(d, row);

  bool sent = iot::wifiOK() && queued == 0 && cloud::supabaseInsert("attendance", row);
  if (!sent) { d["offline"] = true; row = ""; serializeJson(d, row); queueRecord(row); }

  JsonDocument e;
  e["type"] = "scan"; e["uid"] = uid; e["name"] = name; e["dir"] = dir; e["cloud"] = sent;
  String s; serializeJson(e, s); iot::emit(s);
}

// Commands: enroll:<name>  delete:<UID>  list  cancel
bool onCommand(const String& cmd, const String& arg, bool authed) {
  if (cmd == "setting") return true;
  if (cmd == "enroll" || cmd == "delete" || cmd == "cancel" || cmd == "list" || cmd == "syncnow") {
    if (!authed) { iot::emitAck(cmd, false, "send auth:<PIN> first"); return true; }
    if (cmd == "enroll") {
      if (arg.isEmpty()) { iot::emitAck(cmd, false, "use enroll:<name>"); return true; }
      enrollName = arg; enrollUntil = millis() + 30000;
      show("ENROL MODE", "Tap card", "for " + arg, 30000);
      iot::emitAck(cmd, true, "tap the card within 30 s");
    } else if (cmd == "delete") {
      cards.remove(arg.c_str()); inout.remove(arg.c_str());
      cloud::supabaseRequest("DELETE", "/rest/v1/members?uid=eq." + arg, "");
      iot::emitAck(cmd, true, arg + " removed");
    } else if (cmd == "cancel") {
      enrollName = ""; iot::emitAck(cmd, true);
    } else if (cmd == "syncnow") {
      syncMembers(); flushQueue(); iot::emitAck(cmd, true, "queued=" + String(queued));
    } else {
      iot::emitAck(cmd, true, "members cached: " + String(cards.freeEntries()) + " free NVS entries");
    }
    return true;
  }
  return false;
}

void sendHeartbeat() {
  JsonDocument d;
  d["today"] = scansToday; d["queued"] = queued; d["enrol"] = enrollName.length() > 0;
  d["wifi"] = iot::wifiOK();
  iot::sendData(d);
}

void setup() {
  pinMode(PIN_BUZZER, OUTPUT); pinMode(PIN_LED_OK, OUTPUT); pinMode(PIN_LED_ERR, OUTPUT);
  iot::begin("P06", onCommand);
  cards.begin("cards", false);
  inout.begin("inout", false);
  fsOK = LittleFS.begin(true);              // format on first use
  countQueue();
  SPI.begin(18, 19, 23, PIN_RC522_SS);
  rfid.PCD_Init();
  byte v = rfid.PCD_ReadRegister(MFRC522::VersionReg);
  Serial.printf("[RC522] version 0x%02X %s\n", v, (v == 0x91 || v == 0x92 || v == 0x88) ? "OK" : "(check wiring)");
  Wire.begin(21, 22);
  oledOK = oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR);
  idleScreen();
}

void loop() {
  iot::loop();
  uint32_t now = millis();

  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    handleScan(uidHex(rfid.uid));
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
  }
  if (enrollName.length() && now > enrollUntil) { enrollName = ""; iot::sendEvent("enrol", "timed out"); }
  if (screenUntil && now > screenUntil) { screenUntil = 0; idleScreen(); }

  if (iot::wifiOK() && (lastMemberSync == 0 || now - lastMemberSync > MEMBER_SYNC_MS)) {
    lastMemberSync = now; syncMembers();
  }
  if (now - lastFlush > 15000) { lastFlush = now; flushQueue(); sendHeartbeat(); if (!screenUntil) idleScreen(); }
}
