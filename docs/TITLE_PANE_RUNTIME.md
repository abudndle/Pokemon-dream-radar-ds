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
- Only the title menu's 15 relevant hierarchy nodes and four interactive rows
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

## Restore original 3DS title backgrounds without redistributing them

The public ROM **already contains the owner's original extracted English
title logo sprite**, and the 320x240 title-menu BCLYT hierarchy powers its
interactive panes. The two public full-screen title backdrops, however, were
re-created approximations and **are not the original 3DS bitmaps**. A 3DS-exact
title cannot be claimed until the owner has supplied and validated the missing
original background and window textures, material bindings and animations.

To put genuine private original 3DS title-background images into the DS build,
extract the opaque 400x240 title-top and 320x240 title-bottom background
compositions from the **owner's own game dump**, then stage both together:

```sh
python3 tools/stage_original_title_art.py \
  --top /private/title-top-400x240.bclim \
  --bottom /private/title-bottom-320x240.png \
  --output-root /private/dsi-sd-card
```

This writes `DreamRadarDSi/UI/title_top.raw` and
`DreamRadarDSi/UI/title_bottom.raw` under the specified private storage
root. Supported sources are privately extracted uncompressed BCLIM or
opaque PNG/BMP files with the original screen dimensions. ETC1 formats are
explicitly rejected by the decoder, not silently approximated.
Both screens are scaled to 256x192 RGB555, the physical DS/DSi screen size;
the extracted title logo and existing menu-pane labels are still overdrawn
by the runtime, so provide **background-only** images rather than screenshots
already containing a complete logo or text.

On startup, if the DSi SD or DS flashcart FAT volume contains both files,
the runtime validates their exact 98,304-byte length and opaque RGB555 pixels,
then replaces both title backgrounds together. Missing, partial or corrupt
pairs are ignored without changing the bundled fallback. The staging script
refuses to place converted original Nintendo artwork inside the public GitHub
checkout. No original 3DS bitmap has been published in this PR.

### Unobstructed original title menu

The extra DS-only camera settings gear is removed from the title artwork.
`SELECT + X` held together on the title screen opens the optional camera
settings, and B restores the title selection. One key or a random touchscreen
tap cannot open it. This keeps the original title menu unmodified by the
camera settings feature, though the still-approximate fallback backgrounds
remain to be replaced by the owner's original images.

**Outstanding:** exact material/window image composition, original animated
opacity, all pane timelines, idle Pokémon title background, pixel-verified
original 3DS fidelity, and DS/DSi hardware acceptance tests.
