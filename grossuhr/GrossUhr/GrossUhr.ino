/*
  GrossUhr – Schrittmotor-Uhrwerk (Nema 17 + A4988) mit ESP32
  ============================================================
  Arduino-ESP32 Core 2.x oder 3.x, keine Zusatzbibliotheken nötig.

  Verdrahtung (ESP32-Devboard -> A4988):
     GPIO14 (D14) -> STEP        GPIO12 (D12) -> DIR
     GPIO25 -> MS1               GPIO26 -> MS2        GPIO27 -> MS3
     ENABLE: offen/GND lassen (oder EN_PIN unten setzen), RESET <-> SLEEP verbinden
     A4988-VDD an 3,3 V des ESP32, gemeinsame Masse, Motorversorgung 12 V (+100 µF am Treiber)

  Mechanik (Annahme): Motor -> Vollachse -> Zeiger 1 (Minutenzeiger, 1:1),
  Hohlrohr -> Zeiger 2 (Stundenzeiger) über 3:1 x 4:1 = 12:1.
  => 12 Motorumdrehungen = 12 Stunden = 38400 Mikroschritte (bei 1/16).

  Bedienung: WLAN "GrossUhr" (Passwort siehe unten), dann http://192.168.4.1
  oder http://grossuhr.local ; Admin: /admin
*/

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <WiFiUdp.h>
#include <Preferences.h>
#include <ESPmDNS.h>
#include <esp_timer.h>
#include <soc/soc.h>
#include <soc/gpio_reg.h>

// ----------------------------------------------------------------------------
// Pins / Konstanten
// ----------------------------------------------------------------------------
#define STEP_PIN 14
#define DIR_PIN  12
#define MS1_PIN  25
#define MS2_PIN  26
#define MS3_PIN  27
#define EN_PIN   -1            // optional, z.B. 33 (LOW = Treiber aktiv)

static const int32_t USTEPS_REV  = 200 * 16;        // 3200 Mikroschritte pro Motorumdrehung
static const int32_t HAND_RATIO  = 12;               // Zeiger1 : Zeiger2
static const int32_t USTEPS_12H  = USTEPS_REV * HAND_RATIO;   // 38400
static const int32_t SEC_12H     = 43200;
static const uint32_t TICK_HZ    = 20000;            // ISR-Takt, max. Schrittrate = TICK_HZ/2 (wir begrenzen auf 8 kHz)
static const float   MAX_PPS     = 8000.0f;
#define STEP_MASK (1UL << STEP_PIN)

// ----------------------------------------------------------------------------
// Konfiguration (persistent)
// ----------------------------------------------------------------------------
struct Cfg {
  float maxRpm   = 60;     // maximale Geschwindigkeit (U/min Minutenzeiger = Motorwelle)
  float minRpm   = 1;      // Geschwindigkeit bei Fader ganz unten
  float accel    = 100;    // Beschleunigung in U/min pro Sekunde
  float startRpm = 3;      // Anfahr-/Stoppgeschwindigkeit
  float swRpm    = 30;     // darüber Vollschritt (wenn autoFull)
  float calRpm   = 2;      // Geschwindigkeit der Kalibrier-Tasten
  bool  autoFull = true;

  bool  autoSmooth = false;  // Auto: false = Minutensprung wie eine Uhr, true = fließend in Mikroschritten
  bool  invDir   = false;    // Standard aus: die Grundrichtung ist intern bereits so gewählt, dass 'vorwärts' im Uhrzeigersinn läuft
  bool  artOn    = true;
  uint16_t artUni = 0;
  uint16_t artCh  = 1;
  String apSsid = "GrossUhr";
  String apPass = "uhr12345";
  String staSsid = "";
  String staPass = "";
  String host = "grossuhr";
} cfg;

Preferences prefs;

// UI-Zustand (persistent)
String rowT[5] = {"12:00", "03:00", "06:00", "09:00", "12:00"};
bool   rowB[5] = {false, false, false, false, false};
int    faderPct = 50;
float  autoMult = 1.0f;
bool   autoOn   = false;

// ----------------------------------------------------------------------------
// Bewegungs-Engine
//   ISR (20 kHz): erzeugt Schrittimpulse per Phasenakkumulator, zählt Position,
//                 stoppt exakt nach 'g_rem' Impulsen.
//   Planer-Task (2 ms): Rampen, Segmente (Mikro/Voll), Zielverwaltung.
// ----------------------------------------------------------------------------
portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
volatile bool     g_running = false;
volatile bool     g_stepHigh = false;
volatile int32_t  g_pos = 0;          // Mikroschritte, absolut (0 = Treiber-Home beim Einschalten)
volatile int32_t  g_rem = 0;          // verbleibende Impulse im Segment
volatile int32_t  g_dirunit = 1;      // +-(1|16) Mikroschritte pro Impuls
volatile uint32_t g_inc = 0;
volatile uint32_t g_acc = 0;
volatile int32_t  g_unit = 1;         // 1 = 1/16-Schritt, 16 = Vollschritt (nur Anzeige)

volatile int32_t  w_target = 0;       // Wunschziel (absolut, Mikroschritte)
volatile float    w_rpm = 10;         // Wunschgeschwindigkeit, 0 = halten
volatile float    g_curRpm = 0;       // aktuelle Geschwindigkeit (nur Anzeige)
int32_t zeroPos = 0;                  // g_pos, bei dem die Uhr 12:00 zeigt
volatile bool posDirty = false;
volatile bool g_stopReq = false;     // STOP: sofort abbremsen, alle Ziele verwerfen

hw_timer_t* stepTimer = nullptr;

void IRAM_ATTR onTimer() {
  if (g_stepHigh) {
    REG_WRITE(GPIO_OUT_W1TC_REG, STEP_MASK);
    g_stepHigh = false;
  }
  if (!g_running) return;
  uint32_t old = g_acc;
  uint32_t nw = old + g_inc;
  g_acc = nw;
  if (nw < old) {                       // Überlauf = ein Schritt
    REG_WRITE(GPIO_OUT_W1TS_REG, STEP_MASK);
    g_stepHigh = true;
    g_pos = g_pos + g_dirunit;
    int32_t r = g_rem - 1;
    g_rem = r;
    if (r <= 0) g_running = false;
  }
}

// ---- Planer-interner Zustand
struct Seg { int8_t dir; uint8_t unit; int32_t count; };
static Seg    segs[3];
static int    segN = 0, segI = 0;
static bool   segActive = false, stopping = false;
static float  pv = 0;                  // Geschwindigkeit in U/s
static int32_t planTarget = 0;
static double autoAcc = 0;
// Ablauf: von Startzeit zu Endzeit in vorgegebener Dauer
static volatile uint8_t sweepPhase = 0;   // 0 aus, 1 fährt zur Startzeit, 2 läuft
static int32_t sweepBase = 0, sweepDelta = 0;
static float   sweepDur = 1, sweepEl = 0;
String swS = "12:00", swE = "12:30"; float swD = 10; bool swB = false;

static double autoMinAcc = 0;    // Minutensprung-Modus: angesammelte Minuten
static double autoCarry = 0;     // Minuten -> Mikroschritte ohne Rundungsdrift

static void setTarget(int32_t t);
static inline int32_t pmod(int32_t a, int32_t m) { int32_t r = a % m; return r < 0 ? r + m : r; }
static inline int32_t secToSteps(int32_t sec) { return (int32_t)lround((double)sec * (double)USTEPS_12H / (double)SEC_12H); }
static inline int32_t relOf(int32_t pos) { return pmod(pos - zeroPos, USTEPS_12H); }

static void setMicrostep(bool micro16) {
  digitalWrite(MS1_PIN, micro16);
  digitalWrite(MS2_PIN, micro16);
  digitalWrite(MS3_PIN, micro16);
}

static void startSegment(int i) {
  const Seg& s = segs[i];
  digitalWrite(DIR_PIN, ((s.dir > 0) == cfg.invDir) ? HIGH : LOW);
  setMicrostep(s.unit == 1);
  delayMicroseconds(10);
  g_unit = s.unit;
  pv = 0;                                           // wird im Tick auf Startgeschwindigkeit gesetzt
  portENTER_CRITICAL(&mux);
  g_acc = 0;
  g_inc = 0;
  g_dirunit = (int32_t)s.dir * s.unit;
  g_rem = s.count;
  g_running = true;
  portEXIT_CRITICAL(&mux);
  segActive = true;
}

static void planMove(int32_t want, float rpm) {
  int32_t p = g_pos;
  int32_t d = want - p;
  if (d == 0) return;
  int8_t dir = d > 0 ? 1 : -1;
  int32_t ad = d > 0 ? d : -d;
  segN = 0; segI = 0;
  bool full = cfg.autoFull && rpm > cfg.swRpm && ad >= 96;
  if (full) {
    int32_t head = dir > 0 ? pmod(16 - pmod(p, 16), 16) : pmod(p, 16);
    int32_t rest = ad - head;
    int32_t body = rest / 16;
    int32_t tail = rest - body * 16;
    if (body < 4) full = false;
    else {
      if (head > 0) segs[segN++] = {dir, 1, head};
      segs[segN++] = {dir, 16, body};
      if (tail > 0) segs[segN++] = {dir, 1, tail};
    }
  }
  if (!full) { segN = 0; segs[segN++] = {dir, 1, ad}; }
  planTarget = want;
  startSegment(0);
}

static void haltNow() {
  portENTER_CRITICAL(&mux);
  g_running = false;
  g_rem = 0;
  portEXIT_CRITICAL(&mux);
  segActive = false; segN = 0; segI = 0; stopping = false; pv = 0;
  g_curRpm = 0;
}

void plannerTick(float dt) {
  // --- Automodus: Ziel läuft in Echtzeit x Multiplikator vor
  float rpm = w_rpm;
  if (autoOn) {
    int32_t whole = 0;
    if (cfg.autoSmooth) {
      autoAcc += (double)autoMult * dt * (double)USTEPS_REV / 3600.0;
      whole = (int32_t)autoAcc;
      autoAcc -= whole;
    } else {                                           // Minutensprung: alle 60/Faktor Sekunden eine Minute weiter
      autoMinAcc += (double)autoMult * dt / 60.0;
      int32_t m = (int32_t)autoMinAcc;
      if (m > 0) {
        autoMinAcc -= m;
        autoCarry += (double)m * USTEPS_REV / 60.0;
        whole = (int32_t)autoCarry;
        autoCarry -= whole;
      }
    }
    if (whole != 0) {
      portENTER_CRITICAL(&mux);
      w_target = w_target + whole;
      portEXIT_CRITICAL(&mux);
    }
    float need = 1.5f * autoMult / 60.0f + 3.0f;
    if (rpm < need) rpm = need;
  } else {
    autoAcc = 0; autoMinAcc = 0; autoCarry = 0;
  }
  if (sweepPhase == 1) {
    if (!segActive && !g_running && g_pos == w_target) { sweepEl = 0; sweepPhase = 2; }
  }
  if (sweepPhase == 2) {
    sweepEl += dt;
    float f = sweepEl / sweepDur; if (f > 1) f = 1;
    int32_t t = sweepBase + (int32_t)lround((double)sweepDelta * (double)f);
    if (t != w_target) setTarget(t);
    float rr = fabsf((float)sweepDelta) / sweepDur / (float)USTEPS_REV * 60.0f;   // U/min im Mittel
    float need = 1.5f * rr + 3.0f;
    if (rpm < need) rpm = need;
    if (sweepEl >= sweepDur) sweepPhase = 0;
  }
  if (g_stopReq) {
    autoOn = false; sweepPhase = 0;
    if (segActive && g_running) stopping = true;      // zügig abbremsen, dann haltNow()
    else {
      segActive = false; segN = 0; segI = 0; stopping = false; pv = 0; g_curRpm = 0;
      setTarget(g_pos);
      g_stopReq = false;
    }
  }
  int32_t want = w_target;
  if (g_stopReq) want = planTarget;                   // während des Bremsens kein neues Ziel annehmen

  // --- Segment beendet (von der ISR)?
  if (segActive && !g_running) {
    segActive = false;
    segI++;
    if (segI < segN) startSegment(segI);
  }

  if (!segActive) {
    pv = 0; g_curRpm = 0;
    if (stopping) stopping = false;
    if (rpm > 0 && want != g_pos) { planMove(want, rpm); }
    else if (!g_running && (g_pos > 20 * USTEPS_12H || g_pos < -20 * USTEPS_12H)) {
      int32_t shift = (g_pos / USTEPS_12H) * USTEPS_12H;     // Vielfaches von 12 h (und von 16)
      portENTER_CRITICAL(&mux);
      g_pos = g_pos - shift;
      w_target = w_target - shift;
      portEXIT_CRITICAL(&mux);
    }
    if (!segActive) return;
  }

  // --- Ziel geändert während der Fahrt?
  if (!stopping && want != planTarget) {
    portENTER_CRITICAL(&mux);
    int32_t d = want - g_pos;
    bool ok = g_running && segN == 1 && segs[0].unit == 1 && d != 0 && ((d > 0) == (segs[0].dir > 0));
    if (ok) { g_rem = d > 0 ? d : -d; planTarget = want; }
    portEXIT_CRITICAL(&mux);
    if (!ok) stopping = true;
  }
  if (rpm <= 0) stopping = true;

  // --- Geschwindigkeitsprofil
  const Seg& s = segs[segI];
  float a    = cfg.accel / 60.0f;                     // U/s^2
  if (a < 0.05f) a = 0.05f;
  if (g_stopReq) a *= 3.0f;                           // STOP bremst dreimal so hart
  float vs   = cfg.startRpm / 60.0f;
  float ppr  = (float)USTEPS_REV / (float)s.unit;     // Impulse pro Umdrehung
  float vmax = (rpm > cfg.maxRpm ? cfg.maxRpm : rpm) / 60.0f;
  float vcap = (MAX_PPS * 0.95f) / ppr;
  if (vmax > vcap) vmax = vcap;
  float vsE  = vs < vmax ? vs : vmax;
  if (pv < vsE) pv = vsE;

  float vdes;
  if (stopping) vdes = 0;
  else {
    float dist = (float)g_rem * (float)s.unit / (float)USTEPS_REV;   // verbleibende Umdrehungen
    float vd = sqrtf(vsE * vsE + 2.0f * a * dist);
    vdes = vd < vmax ? vd : vmax;
  }
  if (pv < vdes) { pv += a * dt; if (pv > vdes) pv = vdes; }
  else           { pv -= a * dt; if (pv < vdes) pv = vdes; }

  if (stopping && pv <= vs * 1.001f) { haltNow(); return; }
  float v = pv < vsE ? vsE : pv;
  g_curRpm = v * 60.0f;
  float pps = v * ppr;
  if (pps > MAX_PPS) pps = MAX_PPS;
  uint32_t inc = (uint32_t)((double)pps / (double)TICK_HZ * 4294967296.0);
  g_inc = inc;
}

void motionTask(void*) {
  int64_t last = esp_timer_get_time();
  for (;;) {
    int64_t now = esp_timer_get_time();
    float dt = (float)(now - last) * 1e-6f;
    last = now;
    if (dt > 0.05f) dt = 0.05f;
    plannerTick(dt);
    vTaskDelay(pdMS_TO_TICKS(2));
  }
}

// ----------------------------------------------------------------------------
// Befehle (von Web und Art-Net)
// ----------------------------------------------------------------------------
static void setTarget(int32_t t) { portENTER_CRITICAL(&mux); w_target = t; portEXIT_CRITICAL(&mux); }

float faderToRpm(int p) {
  if (p < 1) p = 1;
  if (p > 100) p = 100;
  float lo = cfg.minRpm < 0.05f ? 0.05f : cfg.minRpm;
  float hi = cfg.maxRpm < lo ? lo : cfg.maxRpm;
  return lo * powf(hi / lo, (p - 1) / 99.0f);
}

// Zeit (Sekunden im 12-h-Ziffernblatt) anfahren, Richtung vorgegeben (kein "Umweg" über 24 h)
void cmdGoSec(int32_t sec12, bool back, float rpm) {
  sweepPhase = 0;
  sec12 = pmod(sec12, SEC_12H);
  int32_t T = secToSteps(sec12);
  int32_t pos = g_pos;
  int32_t cur = relOf(pos);
  int32_t dF = pmod(T - cur, USTEPS_12H);
  int32_t dB = pmod(cur - T, USTEPS_12H);
  w_rpm = rpm;
  setTarget(back ? pos - dB : pos + dF);
}

// Relativ um 'minutes' Minuten (auch negativ), rastet auf das Minutenraster ein
void cmdJogMin(int minutes, float rpm) {
  sweepPhase = 0;
  int32_t base = w_target;
  int32_t rel = relOf(base);
  int32_t idx = (int32_t)lround((double)rel * 720.0 / (double)USTEPS_12H);
  int32_t t = base + secToSteps((idx + minutes) * 60) - rel;
  w_rpm = rpm;
  setTarget(t);
}

void cmdJogRaw(int32_t usteps, float rpm) { sweepPhase = 0; w_rpm = rpm; setTarget(w_target + usteps); }

// Ablauf starten: zuerst Startzeit auf kürzestem Weg anfahren, dann gleichmäßig zur Endzeit laufen
void sweepStart(int32_t sA, int32_t sB, float durS, bool back, float rpm) {
  autoOn = false; sweepPhase = 0;
  int32_t TA = secToSteps(pmod(sA, SEC_12H)), TB = secToSteps(pmod(sB, SEC_12H));
  bool bk = pmod(TA - relOf(w_target), USTEPS_12H) > USTEPS_12H / 2;
  cmdGoSec(sA, bk, rpm);
  int32_t span = back ? pmod(TA - TB, USTEPS_12H) : pmod(TB - TA, USTEPS_12H);
  if (span == 0) span = USTEPS_12H;
  sweepBase = w_target; sweepDelta = back ? -span : span;
  sweepDur = durS < 1 ? 1 : durS; sweepEl = 0;
  sweepPhase = 1;
}

bool parseHM(const String& s, int32_t& sec12) {
  int c = s.indexOf(':');
  if (c < 1) return false;
  int h = s.substring(0, c).toInt();
  int m = s.substring(c + 1).toInt();
  if (h < 0 || h > 24 || m < 0 || m > 59) return false;
  sec12 = ((h % 12) * 60 + m) * 60;
  return true;
}

String clockStr(int32_t pos) {
  int32_t rel = relOf(pos);
  int32_t sec = pmod((int32_t)llround((double)rel * SEC_12H / USTEPS_12H), SEC_12H);
  int h = sec / 3600, m = (sec % 3600) / 60;
  if (h == 0) h = 12;
  char b[12]; snprintf(b, sizeof(b), "%d:%02d", h, m);
  return String(b);
}

// ----------------------------------------------------------------------------
// Speicher
// ----------------------------------------------------------------------------
void saveRel() { prefs.putInt("rel", relOf(g_pos)); posDirty = false; }
void saveRows() {
  for (int i = 0; i < 5; i++) { prefs.putString(("t" + String(i)).c_str(), rowT[i]); prefs.putBool(("b" + String(i)).c_str(), rowB[i]); }
}
void saveSweep() { prefs.putString("swS", swS); prefs.putString("swE", swE); prefs.putFloat("swD", swD); prefs.putBool("swB", swB); }
void saveUi() { prefs.putInt("fader", faderPct); prefs.putFloat("mult", autoMult); prefs.putBool("auto", autoOn); }
void saveCfg() {
  prefs.putFloat("maxRpm", cfg.maxRpm); prefs.putFloat("minRpm", cfg.minRpm); prefs.putFloat("accel", cfg.accel);
  prefs.putFloat("startRpm", cfg.startRpm); prefs.putFloat("swRpm", cfg.swRpm); prefs.putFloat("calRpm", cfg.calRpm);
  prefs.putBool("autoFull", cfg.autoFull); prefs.putBool("invDir", cfg.invDir); prefs.putBool("autoSmooth", cfg.autoSmooth); prefs.putBool("artOn", cfg.artOn);
  prefs.putUShort("artUni", cfg.artUni); prefs.putUShort("artCh", cfg.artCh);
  prefs.putString("apSsid", cfg.apSsid); prefs.putString("apPass", cfg.apPass);
  prefs.putString("staSsid", cfg.staSsid); prefs.putString("staPass", cfg.staPass); prefs.putString("host", cfg.host);
}
void loadAll() {
  cfg.maxRpm = prefs.getFloat("maxRpm", cfg.maxRpm); cfg.minRpm = prefs.getFloat("minRpm", cfg.minRpm);
  cfg.accel = prefs.getFloat("accel", cfg.accel); cfg.startRpm = prefs.getFloat("startRpm", cfg.startRpm);
  cfg.swRpm = prefs.getFloat("swRpm", cfg.swRpm); cfg.calRpm = prefs.getFloat("calRpm", cfg.calRpm);
  cfg.autoFull = prefs.getBool("autoFull", cfg.autoFull); cfg.invDir = prefs.getBool("invDir", cfg.invDir); cfg.autoSmooth = prefs.getBool("autoSmooth", cfg.autoSmooth);
  cfg.artOn = prefs.getBool("artOn", cfg.artOn);
  cfg.artUni = prefs.getUShort("artUni", cfg.artUni); cfg.artCh = prefs.getUShort("artCh", cfg.artCh);
  cfg.apSsid = prefs.getString("apSsid", cfg.apSsid); cfg.apPass = prefs.getString("apPass", cfg.apPass);
  cfg.staSsid = prefs.getString("staSsid", cfg.staSsid); cfg.staPass = prefs.getString("staPass", cfg.staPass);
  cfg.host = prefs.getString("host", cfg.host);
  if (prefs.getInt("dirv", 0) < 1) {            // einmalige Migration: neue Standard-Drehrichtung übernehmen
    cfg.invDir = true; prefs.putBool("invDir", true); prefs.putInt("dirv", 1);
  }
  if (prefs.getInt("dirv", 0) < 2) {            // Bedeutung der Checkbox umgedreht: physikalisch gleiche Richtung behalten
    cfg.invDir = !cfg.invDir; prefs.putBool("invDir", cfg.invDir); prefs.putInt("dirv", 2);
  }
  for (int i = 0; i < 5; i++) { rowT[i] = prefs.getString(("t" + String(i)).c_str(), rowT[i]); rowB[i] = prefs.getBool(("b" + String(i)).c_str(), rowB[i]); }
  faderPct = prefs.getInt("fader", faderPct);
  swS = prefs.getString("swS", swS); swE = prefs.getString("swE", swE); swD = prefs.getFloat("swD", swD); swB = prefs.getBool("swB", swB);
  autoMult = prefs.getFloat("mult", autoMult);
  autoOn = prefs.getBool("auto", false);
}

// ----------------------------------------------------------------------------
// Art-Net  (Kanal 1: Stunden 20/Stufe, Kanal 2: Minuten 4/Stufe,
//           Kanal 3: Geschwindigkeit+Richtung: 0=Stopp, 1-126 vor, 127-255 rück)
// ----------------------------------------------------------------------------
WiFiUDP udp;
static bool    artFirst = true;
static uint8_t artH = 0, artM = 0, artS = 0;
volatile uint32_t artPackets = 0;

void artApply(uint8_t h, uint8_t m, uint8_t s) {
  bool timeChanged = artFirst || h != artH || m != artM;
  bool dirChanged  = artFirst || ((s >= 127) != (artS >= 127));
  bool spdChanged  = artFirst || s != artS;
  artFirst = false; artH = h; artM = m; artS = s;

  bool back = s >= 127;
  if (spdChanged) {
    float rpm = 0;
    if (s != 0) {
      int idx = back ? s - 126 : s;
      int top = back ? 129 : 126;
      float f = (idx - 1) / (float)(top - 1);
      float lo = cfg.minRpm < 0.05f ? 0.05f : cfg.minRpm;
      float hi = cfg.maxRpm < lo ? lo : cfg.maxRpm;
      rpm = lo * powf(hi / lo, f);
    }
    w_rpm = rpm;
  }
  if (timeChanged || dirChanged) {
    int hour = h / 20; if (hour > 11) hour = 11;
    int minute = m / 4; if (minute > 59) minute = 59;
    autoOn = false;
    float keep = w_rpm;
    cmdGoSec((hour * 60 + minute) * 60, back, keep);
  }
}

void sendPollReply(IPAddress to) {
  uint8_t r[239]; memset(r, 0, sizeof(r));
  memcpy(r, "Art-Net\0", 8);
  r[8] = 0x00; r[9] = 0x21;
  IPAddress ip = WiFi.status() == WL_CONNECTED ? WiFi.localIP() : WiFi.softAPIP();
  for (int i = 0; i < 4; i++) r[10 + i] = ip[i];
  r[14] = 0x36; r[15] = 0x19;
  r[17] = 14;
  r[18] = (cfg.artUni >> 8) & 0x7F;
  r[19] = (cfg.artUni >> 4) & 0x0F;
  r[23] = 0xE0;
  strncpy((char*)r + 26, "GrossUhr", 17);
  strncpy((char*)r + 44, "Grossuhr Schrittmotor", 63);
  strncpy((char*)r + 108, "#0001 OK", 63);
  r[173] = 1;
  r[174] = 0x80;
  r[182] = 0x80;
  r[190] = cfg.artUni & 0x0F;
  r[200] = 0x00;
  uint8_t mac[6]; WiFi.macAddress(mac); memcpy(r + 201, mac, 6);
  udp.beginPacket(to, 6454);
  udp.write(r, sizeof(r));
  udp.endPacket();
}

void handleArtnet() {
  int n;
  while ((n = udp.parsePacket()) > 0) {
    static uint8_t buf[600];
    IPAddress from = udp.remoteIP();
    int len = udp.read(buf, sizeof(buf));
    if (len < 12 || memcmp(buf, "Art-Net\0", 8) != 0) continue;
    uint16_t op = buf[8] | (buf[9] << 8);
    if (op == 0x2000) { sendPollReply(from); continue; }
    if (op != 0x5000 || len < 18 || !cfg.artOn) continue;
    uint16_t uni = buf[14] | ((buf[15] & 0x7F) << 8);
    if (uni != cfg.artUni) continue;
    int dl = (buf[16] << 8) | buf[17];
    if (dl > len - 18) dl = len - 18;
    int c = cfg.artCh - 1;
    if (c < 0 || dl < c + 3) continue;
    artPackets = artPackets + 1;
    artApply(buf[18 + c], buf[18 + c + 1], buf[18 + c + 2]);
  }
}

// ----------------------------------------------------------------------------
// Web
// ----------------------------------------------------------------------------
WebServer server(80);

static String jsonEsc(const String& s) {
  String o; o.reserve(s.length() + 4);
  for (size_t i = 0; i < s.length(); i++) {
    char c = s[i];
    if (c == '"' || c == '\\') { o += '\\'; o += c; }
    else if ((uint8_t)c < 0x20) o += ' ';
    else o += c;
  }
  return o;
}

String stateJson() {
  String j; j.reserve(900);
  j += "{\"clock\":\"" + clockStr(g_pos) + "\"";
  j += ",\"moving\":" + String(g_running || segActive ? "true" : "false");
  j += ",\"rpm\":" + String(g_curRpm, 1);
  j += ",\"mode\":\"" + String(g_unit == 16 ? "Vollschritt" : "1/16") + "\"";
  j += ",\"auto\":" + String(autoOn ? "true" : "false");
  j += ",\"mult\":" + String(autoMult, 3);
  j += ",\"sw\":" + String((int)sweepPhase) + ",\"swr\":" + String(sweepPhase == 2 ? (long)(sweepDur - sweepEl + 0.5f) : (sweepPhase == 1 ? (long)sweepDur : 0L));
  j += ",\"sws\":\"" + swS + "\",\"swe\":\"" + swE + "\",\"swd\":" + String(swD, 2) + ",\"swb\":" + String(swB ? "true" : "false");
  j += ",\"fader\":" + String(faderPct);
  j += ",\"faderRpm\":" + String(faderToRpm(faderPct), 1);
  j += ",\"pos\":" + String((long)g_pos);
  j += ",\"rel\":" + String((long)relOf(g_pos));
  j += ",\"art\":" + String((unsigned long)artPackets);
  j += ",\"ip\":\"" + (WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : String("nicht verbunden")) + "\"";
  j += ",\"t\":[";
  for (int i = 0; i < 5; i++) { j += "\"" + rowT[i] + "\""; if (i < 4) j += ","; }
  j += "],\"b\":[";
  for (int i = 0; i < 5; i++) { j += rowB[i] ? "true" : "false"; if (i < 4) j += ","; }
  j += "],\"cfg\":{";
  j += "\"maxRpm\":" + String(cfg.maxRpm, 2) + ",\"minRpm\":" + String(cfg.minRpm, 2) + ",\"accel\":" + String(cfg.accel, 1);
  j += ",\"startRpm\":" + String(cfg.startRpm, 2) + ",\"swRpm\":" + String(cfg.swRpm, 1) + ",\"calRpm\":" + String(cfg.calRpm, 1);
  j += ",\"autoFull\":" + String(cfg.autoFull ? "true" : "false") + ",\"invDir\":" + String(cfg.invDir ? "true" : "false") + ",\"autoSmooth\":" + String(cfg.autoSmooth ? "true" : "false");
  j += ",\"artOn\":" + String(cfg.artOn ? "true" : "false") + ",\"artUni\":" + String(cfg.artUni) + ",\"artCh\":" + String(cfg.artCh);
  j += ",\"apSsid\":\"" + jsonEsc(cfg.apSsid) + "\",\"apPass\":\"" + jsonEsc(cfg.apPass) + "\"";
  j += ",\"staSsid\":\"" + jsonEsc(cfg.staSsid) + "\",\"staPass\":\"" + jsonEsc(cfg.staPass) + "\",\"host\":\"" + jsonEsc(cfg.host) + "\"}}";
  return j;
}

static void sendOk() { server.send(200, "text/plain", "OK"); }

void hState() { server.send(200, "application/json", stateJson()); }

void hSet() {   // /api/set?i=0&t=12:30&b=1
  int i = server.arg("i").toInt();
  int32_t s;
  if (i < 0 || i > 4 || !parseHM(server.arg("t"), s)) { server.send(400, "text/plain", "bad"); return; }
  rowT[i] = server.arg("t"); rowB[i] = server.arg("b") == "1";
  saveRows(); sendOk();
}

void hGo() {    // /api/go?i=0&t=12:30&b=1
  int i = server.arg("i").toInt();
  int32_t s;
  if (i < 0 || i > 4 || !parseHM(server.arg("t"), s)) { server.send(400, "text/plain", "bad"); return; }
  rowT[i] = server.arg("t"); rowB[i] = server.arg("b") == "1";
  saveRows();
  cmdGoSec(s, rowB[i], faderToRpm(faderPct));
  sendOk();
}

void hSpeed() { // /api/speed?p=50[&save=1]
  faderPct = constrain(server.arg("p").toInt(), 1, 100);
  w_rpm = faderToRpm(faderPct);
  if (server.arg("save") == "1") saveUi();
  sendOk();
}

void hJog() {   // /api/jog?m=-1  (Minuten)
  cmdJogMin(server.arg("m").toInt(), faderToRpm(faderPct));
  sendOk();
}

void hAuto() {  // /api/auto?on=1&mult=1
  if (server.hasArg("mult")) { float m = server.arg("mult").toFloat(); if (m < 0.01f) m = 0.01f; if (m > 3600) m = 3600; autoMult = m; }
  if (server.hasArg("on")) { autoOn = server.arg("on") == "1"; if (autoOn) sweepPhase = 0; w_rpm = faderToRpm(faderPct); }
  saveUi(); sendOk();
}

void hPhone() { // /api/phone?h=14&m=7&s=30  -> aktuelle Handyzeit, vorwärts anfahren
  int h = server.arg("h").toInt(), m = server.arg("m").toInt(), s = server.arg("s").toInt();
  int32_t sec = ((h % 12) * 60 + m) * 60 + s;
  int32_t T = secToSteps(sec);
  bool back = pmod(T - relOf(w_target), USTEPS_12H) > USTEPS_12H / 2;   // kürzester Weg
  cmdGoSec(sec, back, faderToRpm(faderPct));
  sendOk();
}

void hCalJog() { // /api/cal/jog?d=-16
  cmdJogRaw(server.arg("d").toInt(), cfg.calRpm);
  sendOk();
}

void hCalMin() { // /api/cal/min?m=-1  (Minutenraster, langsam)
  cmdJogMin(server.arg("m").toInt(), cfg.calRpm);
  sendOk();
}

void hCalSet() { // /api/cal/set?t=3:25   -> "die Zeiger zeigen gerade ..."
  if (g_running || segActive) { server.send(409, "text/plain", "Uhr laeuft noch"); return; }
  int32_t s;
  if (!parseHM(server.arg("t"), s)) { server.send(400, "text/plain", "bad"); return; }
  autoOn = false;
  zeroPos = g_pos - secToSteps(s);
  setTarget(g_pos);
  saveRel(); saveUi();
  sendOk();
}

void hStop() { autoOn = false; sweepPhase = 0; g_stopReq = true; saveUi(); sendOk(); }

static float argF(const char* n, float d, float lo, float hi) {
  if (!server.hasArg(n)) return d;
  float v = server.arg(n).toFloat();
  return v < lo ? lo : (v > hi ? hi : v);
}

void hSweep() {  // /api/sweep?s=12:00&e=12:30&d=10&b=0&go=1   (d = Minuten)
  int32_t a, b;
  if (!parseHM(server.arg("s"), a) || !parseHM(server.arg("e"), b)) { server.send(400, "text/plain", "bad"); return; }
  swS = server.arg("s"); swE = server.arg("e"); swB = server.arg("b") == "1";
  swD = argF("d", swD, 0.05f, 100000);
  saveSweep();
  if (server.arg("go") == "1") { sweepStart(a, b, swD * 60.0f, swB, faderToRpm(faderPct)); saveUi(); }
  sendOk();
}

void hCfg() {   // POST /api/cfg
  cfg.maxRpm   = argF("maxRpm", cfg.maxRpm, 1, 600);
  cfg.minRpm   = argF("minRpm", cfg.minRpm, 0.05f, cfg.maxRpm);
  cfg.accel    = argF("accel", cfg.accel, 1, 5000);
  cfg.startRpm = argF("startRpm", cfg.startRpm, 0.5f, 100);
  cfg.swRpm    = argF("swRpm", cfg.swRpm, 1, 600);
  cfg.calRpm   = argF("calRpm", cfg.calRpm, 0.2f, 30);
  cfg.autoFull = server.hasArg("autoFull");
  cfg.invDir   = server.hasArg("invDir");
  cfg.autoSmooth = server.hasArg("autoSmooth");
  cfg.artOn    = server.hasArg("artOn");
  cfg.artUni   = (uint16_t)constrain(server.arg("artUni").toInt(), 0, 32767);
  cfg.artCh    = (uint16_t)constrain(server.arg("artCh").toInt(), 1, 510);
  if (server.hasArg("apSsid") && server.arg("apSsid").length() > 0) cfg.apSsid = server.arg("apSsid");
  if (server.hasArg("apPass")) cfg.apPass = server.arg("apPass");
  cfg.staSsid  = server.arg("staSsid");
  cfg.staPass  = server.arg("staPass");
  if (server.hasArg("host") && server.arg("host").length() > 0) cfg.host = server.arg("host");
  saveCfg();
  w_rpm = faderToRpm(faderPct);
  sendOk();
}

void hDefaults() {   // Motor- und Art-Net-Werte zurücksetzen, WLAN-Daten bleiben erhalten
  Cfg d;
  d.apSsid = cfg.apSsid; d.apPass = cfg.apPass; d.staSsid = cfg.staSsid; d.staPass = cfg.staPass; d.host = cfg.host;
  cfg = d;
  saveCfg();
  w_rpm = faderToRpm(faderPct);
  sendOk();
}

void hReboot() { sendOk(); delay(300); ESP.restart(); }

// ---------------------------- HTML ------------------------------------------
const char MAIN_HTML[] PROGMEM = R"rawliteral(<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Große Uhr</title><style>
:root{--bg:#101012;--fg:#f4f4f6;--ac:#e8a33d;--bt:#2a2a31;--bt2:#3a3a44}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent;touch-action:manipulation}
html,body{margin:0;min-height:100%;background:var(--bg);color:var(--fg);font-family:-apple-system,system-ui,"Segoe UI",sans-serif}
body{display:flex;flex-direction:column;min-height:100dvh;padding:calc(env(safe-area-inset-top) + 4px) 10px calc(env(safe-area-inset-bottom) + 4px);gap:6px}
.top{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
#clk{font-size:clamp(34px,11vw,64px);font-weight:700;font-variant-numeric:tabular-nums;line-height:1}
#st{opacity:.75;font-size:14px;text-align:right}
.row{flex:1 1 56px;min-height:56px;display:grid;grid-template-columns:1fr 34%;gap:8px}
.tin{display:flex;flex-direction:row;align-items:center;gap:6px;background:var(--bt);border-radius:14px;padding:4px 10px;min-height:0;min-width:0}
.tin input[type=time]{flex:1 1 0;min-width:0;height:100%;max-height:52px;background:none;border:0;color:var(--fg);font-size:clamp(26px,8vw,40px);font-weight:600;font-family:inherit;text-align:left;outline:none;padding:0;margin:0}
.tin label{flex:0 0 auto;display:flex;align-items:center;gap:5px;font-size:13px;opacity:.85}
.tin input[type=checkbox]{width:26px;height:26px;margin:0;accent-color:var(--ac)}
button{border:0;border-radius:14px;background:var(--bt2);color:var(--fg);font-size:clamp(20px,6vw,30px);font-weight:700;font-family:inherit}
button:active{filter:brightness(1.5)}
.go{background:var(--ac);color:#1a1205;font-size:clamp(26px,8vw,42px)}
.fad{flex:0 0 auto;background:var(--bt);border-radius:14px;padding:8px 12px;display:flex;flex-direction:column;gap:2px}
.fad .l{display:flex;justify-content:space-between;font-size:14px;opacity:.85}
.fad input{width:100%;height:46px;accent-color:var(--ac);margin:0}
.jog{flex:1 1 48px;min-height:48px;display:grid;grid-template-columns:1fr 1fr;gap:8px}
.auto{display:grid;grid-template-columns:1.2fr 1fr 1.2fr;gap:8px;flex:0 0 56px}
.mu{display:flex;align-items:center;justify-content:center;background:var(--bt);border-radius:14px;padding:0 8px;gap:4px;min-width:0}
.mu span{font-size:28px;font-weight:700;color:var(--ac)}
.stop{flex:0 0 64px;background:#d93636;color:#fff;font-size:clamp(30px,9vw,44px);letter-spacing:2px;box-shadow:0 0 0 3px #ffffff22 inset}
.mu select{width:100%;min-width:0;background:none;border:0;color:var(--fg);font-size:24px;font-weight:600;font-family:inherit;outline:none;-webkit-appearance:none;appearance:none;padding:0}
.on{background:#3aa85c !important}
#ab{font-size:clamp(16px,5vw,24px);white-space:nowrap}
.sw{flex:0 0 auto;background:var(--bt);border-radius:14px;padding:8px 10px;display:flex;flex-direction:column;gap:6px}
.swh{display:flex;justify-content:space-between;font-size:14px;opacity:.85}
.swg{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr) minmax(0,.8fr);gap:6px}
.swg label{display:flex;flex-direction:column;font-size:12px;opacity:.9;gap:2px;min-width:0}
.swg input{width:100%;min-width:0;max-width:100%;background:#17171b;border:0;border-radius:10px;color:var(--fg);font-size:17px;font-family:inherit;padding:6px 4px;outline:none;box-sizing:border-box}
.swg label{overflow:hidden}
.swg2{display:grid;grid-template-columns:1fr 1fr;gap:8px;align-items:center}
.swg2 .go{font-size:clamp(20px,6vw,30px);padding:10px}
.cb{display:flex;align-items:center;gap:6px;font-size:14px}
.cb input{width:26px;height:26px;margin:0;accent-color:var(--ac)}
a{color:var(--ac);text-align:center;font-size:14px;padding:2px 2px 6px}
</style></head><body>
<div class="top"><div id="clk">--:--</div><div id="st">verbinde…</div></div>
<button class="stop" onclick="api('/api/stop')">STOP</button>
<div id="rows" style="display:contents"></div>
<div class="fad"><div class="l"><span>Geschwindigkeit</span><span id="spl"></span></div><input id="sp" type="range" min="1" max="100" value="50"></div>
<div class="jog"><button onclick="jog(-1)">◀ 1 min</button><button onclick="jog(1)">1 min ▶</button></div>
<div class="jog"><button onclick="jog(-60)">◀ 1 h</button><button onclick="jog(60)">1 h ▶</button></div>
<div class="sw"><div class="swh"><span>Ablauf</span><span id="swst"></span></div>
<div class="swg"><label>Von<input type="time" id="s0"></label><label>Bis<input type="time" id="s1"></label><label>Dauer min<input type="number" id="s2" min="0.1" step="any" inputmode="decimal"></label></div>
<div class="swg2"><label class="cb"><input type="checkbox" id="s3">Rückwärts</label><button class="go" onclick="sw(1)">Start</button></div></div>
<div class="auto"><button id="ab" onclick="tgl()">AUTO aus</button><div class="mu"><span>×</span><select id="mu" title="Multiplikator"></select></div><button onclick="phone()" style="font-size:clamp(14px,4vw,20px)">aktuelle Uhrzeit setzen</button></div>
<a href="/admin">Admin</a>
<script>
const $=id=>document.getElementById(id);
const api=u=>fetch(u).then(r=>r.text()).catch(()=>null);
let S=null,init=false;
const rows=$('rows');
for(let i=0;i<5;i++){rows.insertAdjacentHTML('beforeend',`<div class="row"><div class="tin"><input type="time" id="t${i}" onchange="sv(${i})"><label><input type="checkbox" id="b${i}" onchange="sv(${i})">Rückwärts</label></div><button class="go" onclick="go(${i})">Go</button></div>`)}
const q=i=>`i=${i}&t=${$('t'+i).value||'12:00'}&b=${$('b'+i).checked?1:0}`;
function sv(i){api('/api/set?'+q(i))}
function go(i){api('/api/go?'+q(i))}
function swq(go){return `s=${$('s0').value||'12:00'}&e=${$('s1').value||'12:00'}&d=${$('s2').value||1}&b=${$('s3').checked?1:0}&go=${go}`}
function sw(go){api('/api/sweep?'+swq(go))}
for(const i of ['s0','s1','s2','s3'])$(i).onchange=()=>sw(0);
const mmss=t=>{t=Math.max(0,t|0);const h=(t/3600)|0,m=((t%3600)/60)|0,s=t%60;return (h?h+':'+String(m).padStart(2,'0'):m)+':'+String(s).padStart(2,'0')};
function jog(m){api('/api/jog?m='+m)}
function tgl(){api('/api/auto?on='+(S&&S.auto?0:1)+'&mult='+($('mu').value||1))}
const MU=[0.5,1,2,5,10,20,30,60,120,300,600,1200,3600];
function fillMu(v){const s=$('mu');s.innerHTML='';const a=MU.slice();if(!a.includes(v)){a.push(v);a.sort((x,y)=>x-y)}a.forEach(x=>s.add(new Option(String(x),x)));s.value=v}
function phone(){const d=new Date();api(`/api/phone?h=${d.getHours()}&m=${d.getMinutes()}&s=${d.getSeconds()}`)}
$('mu').onchange=()=>api('/api/auto?mult='+($('mu').value||1));
function rpmOf(p){const lo=S.cfg.minRpm,hi=Math.max(S.cfg.maxRpm,lo);return lo*Math.pow(hi/lo,(p-1)/99)}
function lab(){if(S)$('spl').textContent=rpmOf(+$('sp').value).toFixed(1)+' U/min'}
let tm=0;
$('sp').oninput=()=>{lab();clearTimeout(tm);tm=setTimeout(()=>api('/api/speed?p='+$('sp').value),60)};
$('sp').onchange=()=>api('/api/speed?save=1&p='+$('sp').value);
async function poll(){
  try{S=await (await fetch('/api/state')).json()}catch(e){$('st').textContent='keine Verbindung';return}
  $('clk').textContent=S.clock;
  $('st').innerHTML=(S.moving?'fährt · '+S.rpm+' U/min · '+S.mode:'Stillstand')+(S.auto?'<br>AUTO ×'+S.mult:'')+(S.sw==1?'<br>ABLAUF: fährt zum Start':(S.sw==2?'<br>ABLAUF: noch '+mmss(S.swr):''));
  $('swst').textContent=S.sw==2?'läuft · noch '+mmss(S.swr):(S.sw==1?'fährt zum Start':'');
  $('ab').textContent=S.auto?'AUTO an':'AUTO aus';$('ab').classList.toggle('on',S.auto);
  if(!init){init=true;for(let i=0;i<5;i++){$('t'+i).value=S.t[i];$('b'+i).checked=S.b[i]}$('s0').value=S.sws;$('s1').value=S.swe;$('s2').value=S.swd;$('s3').checked=S.swb;$('sp').value=S.fader;fillMu(+S.mult);lab()}
}
poll();setInterval(poll,700);
</script></body></html>)rawliteral";

const char ADMIN_HTML[] PROGMEM = R"rawliteral(<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Große Uhr – Admin</title><style>
:root{--bg:#101012;--fg:#f4f4f6;--ac:#e8a33d;--bt:#2a2a31;--bt2:#3a3a44}
*{box-sizing:border-box}
body{margin:0;padding:12px 12px 40px;background:var(--bg);color:var(--fg);font-family:-apple-system,system-ui,sans-serif;max-width:640px;margin:auto}
h1{font-size:22px;margin:6px 0}h2{font-size:17px;margin:22px 0 8px;color:var(--ac)}
.card{background:var(--bt);border-radius:14px;padding:10px 12px}
label{display:flex;justify-content:space-between;align-items:center;gap:10px;margin:8px 0;font-size:15px}
label small{display:block;opacity:.6;font-size:12px}
input[type=text],input[type=number],input[type=time],input[type=password]{width:48%;min-width:110px;padding:9px;border-radius:10px;border:0;background:#17171b;color:var(--fg);font-size:16px}
input[type=checkbox]{width:24px;height:24px;accent-color:var(--ac)}
button{border:0;border-radius:12px;background:var(--bt2);color:var(--fg);padding:12px 8px;font-size:16px;font-weight:600;font-family:inherit}
button:active{filter:brightness(1.5)}.pri{background:var(--ac);color:#1a1205}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:6px 0}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}
#msg{position:sticky;bottom:8px;background:#222;border-radius:10px;padding:8px 12px;margin-top:12px;display:none}
a{color:var(--ac)}
</style></head><body>
<h1>Große Uhr – Admin</h1><a href="/">← Steuerung</a>
<h2>Kalibrierung</h2><div class="card">
<div>Interne Anzeige: <b id="clk">–</b> · Position <span id="pos">–</span> · <span id="st"></span></div>
<div class="g4">
<button onclick="cm(-10)">−10 min</button><button onclick="cm(-1)">−1 min</button><button onclick="cm(1)">+1 min</button><button onclick="cm(10)">+10 min</button>
<button onclick="cj(-16)">−1 Schritt</button><button onclick="cj(-1)">−1 µ</button><button onclick="cj(1)">+1 µ</button><button onclick="cj(16)">+1 Schritt</button>
</div>
<small style="opacity:.6">1 Schritt = Vollschritt = 1,8° (≈ 19 mm am Zeigerende bei 60 cm), 1 µ = 1/16 Schritt</small>
<label style="margin-top:12px">Die Zeiger zeigen gerade:<input type="time" id="ct" value="12:00"></label>
<div class="g2"><button class="pri" onclick="cs($('ct').value)">Zeit übernehmen</button><button onclick="cs('12:00')">Hier ist 12:00</button></div>
<div class="g2"><button onclick="api('/api/stop')">Stopp</button><span></span></div>
</div>
<form id="f">
<h2>Motor</h2><div class="card">
<label>Maximale Geschwindigkeit<small>U/min Minutenzeiger · Standard 60</small><input type="number" step="any" name="maxRpm"></label>
<label>Minimale Geschwindigkeit<small>Fader ganz unten · Standard 1</small><input type="number" step="any" name="minRpm"></label>
<label>Beschleunigung<small>U/min pro Sekunde · Standard 100</small><input type="number" step="any" name="accel"></label>
<label>Anfahrgeschwindigkeit<small>U/min · Standard 3</small><input type="number" step="any" name="startRpm"></label>
<label>Vollschritt ab<small>U/min (darunter 1/16 Mikroschritt) · Standard 30</small><input type="number" step="any" name="swRpm"></label>
<label>Automatisch Vollschritt nutzen<input type="checkbox" name="autoFull"></label>
<label>Kalibriertasten-Tempo<small>U/min · Standard 2</small><input type="number" step="any" name="calRpm"></label>
<label>Auto fließend<small>an: kleinste Schritte (ca. alle 1,1 s bei ×1) · aus: eine Minute pro Minute wie eine Uhr · Standard: aus</small><input type="checkbox" name="autoSmooth"></label>
<label>Drehrichtung invertieren<small>Standard: aus · nur ankreuzen, falls vorwärts gegen den Uhrzeigersinn läuft</small><input type="checkbox" name="invDir"></label>
</div>
<h2>Art-Net</h2><div class="card">
<label>Art-Net aktiv<input type="checkbox" name="artOn"></label>
<label>Universe<small>0–32767</small><input type="number" name="artUni"></label>
<label>Startkanal<small>K1 Stunden (20/Std.), K2 Minuten (4/Min.), K3 Tempo/Richtung (0 Stopp, 1–126 vor, 127–255 rück)</small><input type="number" name="artCh"></label>
<div id="art" style="opacity:.7;font-size:13px"></div>
</div>
<h2>WLAN</h2><div class="card">
<label>Eigener AP – Name<input type="text" name="apSsid"></label>
<label>AP-Passwort<small>mind. 8 Zeichen, sonst offen</small><input type="text" name="apPass"></label>
<label>Haus-WLAN – Name<input type="text" name="staSsid"></label>
<label>Haus-WLAN – Passwort<input type="password" name="staPass"></label>
<label>Hostname<small>→ http://&lt;name&gt;.local</small><input type="text" name="host"></label>
<div id="ip" style="opacity:.7;font-size:13px"></div>
</div>
<div class="g2"><button type="button" class="pri" onclick="save(false)">Speichern</button><button type="button" onclick="save(true)">Speichern &amp; Neustart</button></div>
<div class="g2"><button type="button" onclick="defaults()">Standardwerte (Motor &amp; Art-Net)</button><span></span></div>
</form>
<div id="msg"></div>
<script>
const $=id=>document.getElementById(id);
const msg=t=>{const m=$('msg');m.textContent=t;m.style.display='block';clearTimeout(msg.t);msg.t=setTimeout(()=>m.style.display='none',3500)};
const api=u=>fetch(u).then(async r=>{if(!r.ok)msg(await r.text());return r}).catch(()=>msg('keine Verbindung'));
const cm=m=>api('/api/cal/min?m='+m),cj=d=>api('/api/cal/jog?d='+d);
async function cs(t){const r=await api('/api/cal/set?t='+t);if(r&&r.ok)msg('Kalibriert: Zeiger zeigen '+t)}
let first=true;
async function poll(){
 let S;try{S=await (await fetch('/api/state')).json()}catch(e){return}
 $('clk').textContent=S.clock;$('pos').textContent=S.pos;$('st').textContent=S.moving?'fährt':'Stillstand';
 $('art').textContent='Art-Net-Pakete empfangen: '+S.art;$('ip').textContent='Haus-WLAN IP: '+S.ip;
 if(first){first=false;const f=$('f');for(const k in S.cfg){const e=f.elements[k];if(!e)continue;if(e.type==='checkbox')e.checked=S.cfg[k];else e.value=S.cfg[k]}}
}
async function defaults(){
 if(!confirm('Motor- und Art-Net-Werte auf Standard zurücksetzen? (WLAN-Daten bleiben erhalten)'))return;
 const r=await fetch('/api/defaults',{method:'POST'}).catch(()=>null);
 if(r&&r.ok){first=true;await poll();msg('Standardwerte geladen')}else msg('Fehler')
}
async function save(rb){
 const body=new URLSearchParams(new FormData($('f')));
 const r=await fetch('/api/cfg',{method:'POST',body}).catch(()=>null);
 if(!r||!r.ok){msg('Fehler beim Speichern');return}
 if(rb){msg('Neustart…');fetch('/api/reboot');setTimeout(()=>location.href='/',6000)}else{msg('Gespeichert');setTimeout(()=>location.href='/',400)}
}
poll();setInterval(poll,800);
</script></body></html>)rawliteral";

void hMain()  { server.send_P(200, "text/html", MAIN_HTML); }
void hAdmin() { server.send_P(200, "text/html", ADMIN_HTML); }

// ----------------------------------------------------------------------------
// Setup / Loop
// ----------------------------------------------------------------------------
static uint32_t lastSave = 0, lastWifi = 0;
static int32_t  lastSavedRel = -1;

void startTimer() {
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  stepTimer = timerBegin(1000000);
  timerAttachInterrupt(stepTimer, &onTimer);
  timerAlarm(stepTimer, 1000000 / TICK_HZ, true, 0);
#else
  stepTimer = timerBegin(0, 80, true);
  timerAttachInterrupt(stepTimer, &onTimer, true);
  timerAlarmWrite(stepTimer, 1000000 / TICK_HZ, true);
  timerAlarmEnable(stepTimer);
#endif
}

void setupWifi() {
  WiFi.persistent(false);
  WiFi.mode(WIFI_AP_STA);
  WiFi.setHostname(cfg.host.c_str());
  if (cfg.apPass.length() >= 8) WiFi.softAP(cfg.apSsid.c_str(), cfg.apPass.c_str());
  else WiFi.softAP(cfg.apSsid.c_str());
  if (cfg.staSsid.length() > 0) WiFi.begin(cfg.staSsid.c_str(), cfg.staPass.c_str());
  WiFi.setSleep(false);
  MDNS.begin(cfg.host.c_str());
  MDNS.addService("http", "tcp", 80);
}

void setup() {
  Serial.begin(115200);
  pinMode(STEP_PIN, OUTPUT); digitalWrite(STEP_PIN, LOW);
  pinMode(DIR_PIN, OUTPUT);  digitalWrite(DIR_PIN, LOW);
  pinMode(MS1_PIN, OUTPUT); pinMode(MS2_PIN, OUTPUT); pinMode(MS3_PIN, OUTPUT);
  setMicrostep(true);
  if (EN_PIN >= 0) { pinMode(EN_PIN, OUTPUT); digitalWrite(EN_PIN, LOW); }

  prefs.begin("uhr", false);
  loadAll();
  // Position: Treiber startet bei "0"; gespeicherte Zeigerstellung wird als Versatz übernommen
  int32_t rel = prefs.getInt("rel", 0);
  g_pos = 0; w_target = 0; zeroPos = -rel; lastSavedRel = rel;
  w_rpm = faderToRpm(faderPct);

  setupWifi();
  udp.begin(6454);

  server.on("/", hMain);
  server.on("/admin", hAdmin);
  server.on("/api/state", hState);
  server.on("/api/set", hSet);
  server.on("/api/go", hGo);
  server.on("/api/speed", hSpeed);
  server.on("/api/jog", hJog);
  server.on("/api/auto", hAuto);
  server.on("/api/sweep", hSweep);
  server.on("/api/phone", hPhone);
  server.on("/api/stop", hStop);
  server.on("/api/cal/jog", hCalJog);
  server.on("/api/cal/min", hCalMin);
  server.on("/api/cal/set", hCalSet);
  server.on("/api/cfg", HTTP_POST, hCfg);
  server.on("/api/defaults", HTTP_POST, hDefaults);
  server.on("/api/reboot", hReboot);
  server.onNotFound([]() { server.sendHeader("Location", "/"); server.send(302, "text/plain", ""); });
  server.begin();

  startTimer();
  xTaskCreatePinnedToCore(motionTask, "motion", 4096, nullptr, 3, nullptr, 1);
}

void loop() {
  server.handleClient();
  handleArtnet();

  uint32_t now = millis();
  // WLAN-Wiederverbindung zum Haus-WLAN
  if (cfg.staSsid.length() > 0 && WiFi.status() != WL_CONNECTED && now - lastWifi > 15000) {
    lastWifi = now; WiFi.disconnect(); WiFi.begin(cfg.staSsid.c_str(), cfg.staPass.c_str());
  }
  // Position sichern: im Stillstand nach 2 s, im Automodus alle 5 min
  bool moving = g_running || segActive;
  int32_t rel = relOf(g_pos);
  if (!moving && rel != lastSavedRel && now - lastSave > 2000) { saveRel(); lastSavedRel = rel; lastSave = now; }
  else if (autoOn && rel != lastSavedRel && now - lastSave > 300000) { saveRel(); lastSavedRel = rel; lastSave = now; }
  if (moving) lastSave = now;
  delay(1);
}
