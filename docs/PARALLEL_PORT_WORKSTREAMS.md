# Dream Radar DS — parallel port integration plan

Primary integration PR: #57. All five tracks are open and may proceed independently. **Issues do not automatically run coding agents.**

| Track | Issue | Main outputs | Acceptance gate |
| --- | --- | --- | --- |
| Private original assets | #62 | Deterministic conversion manifest, title/menu art, meshes, rigs, animations, audio | Private extraction inputs validated; converted output hashes and visual comparisons |
| Gameplay parity | #63 | Cloud search, sandbox projectiles, orb pickup, sphere capture, rewards, story and upgrades | Portable host acceptance plus live melonDS encounter test |
| Renderer, input, DSi | #64 | DS VRAM renderer, stylus/A, D-pad fallback, DSi camera | DS build, live input verification, DSi-only hardware check |
| Persistence and transfer | #65 | Save/restore previous screen, rewards, corruption recovery, transfer investigation | Save/restart integration, confirmed protocol evidence before compatibility claim |
| Build and release | #66 | BlocksDS ROM, Linux melonDS run, screenshots, logs, release package | Reproducible build, 10-stage live capture evidence, source/release provenance |

## Execution

1. Each track uses a separate Git branch and PR to avoid concurrent edits to `source/game.c` and `source/main.c`.
2. Asset conversion and renderer work must agree on memory and texture contracts before integration. Keep copyrighted 3DS assets in the owner's private workspace, never in public Git history.
3. Gameplay and persistence can share test fixtures, but each branch must pass `make test-host test-syntax` before merge.
4. The build/test track continuously integrates approved changes into PR #57 and runs real melonDS checks. External emulator screenshots are allowed; **do not implement in-game screenshot capture**.
5. A green host test is not a green emulator test. The ten-stage capture acceptance gate remains open until independently verified from a real emulator session.
6. Actual Pokémon Black 2/White 2 transfer support requires verified protocol implementation, not a custom text export.

## Integration blockers

- Original decrypted NCCH files and extracted copyrighted assets must be accessible privately to the converter.
- BlocksDS, melonDS, and DSi camera-capable test hardware/emulation must be available for final verification.
- Workstream issues currently have no assigned autonomous coding worker; creation of issues is planning, not completed implementation.

## Definition of done

An actual DS/DSi ROM boots; the original title and interfaces render using authorized converted assets; cloud discovery precedes encounters; rewards and story progression persist across restart; gameplay and controls function on DS and DSi; original animation/audio have been evaluated and ported within hardware constraints; transfer compatibility claims are substantiated; and all acceptance artifacts are attached to the integration PR.
