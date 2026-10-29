"""Cut static weights out of the variable Fredoka font for the 3D UI.

Panda3D only reads a variable font's default instance, which for Fredoka is Light (300),
so the game needs real static files for heavier text. Run once after changing the list:

    python -m pip install fonttools
    python tools/make_font_weights.py

Fredoka is under the SIL OFL 1.1 with no Reserved Font Name, so derived instances may ship
next to OFL-Fredoka.txt.
"""
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

FONTS = Path(__file__).resolve().parent.parent / 'Source' / 'assets' / 'fonts'

# file name -> (weight 300..700, width 75..125)
WEIGHTS = {
    'Fredoka-Medium.ttf': (500, 100),          # body text, numbers in panels
    'Fredoka-SemiBold.ttf': (600, 100),        # buttons, labels, key hints
    'Fredoka-BoldCondensed.ttf': (700, 80),    # titles, headings, big stats
}


def main():
    for name, (weight, width) in WEIGHTS.items():
        font = TTFont(FONTS / 'Fredoka.ttf')
        static = instantiateVariableFont(font, {'wght': weight, 'wdth': width}, updateFontNames=False)
        static.save(FONTS / name)
        print('wrote', name)


if __name__ == '__main__':
    main()
