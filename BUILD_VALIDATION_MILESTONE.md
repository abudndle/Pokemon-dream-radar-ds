# Build validation milestone

- Expanded `scripts/check_nds.py` to reject overlapping ARM9/ARM7/FNT/FAT sections, invalid NitroFS FAT lengths, and malformed/out-of-ROM NitroFS file extents.
- Eight generated header fixtures (including valid nonempty file entries) exercise failure and acceptance cases.
- `make test-host test-syntax` passes in the current environment. This does **not** prove the .nds boots.
- Neither the BlocksDS SDK nor the Wonderful ARM toolchain is installed here; no executable ROM is included.
- The original game's gameplay, animations, real camera support, and retail Black 2/White 2 transfer are not complete.

## Build on a BlocksDS-equipped machine

Run `sh scripts/build_both.sh`, then open each resulting `.nds` in melonDS and test on target hardware. Never test save-transfer code against the only copy of a Pokemon save.
