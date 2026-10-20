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
- Textures `Source/assets/textures/` (gravel, concrete, wood, fragile, steel) and the prop sprites
  `Source/assets/props/vent.png`, `skylight.png` were generated with the same SDXL setup
  (`tools/comfy_gen.py`, prompts and seeds 201-205 and 304-305 in that run) and post-processed with
  `tools/process_assets.py` (made seamless / background removed). Props without a sprite are drawn in code.
