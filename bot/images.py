"""Fase 3: grafica del post Instagram (1080x1350, JPEG)."""
from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .deals import Deal
from .telegram import fmt_day

W, H = 1080, 1350
FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "/Library/Fonts", "C:/Windows/Fonts"]
PALETTES = [  # (alto, basso, accento)
    ((15, 76, 129), (6, 30, 62), (255, 196, 0)),
    ((196, 69, 54), (92, 22, 30), (255, 230, 160)),
    ((22, 120, 105), (8, 48, 52), (255, 214, 102)),
    ((88, 54, 160), (30, 18, 70), (120, 230, 255)),
    ((230, 120, 40), (120, 40, 30), (255, 255, 255)),
]


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    names = ["DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"] if bold else \
            ["DejaVuSans.ttf", "Arial.ttf", "arial.ttf"]
    for d in FONT_DIRS:
        for n in names:
            p = Path(d) / n
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


def _fit(draw, text, max_w, start, bold=True):
    size = start
    while size > 30:
        f = _font(size, bold)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return _font(size, bold)


def _center(draw, y, text, font, fill):
    w = draw.textlength(text, font=font)
    draw.text(((W - w) / 2, y), text, font=font, fill=fill)


def render(deal: Deal, origin_name: str, dest_name: str, out: Path) -> Path:
    f = deal.flight
    idx = int(hashlib.md5(f.destination.encode()).hexdigest(), 16) % len(PALETTES)
    top, bottom, accent = PALETTES[idx]

    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):  # sfondo sfumato
        t = y / H
        draw.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))

    white = (255, 255, 255)
    soft = (220, 228, 240)
    margin = 80

    # badge in alto
    badge = "OFFERTA VOLO" if not deal.typical_price else f"-{deal.discount:.0%} SUL PREZZO TIPICO"
    bf = _font(40)
    bw = draw.textlength(badge, font=bf) + 60
    draw.rounded_rectangle([(W - bw) / 2, 110, (W + bw) / 2, 180], radius=35, fill=accent)
    _center(draw, 122, badge, bf, bottom)

    _center(draw, 250, f"da {origin_name.upper()}", _font(48, False), soft)
    _center(draw, 320, dest_name.upper(), _fit(draw, dest_name.upper(), W - 2 * margin, 130), white)

    price = f"{f.price:.0f}€"
    _center(draw, 520, price, _font(260), accent)
    _center(draw, 810, "andata e ritorno", _font(46, False), soft)
    if deal.typical_price:
        _center(draw, 870, f"invece di circa {deal.typical_price:.0f}€", _font(42, False), soft)

    # riquadro date
    draw.rounded_rectangle([margin, 970, W - margin, 1150], radius=30, fill=(255, 255, 255))
    _center(draw, 995, f"{fmt_day(f.departure)}  →  {fmt_day(f.return_date)}", _font(58), bottom)
    scali = "volo diretto" if f.transfers == 0 else "1 scalo"
    _center(draw, 1075, f"{f.nights} notti · {scali}", _font(40, False), bottom)

    _center(draw, 1210, "Link in bio · i prezzi cambiano in fretta", _font(34, False), soft)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=90)   # Instagram accetta solo JPEG
    return out
