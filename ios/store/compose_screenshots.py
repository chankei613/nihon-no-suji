#!/usr/bin/env python3
"""App Store 用スクリーンショットの合成（1320x2868）。
使い方: python3 compose_screenshots.py <素材dir> <出力dir>
素材は StoreScreenshotTests が撮った 01-today.png … 05-favorites.png。"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1320, 2868
BG = (250, 248, 244)      # Theme.bg
INK = (27, 26, 24)        # Theme.ink
SUB = (139, 136, 130)     # Theme.sub
FONT = "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc"

SHOTS = [
    ("01-today", "今日の日本を、", "数字ひとつずつ"),
    ("02-changes", "いつもと違う数字が、", "ひと目でわかる"),
    ("03-list", "気になる数字が、", "きっと見つかる"),
    ("04-detail", "30日のうつりかわりも", "チェック"),
    ("05-favorites", "気になる数字だけを、", "自分の一覧に"),
]

src_dir, out_dir = sys.argv[1], sys.argv[2]
os.makedirs(out_dir, exist_ok=True)
font = ImageFont.truetype(FONT, 92, index=0)

for i, (name, l1, l2) in enumerate(SHOTS, 1):
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)
    for j, line in enumerate((l1, l2)):
        w = d.textlength(line, font=font)
        d.text(((W - w) / 2, 150 + j * 130), line, font=font, fill=INK)

    shot = Image.open(os.path.join(src_dir, name + ".png")).convert("RGB")
    sw = 1100
    sh = round(shot.height * sw / shot.width)
    shot = shot.resize((sw, sh), Image.LANCZOS)
    x, y = (W - sw) // 2, 470

    mask = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, sw, sh), radius=80, fill=255)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((x, y + 14, x + sw, y + sh + 14), radius=80, fill=(0, 0, 0, 40))
    canvas.paste(Image.alpha_composite(canvas.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(24))).convert("RGB"))
    canvas.paste(shot, (x, y), mask)
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((x, y, x + sw, y + sh), radius=80, outline=(230, 225, 216), width=3)
    canvas.save(os.path.join(out_dir, f"{i:02d}-{name.split('-', 1)[1]}.png"), optimize=True)
    print("wrote", i, name)
