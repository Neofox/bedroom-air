# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial==3.5"]
# ///
"""Configure a Bedroom Air monitor through its USB serial port."""
import argparse
import hashlib
import time
from getpass import getpass

import serial


def wait_for(port, prefix, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        line = port.readline().decode("utf-8", errors="replace").strip()
        if line.startswith(prefix):
            return line
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", help="USB serial device from pio device list")
    args = parser.parse_args()
    ssid = input("2.4 GHz Wi-Fi name: ").encode("utf-8")
    key = getpass("Wi-Fi password (blank for an open network): ").encode("utf-8")
    if not 1 <= len(ssid) <= 32 or len(key) > 64:
        parser.error("SSID must be 1–32 bytes and the password at most 64 bytes.")
    ota = getpass("Choose an OTA password, or leave blank to skip: ")
    if ota and ota != getpass("Repeat OTA password: "):
        parser.error("The two OTA passwords differ.")

    port = serial.Serial(baudrate=115200, timeout=0.7, write_timeout=4)
    port.port = args.port
    port.dtr = port.rts = False
    with port:
        time.sleep(3)
        port.reset_input_buffer()
        if ota:
            digest = hashlib.sha256(ota.encode("utf-8")).hexdigest()
            port.write(f"OTAKEY {digest}\n".encode("ascii"))
            if not wait_for(port, "OTA key saved", 8):
                raise SystemExit("No OTA acknowledgement. Check the port and flash the main sketch.")
        port.write(f"JOIN {len(ssid)} {len(key)}\n".encode("ascii") + ssid + key)
        if not wait_for(port, "Wi-Fi settings received", 8):
            raise SystemExit("No Wi-Fi acknowledgement. Check the port and close other serial monitors.")
        for _ in range(10):
            port.write(b"URL\n")
            url = wait_for(port, "Dashboard http://", 3)
            if url:
                print(url)
                return
        raise SystemExit("Settings saved. Check the 2.4 GHz network and retry if the board stays offline.")


if __name__ == "__main__":
    main()
