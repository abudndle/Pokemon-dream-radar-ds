# Pokémon Dream Radar DSi — BlocksDS ARM9 project.
# Use the maintained SDK make rules, not hand-written GCC/linker commands.
BLOCKSDS ?= /opt/wonderful/thirdparty/blocksds/core
WONDERFUL_TOOLCHAIN ?= /opt/wonderful
HOSTCC ?= gcc
# One DSi-enhanced ROM: runtime isDSiMode() selects DS fallback or DSi features.
NAME := dream_radar
GAME_TITLE := Dream Radar
SPECS := $(BLOCKSDS)/sys/crts/dsi_arm9.specs
GAME_SUBTITLE := Unofficial homebrew demake
GAME_AUTHOR := Built with BlocksDS
GAME_ICON := icon.png
SOURCEDIRS := source
NITROFSDIR := nitrofs

.PHONY: test-host test-syntax check-sdk dialogue assets item-catalog burnet-tips build-all
# Host targets must work even if the cross-compiler and SDK aren't installed.
ifneq ($(filter test-host test-syntax check-sdk dialogue assets item-catalog burnet-tips build-all,$(MAKECMDGOALS)),)
else
include $(BLOCKSDS)/sys/default_makefiles/rom_arm9/Makefile
endif

check-sdk:
	@test -f "$(BLOCKSDS)/sys/default_makefiles/rom_arm9/Makefile" || (echo "BlocksDS SDK not installed: $(BLOCKSDS)"; exit 1)
	@test -f "$(SPECS)" || (echo "ARM9 specs missing: $(SPECS)"; exit 1)
	@test -x "$(WONDERFUL_TOOLCHAIN)/toolchain/gcc-arm-none-eabi/bin/arm-none-eabi-gcc" || (echo "Wonderful ARM GCC not installed"; exit 1)
assets:
	python3 tools/build_assets.py
	python3 tools/build_reference_ui.py
	python3 tools/build_cloud_transfer_assets.py
dialogue:
	python3 tools/build_dialogue.py
item-catalog:
	python3 tools/build_item_catalog.py
burnet-tips:
	python3 tools/build_burnet_tips.py

test-syntax:
	$(HOSTCC) -std=gnu11 -Wall -Wextra -Werror -fsyntax-only -Isource -Itests/host_nds source/main.c

build-all:
	sh scripts/build_both.sh

test-host:
	@mkdir -p build
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/cloud_animation.c tests/test_cloud_animation.c -o build/test_cloud_animation
	./build/test_cloud_animation
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c tests/test_capture_expiry.c -o build/test_capture_expiry
	./build/test_capture_expiry
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c tests/test_legendary_escape.c -o build/test_legendary_escape
	./build/test_legendary_escape
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c tests/test_capture_timeout_policy.c -o build/test_capture_timeout_policy
	./build/test_capture_timeout_policy
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c tests/test_encounter_types.c -o build/test_encounter_types
	./build/test_encounter_types
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c tests/test_cloud_recharge.c -o build/test_cloud_recharge
	./build/test_cloud_recharge
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c tests/test_cloud_targeting.c -o build/test_cloud_targeting
	./build/test_cloud_targeting
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c tests/test_effect_frame_timing.c -o build/test_effect_frame_timing
	./build/test_effect_frame_timing
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c tests/test_orb_overflow.c -o build/test_orb_overflow
	./build/test_orb_overflow
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c tests/test_empty_cloud_search.c -o build/test_empty_cloud_search
	./build/test_empty_cloud_search
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c tests/test_support_gameplay.c -o build/test_support_gameplay
	./build/test_support_gameplay
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c tests/test_capture_viewport.c -o build/test_capture_viewport
	./build/test_capture_viewport
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c tests/test_logic.c -o build/test_logic
	./build/test_logic
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c source/twilight_saves.c source/save_backend.c tests/test_twilight.c -o build/test_twilight
	./build/test_twilight
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c source/twilight_saves.c source/save_backend.c tests/test_recovery.c -o build/test_recovery
	./build/test_recovery
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c tests/test_archive.c -o build/test_archive
	./build/test_archive
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c tests/test_storage_replace.c -o build/test_storage_replace
	./build/test_storage_replace
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c tests/test_item_catalog.c -o build/test_item_catalog
	./build/test_item_catalog
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource tests/test_burnet_tips.c -o build/test_burnet_tips
	./build/test_burnet_tips
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/photo_album.c tests/test_photo_album.c -o build/test_photo_album
	./build/test_photo_album
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/platform_compat.c tests/test_platform_compat.c -o build/test_platform_compat
	./build/test_platform_compat

	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/game.c tests/test_original_limits.c -o build/test_original_limits
	./build/test_original_limits
	$(HOSTCC) -std=gnu11 -O2 -Wall -Wextra -Werror -Isource source/reference_layout.c source/game.c tests/test_reference_layout.c -o build/test_reference_layout
	./build/test_reference_layout
	python3 tests/test_title_asset_geometry.py
	python3 tests/test_original_pane_geometry.py
	python3 tests/test_pane_retarget.py
	python3 tests/test_nds_header.py
	python3 tools/verify_assets.py
