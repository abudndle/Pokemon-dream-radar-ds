#!/usr/bin/env python3
"""Contract tests for independently compiled Nitro Engine/DSMA renderer."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
make = (root / "Makefile.3d").read_text()
main = (root / "source_3d/main.c").read_text()
reuse = (root / "source_3d/game_reuse.c").read_text()
ci = (root / ".github/workflows/nitro-engine-3d.yml").read_text()
ignore = (root / ".gitignore").read_text()

assert 'NAME := dream_radar_3d' in make
assert 'SOURCEDIRS := source_3d' in make
assert 'INCLUDEDIRS := source' in make
assert 'LIBS := -lNE -lnds9 -lc' in make
assert 'SPECS := $(BLOCKSDS)/sys/crts/dsi_arm9.specs' in make
assert 'source/game.c' in reuse and 'source/game.c' not in main
assert 'NE_Init3D()' in main
assert 'NE_ModelLoadDSMFAT' in main and 'NE_ModelDraw(model)' in main
assert 'NE_ModelSetAnimation' in main and 'NE_ModelAnimStart' in main
assert 'NE_AnimationLoadFAT' in main
assert 'NE_CameraUse(camera)' in main
assert 'game_begin_search' in main and 'game_tick(&game)' in main
assert 'game_fire(&game)' in main and 'game_resume_radar(&game)' in main
assert 'nitro:/models/pokemon_%02d.dsm' in main
assert 'nitro:/models/pokemon_%02d_walk.dsa' in main
assert 'NE_ModelCreate(NE_Animated)' in main
assert 'NE_VRAM_AB' in main
assert 'videoSetMode(MODE_5_2D)' not in main
assert 'draw_sprite(' not in main
assert 'nitrofs/models/' in ignore and 'private-3d-assets/' in ignore
assert 'a89917d908e49ab6df1c6762101c240a536bd308' in ci
assert 'Makefile.blocksds' in ci
assert 'make -f Makefile.3d -j2' in ci
assert 'dream_radar_3d.nds' in ci
assert 'dream_radar.nds' not in ci
assert 'persist-credentials: false' in ci
guide = (root / "docs/NITRO_ENGINE_DSMA_3D.md").read_text()
for library in ("#libnds", "#maxmod", "#dswifi", "#libxm7", "#libteak", "#grit"):
    assert "https://blocksds.skylyrac.net/docs/libs/core_libs/" + library in guide
for tutorial in ("intermediate/3d_graphics/", "advanced/advanced_3d/",
                 "intermediate/nitrofs/", "intermediate/filesystems/",
                 "basic/input/", "intermediate/dma/"):
    assert "https://blocksds.skylyrac.net/tutorial/" + tutorial in guide
assert "Do not replace or duplicate the libnds hardware layer" in guide
assert "LibXM7" in guide and "Maxmod" in guide
assert "libteak" in guide and "DSWiFi" in guide
assert "Nitro Engine" in guide and "DSMA" in guide
print("PASS: Nitro Engine + DSMA 3D frontend reuses gameplay and documents verified BlocksDS core libraries")
