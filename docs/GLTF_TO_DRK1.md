# Milestone #15 — Verified glTF 2.0 export to DRK1 animation bridge

This milestone provides a **strict, deterministic converter for privately exported glTF 2.0 skeletal animations** into the existing DS/DSi-compatible DRK1 format. The goal is to preserve validated joint order, pivots, two-weight assignments and supported Y-axis animation when bringing a *separately exported* model into Dream Radar DS.

**It does not decode the original game's compressed CARC archives, original 3DS model or animation bytecode, or authenticate a glTF export as having come from the game.** The publicly distributed repository does not include Nintendo assets. Existing original-game NCCH tools inventory CARC archives but do not prove that original skeletal tracks have been decoded.

## Single-model conversion

Export your own user-owned rigged model and a **closed-loop animation** as uncompressed glTF 2.0 JSON with embedded base64 or local external binary buffer. Keep a DRM1 mesh exported from the **exact same vertex topology and vertex order**, with identical triangle indices.

Use:

\`\`\`sh
python3 tools/convert_gltf_skin.py \
  --gltf private_exports/pokemon_00.gltf \
  --mesh private_models/pokemon_00.drm \
  --output private_models/pokemon_00.drk \
  --animation 0 --frames 4 --ticks 8 \
  --report private_models/pokemon_00_retarget_report.json
\`\`\`

The output \`pokemon_00.drk\` can be placed with the corresponding \`pokemon_00.drm\` under \`sd:/DreamRadarDSi/Models/\`, the flashcart \`fat:/DreamRadarDSi/Models/\`, or a private NitroFS build. The existing encounter renderer automatically loads a validated DRK1 file. Textured and flat-color renderer fallbacks remain unchanged.

**Timing:** Source clips are resampled uniformly to 2–8 poses (4 by default). The DS playback period is \`frames × ticks\` game frames, **not** automatically the source glTF duration. For approximate 60 Hz playback timing, select \`ticks ≈ (source duration in seconds × 60) / frames\`, clamped to the supported integer range 1–60. The conversion is intentionally lossy.

## Batch conversion for up to 26 Pokémon

If you privately exported matching pairs \`pokemon_00.gltf\`...\`pokemon_25.gltf\` and \`pokemon_00.drm\`...\`pokemon_25.drm\`:

\`\`\`sh
python3 tools/stage_gltf_animations.py \
  private_gltf_folder/ private_drm_folder/ private_output/ \
  --frames 4 --ticks 8 --animation 0
\`\`\`

This processes only exact names \`pokemon_00.gltf\` through \`pokemon_25.gltf\`. It validates *all* available pairs before writing any DRK1 output. A missing/malformed pair fails the batch without touching previously staged files. The metadata-only \`gltf_animation_manifest.json\` records filenames, vertex counts, bone counts and size without embedding copyrighted source assets. It does not claim that all 26 models are available or converted unless they really exist in your private inputs.

## Strictly supported glTF subset

The bridge intentionally rejects unsupported features rather than silently corrupting Pokémon geometry or animation:

- **glTF 2.0 \`.gltf\` JSON only**, exactly one uncompressed skinned triangle primitive, at most 2,048 vertices and 2,048 triangles. \`.glb\`, Draco compression, morph targets, required extensions and multiple mesh primitives are not supported.
- **Vertex-for-vertex matching**: POSITION coordinates after Q12 quantization must match the supplied DRM1 mesh within one fixed-point unit; triangle index array and winding must match exactly. If your exporter splits vertices at UV seams or reorders triangles, re-export DRM1 from the same unified topology. The tool never guesses a vertex correspondence.
- **Joint hierarchy**: one skin with up to 16 joints. Parent joints are sorted before children. Parent nodes outside the selected skin, cycles, non-identity rest rotations, non-unit scales and matrix transforms must be baked prior to conversion. Neutral inverse bind matrices must describe translation-only Q12 pivots when present.
- **Skin weights**: JOINTS_0 and WEIGHTS_0 only; each vertex needs one or two positive influences, normalized to sum approximately 1. Quantization stores weight A in the existing 0–255 DRK1 format. Joint order is mapped to new parent-first indices; topology and UV index lookup are never changed.
- **Animation**: joint translation and normalized pure-Y quaternion rotation only. Supports LINEAR and STEP samplers with strictly increasing timestamps. Rejects X/Z rotations, arbitrary bone scales, morph weights and CUBICSPLINE tracks instead of dropping them. Every motion must return to its starting transform at the end, avoiding an unintentional loop seam. Source animation length must be greater than zero and no more than 60 seconds.
- **Translation limits**: relative-to-rest position changes must fit a signed 8-bit displacement at 1/256 model unit increments, approximately -0.5 to +0.496 model units. Original animation requiring larger movement needs private asset scaling or a future DRK2 format.
- **Input safety**: bounded JSON/binary payloads, exact glTF accessor and bufferView checks, no sparse accessors, no dangerous external file URIs, no directory escape and no runtime web access.

The converter uses only Python's standard library. The game uses DRK1 as before; no additional ARM runtime modules are needed for this bridge.

## What was and wasn't verified

The converter's unit tests generate a synthetic two-joint skinned glTF model with inverse bind matrices, joint indices deliberately **out of parent order**, a two-influence seam, and a looping animated child. They verify the exact DRK1 layout, joint mapping, keyframe resampling, malformed input rejection, path confinement, and deterministic output. Batch tests verify correct species names and reject-before-write handling. Existing DRK1 C regression tests still validate on-device format decoding and rendering compatibility.

**No actual Pokémon skeletal animation from the decrypted 3DS game was newly decoded or matched in this milestone. No real DS emulator or hardware model-performance measurements are claimed.** The next work is to decode verified original CARC model/animation payloads and map their channels to supported glTF or directly to an expanded DS intermediate format, especially for multi-axis rotations and original skinning weights.

glTF input interpretation references the official [Khronos glTF 2.0 specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html).
