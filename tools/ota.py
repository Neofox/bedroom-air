"""Build the firmware with PlatformIO and send a password-protected wireless update."""
import argparse
from getpass import getpass
import json
from pathlib import Path
import runpy
import socket
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", nargs="?", default="bedroom-air.local")
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1] / "firmware"
    subprocess.run(["pio", "run", "-d", str(project)], check=True)
    info = json.loads(subprocess.check_output(["pio", "system", "info", "--json-output"]))
    core = Path(info["core_dir"]["value"])
    tool = core / "packages/framework-arduinoespressif32/tools/espota.py"
    image = project / ".pio/build/esp32dev/firmware.bin"
    target = socket.gethostbyname(args.host)
    password = getpass("OTA password: ")
    if not password:
        parser.error("Use the OTA password set over USB.")
    upload = runpy.run_path(str(tool))["main"]
    return upload(["-i", target, "-p", "3232", "-a", password, "-f", str(image)])


if __name__ == "__main__":
    raise SystemExit(main())
