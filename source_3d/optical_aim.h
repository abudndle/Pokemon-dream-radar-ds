#ifndef DREAM_RADAR_3D_OPTICAL_AIM_H
#define DREAM_RADAR_3D_OPTICAL_AIM_H
#include <stdint.h>
#include <string.h>
#include "game.h"

/* Keep camera motion data in regular ARM9 memory, never Nitro Engine VRAM.
 * Sampling matches the existing software renderer: 32x24 luma cells. */
typedef struct {
    uint8_t previous[32*24];
    uint8_t valid;
} Dr3dOpticalAim;

static inline void dr3d_optical_reset(Dr3dOpticalAim *state) {
    if(state)memset(state,0,sizeof *state);
}
static inline uint8_t dr3d_optical_luma(uint16_t rgb) {
    int r=rgb&31, g=(rgb>>5)&31, b=(rgb>>10)&31;
    return (uint8_t)((r*3+g*6+b)/10);
}
static inline int dr3d_optical_step(Dr3dOpticalAim *state, Game *game,
                                    const uint16_t *frame, int dsi_mode) {
    uint8_t samples[32*24];
    if(!state || !game || !frame || !dsi_mode || !game->camera_ok ||
       !game->camera_active || !game->save.optical_aim ||
       game->screen!=STATE_SPHERE) {
        dr3d_optical_reset(state);
        return 0;
    }
    for(int y=0;y<24;y++)
        for(int x=0;x<32;x++)
            samples[y*32+x]=dr3d_optical_luma(frame[(y*8+3)*256+x*8+3]);
    int changed=0;
    if(state->valid) {
        unsigned best=~0u, stationary=~0u;
        int dxbest=0,dybest=0;
        for(int dy=-2;dy<=2;dy++)for(int dx=-2;dx<=2;dx++) {
            unsigned error=0;
            for(int y=3;y<21;y+=2)for(int x=3;x<29;x+=2) {
                int delta=(int)samples[y*32+x] -
                          (int)state->previous[(y+dy)*32+x+dx];
                error+=(unsigned)(delta*delta);
            }
            if(!dx && !dy)stationary=error;
            if(error<best) { best=error;dxbest=dx;dybest=dy; }
        }
        /* Reuse the established provisional software optical-flow threshold
         * and 6-pixel gain; reject high-error/missing-motion frames. */
        /* Flat or repeated textures can match every displacement equally.
         * Require a clear improvement over the stationary frame to avoid
         * drifting the reticle when the camera is still. */
        if(best<150000u && (dxbest || dybest) &&
           (uint64_t)best*100u < (uint64_t)stationary*90u) {
            int nx=game->aim_x+dxbest*6, ny=game->aim_y+dybest*6;
            if(nx<6)nx=6;
            if(nx>250)nx=250;
            if(ny<6)ny=6;
            if(ny>185)ny=185;
            changed=(nx!=game->aim_x || ny!=game->aim_y);
            game->aim_x=nx;game->aim_y=ny;
        }
    }
    memcpy(state->previous,samples,sizeof samples);
    state->valid=1;
    return changed;
}
#endif
