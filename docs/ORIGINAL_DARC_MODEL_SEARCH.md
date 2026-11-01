# Milestone #16 — Original Dream Radar DARC model/animation search

## Source material actually inspected

This milestone audited a **privately retained collection of 177 decoded DARC
archives** recovered from earlier project work. Their archive contents were
inspected without extracting or copying the copyrighted payloads into GitHub.

The reproducible, metadata-only aggregate result is in
[ORIGINAL_DARC_ASSET_KIND_AUDIT.json](ORIGINAL_DARC_ASSET_KIND_AUDIT.json).
It is backed by validated DARC entry offsets/sizes, BCLIM footer metadata,
and BCLAN/BCLYT/MSBT format signatures. The original DARC ZIP stays private.

| Original decoded resource type | Validated files | Meaning |
| --- | ---: | --- |
| BCLIM (CLIM footer) | 875 | 2D image/pixel resources |
| BCLAN (CLAN header) | 417 | **UI/pane animation clips**, not Pokémon skeletons |
| BCLYT (CLYT header) | 135 | UI layout/pane hierarchies |
| MSBT (MsgStdBn header) | 35 | Localized message data |
| Independently identified 3D scene/rig candidates | **0** | None among these 1,462 DARC members |

By archive group, the collection includes **99 Obj**, **36 Ui**,
**35 LocalizeTex**, and **7 Message** archives. The label "Obj" is not enough
to infer a 3D model: the verified Obj DARC members are 388 images, 198 UI
animations and 99 layouts. Among the entire 177 archives, no member has an
independently identifiable model/rig extension or a recognized candidate
CGFX/BCH/CSAB/CANM header at the **start** of its payload.

**Limits of this conclusion:** This is a bounded check of this particular
decoded DARC collection. It **does not prove that the original game has no
Pokémon models or skeletal animations**. The assets may be stored in other
non-DARC RomFS files, the executable, an alternate container, or an unknown
encoding. The DARC audit does not reverse-engineer embedded shaders or inspect
arbitrary byte patterns inside compressed images.

## Important parser fix

**170 of the 177 original decoded DARC archives have a legitimate leading
directory entry named "."**. This is a *current-root marker*, not a path
traversal request. The previous DARC parser incorrectly rejected them.

The parser now permits this marker only for a directory at entry index 1 whose
parent is the root. Its name is normalized away when calculating safe paths.
Regular files called ".", any ".." component, nested dot entries, unsafe
separators and malformed directory parents are still rejected. This allows
validated inspection/extraction of the original DARC group without weakening
the private file-extraction path boundary.

## Reproduce the audit using your own private source files

Use the new read-only command with a ZIP of **decoded .darc** files:

\`\`\`sh
python3 tools/audit_darc_asset_kinds.py \
  /private/Dream_Radar_Original_177_DARC_Archives_PRIVATE.zip \
  /private/darc_asset_audit.json \
  --expect-archives 177 --expect-files 1462
\`\`\`

Alternatively, the first argument may be a directory containing decoded
\`.darc\` files. The audit validates actual DARC directory tables and
recognized UI assets, applies archive and byte budgets, rejects ZIP
traversal/symlinks and emits **metadata only**. It does not export original
images or animations. The expected-count switches prevent a partial
collection from being mistaken for this verified 177-archive snapshot.

A 3D candidate identified **by extension or header** is recorded as
\`candidate_only_not_decoded\`; names/magic alone never count as usable
skeletal data. A BCLAN file is always classified as a UI animation and is
never promoted to 3D animation merely because it has keyframes.

CI runs synthetic DARC fixtures and checks the public aggregate report.
The full original archive collection is intentionally **not** in CI or
the public source repository.

## Next original-fidelity work

1. Revisit the decrypted original NCCH at the **RomFS and executable
   file/section level**, outside the 177 already decoded UI DARC archives.
2. Identify a source file containing verifiable 3D geometry/joints/animation,
   with checked file structure—not filename guesses or raw pixel matches.
3. Build an actual native-format decoder or a bounded, validated export
   route into DRM1/DRT1/DRK1, checking original joint and animation fidelity.
4. Profile the resulting assets in a DS emulator and on physical hardware.

The current DS port already has converted DRM1 geometry and DRK1 weighted
animation support, but **no native original 3DS skeletal animation decode
was completed by this milestone**. A successful ARM build remains a
compilation check, not an emulator or hardware playthrough.
