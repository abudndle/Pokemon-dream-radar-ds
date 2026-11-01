# Private original BCLAN title pane animation on DS

This optional build path enables the real owner's decoded original 3DS BCLAN
title tracks to drive the DS title pane compositor. **No original BCLAN keys,
Nintendo animation payloads, or their generated headers are committed.**
A normal public build uses the static source-derived title geometry.

## Locally stage owner-owned title keys

1. Find a legitimate original TitleList animation clip among your privately
   extracted BCLAN files. Verify the CLAN/pai1 signature before decoding.
2. Run the existing bounded decoder *into a private working directory*:

   ```sh
   python3 tools/decode_bclan_panes.py \
     /private/Ui/MnIf_S_TitleList/anim/your_original_clip.bclan \
     /private/title_clpa.json
   ```

3. Retarget the available original CLPA tracks into the optional build header:

   ```sh
   python3 tools/stage_title_clpa.py \
     /private/title_clpa.json source/private_title_clpa.h
   ```

4. Compile privately using the normal BlocksDS instructions. To return to
   the public artifact, delete the local generated header and rebuild.

The generated header is ignored by Git. It can contain privately derived
original animation data; **do not add it to a GitHub commit or artifact.**

## What is implemented

- Runtime CLPA translation X/Y, rotation Z, scale X/Y, size X/Y sampling.
- Hermite and step curves, bounded keyframes, no division by equal-time keys.
- One-shot clip clamping or looping from the original CLAN metadata.
- Composed 2D parent transforms and pane visibility/alpha, optional clipping.
- Original BCLYT TitleList touch pane geometry; labels, focus, and taps use
  the same runtime rectangles.
- Retargeted Touch00..03 and L00..03 pane keyframes with 320x240→256x192
  coordinate conversion. Pos/SRT00 common translation may drive the root.
- Checks that duplicate tracks cannot overwrite one title pane property.

## Not yet implemented

The title entrance offset (center Y=175.4 DS pixels) remains provisional
because source BCLAN placement and material/texture blending have not been
pixel-verified. Other pane targets and materials are rejected or excluded,
rather than silently interpreted. Original foreground/background texture
bindings and full BCLYT hierarchy for other screens still need actual
runtime integration. This is not original Pokémon skeletal animation or
identical 3DS graphics. The 3DS display is 400x240 top/320x240 bottom,
while DS uses 256x192 per screen.

The private clip compiler is a *local, optional* owner workflow, not a
replacement for asset extraction and reference comparison on a real DS/DSi.
