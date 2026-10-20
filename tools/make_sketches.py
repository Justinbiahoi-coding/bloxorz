"""Render the code-drawn props, big and on white, as img2img sketches for SDXL (keeps the top-down layout).

    Source/.venv/bin/python tools/make_sketches.py <comfyui>/input
"""
import os
import sys
from pathlib import Path

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'Source'))

import pygame  # noqa: E402

from ui.building import SIZES, draw_code_prop  # noqa: E402

out = Path(sys.argv[1])
pygame.init()
for kind, (w, h) in SIZES.items():
    if kind == 'antenna':
        continue
    surf = pygame.Surface((1024, 1024))
    surf.fill((255, 255, 255))
    k = 720 / max(w, h)
    rect = pygame.Rect(0, 0, int(w * k), int(h * k))
    rect.center = (512, 512 if kind != 'desk' else 470)      # desk leaves room for its chair
    draw_code_prop(surf, kind, rect, shadow=False)
    pygame.image.save(surf, str(out / 'sketch_{}.png'.format(kind)))
    print('sketch', kind)
