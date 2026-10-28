"""Look of the 3D menus and HUD: an elevator control panel in a low-poly ruined city.

Angular plates with a small chamfer and a little depth, charcoal blue-grey faces, warm gold only for
the main action and whatever is selected. Every screen takes colours, fonts, sizes and timings from
here so they stay in step.

Fredoka has no arrow, play, check or square glyphs (they render as blanks): draw those with
ui3d.icons. Safe extra glyphs: ‹ › « » • × · — –
"""
from panda3d.core import Filename
from ursina import color

from .world import ASSETS


def _font(name):
    return Filename.fromOsSpecific(str(ASSETS / 'fonts' / name)).getFullpath()


# Static cuts of the variable Fredoka (tools/make_font_weights.py); its default instance is Light.
FONT_TITLE = _font('Fredoka-BoldCondensed.ttf')   # titles, headings, big numbers
FONT_LABEL = _font('Fredoka-SemiBold.ttf')        # buttons, captions, key chips
FONT_BODY = _font('Fredoka-Medium.ttf')           # running text

# Glyph texture pixels per unit, one value per font file (Panda3D shares a font between texts,
# so mixing values would re-render glyphs). Big titles need far more than Ursina's default 54.
RESOLUTION = {FONT_TITLE: 260, FONT_LABEL: 110, FONT_BODY: 96}

# Surfaces
BG = color.rgb(10, 12, 17)
PANEL = color.rgba(21, 24, 30, 236)
PANEL_RIM = color.rgb(62, 68, 80)
DIVIDER = color.rgba(120, 128, 142, 70)
DIM = color.rgba(6, 7, 10, 175)                   # veil behind a dialog

FACE = color.rgb(38, 43, 52)                      # secondary button face
FACE_HOVER = color.rgb(52, 59, 71)
FACE_PRESS = color.rgb(29, 33, 40)
EDGE = color.rgb(15, 17, 22)                      # the plate's side, seen below the face
RIM = color.rgb(74, 81, 95)

GOLD = color.rgb(240, 182, 74)                    # primary face, selection, key numbers
GOLD_HOVER = color.rgb(250, 202, 108)
GOLD_PRESS = color.rgb(196, 146, 56)
GOLD_EDGE = color.rgb(128, 88, 30)
GOLD_RIM = color.rgb(255, 214, 128)

OFF_FACE = color.rgb(64, 68, 76)                  # disabled
OFF_TEXT = color.rgb(118, 122, 130)

DONE_FACE = color.rgb(46, 68, 52)                 # completed level
DONE_RIM = color.rgb(92, 128, 96)
GREEN = color.rgb(150, 212, 150)
ORANGE = color.rgb(255, 146, 96)                  # warnings, a fall

TEXT = color.rgb(236, 232, 224)
MUTED = color.rgb(150, 156, 168)
INK = color.rgb(34, 26, 14)                       # text on gold

# Text scales (Ursina Text.size units)
TITLE = 7.5
HEADING = 3.4
SUBHEAD = 1.5
LABEL = 1.25
BODY = 1.15
SMALL = 0.95
TINY = 0.8
STAT = 2.8

# Sizes in camera.ui units (screen height = 1)
BUTTON_H = 0.066
CHAMFER = 0.008
DEPTH = 0.006          # how far the face stands above its edge
RIM_W = 0.0025
FOCUS_W = 0.0045
PAD = 0.03

# Motion
FAST = 0.1
MEDIUM = 0.2
