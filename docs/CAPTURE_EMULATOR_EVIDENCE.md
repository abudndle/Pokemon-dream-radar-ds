# Live melonDS capture evidence (issue #66)

The capture milestone must not be closed on host tests, menu-navigation
screenshots, or a hand-written JSON report alone. The audit now requires a
bundle of real PNG files with matching SHA-256 hashes and a melonDS runtime
log. **This is a structural/provenance gate, not computer-vision verification
of gameplay or proof of original 3DS parity.** Reviewers still need to inspect
the actual screenshots and emulator interaction logs.

## Verified ERRATIC screenshot classifier gap (2026-11-02)

An actual Linux melonDS run (Actions #41384327262) reached a live
ERRATIC sphere after independently verifying **0 → 2 saved Dream Orbs**.
The first sphere-aim plan failed before any guided shot. The retained
`05-sphere-before-1.png` shows a compact lavender encounter sprite:
x=89–109, top-screen y=57–75, with many RGB (211,178,243) pixels.
That palette fails both the prior dark/saturated and pale-pink
thresholds. The updated fallback-only classifier adds a bounded violet
component pass, retaining flat-backdrop validation and multi-target
ambiguity rejection. Synthetic regressions cover shape, movement,
tiny HUD glyphs and two distinct silhouettes.

The screenshot demonstrates an encounter and a **classifier root cause**,
not a completed capture. A successful host classifier test alone cannot
establish live guided aim, meter progress, reward or restart persistence.
Do not commit the emulator screenshot or proprietary source assets to
public code; preserve screenshot evidence in the separate CI artifact.

## Expected evidence directory

```text
capture-evidence/
  capture-report.json
  runtime.log
  cloud_search.png
  cloud_shot.png
  orb_collected.png
  sphere_encounter.png
  capture_reward.png
  results.png
  resume_radar.png
  save.png
  restart.png
  restored_reward.png
```

Capture each screenshot from the actual emulator window at the named stage,
not from the DS source assets or a simulated host renderer. Each PNG must be
an unscaled 256-pixel-wide vertical DS window, 384–480 pixels tall,
and contain complete, decodable PNG scanlines with valid checksums and filters. The runtime log must
contain the emulator name and window ID, as recorded by
`scripts/melonds_smoke.sh`. The smoke script alone **does not** produce the
full capture evidence: its navigation screenshots are insufficient.

## Screenshot-guided cloud acquisition (DS fallback only)

The smoke runner now distinguishes two visual signals from actual melonDS
frames. A magenta-shadow cloud is a possible hittable target. An 11×11 gold
direction marker at the edge of the radar viewport is **not** a cloud: it
means a target is currently offscreen. The runner may move the D-pad toward
that marker, but must reacquire visible cloud pixels and confirm the target
is within 14 pixels of the reticle in a **fresh pre-fire screenshot** before
pressing A. The 7×7 offscreen Dream Orb marker and gold HUD elements are
not accepted as clouds. Eight bounded retry acquisitions handle clouds
temporarily outside the viewport.

The runner saves `05-radar-prefire.png`, `cloud-fire-check.json` and
`05-radar-retry-*-prefire.png` with corresponding per-retry JSON checks.
An absent cloud, marker-only frame, or unaligned target is a warning and
**skips the shot**, never a successful hit. A visible cloud and an A-button
input are still insufficient proof: compare independently decoded cloud
counters or a recognized sphere transition in subsequent screenshots.
The color/geometry heuristic is specific to the public DS fallback
renderer; it does not recognize original 3DS sprites or establish parity.

## Persistent Dream Orb collection evidence

The radar's `ORBS` counter counts **currently active** objects, not saved
currency. Those objects expire after 210 gameplay frames, so a decrease
from 3 to 2 after pressing A does **not** prove an Orb was collected.
The navigation report now records such changes as
`orb_count_decreased_unattributed`, with
`orb_collection_observed: false`.

The melonDS smoke runner now also visits the Development Lab shop before
and after the radar outing. It decodes the shop's gold
`Development Lab  ORBS <balance>` label from native screenshot pixels
and writes `orb-balance-before.json`, `orb-balance-after.json`, and
`orb-balance-change.json`. Only an independently verified increase in
this saved balance earns `orb_collection_observed: true`. The test route
does not buy upgrades or spend Orbs between observations. An unreadable
shop screenshot leaves collection **unverified** rather than assuming
success.

`REQUIRE_ORB_COLLECTION=1` (or the matching manual workflow input) fails
the run unless the saved balance increased. The default run remains
non-strict to permit navigation diagnostics when Orbs expire. This is
still not proof of persistence after an emulator restart. The moving-Orb
planner can use two consecutive screenshots only when the D-pad is
stationary between them, and a fresh observed frame—not predicted
position—must authorize firing.

### Four-color Orb targeting (DS fallback)

The screenshot-guided Orb planner recognizes all four **runtime** RGB555
fills from `source/main.c`: pink `0xC1DF`, green `0x83E0`, orange
`0x829F`, and blue `0xFC00`. Orbs can change color while the runner
moves the D-pad or samples consecutive frames; the previous pink-only
classifier could lose a real target at a color transition. Separate color
components and conservative size bounds reduce accidental matches to
small HUD glyphs. This is a test of the DS adaptation, not extraction of
the original game's textures or motion rules.

A detected Orb, a guided aiming plan, or a disappearing Orb does **not**
prove collection. Only the independently decoded before/after saved
shop balance can establish a collected Orb for this smoke route, and a
subsequent emulator restart is still required to prove persistence.
The palette matcher is intentionally limited to the unscaled fallback
renderer and may fail when the reticle obscures a sprite.

### Bounded live Orb prefire observation

The runner may inspect up to five **fresh, stationary** Orb screenshots after
its directional corrections. Each observation gets its own PNG and
`orb-fire-check-<sample>.json`; an A-button shot is permitted only when
that very frame's planner reports `within_safe_fire_radius: true`.
This addresses a real melonDS trace in which the final Orb was still
25 pixels from the reticle after three correction passes. No stationary
sample, no prediction, and no change to the active-Orb counter is accepted
as proof of a collected Orb. An unreadable or unaligned sample causes no
shot; the window is capped to avoid indefinite searching.

## Optional live encounter instrumentation

The Linux melonDS smoke workflow now tries screenshot-guided aiming on the
known flat DS fallback scene and a bounded A-button shooting sweep after an
actual sphere encounter. It records `05-sphere-sweep-*.png` and
`sphere-progress-*.json` for the visible capture meter. Only a Results
screen with an independently recognized `Caught: <catalog species>` or
`Item: <catalog item>` label earns a `05-capture-reward.png` and
`sphere-reward.json`. A generic Results heading, a moving target, or a
partially filled meter is **not** a successful capture.

Use `REQUIRE_CAPTURE=1` to turn a missing reward into a failing emulator
acceptance test. The default smoke run remains non-strict because the live
target moves and the fallback artwork is not consistently recognizable.
Even a strict capture pass does **not** establish save/restart persistence;
that requires the separate `save`, `restart` and `restored_reward`
screenshots plus independent saved-data checks. The moving target is now recognized by its high-contrast, colored
artwork rather than the large **static white cloud** in the DS background.
A small red hostile projectile (13×13) must not be mistaken for encounter
art. Unknown or original textured backgrounds intentionally skip tracking
instead of inventing a target. This is DS fallback verification, not DSi
camera hardware testing.


```json
{
  "emulator": "melonDS",
  "test_kind": "live_emulator_capture",
  "commit_sha": "0123456789abcdef0123456789abcdef01234567",
  "rom_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "runtime_log": {
    "path": "runtime.log",
    "sha256": "<actual SHA-256 of runtime.log>"
  },
  "stages": {
    "cloud_search": true,
    "cloud_shot": true,
    "orb_collected": true,
    "sphere_encounter": true,
    "capture_reward": true,
    "results": true,
    "resume_radar": true,
    "save": true,
    "restart": true,
    "restored_reward": true
  },
  "captures": {
    "cloud_search": {
      "path": "cloud_search.png",
      "sha256": "<actual SHA-256 of cloud_search.png>"
    }
  }
}
```

The `captures` map must contain an entry for **each** stage, not just the
single entry shown in the abbreviated example. Every path is relative to the
evidence directory and must stay within it (symlink escapes are rejected).
The ten stages must include at least four distinct decoded-frame fingerprints.
The validator reverses PNG row filters before fingerprinting, so re-encoding
one frame with different filter types, compression or metadata does not count
as new gameplay evidence. File SHA-256 still independently authenticates each
artifact's bytes. A fingerprint is not scene recognition; distinct images can
still be fabricated, so independently inspect gameplay and restart behavior.
Each stage value must be the JSON boolean `true`, not a number or string.

Generate hashes using `sha256sum capture-evidence/*.png
capture-evidence/runtime.log dream_radar.nds`. Use the SHA-256 of the ROM
built from the exact `commit_sha` being tested; preserve the ROM artifact
separately so reviewers can independently verify that assertion.

Run the structural gate with:

```sh
python3 tools/audit_capture_milestone.py --emulator-evidence capture-evidence
python3 tests/test_capture_emulator_evidence.py
```

A passing audit means the evidence files exist, their hashes match, and
their basic PNG/log structure is acceptable. It **does not** establish that
the screenshot contents match their stage labels, that a real capture
succeeded, that a restart preserved rewards, or that a DSi camera or retail
Black 2/White 2 transfer worked. Keep those acceptance items open until
reproducible live interaction and independent review confirm them.

Never include private Nintendo 3DS ROM, NCCH, RomFS, or extracted copyrighted
assets in the evidence bundle or public workflow artifacts.
