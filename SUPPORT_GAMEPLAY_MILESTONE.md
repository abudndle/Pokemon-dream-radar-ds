# Support item gameplay consistency milestone

The capture UI now calls `game_use_support()` rather than mutating inventory and effect timers directly. The shared game logic validates the current encounter screen, inventory quantity, and item index; applies freeze/slow effects (300 frames) or a +25-second timer extension; decrements exactly one item only on successful use; and flags save persistence. The timer extension saturates safely rather than overflowing.

A new host regression test validates invalid calls, empty quantities, effect timers, save flags, and timer overflow protection.

## Support availability and feedback milestone (October 31, 2026)

The original three support hexagons now retain their artwork and touch geometry while showing inventory plus a live `READY`, `EMPTY`, `WAIT`, or `ON 5s` status. Freeze and slow countdowns round up to the remaining second and stay visible when the final charge has been used. Radar-mode support taps explain that an active encounter is required; encounter taps report activation, empty stock, or an ongoing effect.

Activation and HUD availability share `game_support_status()`. Freeze and slow cannot be refreshed until all 300 frames expire, preventing an accidental second tap from consuming another charge after just one frame. Energy Recharge still extends the encounter by up to 25 seconds with safe integer saturation. Failed activations do not change saved inventory, timers, or the save-request flag.

Validation: all 27 C host programs, Python regression checks, asset verification, and both DS/DSi syntax checks pass. New regressions attempt reactivation during every remaining effect frame and verify expiration, restocking feedback, final-charge countdowns, label rounding, and read-only HUD queries. The unified BlocksDS ROM compiles and passes its ARM/NitroFS structure check. Pull requests now run the existing build workflow using the same pinned SDK image tested locally.

**Limitations:** Support-effect values are inherited from the prototype and have not been verified against the original game. ROM boot, visual output, DSi camera operation, and physical hardware behavior remain unverified. Black 2/White 2 transfer and complete original animations remain unfinished.
