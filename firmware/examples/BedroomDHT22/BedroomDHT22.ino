#include <Arduino.h>
#include <DHT.h>

constexpr uint8_t dataPin = 18;
constexpr unsigned long sampleIntervalMs = 3000;
DHT sensor(dataPin, DHT22);

void setup() {
  Serial.begin(115200);
  sensor.begin();
  Serial.println("Arduino C++: DHT22 on GPIO18");
}

void loop() {
  delay(sampleIntervalMs);
  const float humidity = sensor.readHumidity();
  const float temperatureC = sensor.readTemperature();

  if (isnan(humidity) || isnan(temperatureC)) {
    Serial.println("DHT22 read failed");
    return;
  }

  Serial.printf("Temperature %.1f C | Humidity %.1f %%RH\n", temperatureC, humidity);
}
