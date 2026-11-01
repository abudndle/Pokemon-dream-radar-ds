# Original 3DS Development ShopList panes on Nintendo DS

## Source and scope

The private user's Dream Radar NCCH supplied recovered `MnIf_S_ShopList.bclyt` metadata. The publicly committed metadata-only snapshot contains the original 320 × 240 lower-screen hierarchy `RootPane / Pos / SRT00 / L00..03 / List00..03 / Touch00..03`. Four original Touch panes are 300 × 36 pixels, spaced in the source at `L00..03` Y positions 157, 117, 77 and 37 with SRT x=-5. The original `wnd1` materials, source CLPA opacity tracks and `Touch04` Back pane are not yet rendered.

## Port integration

- `tools/stage_title_ui.py --layout MnIf_S_ShopList.bclyt` stages recovered source transform/size geometry to a bounded `DRUI` v1 scene. Public builds package **geometry only** at `nitrofs/shoplist.drui`; no proprietary original animations or textures are committed.
- The Development Lab shop draws each row's live text/focus within the matching source-derived `Touch00..03` bounds, and touch selection uses the **identical rectangles**. On malformed or missing scene data the established safe 4-row DS geometry is used.
- The original source has four selectable rows, but the DS port still needs all six shop entries. Selection wraps through all six and displays the shop in two four-slot pages (4 + 2). The purchase and currency gameplay logic is unchanged.
- On transition to the shop, the clip frame counter restarts. A user may stage an original privately decoded BCLAN CLPA scene at `sd:/DreamRadarDSi/UI/shoplist.drui` (DSi) or `fat:/DreamRadarDSi/UI/shoplist.drui` (DLDI flashcart). Bounded loader and per-frame transform evaluation are shared with title, ScanList and MainMenuList.

## Stage a user-owned original animation outside GitHub

```sh
python3 tools/stage_title_ui.py ui_mapping/original_pane_geometry.json \
  /private/dsi-sd/DreamRadarDSi/UI/shoplist.drui \
  --layout MnIf_S_ShopList.bclyt \
  --clip /private/original/Ui/MnIf_S_ShopList/anim/OWNED_CLIP.bclan
```

## Validation and limitations

`tests/test_stage_shoplist_ui.py` uses the exact publicly audited source geometry, a synthetic CLPA step sequence, the existing four-row runtime C test, and private-output rejection. CI runs portable tests, BlocksDS DS/DSi compilation, DeSmuME and melonDS navigation smoke tests.

Window textures (`wnd1`), list focus/flash animations (`ListFlash`, `ListRight`), source alpha/disabled states, original sounds, an animated scrollbar, the 3DS `Touch04` Back pane, and pixel-identical 3DS composition are **not implemented**. This is an evidence-based source-layout integration, not a complete 3DS port. Milestone #47 stays open until further source-material and hardware requirements are met.
