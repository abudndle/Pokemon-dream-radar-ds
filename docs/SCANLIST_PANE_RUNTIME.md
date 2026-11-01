# Milestone #47, phase 4 — original ScanList pane integration

This phase advances the existing title-only source-derived UI runtime to the
**Search Extensions** list. It uses the owner's previously extracted,
metadata-only `MnIf_S_ScanList.bclyt` snapshot rather than guessed touch
coordinates or proprietary graphics in the public repository.

## Runtime behavior

- The four original `L00..L03 / List00..03 / Touch00..03` hierarchy paths are
  staged into the same bounded DRUI v1 file format used by the title.
- The source `SRT00` translation, each pane's origin, size, visibility and
  alpha, and parent transforms are evaluated at DS 256x192 resolution.
  Unrelated `SRT01/SRT02` scrollbar/back panes remain excluded; implementing
  their full source materials and screen behavior is future work.
- The Extensions screen now pages **four** visible entries rather than the
  earlier adapted five. Its label positions, focus borders, and touchscreen
  selection use the same resolved rectangles; D-pad selection and all
  extension unlock/price/search logic are left intact.
- Invalid, unavailable or offscreen animation scenes revert to four bounded
  static rectangles. No undecoded animation or partially corrupt asset is
  trusted by the renderer.
- Original `L00..L03` alpha=0 fields are deliberately made visible, because
  the original CLAN appearance tracks are not decoded yet. This is an
  explicitly non-original visibility fallback.

## Build and private staging

The standard `scripts/build_both.sh` stages both files from the public
source-derived metadata:

```sh
python3 tools/stage_title_ui.py ui_mapping/original_pane_geometry.json nitrofs/title.drui
python3 tools/stage_title_ui.py ui_mapping/original_pane_geometry.json nitrofs/scanlist.drui --layout MnIf_S_ScanList.bclyt
```

Private user-owned BCLAN pane-motion data can be staged *outside* the checkout:

```sh
python3 tools/stage_title_ui.py ui_mapping/original_pane_geometry.json \
  /private/DSCard/DreamRadarDSi/UI/scanlist.drui \
  --layout MnIf_S_ScanList.bclyt \
  --clip /private/original/Ui/MnIf_S_ScanList/anim/SELECTED.bclan
```

The private override is read from `sd:/DreamRadarDSi/UI/scanlist.drui` or
`fat:/DreamRadarDSi/UI/scanlist.drui` if available. A private clip can
change pane positions, sizes and rotations; it must still produce four
nonoverlapping visible on-screen hit areas to be accepted. This phase does
not claim the exact original timing, visuals or source material bindings.

## Validation

`make test-host` runs the public-only synthetic ScanList staging and
portable C runtime test. It checks the actual original extracted four-row
positions, exact touch selection on resolved pane rectangles, synthetic
one-shot CLPA movement, corrupted DRUI rejection and unsupported layouts.
The DS build embeds the public metadata-only `scanlist.drui` scene.

The full retail original scan screen remains incomplete: window textures,
icons, dynamic scrolling, genuine CLAN alpha/material tracks, source text
layout, and visual comparison against original 3DS captures still require
private owner-supplied references. The original 3DS gyroscope and stereo
display cannot be replicated by stock DS/DSi hardware.
