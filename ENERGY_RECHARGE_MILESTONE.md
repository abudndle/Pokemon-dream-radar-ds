# Energy Recharge gameplay milestone

Fixed: Energy Recharge no longer consumes an item when the capture timer is already at INT_MAX. The gameplay method returns failure without modifying inventory or requesting a save.

Verification: `make test-host test-syntax` passed locally. No BlocksDS ARM toolchain was available in this environment; no compiled or emulator-tested .nds is included.

The 25-second effect remains a prototype value and is not a verified original Dream Radar timing value. Black 2/White 2 retail transfer remains unimplemented.
