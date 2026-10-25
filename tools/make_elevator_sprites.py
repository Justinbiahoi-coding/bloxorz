"""Build Source/assets/textures/elev/* for the lift cutscene (ui3d/elevscreen.py).

    python tools/make_elevator_sprites.py SPRITE_DIR BIN_RENDER.png

SPRITE_DIR holds the frames from tools/gm_extract.py (Elevator Pitch). BIN_RENDER.png is the bin on a magenta
background; it is cut out, pixelated and outlined here. Digits 0-9 are drawn from a 5x7 bitmap font in the
same navy-and-white style as the game's floor display (which only counts to 4).
"""
import os
import shutil
import sys

from PIL import Image

SRC, BIN = sys.argv[1:3]
OUT = os.path.join(os.path.dirname(__file__), '..', 'Source', 'assets', 'textures', 'elev')
os.makedirs(OUT, exist_ok=True)
for src, dst in (('sprite_door_left_0', 'door_left'), ('sprite_door_right_0', 'door_right'), ('sprite_wall_0', 'wall'),
                 ('sprite_nineslice2_0', 'panel'), ('sprite_elevatorinfo_6', 'arrow_up'),
                 ('sprite_elevatorinfo_4', 'arrow_up_dim'), ('sprite_elevator_0', 'buttons_0'),
                 ('sprite_elevator_1', 'buttons_1'), ('sprite_elevator_2', 'buttons_2'),
                 ('sprite_office_bg_0', 'hall')):
    shutil.copy(os.path.join(SRC, src + '.png'), os.path.join(OUT, dst + '.png'))

FONT = {'0': '01110 10001 10011 10101 11001 10001 01110', '1': '00100 01100 00100 00100 00100 00100 01110',
        '2': '01110 10001 00001 00010 00100 01000 11111', '3': '11110 00001 00001 01110 00001 00001 11110',
        '4': '00010 00110 01010 10010 11111 00010 00010', '5': '11111 10000 11110 00001 00001 10001 01110',
        '6': '00110 01000 10000 11110 10001 10001 01110', '7': '11111 00001 00010 00100 01000 01000 01000',
        'L': '10000 10000 10000 10000 10000 10000 11111', 'R': '11110 10001 10001 11110 10100 10010 10001',
        '8': '01110 10001 10001 01110 10001 10001 01110', '9': '01110 10001 10001 01111 00001 00010 01100'}
for ch, rows in FONT.items():                      # 32x32 cell like the game's: navy plate, white digit, dark outline
    im = Image.new('RGBA', (32, 32), (36, 44, 78, 255))
    g = [r for r in rows.split()]
    for y, row in enumerate(g):
        for x, c in enumerate(row):
            if c == '1':
                for dx in range(-1, 5):
                    for dy in range(-1, 5):
                        px, py = 4 + x * 4 + dx, 2 + y * 4 + dy
                        if 0 <= px < 32 and 0 <= py < 32 and (dx in (-1, 4) or dy in (-1, 4)):
                            im.putpixel((px, py), (18, 22, 48, 255))
    for y, row in enumerate(g):
        for x, c in enumerate(row):
            if c == '1':
                for dx in range(4):
                    for dy in range(4):
                        im.putpixel((4 + x * 4 + dx, 2 + y * 4 + dy), (238, 242, 250, 255))
    im.save(os.path.join(OUT, 'digit_%s.png' % ch))

im = Image.open(BIN).convert('RGBA')               # the bin: cut out, pixelate, outline
px = im.load()
for y in range(im.height):
    for x in range(im.width):
        r, g, b, a = px[x, y]
        if r > 200 and g < 60 and b > 200:
            px[x, y] = (0, 0, 0, 0)
im = im.crop(im.getbbox())
h = 60
sm = im.resize((max(1, round(im.width * h / im.height)), h), Image.BOX)
alpha = sm.split()[3].point(lambda v: 255 if v > 110 else 0)
rgb = sm.convert('RGB').quantize(colors=10, method=Image.MEDIANCUT).convert('RGB')
rgb = rgb.point(lambda v: min(255, int(v * 1.35 + 14)))        # lift it: the cutscene is brighter than the render
spr = Image.merge('RGBA', (*rgb.split(), alpha))
canvas = Image.new('RGBA', (spr.width + 2, spr.height + 2), (0, 0, 0, 0))
canvas.alpha_composite(spr, (1, 1))
a = canvas.split()[3]
out = canvas.copy()
ap = a.load()
op = out.load()
for y in range(canvas.height):
    for x in range(canvas.width):
        if ap[x, y] == 0 and any(0 <= x + dx < canvas.width and 0 <= y + dy < canvas.height and ap[x + dx, y + dy]
                                 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            op[x, y] = (20, 24, 40, 255)
out.save(os.path.join(OUT, 'bin.png'))
print('elevator sprites ->', os.path.normpath(OUT), sorted(os.listdir(OUT)))
