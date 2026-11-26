#include <Arduino.h>
#include <ArduinoOTA.h>
#include <DHT.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <WebServer.h>
#include <WiFi.h>
#include <Wire.h>
#include <esp_ota_ops.h>
#include <esp_timer.h>
#include <esp_wifi.h>
#include "Dashboard.h"

constexpr char hostname[] = "bedroom-air";
constexpr unsigned long sampleInterval = 3000;
constexpr unsigned long preheat = 60000;
constexpr size_t historyCapacity = 101;
struct Sample {
  unsigned long at;
  unsigned ppm;
};
Sample history[historyCapacity] = {};
size_t nextSample = 0, sampleCount = 0;
// One sample per minute in RAM. Sequence numbers restart with a new boot ID.
struct MinuteSample {
  uint32_t uptime;
  uint16_t co2;
  int16_t temperatureTenths;
  int16_t humidityTenths;
  float light;
};
constexpr uint32_t minuteCapacity = 1440;
constexpr uint32_t pageSize = 48;
MinuteSample minutes[minuteCapacity];
uint32_t minuteSequence = 0, lastMinute = 0;
char bootId[17];
unsigned long lastSample = 0, lastJoin = 0;
unsigned ppm = 0;
float temperature = NAN, humidity = NAN;
float lux = NAN;
uint8_t lightAddress = 0;
String otaHash;
Preferences settings;
const char *co2Status = "Warming up";
bool warmed = false, savedNetwork = false, online = false;
DHT dht(18, DHT22);
WebServer server(80);

void readLight() {
  lux = NAN;
  if (!lightAddress) {
    // ADDR low or high. Start continuous high-resolution conversions.
    for (uint8_t address : {0x23, 0x5c}) {
      Wire.beginTransmission(address);
      Wire.write(0x10);
      if (Wire.endTransmission() == 0) {
        lightAddress = address;
        break;
      }
    }
    return;  // The first conversion needs up to 180 ms.
  }
  if (Wire.requestFrom(lightAddress, size_t(2)) != 2) {
    lightAddress = 0;
    return;
  }
  uint16_t raw = static_cast<uint16_t>(Wire.read()) << 8;
  raw |= Wire.read();
  lux = raw / 1.2f;
}

bool validOtaHash(const String &value) {
  if (value.length() != 64) return false;
  for (size_t i = 0; i < value.length(); ++i) {
    if (!isxdigit(static_cast<unsigned char>(value[i]))) return false;
  }
  return true;
}

void startOta() {
  if (!validOtaHash(otaHash)) return;
  ArduinoOTA.setHostname(hostname);
  ArduinoOTA.setMdnsEnabled(false);  // HTTP and OTA share our mDNS responder.
  ArduinoOTA.setPasswordHash(otaHash.c_str());
  ArduinoOTA.begin();
  MDNS.enableArduino(3232, true);
}

void readCo2() {
  ppm = 0;
  if (!warmed && millis() < preheat) return;
  warmed = true;
  const uint8_t request[] = {0xFF, 0x01, 0x86, 0, 0, 0, 0, 0, 0x79};
  while (Serial2.available()) Serial2.read();
  Serial2.write(request, sizeof(request));
  uint8_t reply[9];
  size_t n = Serial2.readBytes(reply, sizeof(reply));
  if (n != sizeof(reply)) {
    co2Status = n == 0 ? "Sensor did not reply" : "Incomplete sensor reply";
    return;
  }
  uint8_t sum = 0;
  for (size_t i = 1; i < sizeof(reply); ++i) sum += reply[i];
  if (reply[0] != 0xFF || reply[1] != 0x86 || sum != 0) {
    co2Status = "Invalid sensor reply";
    return;
  }
  unsigned value = (static_cast<unsigned>(reply[2]) << 8) | reply[3];
  if (value < 400 || value > 5000) {
    co2Status = "Outside sensor range";
    return;
  }
  ppm = value;
  co2Status = "Live";
}

void sampleSensors() {
  readCo2();
  readLight();
  humidity = dht.readHumidity();
  temperature = dht.readTemperature();
  const uint32_t uptime = esp_timer_get_time() / 1000000ULL;
  if (minuteSequence == 0 || uptime / 60 != lastMinute) {
    lastMinute = uptime / 60;
    minutes[minuteSequence % minuteCapacity] = {
      uptime, static_cast<uint16_t>(ppm),
      static_cast<int16_t>(isfinite(temperature) ? lroundf(temperature * 10) : INT16_MIN),
      static_cast<int16_t>(isfinite(humidity) ? lroundf(humidity * 10) : INT16_MIN), lux
    };
    ++minuteSequence;
  }
  history[nextSample] = {millis(), ppm};
  nextSample = (nextSample + 1) % historyCapacity;
  if (sampleCount < historyCapacity) ++sampleCount;
  if (ppm) Serial.printf("CO2 %u ppm", ppm);
  else Serial.printf("CO2 %s", co2Status);
  if (isnan(temperature) || isnan(humidity)) Serial.println(" | DHT22 read failed");
  else Serial.printf(" | Temperature %.1f C | Humidity %.1f %%RH\n", temperature, humidity);
}

void sendMinutes() {
  const uint32_t oldest = minuteSequence > minuteCapacity ? minuteSequence - minuteCapacity + 1 : 1;
  uint32_t after = 0;
  if (server.arg("boot") == bootId) {
    after = strtoul(server.arg("after").c_str(), nullptr, 10);
  }
  const uint32_t first = after >= minuteSequence ? minuteSequence + 1 : max(oldest, after + 1);
  const uint32_t end = min(minuteSequence + 1, first + pageSize);
  String json;
  json.reserve(300 + (end - first) * 100);
  json = "{\"boot\":\"";
  json += bootId;
  json += "\",\"uptime\":";
  json += static_cast<uint32_t>(esp_timer_get_time() / 1000000ULL);
  json += ",\"latest\":";
  json += minuteSequence;
  json += ",\"samples\":[";
  for (uint32_t seq = first; seq < end; ++seq) {
    const MinuteSample &s = minutes[(seq - 1) % minuteCapacity];
    if (seq != first) json += ',';
    json += "{\"seq\":"; json += seq;
    json += ",\"up\":"; json += s.uptime;
    json += ",\"co2\":"; json += s.co2 ? String(s.co2) : String("null");
    json += ",\"temperature\":";
    json += s.temperatureTenths == INT16_MIN ? String("null") : String(s.temperatureTenths / 10.f, 1);
    json += ",\"humidity\":";
    json += s.humidityTenths == INT16_MIN ? String("null") : String(s.humidityTenths / 10.f, 1);
    json += ",\"lux\":"; json += isfinite(s.light) ? String(s.light, 1) : String("null");
    json += '}';
  }
  json += "]}";
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "application/json", json);
}

void sendReadings() {
  String json;
  json.reserve(1950);
  json = "{\"co2\":";
  json += ppm ? String(ppm) : String("null");
  json += ",\"temperature\":";
  json += isfinite(temperature) ? String(temperature, 1) : String("null");
  json += ",\"humidity\":";
  json += isfinite(humidity) ? String(humidity, 1) : String("null");
  json += ",\"lux\":";
  json += isfinite(lux) ? String(lux, 1) : String("null");
  json += ",\"slot\":\"";
  json += esp_ota_get_running_partition()->label;
  json += "\"";
  json += ",\"status\":\"";
  json += co2Status;
  json += "\",\"history\":[";
  const unsigned long now = millis();
  bool first = true;
  for (size_t i = 0; i < sampleCount; ++i) {
    const Sample &s = history[(nextSample + historyCapacity - sampleCount + i) % historyCapacity];
    unsigned long age = now - s.at;
    if (age > 300000) continue;
    if (!first) json += ',';
    first = false;
    json += '[';
    json += String(age / 1000);
    json += ',';
    json += s.ppm ? String(s.ppm) : String("null");
    json += ']';
  }
  json += "]}";
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "application/json", json);
}

// USB-only provisioning. JOIN <SSID byte count> <key byte count> followed
// by a newline and the two byte strings. Credentials are never echoed.
void handleUsb() {
  if (!Serial.available()) return;
  String header = Serial.readStringUntil('\n');
  header.trim();
  if (header.startsWith("OTAKEY ")) {
    String hash = header.substring(7);
    if (validOtaHash(hash) && settings.putString("ota-hash", hash) == hash.length()) {
      bool wasConfigured = validOtaHash(otaHash);
      otaHash = hash;
      if (online) {
        if (wasConfigured) ArduinoOTA.setPasswordHash(otaHash.c_str());
        else startOta();
      }
      Serial.println("OTA key saved");
    }
    return;
  }
  if (header == "URL") {
    if (WiFi.isConnected()) Serial.printf("Dashboard http://%s/\n", WiFi.localIP().toString().c_str());
    else Serial.println("Wi-Fi offline");
    return;
  }
  unsigned ssidLength, keyLength;
  if (sscanf(header.c_str(), "JOIN %u %u", &ssidLength, &keyLength) != 2 ||
      !ssidLength || ssidLength > 32 || keyLength > 64) return;
  char ssid[33] = {}, key[65] = {};
  if (Serial.readBytes(ssid, ssidLength) == ssidLength && Serial.readBytes(key, keyLength) == keyLength) {
    WiFi.begin(ssid, key);
    savedNetwork = true;
    lastJoin = millis();
    Serial.println("Wi-Fi settings received over USB");
  }
  memset(key, 0, sizeof(key));
}

void updateNetwork() {
  const bool connected = WiFi.isConnected();
  if (connected && !online) {
    if (MDNS.begin(hostname)) MDNS.addService("http", "tcp", 80);
    startOta();
    server.begin();
    Serial.printf("Dashboard http://%s/\n", WiFi.localIP().toString().c_str());
  } else if (!connected && online) {
    ArduinoOTA.end();
    server.stop();
    MDNS.end();
  }
  online = connected;
  if (!online && savedNetwork && millis() - lastJoin >= 30000) {
    lastJoin = millis();
    WiFi.reconnect();
  }
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(1000);
  Serial2.begin(9600, SERIAL_8N1, 16, 17);
  Serial2.setTimeout(500);
  dht.begin();
  Wire.begin(21, 22);
  Wire.setTimeOut(30);
  settings.begin("bedroom-air");
  otaHash = settings.getString("ota-hash", "");
  server.on("/", HTTP_GET, [] { server.send_P(200, "text/html; charset=utf-8", dashboard); });
  server.on("/api/readings", HTTP_GET, sendReadings);
  server.on("/api/minutes", HTTP_GET, sendMinutes);
  WiFi.setHostname(hostname);
  WiFi.persistent(true);
  WiFi.mode(WIFI_STA);
  snprintf(bootId, sizeof(bootId), "%08lx%08lx", (unsigned long)esp_random(), (unsigned long)esp_random());
  WiFi.setAutoReconnect(true);
  wifi_config_t config = {};
  savedNetwork = esp_wifi_get_config(WIFI_IF_STA, &config) == ESP_OK && config.sta.ssid[0];
  if (savedNetwork) WiFi.begin();
  Serial.println("Bedroom Air ready");
}

void loop() {
  handleUsb();
  updateNetwork();
  if (online) {
    ArduinoOTA.handle();
    server.handleClient();
  }
  if (millis() - lastSample >= sampleInterval) {
    lastSample = millis();
    sampleSensors();
  }
  delay(1);
}
