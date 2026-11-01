# Milestone #17 — Original NCCH ExeFS 3D banner discovery

## Original game image actually inspected

The previously supplied **decrypted Pokémon Dream Radar NCCH image** was
located among the project's private mounted files and audited directly.
Only verified structural metadata is committed to this public repository.
The **24,944,640-byte source NCCH, its partition contents, banner models,
logo animation files, audio, shaders, and ROM data remain private**.

Run the bounded, read-only audit against your own decrypted image:

```sh
python3 tools/audit_ncch_exefs.py \
  "/private/Pokmon Dream Radar.0(1).ncch" \
  "/private/ncch_exefs_report.json"
```

The verified **metadata-only** aggregate snapshot is
[ORIGINAL_NCCH_EXEFS_AUDIT.json](ORIGINAL_NCCH_EXEFS_AUDIT.json).

## What the original NCCH contains

| Area | Independently checked resources | Interpretation |
| --- | --- | --- |
| ExeFS `banner` | 14 valid LZ11-compressed **CGFX** containers, all with DATA sections and a CMDL signature | Original **Nintendo 3DS Home Menu banner graphics**; *not* confirmed Pokémon encounter meshes |
| ExeFS `banner` | 1 original **CWAV** sound section | Home Menu banner sound, not the whole game audio set |
| ExeFS `logo` | 1 separate LZ11-compressed **DARC**, 16 entries | Nintendo logo UI: 8 BCLIM, 6 BCLAN and 2 BCLYT |
| ExeFS `icon` | SMDH | Home Menu icon metadata |
| ExeFS `.code` | Executable section, 572,840 bytes | ARM executable; no game-model or bone layout decoded here |
| RomFS | 177 CARC archive files beginning with a validated compression header | Already independently decoded into DARC archives in Milestone #16 |
| RomFS | 10 DVLB shader files (`.shbin`) | GPU shader programs, not direct 3D scene/skeleton files |
| RomFS | 20 CSTM streams (`.bcstm`) and 1 CSAR sound archive (`.bcsar`) | Audio resources, not model/animation assets |

**Confirmed extra original 3D container source:** The ExeFS banner uses
Nintendo's `CBMD` format (3DS Home Menu banner model data). Its graphics
slots are LZ11-compressed CGFX. All **14** present entries decoded within
a 512 KiB limit and passed CGFX header, declared-size, section-count and
DATA-section checks. Together these yielded **2,483,968 bytes of private
CGFX container data**, with **14 CMDL four-byte markers**. The latter are
identification hints only: this milestone does **not** parse the complete
mesh dictionaries, vertices, rigs, or original Pokémon animations.

The banner also contains one separately validated CWAV section of
**106,392 bytes**. An additional ExeFS logo entry is an **LZ11-compressed
DARC**, containing a separate set of **16 Nintendo logo UI assets**.
These 16 are **not part of** the previously inventoried 1,462 RomFS DARC
members.

The full standard RomFS directory inventory has **208 files**:
177 CARC, 10 SHBIN, 20 BCSTM, and 1 BCSAR. The 177 CARCs were previously
decoded and classified as the UI/2D resources described in
[ORIGINAL_DARC_MODEL_SEARCH.md](ORIGINAL_DARC_MODEL_SEARCH.md). No
standalone, independently classified Pokémon model or skeletal-animation
file is identified in this **top-level RomFS filename/signature** census.

**Do not confuse these findings:** The existence of genuine CGFX/CMDL
content inside a Home Menu banner does not establish that Pokémon gameplay
models have been found or converted. The banner is a distinct application
asset; the `.code` section and any unknown embedded data remain opaque.

## How the scanner works

The portable, stdlib-only
[`audit_ncch_exefs.py`](../tools/audit_ncch_exefs.py) checks the
original NCCH content length, ExeFS section bounds/overlaps, required
section names and SMDH icon. It then validates CBMD graphics offsets and
CWAV size, decodes bounded LZ11 variants with strict backreference and
output-length checks, and verifies decoded CGFX headers. It also checks
the logo LZ11/DARC directory entries and recognized UI file signatures.

For RomFS, it reads the directory using the existing validated inventory
parser and checks file headers for the known CARC, DVLB, CSTM and CSAR
types, without extracting them. It emits JSON **metadata**, never the
actual CGFX, DARC, audio, code, or proprietary payload bytes.

The GitHub tests use **synthetic** LZ11 streams, CGFX/DATA containers,
CBMD/CWAV banners, and logo DARC fixtures, plus malformed size,
backreference, overlap and header cases. A separate test verifies the
metadata-only real-image aggregate against known counts. The decrypted
game image remains **outside public GitHub and CI**.

These section layout assumptions are consistent with the
[3dbrew CBMD reference](https://3dbrew.org/wiki/CBMD) and the
[Nintendo LZ11 format](https://github.com/magical/nlzss).
All real-image counts above came from the privately held input itself.

## What remains for original Pokémon 3D/animation fidelity

Original Dream Radar encounter models and authentic skeletal motion are
**not yet identified or decoded**. Additional work should:

1. Examine the 3DS game's **executable code and runtime rendering pipeline**
   for geometry generation, procedural sphere effects, embedded resources
   and any externally linked Pokémon sprite/3D libraries, rather than
   assuming that Home Menu banner CMDL is a playable Pokémon model.
2. Parse actual CGFX CMDL geometry only from a verified, relevant source,
   with material/rig and vertex provenance, before targeting DRM1/DRT1/DRK1.
3. Continue precise gameplay and graphics parity tests in a DS emulator
   and on hardware; CI ARM compilation alone does not validate gameplay.

The existing DS port already supports **converted** models and DRA1,
DRB1, DRK1 animation, but this investigation has not imported an authentic
3DS Pokémon gameplay model or decoded genuine native skeletal keyframes.
