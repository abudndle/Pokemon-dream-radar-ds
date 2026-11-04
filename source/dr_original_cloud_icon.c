#include "dr_original_cloud_icon.h"
#include <stdio.h>
#include <string.h>

enum { DR_SCREEN_WIDTH = 256, DR_SCREEN_HEIGHT = 192 };
#define DR_ORIGINAL_CLOUD_ICON_FILE \
    "DreamRadarDSi/UI/OriginalSprites/Ui/MnIf_S_TitleCloudCount/timg/CloudCountIcon00.spr"
#define DR_CLOUD_ICON_PIXELS \
    (DR_ORIGINAL_CLOUD_ICON_W * DR_ORIGINAL_CLOUD_ICON_H)

/* Read exactly one source-backed original TitleCloudCount texture. This
 * allowlisted path is fixed; it cannot be redirected by a save or menu name.
 * The full original UI archive is optional external SD/FAT data. */
int dr_original_cloud_icon_load(const char *storage_root, DrOriginalCloudIcon *icon) {
    if (!storage_root || !*storage_root || !icon) return 0;
    size_t root_len = strlen(storage_root);
    char path[320];
    int n = snprintf(path, sizeof path, "%s%s%s", storage_root,
                     storage_root[root_len - 1] == '/' ? "" : "/",
                     DR_ORIGINAL_CLOUD_ICON_FILE);
    if (n <= 0 || n >= (int)sizeof path) return 0;
    FILE *f = fopen(path, "rb");
    if (!f) return 0;

    unsigned char header[4];
    int valid = fread(header, 1, sizeof header, f) == sizeof header;
    if (valid) {
        unsigned width = (unsigned)header[0] | ((unsigned)header[1] << 8);
        unsigned height = (unsigned)header[2] | ((unsigned)header[3] << 8);
        valid = width == DR_ORIGINAL_CLOUD_ICON_W &&
                height == DR_ORIGINAL_CLOUD_ICON_H &&
                fseek(f, 0, SEEK_END) == 0 &&
                ftell(f) == 4L + DR_CLOUD_ICON_PIXELS * 2L &&
                fseek(f, 4, SEEK_SET) == 0;
    }
    DrOriginalCloudIcon candidate;
    memset(&candidate, 0, sizeof candidate);
    if (valid) {
        unsigned char bytes[DR_CLOUD_ICON_PIXELS * 2];
        valid = fread(bytes, 1, sizeof bytes, f) == sizeof bytes;
        if (valid) {
            unsigned visible = 0;
            for (unsigned i = 0; i < DR_CLOUD_ICON_PIXELS; ++i) {
                unsigned color = (unsigned)bytes[i * 2] |
                                 ((unsigned)bytes[i * 2 + 1] << 8);
                candidate.pixels[i] = (uint16_t)color;
                if (color & 0x8000u) ++visible;
                else if (color != 0) { valid = 0; break; }
            }
            if (!visible) valid = 0;
        }
    }
    if (fclose(f) != 0) valid = 0;
    if (!valid) return 0;
    candidate.loaded = 1;
    *icon = candidate;
    return 1;
}

/* Renderer is intentionally independent of Nintendo binaries; it accepts
 * only the validated 64x32 RGB555 surface already loaded from private FAT.
 * Transparent pixels preserve the previous framebuffer contents. */
int dr_original_cloud_icon_draw(uint16_t *framebuffer,
                                const DrOriginalCloudIcon *icon, int x, int y) {
    if (!framebuffer || !icon || !icon->loaded ||
        x < 0 || y < 0 ||
        x > DR_SCREEN_WIDTH - DR_ORIGINAL_CLOUD_ICON_W ||
        y > DR_SCREEN_HEIGHT - DR_ORIGINAL_CLOUD_ICON_H) return 0;
    for (int row = 0; row < DR_ORIGINAL_CLOUD_ICON_H; ++row) {
        uint16_t *dst = framebuffer + (y + row) * DR_SCREEN_WIDTH + x;
        const uint16_t *src = icon->pixels + row * DR_ORIGINAL_CLOUD_ICON_W;
        for (int col = 0; col < DR_ORIGINAL_CLOUD_ICON_W; ++col)
            if (src[col] & 0x8000u) dst[col] = src[col];
    }
    return 1;
}
