from pathlib import Path
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

root = Path(__file__).resolve().parents[1]
output = root / "Board-fit-check.pdf"
from reportlab.pdfbase.pdfmetrics import Font
for alias, face in [('Text', 'Helvetica'), ('Bold', 'Helvetica-Bold'), ('Mono', 'Courier')]:
    pdfmetrics.registerFont(Font(alias, face, 'WinAnsiEncoding'))
c = canvas.Canvas(str(output), pagesize=A4, pageCompression=1)
c.setTitle("Bedroom air monitor | PCB fit check")
c.setAuthor("Bedroom air monitor")
c.setViewerPreference("PrintScaling", "None")
ink = "#1B2929"
secondary = "#435557"
accent = "#17675C"
light = "#B2C0BC"
frame = "#687976"
width, height = A4


def point(x, y):
    return x * mm, height - y * mm


def text(x, y, s, size=9, font="Text", color=ink, align="left"):
    c.setFillColor(HexColor(color))
    c.setFont(font, size)
    draw = {"left": c.drawString, "center": c.drawCentredString, "right": c.drawRightString}[align]
    draw(*point(x, y), s)


def line(x1, y1, x2, y2, color=ink, thick=0.22, dash=None):
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(thick * mm)
    c.setDash([v * mm for v in dash] if dash else [])
    c.line(*point(x1, y1), *point(x2, y2))
    c.setDash([])


def rectangle(x, y, w, h, color=ink, thick=0.2, fill=None, dash=None):
    c.setLineWidth(thick * mm)
    c.setStrokeColor(HexColor(color))
    if fill:
        c.setFillColor(HexColor(fill))
    c.setDash([v * mm for v in dash] if dash else [])
    c.rect(*point(x, y+h), w * mm, h * mm, stroke=1, fill=int(bool(fill)))
    c.setDash([])


def circle(x, y, r, color=ink, thick=0.18, fill=None):
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(thick * mm)
    if fill:
        c.setFillColor(HexColor(fill))
    c.circle(*point(x, y), r*mm, stroke=1, fill=int(bool(fill)))


def lines(x,y,entries,lead=4.8,size=9.2,color=secondary):
    for i, entry in enumerate(entries):
        text(x,y+i*lead,entry,size,color=color)


text(18, 17, "BEDROOM AIR MONITOR", 8.5, "Bold", accent)
text(192, 17, "HARDWARE  /  COMPONENT SIDE", 8, "Mono", secondary, "right")
line(18, 21, 192, 21, accent, .45)
text(18, 35, "PCB fit check", 31, "Bold")
text(18, 44, "Print at Actual Size (100%). Measure both scale bars before placing parts on the paper.", 10.3)

bx, by = 25, 62
text(bx, 57, "CARRIER OUTLINE   92 × 70 mm", 8.0, "Bold", secondary)
rectangle(bx, by, 92, 70, ink, .26)


def bt(x, y, s, size=6.5, font="Text", color=secondary, align="left"):
    text(bx+x, by+y, s, size, font, color, align)


def pin(x, y, r=.86, drill=1.0, square=False):
    X,Y=bx+x,by+y
    if square:
        rectangle(X-r, Y-r, 2*r, 2*r, ink, .18)
    else:
        circle(X, Y, r)
    circle(X, Y, drill / 2, color=frame, thick=.10)
    line(X-.18,Y,X+.18,Y,ink,.10)
    line(X,Y-.18,X,Y+.18,ink,.10)


for x in (4,88):
    for y in (4,66):
        circle(bx+x,by+y,1.6)
        line(bx+x-.6,by+y,bx+x+.6,by+y,frame,.12)
        line(bx+x,by+y-.6,bx+x,by+y+.6,frame,.12)

for i in range(15):
    for y in (12,34.86,37.40):
        pin(8+2.54*i,y,square=i==0)
bt(8,9,"VIN",6.4,"Bold",align="center")
bt(43.56,9,"EN",6.4,"Bold",align="center")
bt(26,21.7,"ESP32",8.6,"Bold",ink,"center")
bt(26,25.8,"15 pins per side",6.7,align="center")
line(bx+4.7,by+23.0,bx+.1,by+23.0,ink,.32)
line(bx+.1,by+23.0,bx+1.6,by+21.9,ink,.32)
line(bx+.1,by+23.0,bx+1.6,by+24.1,ink,.32)
bt(0.8,20.8,"USB",6.5,"Bold",ink)
bt(8,41.2,"3V3",6.4,"Bold",align="center")
bt(43.56,41.2,"D23",6.4,"Bold",align="center")
bt(46.2,35.4,"A",6.5,"Bold",ink)
bt(46.2,38.1,"B",6.5,"Bold",ink)

for i in range(5):
    pin(65,9+2.54*i,.875,square=i==0)
bt(68,9.8,"ADDR",6.4,"Bold")
bt(68,19.9,"VCC",6.4,"Bold")
bt(75,14.7,"GY-302",7.1,"Bold",ink)

for start, labels, name in [(9,["5V","GND","TX","RX"],"CO2"),(37,["+5V","GND"],"5V INPUT"),(62,["GND","DATA","3V3"],"DHT22")]:
    center=start+(len(labels)-1)*2.5
    bt(center,50.6,name,7.3,"Bold",ink,"center")
    for i,label in enumerate(labels):
        x=start+5*i
        pin(x,55,1.45,drill=1.4,square=i==0)
        bt(x,60.9 if label=="DATA" else 59.5,label,5.4,"Bold",secondary,"center")

# Orthogonal scale bars catch independent X/Y print scaling.
ybar=140
line(bx,ybar,bx+50,ybar,ink,.28)
for i in range(6):
    xx=bx+10*i
    line(xx,ybar-1.35,xx,ybar+1.35,ink,.28)
text(bx+25,ybar+5.2,"50 mm across end marks",7.5,"Text",secondary,"center")
xbar=18
line(xbar,by+10,xbar,by+60,ink,.26)
for i in range(6):
    yy=by+10+10*i
    line(xbar-1.3,yy,xbar+1.3,yy,ink,.26)
c.saveState()
c.translate(*point(xbar-3.0,by+35))
c.rotate(90)
c.setFont("Text",7.5)
c.setFillColor(HexColor(secondary))
c.drawCentredString(0,0,"50 mm across end marks")
c.restoreState()

text(125,64,"Align the ESP32",12.4,"Bold")
lines(125,71,["Hold the unpowered board pins down,", "USB-C left. Match VIN and EN first.", "All 15 pins must line up on each side."])
text(125,92,"A",9.4,"Bold",accent)
text(132,92,"22.86 mm between row centers",9.1)
text(125,98,"B",9.4,"Bold",accent)
text(132,98,"25.40 mm between row centers",9.1)
lines(125,108,["Fit one lower socket row. Leave the", "other empty. The pin pitch is 2.54 mm", "and the end-to-end span is 35.56 mm."])
lines(125,128,["Check the USB plug against the case", "opening and all four mounting holes", "against the case posts."],lead=4.6)

line(18,153,192,153,light)
text(18,164,"Match the sensor leads",16.5,"Bold")
text(18,171,"Read the carrier terminals from left to right with the USB connector on the left.",9.5,color=secondary)

# Tabular map is deliberately separate from the full-size drawing.
rect_y=178
rectangle(18,rect_y,174,7,"#E8F1EE",.1,"#E8F1EE")
for x,label in [(21,"CARRIER"),(56,"TERMINAL ORDER"),(128,"CONNECT TO")]:
    text(x,182.8,label,7.2,"Bold",accent)
rows=[("CO2","5V   /   GND   /   sensor TX   /   sensor RX","MH-Z19C pins 4, 3, 6, 5"),("5V input","+5V   /   GND","Regulated 5 V DC supply"),("DHT22","GND   /   DATA   /   3V3","Breakout markings  –  /  OUT  /  +")]
for i,(name,order,target) in enumerate(rows):
    yy=192+9*i
    text(21,yy,name,9.2,"Bold")
    text(56,yy,order,9.0)
    text(128,yy,target,8.9)
    line(18,yy+3.5,192,yy+3.5,light,.13)

text(18,224,"Optional GY-302",11.2,"Bold")
lines(18,230,["Place the chip towards the lid, with the module body extending right. From the top edge down,", "the five pins are ADDR, SDA, SCL, GND, VCC. Align the actual breakout before soldering."],size=9.2)
text(18,248,"Before ordering",11.2,"Bold")
lines(18,254,["Match the terminal pins to the 5.00 mm pitch and 1.40 mm drill. Lay the real ESP32 and GY-302", "over the pin centers. If a scale bar, pin, terminal or mounting hole misses, hold the order and", "resolve the mismatch first."],size=9.2)
line(18,277,192,277,accent,.4)
text(18,283,"Exact geometry covers the board outline and marked pin and hole centers.",8.2,color=secondary)
text(192,283,"A4   /   1:1",8.2,"Mono",accent,"right")
c.showPage()
c.save()
