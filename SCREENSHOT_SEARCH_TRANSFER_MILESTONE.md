# Screenshot-accurate cloud radar, search controls & research tray milestone

This milestone is based on the **three latest screenshots provided by the user**. The preconverted NitroFS images are included; a decrypted NCCH/CIA is not included in this archive.

## What changed in actual BlocksDS C code

1. **Cloud radar overview:** `STATE_RADAR` now renders a teal radar, markers and left-side 10/10-style counts rather than a fake live camera preview. It uses the original `RadarIcon00`, `RadarIcon01`, `Radar06` and user-supplied screenshot badges. Counts and marker positions are drawn live, including when clouds are consumed. A camera is not requested until `STATE_SPHERE` (an actual target encounter).
2. **Camera search touchscreen:** Both DSi camera searches and DS/DSi camera-free encounters use the original three-hexagon screenshot artwork, with live consumable quantities, orb total and remaining cloud count. Touch hitboxes correspond to the blue, green and orange hexagons. The user-provided white-cloud fallback is displayed whenever live camera is unavailable.
3. **Send Research Data:** The layout now follows the screenshot's black/cyan dialog + silver tray, with a six-Pokémon and six-item grid, 26 original extracted species thumbnails and 23 original extracted research-item icons, numerical stack amounts, selected-cell border, D-pad/touch slot selection and A/B bottom buttons. When Black 2 or White 2 is the **one** active game, its name is shown in the dialog. Real Unova Link transfer **does not work yet**; **A exports a text file only**, and retail game `.sav` files are read-only. Release of local queued research requires the existing explicit archive confirmation sequence.
4. The existing DS vs DSi camera-optional builds, TWiLight Menu++ save-file recognition, six-slot replacement, original Development Lab, Professor Burnet dialogue, upgrades, and single-active-game rules remain unchanged.

## Native-resolution images

`preview/cloud_search_transfer_triptych.png` is a three-panel composition showing top and bottom DS screens (rendered at 256x192 each and enlarged with nearest-neighbor scaling). The values and captured Pokemon/items are **illustrative example data**. This preview was produced from the project's preconverted assets; **it is NOT a melonDS screenshot or proof of a working ROM**.

`preview/cloud_radar_overview.png`, `preview/camera-free_encounter.png`, and `preview/research_data_archive.png` are individual two-screen images.

## Verification and limitations

- All eleven portable gameplay/UI host-test suites pass, plus NDS header/asset-format checks.
- Both DSi and camera-free DS main C files pass the local syntax smoke tests.
- A BlocksDS ARM toolchain is still required to produce and runtime-test an `.nds` executable. No such successful build has been verified in this environment.
- Exact original BCFLYT/BCLAN menu transitions, 3D Pokemon encounters, camera tracking, original sound, and a real Black 2/White 2 game-save transfer remain unfinished.

## Build and run portable checks

```
make test-host test-syntax
make PLATFORM=ds check-sdk
sh scripts/build_both.sh
```

The last two commands require the BlocksDS ARM build system. `make assets` can regenerate bitmaps if the original extraction is placed at the documented adjacent `dream_radar_dsi/original_romfs` path; prebuilt asset bitmaps and sprites are bundled in `nitrofs/` so a regular build does not need extracted ROM files.
