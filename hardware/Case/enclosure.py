# /// script
# requires-python = ">=3.11"
# dependencies = ["manifold3d==3.5.5", "trimesh==5.2.2", "numpy>=2.0,<3"]
# ///
"""Editable bedroom sensor enclosure, in millimetres. Run: uv run enclosure.py

Working coordinates follow the component-side PCB drawing (+Y down). Export
reflects this drawing into a physical right-handed, component-side-up part.
The lid and keeper STLs are transformed into their recommended print poses.
The optional fit gauge duplicates the CO2 seat on a low-cost test coupon.
"""
from pathlib import Path
import math
import sys

import manifold3d as md
import numpy as np
import trimesh

M = md.Manifold
C = md.CrossSection

# Carrier board and enclosure. The height of every boss is measured from bed Z=0.
X0, X1 = -3.0, 97.0
Y0, Y1 = -10.0, 130.0
RADIUS, WALL, FLOOR = 5.2, 2.2, 2.2
RIM, CAP = 30.6, 2.4
PCB_SEAT, PCB_T = 7.4, 1.6
PCB_HOLES = [(4,4), (88,4), (4,66), (88,66)]
LID_HOLES = [(4,-5), (90,-5), (2,124.7), (91.8,124.7)]
M3_PILOT, M25_PILOT = 2.60, 2.13
GLAND_X, GLAND_Z, GLAND_D = 52.0, 13.5, 12.5
USB_Y0, USB_Y1, USB_Z0, USB_Z1 = 7.8, 41.8, 6.8, 27.0
DHT_X, DHT_Y, DHT_SEAT = 77.0, 123.3, 8.4

# The planar roof descends from the USB side toward the J6 light module.
ROOF_DROP = 10.0
ROOF_SLOPE = ROOF_DROP / (X1-X0)
LIGHT_CHIP_XY = (75.0,14.08)
LIGHT_SEAT = PCB_SEAT + PCB_T + 8.5 + 2.54  # carrier socket + male header body


def rise_at(x):
    return -ROOF_SLOPE * (x-X0)


def on_roof(part):
    return part.transform([[1,0,0,0],[0,1,0,0],[-ROOF_SLOPE,0,1,ROOF_SLOPE*X0]])


# Winsen terminal-type module in local coordinates. U runs from the bare PCB
# tongue to the factory plug. V=0 is the centreline. The gold body is wider
# than the PCB tongue. Supports touch the two exposed end regions only.
CO2_X, CO2_Y = 23.0, 124.0
CO2_SEAT, EDGE_GAP, KEEPER_T = 6.4, 2.0, 2.4
TIP_PAD = (0.25, 1.95)
NECK_PAD = (30.85, 32.10)
FRAME_V = 13.35
FRAME_U = (1.1, 31.50)
KEEPER_SCREWS = [(FRAME_U[0], -FRAME_V), (FRAME_U[1], FRAME_V)]


def union(parts):
    return M.batch_boolean(parts, md.OpType.Add)


def cut(part, tools):
    return M.batch_boolean([part, *tools], md.OpType.Subtract)


def box(x0, y0, z0, x1, y1, z1):
    return M.cube((x1-x0, y1-y0, z1-z0)).translate((x0, y0, z0))


def tube(x, y, z0, z1, diameter):
    return M.cylinder(z1-z0, diameter/2, circular_segments=48).translate((x,y,z0))


def rounded(x0, y0, x1, y1, radius):
    # Offset an inner rectangle outward by the corner radius.
    return C.square((x1-x0-2*radius, y1-y0-2*radius)).offset(
        radius, circular_segments=48).translate((x0+radius, y0+radius))


def obround(x0, y0, x1, y1, radius, z0, z1):
    return rounded(x0,y0,x1,y1,radius).extrude(z1-z0).translate((0,0,z0))


def co2(part):
    return part.rotate((0,0,-90)).translate((CO2_X,CO2_Y,0))


def saddle(x,y):
    # Tie passes across the cable, through the X-direction tunnel below.
    block = box(x-3.15,y-3.35,FLOOR-.1,x+3.15,y+3.35,6.55)
    tunnel = box(x-4,y-1.65,FLOOR-.01,x+4,y+1.65,4.65)
    return block - tunnel


def co2_mounts():
    tops = CO2_SEAT + EDGE_GAP
    features = []
    for u0,u1 in (TIP_PAD, NECK_PAD):
        features.append(box(u0,-5.2,FLOOR-.1,u1,5.2,CO2_SEAT))
    # Left end of the PCB and the two side edges locate the tip.
    features.append(box(-1.75,-6.8,FLOOR-.1,-0.40,6.8,tops))
    for v0,v1 in ((-8.4,-7.0), (7.0,8.4)):
        features.append(box(-.65,v0,FLOOR-.1,1.9,v1,tops))
        features.append(box(30.85,v0,FLOOR-.1,32.0,v1,tops))
    # The connector tongue narrows from 13.3 to ~10 mm. Stops abut that step;
    # the open middle clears both the projecting connector and the cable.
    for v0,v1 in ((-7.15,-5.78), (5.78,7.15)):
        features.append(box(33.10,v0,FLOOR-.1,35.60,v1,tops))
    for u in FRAME_U:
        for v in (-FRAME_V,FRAME_V):
            features.append(tube(u,v,FLOOR-.1,tops,6.1))
    bores = [tube(u,v,tops-4.6,tops+1,M25_PILOT) for u,v in KEEPER_SCREWS]
    return co2(cut(union(features),bores))


def co2_keeper():
    # Each narrow crossbar is above bare FR-4. The two long rails lie outside
    # the gold shell, exposing the whole diffusion window. Positive hardware
    # stops set the vertical gap independently of screw torque.
    z = CO2_SEAT + EDGE_GAP
    top = z+KEEPER_T
    rails = [box(FRAME_U[0],v-1.2,z,FRAME_U[1],v+1.2,top)
             for v in (-FRAME_V,FRAME_V)]
    for u0,u1 in (TIP_PAD,NECK_PAD):
        rails.append(box(u0,-FRAME_V,z,u1,FRAME_V,top))
    for u in FRAME_U:
        for v in (-FRAME_V,FRAME_V):
            rails.append(tube(u,v,z,top,6.1))
    holes = [tube(u,v,z-1,top+1,2.9) for u,v in KEEPER_SCREWS]
    return co2(cut(union(rails),holes))


def front_profile():
    return rounded(X0,Y0,X1,Y1,RADIUS)


def base():
    outside = front_profile()
    inside = rounded(X0+WALL,Y0+WALL,X1-WALL,Y1-WALL,RADIUS-WALL)
    features = [outside.extrude(RIM) - inside.extrude(RIM).translate((0,0,FLOOR))]
    voids = [box(X0-1,USB_Y0,USB_Z0,1.0,USB_Y1,RIM+1)]
    for x,y in LID_HOLES:
        features.append(tube(x,y,FLOOR-.1,RIM,7.6))
        voids.append(tube(x,y,RIM+rise_at(x)-7.4,RIM+1,M3_PILOT))
    for x,y in PCB_HOLES:
        features.append(tube(x,y,FLOOR-.1,PCB_SEAT,6.9))
        voids.append(tube(x,y,PCB_SEAT-5.5,PCB_SEAT+1,M3_PILOT))
    roof_limit = on_roof(box(X0-5,Y0-5,-50,X1+5,Y1+5,RIM))
    partitions = union([
        box(-1.3,74.0,FLOOR-.1,95.4,75.6,RIM-.4),
        box(39.8,75.5,FLOOR-.1,41.4,128.2,RIM-.4),
        box(62.6,75.5,FLOOR-.1,64.2,128.2,RIM-.4),
    ])
    features.extend([
        partitions ^ roof_limit.translate((0,0,-.4)),
        co2_mounts(), tube(DHT_X,DHT_Y,FLOOR-.1,DHT_SEAT,6.4),
        saddle(23.0,79.7), saddle(87.5,82.2), saddle(GLAND_X,87.0),
    ])
    voids.append(tube(DHT_X,DHT_Y,1.5,DHT_SEAT+1,M25_PILOT))
    # Optional lashing around the unvented breakout neck for clone boards.
    # End slots also allow the tie to work if the white tab hole is obstructed.
    for x in (DHT_X-7.2,DHT_X+5.8):
        features.append(box(x,85.2,FLOOR-.1,x+1.4,97.8,6.3))
    for y in (88.0,94.5):
        for x in (64.9,89.0):
            voids.append(box(x,y-1.8,-1,x+2.0,y+1.8,FLOOR+.2))
        voids.append(box(64.9,y-1.8,-1,91.0,y+1.8,.95))
    # Separate wire passages leave the full-height sensor partitions intact.
    for x0,x1,lo,hi in ((16,30,5.0,14.8),(38.5,55.5,5.0,15.5),(70,86,5.0,18.0)):
        voids.append(box(x0,73.5,lo,x1,76.0,hi))
    # Inlet slot spans only 2.9 mm along Y, so its roof bridges easily.
    for y in range(84,121,6):
        for x0,x1 in ((X0-1,X0+WALL+1),(X1-WALL-1,X1+1)):
            voids.append(box(x0,y,4.8,x1,y+2.9,17.8 if x0>0 else 20.8))
    for y in (44,50,56,62):
        voids.append(box(X0-1,y,5.5,X0+WALL+1,y+2.9,17.8))
    # Through-hole for the separate nylon M12 gland and its hex locknut.
    gland = M.cylinder(5,GLAND_D/2,circular_segments=72).rotate((90,0,0))
    voids.append(gland.translate((GLAND_X,Y1+1,GLAND_Z)))
    return cut(union(features),voids) ^ roof_limit


def light_window():
    # Join two parallel rounded openings to make the lip slope outwards.
    x,y = LIGHT_CHIP_XY
    def profile(half_x,half_y,z):
        return obround(x-half_x,y-half_y,x+half_x,y+half_y,1.7,z,z+.01)
    lower = profile(9.0,7.0,RIM)
    upper = profile(11.5,9.5,RIM+CAP)
    return union([lower,upper]).hull() + profile(9.0,7.0,RIM-.005)


def lid():
    features = [front_profile().extrude(CAP).translate((0,0,RIM))]
    voids = [tube(x,y,RIM-1,RIM+CAP+1,3.45) for x,y in LID_HOLES]
    # Lid-borne lintel leaves the base USB mouth entirely open for insertion.
    features.append(box(X0,USB_Y0+.35,USB_Z1,X0+WALL,USB_Y1-.35,RIM+.05))
    # Six guide tabs give 0.35 mm side clearance inside the rim.
    features.extend([box(x,y,RIM-2.3,x+dx,y+dy,RIM+.05) for x,y,dx,dy in [
        (20,Y0+WALL+.35,12,1.35),(64,Y0+WALL+.35,12,1.35),
        (X0+WALL+.35,43,1.35,12),(X1-WALL-1.70,44,1.35,12),
        (20,Y1-WALL-1.70,11,1.35),(68,Y1-WALL-1.70,11,1.35)
    ]])
    drill0,drill1 = RIM-1,RIM+CAP+1
    for x in (9,15,21,27,33):
        for ya,yb in ((87.0,98.0),(100.8,112.7),(115.5,124.3)):
            voids.append(obround(x,ya,x+3.3,yb,1.60,drill0,drill1))
    for x in (67,73,79,85,91):
        for ya,yb in ((87.0,98.0),(100.8,112.7),(115.5,121.7)):
            # Shorten the corner slot to clear the screw and supporting boss.
            if (x,ya) != (91,115.5):
                voids.append(obround(x,ya,x+3.0,yb,1.45,drill0,drill1))
    for x in (9,15,21,27,33,39,45):
        voids.append(obround(x,10.0,x+2.9,33.0,1.40,drill0,drill1))
    voids.append(light_window())
    lid_shell = on_roof(cut(union(features),voids))
    # The screw axes are vertical. Recess their heads onto level seats.
    seats = [tube(x,y,RIM+CAP+rise_at(x)-.45,RIM+CAP+2,7.1)
             for x,y in LID_HOLES]
    return cut(lid_shell,seats)


def physical(part):
    return part.mirror((0,1,0)).translate((-X0,Y1,0))


def mesh(part):
    mm = part.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mm.vert_properties)[:,:3],
                           faces=np.asarray(mm.tri_verts),process=True)


def manufacturing_parts():
    # Lay the inclined exterior face flat on the print bed.
    angle = math.degrees(math.atan(ROOF_SLOPE))
    cover = physical(lid()).rotate((180,0,0)).rotate((0,angle,0))
    cx,cy,cz,*_ = cover.bounding_box()
    cover = cover.translate((-cx,-cy,-cz))
    keeper = physical(co2_keeper())
    x0,y0,z0,*_ = keeper.bounding_box()
    # The optional gauge duplicates the production supports and screw pilots;
    # use the production keeper on it before committing to the full base print.
    plate = co2(rounded(-3.1,-17.3,40.5,17.3,2.0).extrude(FLOOR))
    gauge = physical(plate+co2_mounts())
    gx,gy,*_ = gauge.bounding_box()
    return {"01-base.stl":physical(base()),"02-lid.stl":cover,
            "03-co2-keeper.stl":keeper.translate((-x0,-y0,-z0)),
            "04-optional-co2-fit-gauge.stl":gauge.translate((-gx,-gy,0))}


def main():
    directory = Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent
    directory.mkdir(parents=True,exist_ok=True)
    for name,part in manufacturing_parts().items():
        result = mesh(part)
        assert part.status()==md.Error.NoError and len(part.decompose())==1
        assert result.is_volume and result.is_watertight and result.is_winding_consistent
        assert abs(result.bounds[0,2])<1e-4
        target = directory/name
        result.export(target)
        reread = trimesh.load_mesh(target,process=True)
        assert reread.is_volume and reread.is_watertight
        print(f"{name}: {np.round(reread.extents,2)} mm, {len(reread.faces)} triangles")


if __name__ == "__main__":
    main()
