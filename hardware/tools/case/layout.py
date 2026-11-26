from PIL import Image,ImageDraw,ImageFont,ImageFilter
from pathlib import Path
W,H=1580,929
canvas=Image.new('RGB',(W,H),(246,246,241))
d=ImageDraw.Draw(canvas)
fontpath='/System/Library/Fonts/HelveticaNeue.ttc'
def f(n, i=0):
    if Path(fontpath).exists():
        return ImageFont.truetype(fontpath, n, index=i)
    return ImageFont.truetype("DejaVuSans-Bold.ttf" if i else "DejaVuSans.ttf", n)
def label(x,y,s,n,i=0,fill='#26342f'): d.text((x,y),s,font=f(n,i),fill=fill)
label(48,33,'Sloped sensor enclosure',50,1)
label(50,103,'Bedroom air monitor  /  Enclosure revision C',24,0, '#50635b')
d.text((W-48,45),'100 × 140 mm',font=f(33,0),fill='#253930',anchor='rt')
d.text((W-49,93),'33 mm at USB  /  23 mm at the low edge',font=f(20,0),fill='#536459',anchor='rt')
d.line((48,150,W-48,150),fill='#b8c1b6',width=1)
here = Path(__file__).resolve().parent / 'rendered'
for x,name,crop in ((48,'closed',(0,26,760,701)),(802,'open',(0,12,760,687))):
    im=Image.open(here/(name+'.png')).convert('RGB').crop(crop)
    im=im.filter(ImageFilter.GaussianBlur(.52)).resize((730,648),Image.Resampling.LANCZOS)
    mask=Image.new('L',im.size); ImageDraw.Draw(mask).rounded_rectangle((0,0,729,647),radius=7,fill=255)
    canvas.paste(im,(x,169),mask)
label(48,831,'Closed enclosure',30,1)
label(802,831,'Sensor layout',30,1)
label(48,877,'The lid slopes down to the light sensor.',21,0,'#536459')
label(802,877,'The blue light module plugs straight into the carrier.',21,0,'#536459')
canvas.save(Path(__file__).resolve().parents[2] / 'Case' / 'Case-preview.jpg',quality=92,subsampling=0,optimize=True)
