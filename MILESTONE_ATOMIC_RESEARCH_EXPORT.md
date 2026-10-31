# Research export atomic-write milestone

- Research text export now stages to `<destination>.tmp`, checks every output operation, flushes, closes, then renames the staging file over the destination.
- Failed writes or failed renames remove the staging file and do not authorize release of research storage.
- Prior complete archives are not truncated by attempted replacement.
- Added regression coverage for a failing destination rename and cleanup.
- Full `make test-host test-syntax` passed in the current environment. These tests are host-side; they do not establish DS/DSi runtime compatibility.

## Important limits
- These archives are **not** actual Black 2 / White 2 Unova Link transfers; no retail save is modified.
- Some FAT implementations may not support atomic replacement of an *existing* filename with `rename()`; in that case the operation safely fails, preserving the existing archive. Real SD-card testing and an appropriate replacement/backup transaction are still necessary.
- No bootable `.nds` was compiled or hardware-tested in this environment.
