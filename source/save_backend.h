#ifndef DREAM_RADAR_SAVE_BACKEND_H
#define DREAM_RADAR_SAVE_BACKEND_H
#include "game.h"
#include "twilight_saves.h"

typedef struct {
    char active[TW_MAX_PATH];
    char legacy[TW_MAX_PATH];
    int using_twilight_path;
    int migrated_legacy;
    int recovered_backup; /* Valid .bak was loaded after main save failed validation. */
} SaveBackend;

/* Works with real SD prefixes such as sd:/ and host test paths. */
int save_backend_init(SaveBackend *backend,const char *root,const char *rom_path);
int save_backend_load(SaveBackend *backend,Game *g);
int save_backend_write(SaveBackend *backend,Game *g);
#endif
