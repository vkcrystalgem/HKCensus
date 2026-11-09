"""Render the original HK Census Play artwork, with editable SVG companions.

Requires Pillow. Uses the Windows Segoe UI family; no downloaded assets.
Run from any directory: python store-listing/graphics/render_graphics.py
"""

from __future__ import annotations

import hashlib
import html
import json
import struct
from pathlib import Path

from PIL import Image, ImageCms, ImageDraw, ImageFont


OUT = Path(__file__).resolve().parent
SCALE = 4
CREAM = "#FFF8EE"
PAPER = "#F2ECDF"
INK = "#1D1D1B"
TEAL = "#0F766E"
DEEP_TEAL = "#0B625C"
GOLD = "#A16207"
PALE_GOLD = "#E7BD78"
SERIF_FREE_FONT = Path("C:/Windows/Fonts/seguisb.ttf")
REGULAR_FONT = Path("C:/Windows/Fonts/segoeui.ttf")


class Drawing:
    def __init__(self, width: int, height: int, background: str | None, title: str, rgba=False):
        self.width, self.height = width, height
        self.image = Image.new("RGBA" if rgba or not background else "RGB", (width * SCALE, height * SCALE), background or (0,0,0,0))
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">',
            f'<title id="title">{html.escape(title)}</title>',
        ]
        if background:
            self.svg.append(f'<rect width="{width}" height="{height}" fill="{background}"/>')

    def rectangle(self, box, fill):
        self.draw.rectangle(tuple(v * SCALE for v in box), fill=fill)
        x1, y1, x2, y2 = box
        self.svg.append(f'<rect x="{x1}" y="{y1}" width="{x2-x1}" height="{y2-y1}" fill="{fill}"/>')

    def polygon(self, points, fill):
        self.draw.polygon([(x*SCALE, y*SCALE) for x,y in points], fill=fill)
        self.svg.append(f'<polygon points="{" ".join(f"{x},{y}" for x,y in points)}" fill="{fill}"/>')

    def line(self, points, fill, width, rounded=False):
        scaled = [(int(x*SCALE), int(y*SCALE)) for x,y in points]
        self.draw.line(scaled, fill=fill, width=round(width*SCALE), joint="curve")
        if rounded:
            radius = width * SCALE / 2
            for x,y in scaled:
                self.draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=fill)
        self.svg.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in points)}" fill="none" stroke="{fill}" stroke-width="{width}" stroke-linecap="{"round" if rounded else "butt"}" stroke-linejoin="round"/>')

    def circle(self, x, y, radius, fill):
        self.draw.ellipse(((x-radius)*SCALE, (y-radius)*SCALE, (x+radius)*SCALE, (y+radius)*SCALE), fill=fill)
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}"/>')

    def text(self, x, baseline, content, size, fill, semibold=False):
        font_path = SERIF_FREE_FONT if semibold else REGULAR_FONT
        font = ImageFont.truetype(str(font_path), round(size*SCALE))
        self.draw.text((x*SCALE, baseline*SCALE), content, fill=fill, font=font, anchor="ls")
        self.svg.append(f'<text x="{x}" y="{baseline}" font-family="Segoe UI, sans-serif" font-size="{size}" font-weight="{600 if semibold else 400}" fill="{fill}">{html.escape(content)}</text>')

    def save(self, basename):
        self.svg.append("</svg>")
        (OUT / f"{basename}.svg").write_text("\n".join(self.svg) + "\n", encoding="utf-8")
        image = self.image.resize((self.width, self.height), Image.Resampling.LANCZOS)
        profile = bytearray(ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes())
        # ICC creation dates otherwise vary between identical renders.
        profile[24:36] = struct.pack(">6H", 2026, 1, 1, 0, 0, 0)
        image.save(OUT / f"{basename}.png", optimize=True, icc_profile=bytes(profile))


def skyline(drawing, x, y, scale=1, fill=CREAM, structure=TEAL):
    """An original abstract skyline, not a tracing of a building or emblem."""
    def points(values):
        return [(x+px*scale, y+py*scale) for px,py in values]

    drawing.polygon(points([(0,264),(0,184),(56,184),(56,145),(105,145),(105,92),(148,46),(191,92),(191,264)]), fill)
    drawing.polygon(points([(237,264),(237,39),(264,12),(304,12),(304,264)]), fill)
    drawing.line(points([(284,12),(284,-12)]), fill, 10*scale)
    drawing.line(points([(105,96),(191,181),(105,264)]), structure, 9*scale)
    drawing.line(points([(257,72),(257,233)]), structure, 8*scale)


def icon_mark(d):
    skyline(d, 102, 100)
    d.line([(94,391),(414,391)], CREAM, 14)
    trend = [(95,340),(150,311),(205,325),(260,282),(302,291),(355,232),(405,207)]
    d.line(trend, TEAL, 25, rounded=True)
    d.line(trend, CREAM, 17, rounded=True)
    d.line(trend, GOLD, 10, rounded=True)
    d.circle(405, 207, 22, TEAL)
    d.circle(405, 207, 17, CREAM)
    d.circle(405, 207, 11, PALE_GOLD)


def icon():
    d = Drawing(512, 512, TEAL, "HK Census app icon: abstract Hong Kong skyline and rising data line", rgba=True)
    # Full square; Google Play applies its own launcher icon mask.
    icon_mark(d)
    d.save("app-icon-512")


class TransformedDrawing:
    def __init__(self, target, scale, x, y):
        self.target, self.scale, self.x, self.y = target, scale, x, y

    def points(self, values):
        return [(self.x+x*self.scale,self.y+y*self.scale) for x,y in values]

    def polygon(self, values, fill):
        self.target.polygon(self.points(values),fill)

    def line(self, values, fill, width, rounded=False):
        self.target.line(self.points(values),fill,width*self.scale,rounded)

    def circle(self, x, y, radius, fill):
        self.target.circle(self.x+x*self.scale,self.y+y*self.scale,radius*self.scale,fill)


def adaptive_foreground():
    d = Drawing(1024,1024,None,"HK Census adaptive icon foreground: transparent skyline and trend mark")
    # All visible artwork fits inside a central circle of 66% of the canvas.
    factor = 1.46
    transformed = TransformedDrawing(d,factor,512-256*factor,512-244*factor)
    icon_mark(transformed)
    d.save("adaptive-icon-foreground")


def feature():
    d = Drawing(1024, 500, PAPER, "HK Census. Explore the long view. Abstract skyline and statistical trend artwork")
    # Two fields connect the quiet editorial typography to the graphic identity.
    d.rectangle((552,0,1024,500), TEAL)
    d.rectangle((552,0,566,500), DEEP_TEAL)
    # An understated rule and gold datum establish the same chart vocabulary.
    d.line([(60,80),(165,80)], TEAL, 5)
    d.circle(184,80,5,GOLD)
    d.text(56,212,"HK Census",66,INK,semibold=True)
    d.text(60,265,"Explore the long view",25,TEAL)
    d.line([(60,352),(450,352)], "#D6CFBF", 1)
    for left,height in [(60,17),(80,28),(100,22),(120,39)]:
        d.rectangle((left,418-height,left+8,418),TEAL)
    d.line([(152,418),(252,418)], "#D6CFBF",1)
    d.circle(272,418,3,GOLD)

    # Chart scaffolding carries no ticks, values, or purported data.
    for gy in (100,180,260,340,420):
        d.line([(593,gy),(992,gy)], "#2C8980",1)
    for gx in (625,705,785,865,945):
        d.line([(gx,64),(gx,444)], "#2C8980",1)
    skyline(d, 618, 116, 1.1, CREAM, TEAL)
    d.line([(600,420),(992,420)], CREAM,3)
    # Paired irregular paths suggest long time series without imitating app UI.
    d.line([(589,381),(635,350),(677,360),(720,330),(757,345),(801,292),(845,300),(887,244),(932,222),(978,166)], "#71B1A5",3,rounded=True)
    trend = [(589,368),(635,339),(677,351),(720,303),(757,316),(801,263),(845,278),(887,220),(932,202),(978,146)]
    d.line(trend, TEAL,15,rounded=True)
    d.line(trend, PALE_GOLD,7,rounded=True)
    d.circle(978,146,14,TEAL)
    d.circle(978,146,10,CREAM)
    d.circle(978,146,6,PALE_GOLD)
    d.save("feature-graphic-1024x500")


def validate():
    result = []
    for name, size, limit, mode in [
        ("app-icon-512.png", (512,512), 1024*1024, "RGBA"),
        ("feature-graphic-1024x500.png", (1024,500), 15*1024*1024, "RGB"),
    ]:
        path = OUT/name
        with Image.open(path) as image:
            assert image.size == size
            assert image.mode == mode
            if mode == "RGBA":
                assert image.getchannel("A").getextrema() == (255,255)
            assert image.info.get("icc_profile")
            assert path.stat().st_size <= limit
            result.append({"file":name,"width":image.width,"height":image.height,"format":image.format,"mode":image.mode,"opaque":True,"colorProfile":"sRGB","bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    adaptive_path = OUT/"adaptive-icon-foreground.png"
    with Image.open(adaptive_path) as adaptive:
        assert adaptive.size == (1024,1024)
        assert adaptive.mode == "RGBA"
        alpha = adaptive.getchannel("A")
        assert alpha.getextrema() == (0,255)
        visible = [(x,y) for y in range(adaptive.height) for x in range(adaptive.width) if alpha.getpixel((x,y))]
        max_radius = max(((x-512)**2+(y-512)**2)**0.5 for x,y in visible)
        assert max_radius < 1024*0.66/2
        result.append({"file":adaptive_path.name,"width":1024,"height":1024,"format":"PNG","mode":"RGBA","opaque":False,"colorProfile":"sRGB","alphaBounds":alpha.getbbox(),"maximumVisibleRadiusPx":round(max_radius,2),"safeCircleRadiusPx":1024*0.66/2,"backgroundColor":TEAL,"bytes":adaptive_path.stat().st_size,"sha256":hashlib.sha256(adaptive_path.read_bytes()).hexdigest()})
    (OUT/"graphics-validation.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    icon()
    feature()
    adaptive_foreground()
    validate()
