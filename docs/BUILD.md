# Building Pokémon Dream Radar DS/DSi

## Toolchain

The project uses BlocksDS with the Wonderful toolchain. The default Makefile expects:

- BlocksDS at `/opt/wonderful/thirdparty/blocksds/core`
- Wonderful toolchain at `/opt/wonderful`
- Docker for the reproducible CI build, or the equivalent local BlocksDS environment

Override `BLOCKSDS` and `WONDERFUL_TOOLCHAIN` if your installation uses different paths.

## Host validation

Run:

```sh
make test-host test-syntax
python3 tests/test_nds_header.py
python3 tools/verify_assets.py
```

## ROM build

Build both DS and DSi variants with:

```sh
make build-all
```

The generated ROMs are build products and are ignored by Git. CI publishes them as test artifacts only; they are not proof of hardware compatibility. Review the BlocksDS and melonDS workflow logs before calling a build verified.

## Emulator testing

Use the repository's `scripts/melonds_smoke.sh` and `scripts/build_both.sh` scripts where their documented dependencies are available. Retain screenshots, runtime logs, navigation reports, and capture/reward evidence as CI artifacts. Do not claim a capture or save/restart milestone from a successful boot alone.

## DSi hardware

A desktop emulator cannot prove camera access, SD/photo album behavior, or real DSi mode detection. Test those features on actual DSi hardware and record the hardware model, firmware, ROM hash, and steps performed.

## Proprietary inputs

Do not commit retail ROMs, NCCH/CCI/CIA files, decrypted RomFS/ExeFS, copyrighted archives, or extracted proprietary source files. Store authorized inputs in a private local workspace and use the project's validation scripts to verify them without uploading their contents.
