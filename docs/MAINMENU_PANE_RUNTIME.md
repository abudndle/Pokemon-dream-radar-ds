# Original 3DS Research Lab main menu panes on DS

## Source

The recovered `MnIf_S_MainMenuList.bclyt` metadata contains a 320 × 240 original lower-screen source layout with four interactive rows: `RootPane / Pos / SRT / L00..03 / List00..03 / Touch00..03`. The original first-row touch pane is 294 × 48 source pixels; the remaining three are 266 × 34. Their source vertical offsets are 125, 78, 34 and -10. These are real extracted source values, not guessed DS button positions.

## Runtime implementation

- The existing bounded `DRUI v1` parser now accepts a third **original** BCLYT layout, `MnIf_S_MainMenuList.bclyt`, preserving its `SRT` parent and the four distinct hit rectangles.
- A geometry-only `nitrofs/mainmenu.drui` is generated from the previously audited metadata-only JSON during builds; no proprietary archive or original decoded animation curves are committed.
- The DS retarget transform scales source X/Y by 0.8 and uses an explicit **provisional +24 screen-pixel Y offset**, giving roughly x=10..246 for row 0 and x=21..235 for rows 1–3, at y=0, 44, 79 and 114.
- The Research Lab screen renders its labels, selection border and touchscreen targets from **the same live four rectangles**. A broken/overlapping/missing scene falls back to fixed four-row bounds that are safe on the 256 × 192 DS screen.
- The port retains **every existing DS/DSi option** by paginating four entries per page: Start Search, Development Lab, Send Research Data, Records on page 1; Options, Talk to Burnet, and Photo Album (DSi only) on page 2. Up/Down still cycles all available rows. B still returns to Title.
- A private original BCLAN pane-motion scene may be staged to `sd:/DreamRadarDSi/UI/mainmenu.drui` (DSi) or `fat:/DreamRadarDSi/UI/mainmenu.drui` (compatible flashcart) and overrides the geometry-only NitroFS scene after strict validation.

## Private animation staging

Run this outside the public GitHub checkout with a privately extracted genuine MainMenuList BCLAN clip:

```sh
python3 tools/stage_title_ui.py ui_mapping/original_pane_geometry.json \
  /private/SD/DreamRadarDSi/UI/mainmenu.drui \
  --layout MnIf_S_MainMenuList.bclyt --offset-y 24 \
  --clip /private/original/Ui/MnIf_S_MainMenuList/anim/OWNED_CLIP.bclan
```

## Known fidelity gaps

- Only the original four selectable row **transform, size, and bound** panes are reconstructed. Its `wnd1` textures, `txt1` fonts, focus/hover/disabled materials, alpha=0 animation, navigation sounds, page scroll transition and original 3DS compositor remain unsupported.
- DS-only additional options are reachable on page 2, rather than inventing seven simultaneously visible original 3DS rows. This is an explicit hardware/feature adaptation.
- The +24 Y calibration is provisional until original-vs-DS screenshot comparison. Exact pixel parity is **not claimed**.
- The accepted keyframes are privately staged; the public game does not contain or redistribute original commercial BCLAN animation payloads.
- The new portable tests validate both the recovered original geometry and a synthetic CLPA track plus corrupt-file rejection. Linux emulator smoke verifies boot/navigation but not every touch page or physical DSi behavior.

Milestone #47 remains open until the other original BCLYT material/animation/layout families and actual hardware validation are complete.