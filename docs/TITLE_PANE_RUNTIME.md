# Title-screen BCLYT pane runtime and optional original BCLAN tracks

This milestone integrates **part** of the recovered original UI into the DS/DSi
runtime. The four title menu rows are resolved from source-derived
\`MnIf_S_TitleList.bclyt\` pane hierarchy and \`Touch00..Touch03\` hit panes
using a compact, bounded scene. The same rectangles drive the title labels,
selection borders and stylus hit testing in \`source/main.c\`.

## What is built into the ROM

\`scripts/build_both.sh\` runs:

\`\`\`sh
python3 tools/stage_title_ui.py \
  ui_mapping/original_pane_geometry.json nitrofs/title.drui
\`\`\`

This uses the already-public metadata-only BCLYT snapshot, not private original
Nintendo UI animation files. It keeps the original 320x240 title hierarchy,
origin, local translation, Z rotation, XY scale, sizes, flags and parent transforms.
The 256x192 title placement uses explicit 0.8 X/Y retargeting and a **provisional
80px Y calibration** to preserve the previously verified DS menu placement.
Rows are left visible because original BCLAN opacity tags are not yet decoded.
No original material, texture or alpha curves are claimed as reconstructed.

When an override is absent, corrupt, unsupported or drives the four title touch
panes off screen/into overlap, the existing fixed DS panel geometry is used.

## Add your privately recovered original animation

To stage your own CLPA pane curves decoded from the original title animation,
run the command below outside the public repository. Choose a BCLAN file
whose target names match the title BCLYT.

\`\`\`sh
python3 tools/stage_title_ui.py \
  ui_mapping/original_pane_geometry.json \
  /private/DreamRadarDSi/UI/title.drui \
  --clip /private/original/Ui/MnIf_S_TitleList/anim/<clip>.bclan
\`\`\`

Copy the resulting file to \`sd:/DreamRadarDSi/UI/title.drui\` on DSi or
\`fat:/DreamRadarDSi/UI/title.drui\` on compatible DS flashcart/DLDI storage.
It takes precedence over the generated NitroFS geometry-only scene. The game
samples CLPA translation, Z rotation, scale and size at runtime, including
Hermite slopes, step keys, equal-frame selection, clip duration and optional
looping. Other CLPA properties are preserved by the format but do not have DS
visible geometry effects. The loader rejects oversize, corrupt, non-finite,
out-of-order, overlapping or invalid scene input before applying it.

Private clip **keyframes must not be committed or uploaded to public GitHub**.
The stager rejects private-clip outputs inside the repository checkout.

## Limitations that remain

- The bundled title background is still a static converted bitmap; moved panes
  use readable DS-adapted overlays. Exact original image/material binding,
  opacity animation, source mask clipping and 3DS transforms are unfinished.
- Only the title menu's 11 relevant hierarchy nodes and four interactive rows
  are staged. The remaining BCLYT screens, windows, text panes and complex
  visual materials have not been integrated with this compositor.
- Original alpha=0 row activation is intentionally overridden to ensure the
  menu stays usable; this is not a decoded original alpha animation.
- There is only one active optional title CLPA clip. Multiple simultaneous
  clips, clip layering, material/color/visibility tags, and animation events
  remain unimplemented. Pokémon skeletal animations are entirely separate.
- Host tests validate the original metadata snapshot, geometry, touch alignment,
  Hermite curve samples and malformed resources. Actual private clip playback,
  visual frame parity, DS/DSi hardware performance and complete gameplay need
  further independent testing.

This is a concrete first runtime integration, **not full milestone #47 or retail
3DS feature parity**.
