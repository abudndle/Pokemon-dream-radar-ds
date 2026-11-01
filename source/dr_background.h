/* Transactional camera-free placeholder selection, portable for host tests.
 * User-controlled BMPs stay on the private SD/FAT volume. */
#ifndef DR_BACKGROUND_H
#define DR_BACKGROUND_H
#include "game.h"
#include <stddef.h>
#include <stdint.h>
#define DR_BACKGROUND_IMPORT_MARKER 0xB7
/* Import fixed DreamRadarDSi/placeholder.bmp. Failure preserves framebuffer,
 * saved preference, camera switch, and runtime image metadata unchanged.
 * The Game and output parameters must be distinct valid objects. */
int dr_background_import(const char *storage_root,uint16_t *pixels,size_t count,
                         Game *game,int *loaded,int *slot);
/* Restore only the imported marker without mutating persistent save state.
 * Missing/broken file leaves caller's framebuffer and metadata untouched. */
int dr_background_restore(const char *storage_root,uint16_t *pixels,size_t count,
                          const Game *game,int *loaded,int *slot);
/* Switch to bundled camera-free default, leaving the user's file untouched. */
void dr_background_reset(Game *game,int *loaded,int *slot);
#endif
