# Bedroom Air · Carrier Rev A

This carrier lets you move the programmed ESP32, MH-Z19C and DHT22 off the breadboard. The GY-302 adds light readings. **Order the bare PCB and hand-solder the through-hole parts.** The sockets let you lift out the programmed ESP32 and light sensor. The screw terminals secure the sensor harnesses.

## Before ordering

1. Print the A4 fit sheet at **Actual Size / 100%**. Measure the horizontal and vertical 50 mm bars with a ruler. [Board fit sheet](Board-fit-check.pdf)
2. Place the unpowered ESP32 pins down, USB-C to the left. Match VIN and EN on the fixed row, then check that all 15 pins on the opposite row line up. The two possible center spacings are **22.86 mm** and **25.40 mm**. Mark the row that matches your board on the paper template. Fit exactly two 1×15 sockets in total. The third row stays empty.
3. Check the five GY-302 pads against the template with the chip upwards and the body extending right. Measure the fitted USB plug and socket stack, DHT22 breakout and cable, and the CO₂ module with its plug inserted. Check the board mounting holes, connector clearance, sensor supports and lid height against the enclosure. Resolve any mismatch before ordering a board or case. [Case parts and fit instructions](Case/Assembly.md)
4. Request a **92 × 70 mm, two-layer FR-4 board, 1.6 mm thick, with 1 oz copper**, solder mask on both sides and front silkscreen. Upload the [Rev A fabrication ZIP](Bedroom-Air-RevA-fabrication.zip), which contains the Gerber layers and separate plated and non-plated drill files. Check that the fabrication preview includes four Ø3.2 mm non-plated mounting holes on an 84 × 62 mm pattern. Select bare PCB fabrication and source the through-hole parts below. [PCB files](PCB/) · [Schematic](PCB/Bedroom-Air-schematic.pdf)

## Bill of materials for one monitor

Keep your **30-pin USB-C ESP32 with its existing firmware**, terminal-type MH-Z19C with its seven-position factory harness, three-pin DHT22 breakout and, optionally, the GY-302 V3.22. The breadboard and expansion board can stay out of the enclosure.

| Reference | Qty | Part to fit |
| --- | --- | --- |
| Carrier | 1 | Rev A PCB with the fabrication options above. |
| U1 | 2 | Straight, single-row 1×15 female sockets, 2.54 mm pitch, for standard 0.64 mm square header pins. Use identical heights. |
| J4, J5, J7 | 1 each | Four-, three- and two-position through-hole screw terminals, respectively. Single pin row, **5.00 mm pitch**, Ø1.40 mm PCB drills. The 2-, 3- and 4-position KF301 blocks from your kit can be reused if they match this pitch and drill. Choose compatible side-entry bodies, approximately 8.5 mm deep, with screw access from above. Face the wire openings toward the nearest long edge of the board. |
| JP1 | 1 set | Straight 1×2 male header, 2.54 mm pitch, and a removable shorting cap. Keep the cap off during initial checks. |
| C1 | 1 | 100 µF radial electrolytic, 10 V or higher, ≤6.3 mm body diameter, ≤12.5 mm body height, 2.5 mm lead spacing. Fit positive lead in the marked `+` pad, negative stripe toward GND. |
| C2 | 1 | 100 nF ceramic, 10 V or higher, 2.5 mm lead spacing. Either orientation. |
| R1 | 0 or 1 | 10 kΩ axial resistor, ¼ W, 7.62 mm formed lead spacing. Fit only if the DHT breakout lacks a pull-up from OUT to `+`. Check the disconnected breakout with an ohmmeter. |
| J6 and GY-302 | 1 pair, optional | Straight 1×5 female socket on the carrier and matching standard male header on the sensor, 2.54 mm pitch. The case is modeled for an 8.5 mm socket and a 2.54 mm male-header body. [Installation and fit](Case/Assembly.md#fit-the-light-sensor) |
| Power and leads | 1 set | Regulated 5.0 V DC adapter rated **at least 1 A** for the complete monitor, a matching two-wire pigtail for J7 and short sensor leads with screw-terminal-compatible ends. A factory-made USB-A to two-wire 5 V power pigtail is one option when your adapter has a USB-A output. Label the existing leads before removing them from the breadboard. Use the case guide for the gland and fasteners. |

## Hand-solder the carrier

1. Fit C2, JP1 and R1 (if needed). Set the two ESP32 sockets into the rows you marked. Tack one end pin on each socket, check that both sit flat and parallel, and test-fit the unpowered ESP32. Lift it out before soldering the remaining pins.
2. Fit the light-sensor socket J6, the three screw terminals with their wire entries facing the near long edge, and C1 with its positive lead in the marked pad. Keep the JP1 shorting cap off. Check for bridges and trim projecting leads before mounting the PCB.
3. On the blue GY-302, solder the straight male header with its plastic body flush to the underside of the board. Seat the module in J6, chip up, and check the fit under the sloped lid. [Light sensor instructions](Case/Assembly.md#fit-the-light-sensor)
4. Inspect the joints and run the empty-carrier continuity check below before installing the modules. You’ll need a multimeter and a small screwdriver for the terminals.

If you keep the original three-pin DHT plug, secure its harness to the case with a cable tie and leave a short slack loop at the plug. For a fixed connection, solder those three wires to the breakout pads after verifying **−, OUT, +**. Retain the factory CO₂ plug and give the lead slack. Never solder to or clamp the gold CO₂ chamber. Keep both air openings clear and plug the light sensor into J6 with its chip facing the flared opening in the sloped lid. [Enclosure](Case/Assembly.md)

## Terminal map

View the component side with ESP32 USB-C on the left. J4, J7 and J5 count from **left to right**. J6 counts **top to bottom**. Identify each harness lead by continuity to its numbered contact with both ends unplugged. The factory connector drawing is viewed from the sensor face; a loose plug viewed from the wire side can appear reversed. [Winsen MH-Z19C manual, terminal version, Fig. 4](https://www.winsen-sensor.com/d/files/manual/mh-z19c.pdf)

| Connector | Pins in physical order | Destination |
| --- | --- | --- |
| J4 · CO₂ | 1 `5V_SYS`, 2 `GND`, 3 `CO2_TX`, 4 `CO2_RX` | Sensor pins **4 VIN, 3 GND, 6 TXD, 5 RXD**. Sensor TXD goes to ESP32 GPIO16 / RX2. Sensor RXD goes to GPIO17 / TX2. Insulate unused sensor leads **1 HD, 2 reserved and 7 PWM** individually. |
| J7 · power | 1 `5V_SYS`, 2 `GND` | Regulated +5 V and return. Confirm polarity on the supply pigtail with a meter before connecting it. |
| J5 · DHT22 | 1 `GND`, 2 `DHT_DATA`, 3 `3V3` | Actual three-pin breakout **−, OUT, +**. OUT goes to GPIO18. A bare four-pin DHT22 has a different pinout. |
| J6 · optional light | 1 `GND` (ADDR), 2 `I2C_SDA`, 3 `I2C_SCL`, 4 `GND`, 5 `3V3` | GY-302 **ADDR, SDA, SCL, GND, VCC**. SDA goes to GPIO21, SCL to GPIO22. ADDR grounded selects address `0x23`. |
| JP1 · RUN | 1 `5V_SYS`, 2 `VIN_ESP` | The shunt joins the sensor 5 V rail to ESP32 VIN. Grounds remain common when the shunt is open. |

## First power and normal operation

Change wiring and move JP1 with both supplies disconnected. The shunt directly joins two power rails. **When J7 and ESP32 USB are powered together, JP1 must be open.**

1. **Check the empty carrier.** Remove JP1, the ESP32 and sensor modules. Disconnect USB and J7. Inspect the solder joints and C1 polarity. With a meter, confirm ground continuity at J4, J5 and J7, no persistent short from `5V_SYS` to GND, and an open circuit between the two JP1 pins.
2. **Test the sensor supply alone.** Keep USB disconnected and JP1 open. Power J7 from the regulated adapter. Measure J4 pin 1 against pin 2 and confirm **4.9–5.1 V** with the expected polarity. Turn J7 off. This check covers the empty carrier. Repeat at the sensor under load in step 4.
3. **Test the ESP32 over USB.** Leave J7 disconnected, JP1 open and the CO₂ harness unplugged. Fit the ESP32 in its two sockets. Power it by USB and verify about 3.3 V across J5 pins 3 and 1. Disconnect USB before fitting the DHT22 and optional GY-302. This is also the simplest USB service mode. The existing ESP32 firmware and saved Wi-Fi configuration can stay in place.
4. **Run from one supply.** With USB physically unplugged and J7 off, attach the mapped CO₂ harness, DHT22 and optional GY-302. Close JP1 and power J7. The adapter now feeds both the MH-Z19C and ESP32 VIN. **Measure at the MH-Z19C end of the harness, between pin 4 and pin 3, with the complete monitor running.** Target 4.9–5.1 V throughout sampling. Winsen lists 125 mA peak for the sensor alone. Use min/max capture if available. A low reading calls for checking the adapter, cable and terminal connections. [Winsen specifications](https://www.winsentech.com/NDIR_CO2_Sensor_MH-Z19C.html)
5. **Confirm the readings before closing the case.** On the same Wi-Fi network, open the dashboard. Allow at least one minute for the CO₂ warm-up. Check CO₂, temperature and humidity, then cover and uncover the GY-302 and watch lux change. Readings refresh roughly every three seconds. If the light module is omitted, lux remains unavailable. [Bedroom Air dashboard](http://bedroom-air.local/) · [Live readings](http://bedroom-air.local/api/readings)

For USB diagnostics with the *complete* monitor, disconnect power, remove JP1, and use USB for the ESP32 and J7 for the CO₂ rail. Power both sides while the UART is connected. Disconnect the CO₂ harness if either side will stay off. For daily use, return to the single J7 supply in step 4. A USB-fed DevKit VIN can fall below the MH-Z19C working voltage.

With the lid fastened and the monitor in its usual spot, check Wi-Fi reception and compare the stabilized temperature with the open-case reading. The Raspberry Pi can keep logging in its existing location.

The pin map was checked against the existing Bedroom Air firmware. Physical fit, loaded supply voltage and live operation of the new carrier still require the hardware checks above.
