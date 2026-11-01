# Linux DS emulator smoke tests and real screenshots

This project now has a **real DeSmuME CLI emulator** boot-and-capture workflow in addition to BlocksDS compilation and host simulation tests. Unlike UI mockups or reconstructed 3DS assets, its PNG files are **captured from the emulator's displayed Nintendo DS dual-screen window** after launching the compiled `dream_radar.nds`.

The automated workflow [`emulator-smoke.yml`](../.github/workflows/emulator-smoke.yml) runs:

- On relevant pull requests and pushes to `main`.
- Every Sunday at 12:30 UTC to provide occasional ongoing emulator checks.
- Manually through GitHub Actions → **Linux DS emulator smoke and screenshots** → **Run workflow**.

## What the test does

GitHub's Ubuntu 24.04 runner installs DeSmuME CLI, Xvfb, X11 input tools, and ImageMagick. It compiles the current Nintendo DS/DSi homebrew ROM with the BlocksDS container, verifies its DS cartridge header, then boots it in a virtual Linux X11 display.

The script [`emulator_smoke.sh`](../scripts/emulator_smoke.sh) captures the **visible emulator window**, not a static design preview:

1. `01-title.png` — initial screen after a short boot period.
2. `02-after-start.png` — screen after attempting the DS Start button.
3. `03-after-a.png` — screen after attempting the DS A button.

The corresponding `runtime.log`, `emulator.log` and machine-readable `report.json` are uploaded alongside the screenshots as the `linux-desmume-real-screenshots` workflow artifact. Even on failure, any existing images and diagnostic logs are uploaded for inspection.

The verifier checks that images are PNG, have plausible dual-screen dimensions, decode to meaningful nonblank pixels, and record image hashes. It reports whether frames differ. **A nonblank image alone cannot prove menu navigation, saved game recovery, camera support, or uninterrupted 60 FPS; the images still require visual review.** Attempted keypresses are not reported as confirmed game-state transitions without visual evidence.

## Run the same test on Linux

A Linux desktop can run it with:

```sh
sudo apt-get update
sudo apt-get install -y desmume xvfb xauth xdotool imagemagick x11-utils

# First build dream_radar.nds with scripts/build_both.sh in BlocksDS.
python3 scripts/check_nds.py dream_radar.nds
xvfb-run -a -s '-screen 0 1024x900x24' \
  bash scripts/emulator_smoke.sh dream_radar.nds emulator-results
```

Then inspect the actual PNG files under `emulator-results/` and read `emulator-results/report.json`.

If DeSmuME fails to boot, doesn't open a window, or produces blank images, **do not replace those captures with fabricated screenshots**. The workflow should fail and preserve the logs, so the runtime problem can be fixed.

## Remaining validation

- Independently boot the exact same ROM in **melonDS** and review the two screens with normal controls.
- Complete menu → radar → shooting → encounter → results → save reload test sequences with actual button input.
- Test DS-only fallback separately from genuine DSi camera/SD features.
- Investigate audio, frame timing and physical hardware compatibility.

This is a Linux emulator smoke milestone, **not a guarantee that the Nintendo 3DS original gameplay has been fully ported**. Only user-owned, private original assets should be supplied via local SD/FAT overrides; the public repository must not receive Nintendo copyrighted game archives.
