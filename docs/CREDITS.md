# Credits

## Stage layouts
`Source/levels/21.json` to `53.json` are the 33 levels of the original Bloxorz
(by Damien Clarke / DX Interactive, 2007), in order (file 20+n is original level n),
re-encoded into this project's JSON format (cropped to a square grid; switch, bridge and split
data converted to our coordinates).

The layouts were taken from the level data of the Game Boy Advance port
[jacobcoughenour/bloxorz_gba](https://github.com/jacobcoughenour/bloxorz_gba) (GPL-3.0).
Only the stage layouts were used; no code from that project is included.
The assignment explicitly allows recreating classic levels.

`Source/levels/1.json` to `20.json` were designed by the project authors.

## Visual assets
- Font: [Fredoka](https://fonts.google.com/specimen/Fredoka), SIL Open Font License 1.1 (`Source/assets/fonts/OFL-Fredoka.txt`).
- Tower backgrounds `Source/assets/backgrounds/sky_0..3.png` were generated with Stable Diffusion XL base 1.0
  (CreativeML OpenRAIL++-M) through ComfyUI. Prompts, in order: golden-hour sky, coral-to-violet sunset sky,
  indigo dusk sky with faint stars, navy night sky with soft city-light glow; each "minimalist painterly
  illustration, clean empty composition, game background". Seeds 11 to 14, size 1152x832.
- Tiles, block, HUD and transitions are drawn in code (`Source/ui/rooftop.py`, `Source/ui/hud.py`).
- Textures `Source/assets/textures/` (gravel, concrete, wood, fragile, steel) were generated with the same
  SDXL setup (`tools/comfy_gen.py`, seeds 201-205) and made seamless with `tools/process_assets.py`.
- Prop sprites `Source/assets/props/` were made image-to-image: the code-drawn props
  (`ui/building.py: draw_code_prop`) are rendered as sketches by `tools/make_sketches.py`, then SDXL adds
  detail at denoise 0.8 (seeds 401-408, 501-509), and `tools/process_assets.py` removes the white background.

## 3D version (`Source/ui3d/`, run `python main3d.py`)
- Furniture and walls: [Kenney Furniture Kit](https://kenney.nl/assets/furniture-kit) (CC0),
  `Source/assets/models/*.glb`, licence in `Source/assets/models/LICENSE-kenney-furniture.txt`.
- Intro landscape (pines, rocks used as mountains, grass, stumps, bushes): [Kenney Nature Kit](https://kenney.nl/assets/nature-kit)
  (CC0), re-coloured for night in code; licence in `Source/assets/models/LICENSE-kenney-nature.txt`.
- Rooftop equipment, path tiles, stairwell, block and the intro city are built from primitives in code;
  `assets/textures/facade.png` is drawn by code (pygame).
