# Flash the ESP32

The main sketch reads the MH-Z19C over UART, the DHT22 on GPIO18 and the optional BH1750 over I²C. It serves a live page, a JSON API and a 1,440-sample minute buffer. The project uses Arduino C++ and PlatformIO. The small Python tools run on your computer during setup.

## First USB flash

1. Install PlatformIO Core 6.x (or use the PlatformIO IDE terminal), and install `uv` to run the USB setup helper. Use a data-capable USB-C cable. These commands run from the repository root. [PlatformIO installation](https://docs.platformio.org/en/latest/core/installation/index.html) · [uv installation](https://docs.astral.sh/uv/getting-started/installation/)
2. For the first flash, lift the ESP32 out of the unpowered carrier and connect it directly to your computer. If you use USB with the board installed, follow the JP1 and supply sequence in the [carrier power guide](../hardware/Assembly.md#first-power-and-normal-operation).
3. Find the USB serial device and upload the sketch. Replace `YOUR_PORT` with the device reported on your computer, such as a `/dev/cu.*` device on macOS, `/dev/ttyUSB0` on Linux, or `COM3` on Windows.

```sh
pio device list
pio run -d firmware -t upload --upload-port YOUR_PORT
uv run tools/provision.py YOUR_PORT
```

The helper asks for your **2.4 GHz Wi-Fi name and password** and optionally an **OTA password** for later wireless updates. It sends the configuration through USB and prints the dashboard address once the board joins. Save the OTA password in your password manager. Wi-Fi and OTA settings persist across reboots. Close any open serial monitor before provisioning.

Open `http://bedroom-air.local/` on a phone connected to the same network, or use the address printed by the helper. You can get the IP again by opening the serial monitor at **115200 baud** and sending `URL` with a newline. To follow the readings in a terminal, run:

```sh
pio device monitor -p YOUR_PORT -b 115200
```

Unplug USB before inserting the ESP32 into its carrier. Follow the first-power checks, then allow at least a minute for CO₂ warm-up. Confirm a ppm value, temperature and humidity, and cover/uncover the optional light sensor to see lux change. A missing sensor is shown as unavailable.

## Wireless updates

With `pio` on your PATH and both devices on the same LAN, run the following from the repository root. It rebuilds the main sketch and prompts for the OTA password you chose over USB.

```sh
python3 tools/ota.py bedroom-air.local
```

You can substitute the ESP32’s IP address. A firmware update reboots the ESP32 and clears its RAM buffer. Already saved history stays on the Pi. If you forget the OTA password, run the USB setup helper again and choose a new one.

## Sensor pins and diagnostics

| Module | ESP32 connections |
| --- | --- |
| MH-Z19C | Sensor TXD → GPIO16 (RX2), sensor RXD → GPIO17 (TX2), shared GND and regulated 5 V at the sensor |
| DHT22 breakout | OUT → GPIO18, + → 3V3, − → GND |
| BH1750 / GY-302 | SDA → GPIO21, SCL → GPIO22, VCC → 3V3, GND → GND. The carrier grounds ADDR. The firmware probes 0x23 and 0x5C. |

[Wiring diagram](../docs/images/wiring.svg) · [Harness pin numbers and terminal order](../hardware/Assembly.md#terminal-map)

- `GET /api/readings` returns the live sample, status and a short CO₂ trace.
- `GET /api/minutes` returns paged buffered samples. The Pi handles paging and deduplication.
- The [standalone bench sketches](examples/) include the DHT-only test, the combined CO₂/DHT serial test, and the original MicroPython DHT diagnostic. Normal operation uses [BedroomAir.ino](BedroomAir/BedroomAir.ino) and [Dashboard.h](BedroomAir/Dashboard.h).
