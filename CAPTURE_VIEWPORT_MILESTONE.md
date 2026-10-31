# Capture viewport consistency milestone

Updated `game_tick()` to clamp the moving target to x=20..236 and y=30..164 after each step, and reverse outward movement at the boundary. This corrects a concrete inconsistency where the on-screen sphere could move outside the touchscreen target area for one frame.

Added `tests/test_capture_viewport.c` and wired it into `make test-host`. The test checks edge overshoot, 1000 frames of motion, and short-term freeze behavior. This is a consistency correction, **not** verified reproduction of the original Dream Radar sphere trajectory, capture difficulty, or underlying 3DS code.

A real BlocksDS ARM9 build and DS/DSi emulator or hardware testing remain outstanding, as do complete gameplay and Black 2/White 2 transfer compatibility.
