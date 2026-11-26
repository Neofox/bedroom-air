# Edit and check the hardware

For a first build, use the supplied [Gerbers](../Bedroom-Air-RevA-fabrication.zip), [fit sheet](../Board-fit-check.pdf) and [STL files](../Case/). The KiCad project and parametric enclosure model are the editable sources. The optional scripts here regenerate or check the published designs. Run generation in a working copy since it rewrites design files.

## Carrier A

Open [Bedroom-Air.kicad_pro](../PCB/Bedroom-Air.kicad_pro) in KiCad. Both the symbol and footprint library tables use project-relative paths. KiCad 10.0.8 was used for the included electrical and layout reports.

To reproduce the carrier from the original layout generator, run these commands from the repository root with Python and `kicad-cli` on your PATH:

```sh
python3 hardware/tools/carrier/design.py
kicad-cli sch export netlist --format kicadxml -o hardware/tools/carrier/net.xml hardware/PCB/Bedroom-Air.kicad_sch
python3 hardware/tools/carrier/board.py
kicad-cli sch erc --exit-code-violations -o erc.rpt hardware/PCB/Bedroom-Air.kicad_sch
kicad-cli pcb drc --schematic-parity --exit-code-violations -o drc.rpt hardware/PCB/Bedroom-Air.kicad_pcb
```

The stored `routes.json` contains the Rev A traces. For a layout revision you can edit the PCB in KiCad, or regenerate the routes with `uv run --with numpy --with pillow --with "shapely>=2" hardware/tools/carrier/route.py` before running `board.py`. Re-export the Gerbers and drills after any PCB change. Check terminal-to-sensor connectivity against the [terminal map](../Assembly.md#terminal-map).

## Enclosure C and fit sheet

The four printable meshes come from one model. The geometry check also tests clearances for the light sensor’s field of view. To regenerate and check them:

```sh
uv run hardware/Case/enclosure.py
uv run --with manifold3d==3.5.5 --with trimesh==5.2.2 --with "numpy>=2,<3" hardware/tools/case/check.py
uv run --with reportlab hardware/tools/fit-sheet.py
uv run --with pdfplumber --with pypdf hardware/tools/fit-verify.py
```

Optional rendering tools in `case/` produce the open and closed views with Mitsuba 3, trimesh, manifold3d and NumPy. Run `render.py open` and `render.py closed`, then `layout.py` with Pillow to compose the case preview. On Linux, the composition script uses the DejaVu Sans fonts.
