#ifndef DREAM_RADAR_PHOTO_ALBUM_H
#define DREAM_RADAR_PHOTO_ALBUM_H
#include <stdint.h>
#include <stddef.h>

#define DR_PHOTO_W 256
#define DR_PHOTO_H 192
#define DR_PHOTO_MAX 1000
/* Files produced by the game use standard, uncompressed bottom-up 24-bit BMP.
   The stored pixel format for rendering is DS RGB555 with bit 15 enabled. */
int dr_photo_find(const char *folder, int from, int direction, int *slot_out);
int dr_photo_read(const char *filename, uint16_t *dst, size_t pixel_count);
int dr_photo_write(const char *filename, const uint16_t *src, size_t pixel_count);
int dr_photo_save_new(const char *folder, int *next_slot,
                      const uint16_t *src, size_t pixel_count);
#endif
