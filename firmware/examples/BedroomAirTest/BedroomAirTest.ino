#include <Arduino.h>
#include <DHT.h>

constexpr uint8_t dhtPin = 18;
constexpr int co2RxPin = 16;  // ESP32 receives from the MH-Z19C TX pin.
constexpr int co2TxPin = 17;  // ESP32 transmits to the MH-Z19C RX pin.
constexpr unsigned long preheatMs = 60000;
constexpr unsigned long sampleIntervalMs = 3000;

DHT dht(dhtPin, DHT22);
bool warmingUp = true;

void printCo2() {
  const unsigned long elapsed = millis();
  if (warmingUp && elapsed < preheatMs) {
    Serial.printf("CO2 warming up (%lu s left)", (preheatMs - elapsed + 999) / 1000);
    return;
  }
  warmingUp = false;

  // Winsen read-concentration command. This test only requests measurements.
  const uint8_t request[] = {0xFF, 0x01, 0x86, 0, 0, 0, 0, 0, 0x79};
  while (Serial2.available() > 0) {
    Serial2.read();
  }
  Serial2.write(request, sizeof(request));
  uint8_t reply[9];
  const size_t received = Serial2.readBytes(reply, sizeof(reply));
  if (received == 0) {
    Serial.print("CO2 sensor did not reply");
    return;
  }
  if (received != sizeof(reply)) {
    Serial.printf("CO2 incomplete reply (%u/9 bytes)", static_cast<unsigned>(received));
    return;
  }
  uint8_t sum = 0;
  for (size_t i = 1; i < sizeof(reply); ++i) {
    sum += reply[i];  // Bytes 1 through 8, including the checksum, sum to zero modulo 256.
  }
  if (reply[0] != 0xFF || reply[1] != 0x86 || sum != 0) {
    Serial.print("CO2 invalid reply (header or checksum)");
    return;
  }
  const unsigned ppm = (static_cast<unsigned>(reply[2]) << 8) | reply[3];
  if (ppm < 400 || ppm > 5000) {
    Serial.printf("CO2 outside sensor range (%u ppm)", ppm);
    return;
  }
  Serial.printf("CO2 %u ppm", ppm);
}

void setup() {
  Serial.begin(115200);
  Serial2.begin(9600, SERIAL_8N1, co2RxPin, co2TxPin);
  Serial2.setTimeout(500);
  dht.begin();
  Serial.println("Bedroom air test | MH-Z19C + DHT22");
}

void loop() {
  delay(sampleIntervalMs);
  printCo2();
  const float humidity = dht.readHumidity();
  const float temperatureC = dht.readTemperature();
  if (isnan(humidity) || isnan(temperatureC)) {
    Serial.println(" | DHT22 read failed");
  } else {
    Serial.printf(" | Temperature %.1f C | Humidity %.1f %%RH\n", temperatureC, humidity);
  }
}
