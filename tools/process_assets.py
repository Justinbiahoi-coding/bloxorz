"""Turn raw ComfyUI images into game assets. Needs numpy + Pillow (dev only, not a game dependency).

    python tools/process_assets.py <raw_dir> <Source/assets>

Props (*.png not starting with tex_): white background keyed out from the borders, cropped, max 512 px.
Textures (tex_*.png): resized to 512 and made seamless by blending with a half-offset copy.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

MARK = (255, 0, 255)


def prop(src, dst):
    img = Image.open(src).convert('RGB')
    w, h = img.size
    rgb = np.asarray(img).astype(np.float32)
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    bg = np.median(border, axis=0)                               # background colour, even if not pure white
    region = img.filter(ImageFilter.GaussianBlur(2))             # blur so noise does not stop the fill
    for xy in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        if region.getpixel(xy) != MARK:
            ImageDraw.floodfill(region, xy, MARK, thresh=60)
    outside = np.all(np.asarray(region) == MARK, axis=2)         # background connected to the borders
    dist = np.linalg.norm(rgb - bg, axis=2)
    soft = np.clip((dist - 14) / 34, 0, 1)                       # soft edge instead of a hard cut-out
    alpha = np.where(outside, soft, 1.0) * 255
    alpha = Image.fromarray(alpha.astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.7))
    out = img.convert('RGBA')
    out.putalpha(alpha)
    out = out.crop(alpha.point(lambda v: 255 if v > 24 else 0).getbbox())
    out.thumbnail((512, 512), Image.LANCZOS)
    out.save(dst)


def texture(src, dst, size=512):
    a = np.asarray(Image.open(src).convert('RGB').resize((size, size), Image.LANCZOS)).astype(np.float32)
    rolled = np.roll(a, (size // 2, size // 2), axis=(0, 1))      # seamless at its own borders
    t = np.linspace(0, 1, size)
    edge = np.minimum(t, 1 - t) * 2                                # 0 at the borders, 1 in the middle
    weight = np.clip(np.minimum.outer(edge, edge) * 2.5, 0, 1)[..., None]
    out = a * weight + rolled * (1 - weight)                       # borders from the rolled copy
    Image.fromarray(out.astype(np.uint8)).save(dst)


def main():
    raw, assets = Path(sys.argv[1]), Path(sys.argv[2])
    (assets / 'props').mkdir(parents=True, exist_ok=True)
    (assets / 'textures').mkdir(parents=True, exist_ok=True)
    for f in sorted(raw.glob('*.png')):
        if f.name.startswith('tex_'):
            texture(f, assets / 'textures' / f.name[4:])
        else:
            prop(f, assets / 'props' / f.name)
        print('processed', f.name)


if __name__ == '__main__':
    main()
