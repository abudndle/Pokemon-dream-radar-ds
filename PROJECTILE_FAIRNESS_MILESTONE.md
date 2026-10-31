# Milestone: Legendary projectile collision fairness

The preceding milestone introduced three simultaneous independently targetable
energy balls. This follow-up fixes overlapping-projectile behavior:

- At most one timer penalty applies in a frame, even when three balls overlap.
- Other energy balls remain active, independently shootable on later frames.
- One beam defense shot targets the nearest ball (not the first array slot).
- No new volley spawns during the frame of a projectile impact.
- `tests/test_projectile_fairness.c` runs through `make test-host`.
- Pull requests run automated host tests and native BlocksDS build checks.

These changes improve the DS port's provisional gameplay; they do not prove
exact original 3DS species patterns or timing. Original animations, camera,
Black 2/White 2 transfer and emulator/hardware verification remain incomplete.
