/* Portable, optional DRA1 additive vertex-keyframe animation for DRM1.
 * Only user-converted assets are supported, no proprietary animation data. */
#ifndef DR_ANIMATION_H
#define DR_ANIMATION_H
#include "dr_mesh.h"
#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint16_t vertices;
    uint8_t frames;
    uint8_t ticks_per_frame;
    int8_t *delta;             /* frames * vertices * 3 signed Q12/16 deltas */
    DrMeshVertex *scratch;     /* reused every frame, no frame allocations */
    DrMesh preview;            /* borrowed: triangles belong to input mesh */
} DrAnimation;

/* An output must be zero-initialized or previously managed by this API.
 * Failed decoding/loading leaves the previous animation unchanged. */
int dr_animation_decode(const unsigned char *bytes,size_t length,
                        const DrMesh *mesh,DrAnimation *out);
int dr_animation_load_file(const char *path,const DrMesh *mesh,DrAnimation *out);
void dr_animation_free(DrAnimation *animation);

/* Linear interpolation and looping with deterministic integer-only timing.
 * Returns an animation-owned borrowed mesh pointer, valid until next call
 * to this function or dr_animation_free. NEVER dr_mesh_free the result.
 * No valid DRA1 file: render the original unmodified DRM1 mesh instead. */
const DrMesh *dr_animation_frame(DrAnimation *animation,const DrMesh *base,
                                 uint32_t ticks);
#endif
