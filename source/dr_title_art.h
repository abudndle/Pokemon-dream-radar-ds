#ifndef DR_TITLE_ART_H
#define DR_TITLE_ART_H
#include <stddef.h>
#include <stdint.h>
/* Load a matched pair of user-owned original 3DS title background adaptations.
 * Strict opaque RGB555 256x192, no header/trailer. Both output buffers remain
 * untouched if either file is invalid. Never touches a commercial game save. */
int dr_title_art_load(const char *storage_root,uint16_t *top,
                      uint16_t *bottom,size_t pixel_count);
#endif
