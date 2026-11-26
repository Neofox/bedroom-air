from itertools import product
from math import isclose
from pathlib import Path
import pdfplumber
from pypdf import PdfReader

path = Path(__file__).resolve().parents[1] / "Board-fit-check.pdf"
mm = 72 / 25.4
near = lambda a, b: isclose(a,b,abs_tol=0.001)
page = pdfplumber.open(path).pages[0]
assert near(page.width/mm, 210) and near(page.height/mm, 297)
assert str(PdfReader(path).trailer["/Root"]["/ViewerPreferences"]["/PrintScaling"]) == "/None"
outline, squares = page.rects[0], page.rects[1:-1]
assert near(outline["width"]/mm,92) and near(outline["height"]/mm,70)
centers = [((o["x0"] + o["width"]/2 - outline["x0"])/mm, (o["top"] + o["height"]/2 - outline["top"])/mm) for o in page.curves + squares if o["width"]/mm>1.5]
expected = list(product([4,88],[4,66]))
expected += [(8+i*2.54,y) for i in range(15) for y in [12,34.86,37.40]]
expected += [(65,9+i*2.54) for i in range(5)]
expected += [(x,55) for x in [9,14,19,24,37,42,62,67,72]]
assert sum(near(o["width"]/mm,1.0) for o in page.curves)==50
assert sum(near(o["width"]/mm,1.4) for o in page.curves)==9
assert len(centers) == len(expected) == 63
for x,y in expected:
    assert sum(near(x,a) and near(y,b) for a,b in centers) == 1, (x,y)
assert any(near(l["width"]/mm,50) and near(l["height"],0) for l in page.lines)
assert any(near(l["height"]/mm,50) and near(l["width"],0) for l in page.lines)
print("A4 actual size, 92 x 70 mm outline, all 63 feature centers within 0.001 mm and two perpendicular 50 mm scale bars.")
