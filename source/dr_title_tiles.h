#ifndef DR_TITLE_TILES_H
#define DR_TITLE_TILES_H
#include <stdint.h>
/* User-private 3DS TitleList ListBg00..04 / ListCursor00..04.
 * Original 8x8 RGBA4444 tiles are never committed in this repository.
 * DTT1: magic[4], version LE16=1, count LE16=10, CRC32 LE32 of payload,
 * then 10x64 row-major little-endian RGBA4444 pixels. */
#define DR_TITLE_TILE_COUNT 10
#define DR_TITLE_TILE_SIZE 8
typedef struct {
    uint16_t pixels[DR_TITLE_TILE_COUNT][DR_TITLE_TILE_SIZE*DR_TITLE_TILE_SIZE];
} DrTitleTiles;
/* Atomic strict private-storage loader; retains prior tiles on any error. */
int dr_title_tiles_load(const char *storage_root,DrTitleTiles *tiles);
/* Original window and highlighted cursor, nine-slice retargeted to DS screen.
 * Returns 0 and leaves framebuffer unchanged on invalid geometry. */
int dr_title_tiles_draw(uint16_t *framebuffer,const DrTitleTiles *tiles,
                        int x,int y,int w,int h,int selected);
#endif
