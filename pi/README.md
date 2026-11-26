# Run the history dashboard on a Raspberry Pi

The Pi polls the ESP32, stores one reading per minute in SQLite and serves the dashboard over your LAN. Leave the Pi and the sensor powered overnight. The Mac can sleep after installation.

## Prepare the Pi

1. Use Raspberry Pi Imager to write **Raspberry Pi OS Lite (64-bit)** to a spare microSD for the **Zero 2 W**. Writing the image erases the selected card. In the customization screen set the hostname to **air-history**, create your own user, enable SSH, and configure your 2.4 GHz Wi-Fi, wireless country and local time zone. The night report uses the Pi’s local clock, from 20:00 to 08:00. [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Insert the card and power the Pi through **PWR IN**. From your computer, connect with `ssh YOUR_USER@air-history.local`. On the Pi, check `timedatectl` and run `getent ahostsv4 bedroom-air.local` to confirm it can resolve the sensor. Raspberry Pi OS should have mDNS available. If it is missing, install `avahi-daemon` and `libnss-mdns`, and start `avahi-daemon`.
3. Build the Go binary on your computer. Use Go 1.27.4 or later and run these commands from the repository root. The UI and its font are embedded into the executable.

```sh
mkdir -p build
(cd pi && go test ./... && CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -trimpath -o ../build/bedroom-air-history .)
scp build/bedroom-air-history pi/bedroom-air.service pi/bedroom-home.service YOUR_USER@air-history.local:
```

For a **32-bit** Raspberry Pi OS on a Zero 2 W, replace `GOARCH=arm64` with `GOARCH=arm GOARM=7`. Check the OS architecture with `dpkg --print-architecture` on the Pi (`arm64` or `armhf`).

## Start logging

On the Pi, from the home directory you copied the files into:

```sh
sudo install -m 0755 bedroom-air-history /usr/local/bin/bedroom-air-history
sudo install -m 0644 bedroom-air.service bedroom-home.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bedroom-air.service
curl -fsS http://127.0.0.1:8080/api/live
```

Open **`http://air-history.local:8080/`** in Safari on your home Wi-Fi. The live card should update within a few seconds. Once at least two minute samples are saved, select a metric and inspect two points on the history chart. In the morning open **Last night**. **Airing out** fills in when the saved data contains a qualifying event.

The service starts automatically after a Pi reboot. It writes to `/var/lib/bedroom-air/readings.sqlite`. To back it up while the service is running, use SQLite’s backup command (install the `sqlite3` CLI first if needed):

```sh
sudo install -d -m 0700 /var/backups/bedroom-air
sudo sqlite3 /var/lib/bedroom-air/readings.sqlite ".backup /var/backups/bedroom-air/history.sqlite"
```

Move the backup to private storage. The HTTP dashboard is intended for your home Wi-Fi and has no sign-in. Keep it on the LAN.

## Optional Apple Home pairing

On the Pi:

```sh
sudo systemctl enable --now bedroom-home.service
sudo cat /var/lib/bedroom-home/setup-pin
```

On the iPhone connected to the same LAN, open **Home → + → Add Accessory → More Options**, select **Bedroom Air**, and enter the eight-digit code from your Pi. Accept the uncertified-accessory prompt if it appears. The service advertises CO₂, temperature and humidity. The full history stays in Safari. The pairing state lives in `/var/lib/bedroom-home/`. Keep it private and retain it across upgrades.

On macOS, you can generate your own pairing image as an alternative to typing the code. With SSH key access and a Pi user allowed to read the PIN using `sudo -n`, run this pipeline from the repository root:

```sh
ssh YOUR_USER@air-history.local 'sudo -n cat /var/lib/bedroom-home/setup-pin' | swift tools/pairing-qr.swift bedroom-pairing.png
```

## If you don’t see readings

- **ESP32 page works but the Pi shows offline.** On the Pi, try `curl http://bedroom-air.local/api/readings`. If the IP works but the name does not, check Avahi or reserve the ESP32’s DHCP address and change the history service’s `-sensor` flag to `http://YOUR_SENSOR_IP/api/readings`.
- **Phone can’t reach the dashboard.** Try the Pi’s IP from `hostname -I` with port 8080. Check that phone, Pi and ESP32 are on the same LAN and guest-network isolation is off.
- **Home can’t discover the accessory.** Check `systemctl status bedroom-home.service` and the history service’s `/api/live`. Discovery uses mDNS and the accessory listens on TCP 51826.
- **Check service logs.** Run `journalctl -u bedroom-air -u bedroom-home -n 50 --no-pager`. A disconnected Pi can recover up to 24 hours from an ESP32 that stayed powered. A sensor power loss clears its unsaved RAM samples.
