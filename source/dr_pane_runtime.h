#ifndef DREAM_RADAR_PANE_RUNTIME_H
#define DREAM_RADAR_PANE_RUNTIME_H
/* Portable 2D pane compositor for owner-extracted BCLYT geometry.
 * Input coordinates are retargeted DS pixels with +Y downward. The exporter
 * handles the source canvas/orientation, rather than silently guessing here.
 * All arrays are bounded; there is no allocation or NDS dependency.
 */
#include <stddef.h>
#include <stdint.h>

#define DR_PANE_MAX_NODES 64u
#define DR_PANE_MAX_TRACKS 128u
#define DR_PANE_MAX_KEYS 1024u

typedef struct {
    int16_t parent;           /* -1=root; parent index must precede child */
    float x, y, width, height;
    float scale_x, scale_y, rotation_deg;
    uint8_t origin;           /* BCLYT grid: 0..8; 4=center */
    uint8_t visible, alpha;
    uint8_t clip_children;    /* optional parent-frame clip */
} DrUiPane;

typedef struct {
    float frame, value, slope;
} DrUiKey;

typedef struct {
    uint16_t pane;
    uint8_t property;         /* CLPA 0..9 (only 2D 0,1,5,6..9 supported) */
    uint8_t curve;            /* 0/1=hold, 2=cubic Hermite */
    uint16_t count;
    const DrUiKey *keys;
} DrUiTrack;

typedef struct {
    const DrUiTrack *tracks;
    uint16_t count;
    float duration;
    uint8_t loop;
} DrUiAnimation;

typedef struct {
    float a,b,c,d,tx,ty;     /* affine transform from pane local to DS */
    float quad[8];           /* transformed TL,TR,BR,BL */
    int x,y,w,h;             /* clipped, axis-aligned DS bounding rectangle */
    uint8_t visible,alpha;
} DrUiFrame;

/* Evaluate one clip at a fractional frame and compose the pane hierarchy.
 * Returns zero (without publishing partial results) on malformed geometry,
 * invalid animation/parent links, unsupported non-2D tracks or nonfinite data.
 */
int dr_ui_evaluate(const DrUiPane *panes,size_t count,
                   const DrUiAnimation *animation,float frame,
                   DrUiFrame *out,size_t output_count);

/* Same clipped rectangle used for visual overlay, labels and broad-phase
 * touch picking. AABB is intentional for rotated panes: exact textured-pixel
 * hit tests are a separate fidelity task.
 */
int dr_ui_hit(const DrUiFrame *frame,int x,int y);
int dr_ui_sample(const DrUiTrack *track,float frame,float *value);
#endif
