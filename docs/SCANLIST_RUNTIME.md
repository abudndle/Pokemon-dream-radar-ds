# Original 3DS ScanList in the Nintendo DS Extensions menu

Source: `MnIf_S_ScanList.bclyt` recovered from the player's own decrypted Pokémon Dream Radar NCCH. The metadata-only snapshot in `ui_mapping/original_pane_geometry.json` includes its `RootPane/Pos/SRT00/L00..03/List00..03/Touch00..03` hierarchy, native 320 × 240 source canvas, local positions, scale, anchors and 3DS origin flags.

## What's implemented

- `tools/stage_scan_ui.py` stages the original four source row envelopes and input bounds as bounded `DRUI` v1 scene data. The publicly distributed scene contains **geometry only**, not proprietary textures or BCLAN keyframes.
- The ROM build packages `nitrofs/scan.drui` next to `nitrofs/title.drui`. The DS runtime loads it at startup.
- The **four** original ScanList touch panes, not five invented DS rows, are mapped into a DS 256 × 192 viewport using X/Y factor 0.8 with a provisional +45 DS-pixel Y calibration. The verified nominal rectangles are approximately x=4..244, y=1..30 / 33..62 / 65..94 / 97..126.
- All visible/unlocked/locked Extensions are retained. When selecting entries using Up/Down, the selection window paginates in groups of four. Touch input uses the **same live panes as rendering**; unused slots and space between panes are not buttons.
- The same bounded C CLPA sampler used by the title screen can play privately staged original ScanList translation, Z rotation, scale and size curves. An offscreen/overlapping/corrupt scene is rejected at evaluation time in favor of four safe fallback rectangles.
- A user-owned original animation override can live at `sd:/DreamRadarDSi/UI/scan.drui` (DSi) or `fat:/DreamRadarDSi/UI/scan.drui` (DS/DS Lite with a flashcart).

## Stage a private original animation

Create the override **outside** the public checkout. Do not commit original BCLAN bytes or decoded keyframes.

```sh
python3 tools/stage_scan_ui.py ui_mapping/original_pane_geometry.json \
  /private/dsi-sd/DreamRadarDSi/UI/scan.drui \
  --clip /private/original/Ui/MnIf_S_ScanList/anim/MyClip.bclan
```

Or stage geometry-only public data with:

```sh
python3 tools/stage_scan_ui.py ui_mapping/original_pane_geometry.json nitrofs/scan.drui
```

## Limitations / fidelity

- The runtime currently draws legible DS-adapted blue panels within the **original source-derived bounds**, not authentic original `wnd1` materials. Extracted original window textures, `ListOff` opacity and clip blending still need integration.
- Only the four ScrollList touch panes are used. The original `Touch04` Back control, the `Scrollbar` asset, and its source animation are not yet wired to touch actions; hardware B remains the supported Back control.
- Original 3DS alpha=0 row wrappers are forced visible because native source opacity tags and animation events have not yet been reconstructed. This is an explicit adaptation, not a claim of 3DS-identical animation.
- The Y offset is measured for a practical DS viewport and remains provisional pending source-vs-emulator visual alignment.
- This adds original-source geometry to **Search Extensions only**, not every BCLYT layout, full Pokémon models or sound.

## Acceptance and tests

`tests/test_stage_scan_ui.py` validates the real recovered metadata plus synthetic transform and malformed-resource fixtures, and `tests/test_scan_ui_scene.c` confirms four DS rectangles, matching stylus hit bounds, clipping and CLPA sampling. GitHub Actions compile the DS/DSi ROM and capture actual emulator boot/navigation screenshots, but those boot tests **do not prove pixel-perfect original ScanList parity** or physical DSi camera/gyro equivalence.
