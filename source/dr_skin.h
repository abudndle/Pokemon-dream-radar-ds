/* DRK1: user-authored hierarchical two-influence skinning for DRM1 meshes.
 * No copyrighted 3DS bone rigs, weights, or animation files are bundled.
 * This is a compact Q12 yaw-only runtime, NOT original 3DS skeletal decode. */
#ifndef DR_SKIN_H
#define DR_SKIN_H
#include "dr_mesh.h"
#include <stddef.h>
#include <stdint.h>
#define DR_SKIN_MAX_VERTICES 2048u
#define DR_SKIN_MAX_BONES 16u
#define DR_SKIN_MAX_FRAMES 8u

typedef struct {
    int16_t x,y,z;       /* absolute neutral-model pivot, Q12 */
    uint8_t parent;      /* 255=root, or smaller bone index (acyclic) */
} DrSkinBone;
typedef struct {
    uint8_t a,b,weight;  /* A weight /255; B weight (255-weight)/255 */
} DrSkinInfluence;
typedef struct {
    int8_t tx,ty,tz,yaw; /* additive Q12/16 offsets; 256 yaw steps/turn */
} DrSkinPose;
typedef struct {
    uint16_t vertices;
    uint8_t bones,frames,ticks_per_frame;
    DrSkinBone *bone;
    DrSkinInfluence *influence;
    DrSkinPose *poses;    /* frame-major then bone-major */
    DrMeshVertex *scratch;
    DrMesh preview;       /* borrows original mesh triangle list */
} DrSkin;

/* out must be initially zeroed or already owned by this API. Invalid files
 * preserve an existing accepted animation atomically. */
int dr_skin_decode(const unsigned char *bytes,size_t size,
                   const DrMesh *mesh,DrSkin *out);
int dr_skin_load_file(const char *path,const DrMesh *mesh,DrSkin *out);
void dr_skin_free(DrSkin *skin);

/* Looped, linearly interpolated pose, hierarchical pivot transforms, and
 * two-influence linear vertex blending. No per-frame heap allocations.
 * Pointer returned is borrowed until the next call/free; never free it. */
const DrMesh *dr_skin_frame(DrSkin *skin,const DrMesh *base,uint32_t tick);
#endif
