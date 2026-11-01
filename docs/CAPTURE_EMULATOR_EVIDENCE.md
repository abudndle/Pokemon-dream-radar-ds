# Live melonDS capture evidence (issue #66)

The capture milestone must not be closed on host tests, menu-navigation
screenshots, or a hand-written JSON report alone. The audit now requires a
bundle of real PNG files with matching SHA-256 hashes and a melonDS runtime
log. **This is a structural/provenance gate, not computer-vision verification
of gameplay or proof of original 3DS parity.** Reviewers still need to inspect
the actual screenshots and emulator interaction logs.

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
