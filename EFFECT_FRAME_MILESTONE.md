# Capture effect frame-timing fix

- Freeze now prevents target motion for all 300 frames of its duration. Previously the last frame could move because its countdown was decremented before checking whether the effect was active.
- Slow now tests the pre-decrement state, ensuring all 300 effect frames use slowed movement.
- Added `tests/test_effect_frame_timing.c` to the host test suite. This checks 300 frozen frames followed by resumed motion and exactly 100 movement ticks during a 300-frame slow effect.
- Ran `make test-host test-syntax` successfully. These are host tests and syntax checks only, **not** a DS/DSi ROM build or boot test.
- The effect durations remain prototype values that require verification against original Dream Radar behavior.
