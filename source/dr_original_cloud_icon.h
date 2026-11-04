#ifndef DR_ORIGINAL_CLOUD_ICON_INCLUDED
#define DR_ORIGINAL_CLOUD_ICON_INCLUDED
#include <stdint.h>

/* Optional private 3DS UI resource: the 64x32 source-derived TitleCloudCount
 * icon. Original Nintendo pixels stay outside the public source repository. */
#define DR_ORIGINAL_CLOUD_ICON_W 64
#define DR_ORIGINAL_CLOUD_ICON_H 32
typedef struct {
    int loaded;
    uint16_t pixels[DR_ORIGINAL_CLOUD_ICON_W * DR_ORIGINAL_CLOUD_ICON_H];
} DrOriginalCloudIcon;

/* Exact private path relative to SD/FAT root; valid opaque 555 pixels must
 * have high bit set, transparent pixels must be zero. Invalid files must
 * leave the preceding icon state intact. */
int dr_original_cloud_icon_load(const char *storage_root, DrOriginalCloudIcon *icon);
/* Blend opaque source pixels onto an in-memory 256x192 framebuffer; fail
 * without modifying the framebuffer on invalid dimensions/position. */
int dr_original_cloud_icon_draw(uint16_t *framebuffer,
                                const DrOriginalCloudIcon *icon, int x, int y);
#endif
