/* Optional, user-supplied DRT1 UV and RGB555 texture companion for DRM1.
 * Neither Nintendo asset data nor textures are included with this module. */
#ifndef DR_TEXTURE_H
#define DR_TEXTURE_H
#include "dr_mesh.h"
#include <stddef.h>
#include <stdint.h>
typedef struct { uint16_t u,v; } DrTextureUV;
typedef struct {
    uint16_t width,height,vertices;
    DrTextureUV *uv;
    uint16_t *texels;
} DrTexture;
/* out must be zero-initialized or previously managed by this API. Failed
 * decode/load preserves the original texture. UV coordinates are Q12. */
int dr_texture_decode(const unsigned char *bytes,size_t size,
                      const DrMesh *mesh,DrTexture *out);
int dr_texture_load_file(const char *path,const DrMesh *mesh,DrTexture *out);
void dr_texture_free(DrTexture *texture);
/* Affine nearest-neighbor texture-mapped triangle preview, RGB555 opaque.
 * Painter's order only: no depth buffer, lighting, or skeletal animation.
 * The caller owns the 256x192-or-smaller framebuffer. */
int dr_texture_render_yaw(const DrMesh *mesh,const DrTexture *texture,
                          uint16_t *pixels,int width,int height,
                          int cx,int cy,int scale,unsigned yaw_step);
#endif
