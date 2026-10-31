# Milestone #14 — DRK1 hierarchical, two-weight Pokémon animation

DRK1 is a compact, *user-converted* hierarchical skinning format for the Dream Radar DS/DSi prototype. It supports parent-child bone transforms, up to two influences per mesh vertex, interpolated local yaw and XYZ translation, and compatibility with the existing DRM1 model, DRT1 texture, and depth-tested software renderers.

**This is not an importer for original 3DS skeletal animation, shaders, bone data, or copyrighted files.** No original Nintendo assets are included in this GitHub repository. Actual 3DS model/keyframe conversion and accurate retargeting remain unfinished.

## File naming and rendering priority

For a model index `00`–`25`, place `pokemon_00.drk` alongside its **matching** `pokemon_00.drm` (and optional `pokemon_00.drt`).

- On supported SD storage: `sd:/DreamRadarDSi/Models/pokemon_00.drk`
- On supported flashcart storage: `fat:/DreamRadarDSi/Models/pokemon_00.drk`
- In your own private NitroFS build: `nitro:/pokemon_00.drk`

Every sidecar is loaded from the same source as its validated DRM1 mesh. Runtime priority is:

**Valid DRK1 weighted hierarchy → valid DRB1 rigid parts → valid DRA1 vertex keys → static DRM1 spin → 2D Pokémon artwork when no mesh exists.**

Only one animation representation is loaded per species at a time, and it is freed on species change. Item encounters continue to display their existing 2D icons. No added data is committed to GitHub.

## Binary layout

Little-endian, exact-length format. All reserved bytes must be zero.

| Offset | Bytes | Meaning |
| --- | --- | --- |
| 0 | 4 | ASCII `DRK1` |
| 4 | 2 | DRM1 vertex count, 3–2048, **exact match** |
| 6 | 1 | Bone count, 1–16 |
| 7 | 1 | Number of keyframes, 2–8 |
| 8 | 1 | Ticks/keyframe, 1–60 |
| 9 | 1 | Reserved, must be 0 |
| 10 | 8 × bones | Bone definitions: signed Q12 `i16 pivot_x, pivot_y, pivot_z`, `u8 parent`, `u8 reserved=0` |
| After bones | 3 × vertices | Each vertex: `u8 bone_a, bone_b, weight_a` |
| After influences | 4 × frames × bones | Frame-major, then bone-major: signed `i8 tx,ty,tz,yaw` |

The exact file size is **10 + 8×bones + 3×vertices + 4×frames×bones**. Maximum is **6,794 bytes** with 2,048 vertices, 16 bones and eight frames. The runtime also stores one scratch mesh (12 KiB for the maximum model), original topology references, and small bone/keyframe arrays, without allocating on each frame.

**Bone definitions:** Neutral pivots are absolute Q12 positions in the original DRM1 geometry. A parent value of 255 means a root; otherwise it must be strictly less than the child index, allowing multiple roots and preventing cycles. Local translation uses the same 1/256 model-unit (Q12/16) scale as DRB1. Local yaw uses a signed byte with 256 steps per full turn. Child pivots move with parent rotations/translations, and child yaw adds to inherited parent yaw.

**Vertex blending:** Two valid bone IDs are recorded for each original vertex. The first influences `weight_a/255` and the second `(255-weight_a)/255`. Use `[bone,bone,255]` for rigid attachment. Two influences blend independently transformed positions, which can soften seams relative to DRB1 rigid parts. Normalized integer arithmetic and final signed-int16 clamping bound all output. This is *linear blend skinning*, not 3DS-complete skinning: only a single local yaw axis is supported and rotations are interpolated in a compact 256-step representation.

**Playback:** Each bone pose interpolates linearly in integer arithmetic to the next pose; yaw follows the shortest circular direction, including the final-to-first transition. Timeline loops without drift. Existing DRM1 vertex IDs, triangles, and DRT1 UV indices remain unchanged, enabling both existing software renderers.

## Pack a private user-owned rig

Create a UTF-8 JSON rig and motion description. For example, the following is **only for a hypothetical six-vertex mesh**:

```json
{
  "bones": [
    {"pivot": [0,0,0], "parent": -1},
    {"pivot": [4096,0,0], "parent": 0}
  ],
  "influences": [
    [0,0,255], [0,0,255], [0,0,255],
    [1,1,255], [1,1,255], [0,1,128]
  ],
  "frames": [
    [[0,0,0,0], [0,0,0,0]],
    [[0,0,0,64], [0,64,0,64]]
  ]
}
```

One influence triple is required for **every** vertex of your actual DRM1 mesh, in exact vertex order. Then run:

```sh
python3 tools/pack_drk1.py --mesh pokemon_00.drm \
  --skin-json pokemon_00_skin.json --ticks 4 \
  --output pokemon_00.drk
```

For a **demonstration only** (invented tail/wing wag), you may use `--demo-tail-wag` to generate four keyframes rotating bone index 1. You must still provide appropriate pivots and influences; this option cannot automatically identify anatomical parts:

```sh
python3 tools/pack_drk1.py --mesh pokemon_00.drm \
  --skin-json pokemon_00_skin.json --demo-tail-wag --ticks 8 \
  --output pokemon_00.drk
```

Converted model files, original texture files and genuine original game animations must remain in private storage unless you have distribution rights.

## Verification and outstanding work

Host tests cover strict file length, hierarchy integrity, invalid parents, invalid influences, two-weight interpolation, inherited transforms, looping, rotation wrap, signed coordinate clamping, atomic replacement, file IO, and compatibility with both model renderers. A successful BlocksDS build proves **compilation only**, not hardware speed, DS emulator boot or original 3DS feature parity.

**Unfinished:** Original 3DS skeletal asset decoding, genuine joint and weight extraction, quaternion/multi-axis interpolation, real material animation, performance profiling on DS/DSi, and end-to-end original-game accuracy.
