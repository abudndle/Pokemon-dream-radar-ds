#ifndef DREAM_RADAR_TWILIGHT_SAVES_H
#define DREAM_RADAR_TWILIGHT_SAVES_H

/* Portable, read-only TWiLight Menu++ retail-save discovery.
 * App saves are a separate format and are NEVER injected into retail saves.
 */
#include <stddef.h>
#include <stdint.h>
#include "game.h"

#define TW_MAX_ENTRIES 32
#define TW_MAX_PATH 320

typedef enum {
    TW_SAVE_NONE=0, TW_SAVE_NEXT_TO_ROM=1, TW_SAVE_GAME_FOLDER=2,
    TW_SAVE_TWLMENU_FOLDER=3
} TwilightSaveLocation;

typedef struct {
    char rom_path[TW_MAX_PATH];
    char save_path[TW_MAX_PATH];
    char game_code[5];
    CartGame game;
    TwilightSaveLocation location;
    uint32_t save_size;
    uint32_t save_fingerprint; /* Read-only sample digest to catch unchanged-size replacements. */
    uint8_t save_slot; /* 0 = .sav; 1..9 = .sav1 .. .sav9 */
} TwilightSaveEntry;

typedef struct {
    TwilightSaveEntry entries[TW_MAX_ENTRIES];
    unsigned count;
    unsigned with_saves;
    unsigned dirs_scanned;
    unsigned truncated;
} TwilightSaveIndex;

/* 'root' is 'sd:/' on DSi, or a regular host folder for tests.
 * 'rom_dir' may be NULL; if provided it is scanned first. No retail file writes. */
void twilight_scan(TwilightSaveIndex *idx, const char *root, const char *rom_dir);

/* Constructs a private, launcher-adjacent .sav for this HOMEbrew's own SaveData,
 * not a Pokémon retail save. Only works with an .nds/.dsi/.srl/.app argv[0]. */
int twilight_homebrew_save_path(const char *rom_path, char *out, size_t cap);

/* Exact currently supported save-extension/size/path checks. */
int twilight_is_supported_rom(const char *name);
int twilight_read_nds_code(const char *rom_path, char out[5]);
/* Verify the selected ROM and save still match before activation. Read-only. */
int twilight_validate_entry(const TwilightSaveEntry *entry);

#endif
