from time import sleep

import dht
from machine import Pin


sensor = dht.DHT22(Pin(18))
print("DHT22 on GPIO18")

while True:
    sleep(3)
    try:
        sensor.measure()
    except (OSError, ValueError) as error:
        print("DHT22 read failed:", error)
    else:
        print("Temperature {:.1f} C | Humidity {:.1f} %RH".format(
            sensor.temperature(), sensor.humidity()
        ))
