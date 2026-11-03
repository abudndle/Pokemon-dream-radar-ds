#ifndef DREAM_RADAR_3D_AIM_INPUT_H
#define DREAM_RADAR_3D_AIM_INPUT_H
#include "game.h"

/* Both DS screens are 256x192. Only accept touchscreen coordinates during
 * actual radar/capture play; never allow menu touches to move the reticle.
 * This adapter changes input, not the authoritative game simulation. */
static inline int dr3d_apply_touch_aim(Game *game, int touching, int x, int y) {
    if(!game || !touching ||
       (game->screen != STATE_RADAR && game->screen != STATE_SPHERE))
        return 0;
    if(x < 0) x = 0;
    if(x > 255) x = 255;
    if(y < 0) y = 0;
    if(y > 191) y = 191;
    game->aim_x = x;
    game->aim_y = y;
    return 1;
}
#endif
