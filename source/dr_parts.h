/* Optional DRB1 rigid body-part keyframes for converted DRM1 geometry.
 * This is not a decoder for Nintendo 3DS skeletal animation data. */
#ifndef DR_PARTS_H
#define DR_PARTS_H
#include "dr_mesh.h"
#include <stddef.h>
#include <stdint.h>
#define DR_PARTS_MAX_VERTICES 2048u
#define DR_PARTS_MAX_GROUPS 16u
#define DR_PARTS_MAX_FRAMES 8u

typedef struct { int16_t x,y,z; } DrPartPivot;
typedef struct { int8_t tx,ty,tz,yaw; } DrPartPose;
typedef struct {
    uint16_t vertices;
    uint8_t groups,frames,ticks_per_frame;
    uint8_t *owner;        /* one rigid body-part ID for each base mesh vertex */
    DrPartPivot *pivot;    /* one fixed Q12 pivot for each part */
    DrPartPose *poses;     /* frame-major, then part-major */
    DrMeshVertex *scratch; /* reused every update */
    DrMesh preview;        /* borrows base triangles, never owns topology */
} DrParts;

/* The output must be zero-initialized or managed by this API. Failure never
 * overwrites an already accepted animation. */
int dr_parts_decode(const unsigned char *bytes,size_t length,
                    const DrMesh *mesh,DrParts *out);
int dr_parts_load_file(const char *path,const DrMesh *mesh,DrParts *out);
void dr_parts_free(DrParts *parts);

/* Return a borrowed animated mesh: valid until the next frame/free.
 * Vertex index and topology are unchanged for DRT1 UV mapping.
 * Missing/invalid animation should fall back to DRA1 or base DRM1. */
const DrMesh *dr_parts_frame(DrParts *parts,const DrMesh *base,
                             uint32_t ticks);
#endif
