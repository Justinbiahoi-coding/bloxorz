"""Look of the 3D menus and HUD: night signage in an abandoned city.

Dark glass panels over the 3D scene, warm street-lamp gold for what matters, orange for danger.
Every screen takes its colours, sizes and timings from here so they stay in step.

Fredoka has no arrow, play or square glyphs (they render as blanks): draw those with ui3d.icons.
Safe extra glyphs: ‹ › « » • × · — –
"""
from ursina import color

BG = color.rgb(8, 12, 26)                 # menu backdrop behind the 3D scene
PANEL = color.rgba(16, 22, 40, 215)       # glass panel
PANEL_SOLID = color.rgb(20, 27, 48)
LINE = color.rgba(255, 200, 87, 70)       # panel outline
DIM = color.rgba(4, 6, 14, 170)           # veil behind a modal

BTN = color.rgb(44, 58, 94)
BTN_HOVER = color.rgb(64, 82, 130)
BTN_OFF = color.rgb(32, 38, 56)

GOLD = color.rgb(255, 200, 87)
GOLD_HOVER = color.rgb(255, 218, 130)
ORANGE = color.rgb(255, 138, 91)
ORANGE_HOVER = color.rgb(255, 165, 125)
GREEN = color.rgb(120, 220, 150)

TEXT = color.rgb(250, 244, 232)
MUTED = color.rgb(170, 178, 200)
INK = color.rgb(24, 20, 14)               # text on gold

# Text scales (Ursina Text.size units)
TITLE = 7.0          # screen title, e.g. BLOXORZ
HEADING = 3.2        # screen heading, e.g. FREE PLAY
SUBHEAD = 1.6        # panel heading
BODY = 1.2
SMALL = 0.95
STAT = 2.6           # big numbers in stat cards

# Sizes in camera.ui units (screen height = 1)
BUTTON_H = 0.072
CORNER = 0.022       # corner radius
GAP = 0.018

# Motion
FAST = 0.12          # hover, press
MEDIUM = 0.22        # panels opening
