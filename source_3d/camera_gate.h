#ifndef DREAM_RADAR_3D_CAMERA_GATE_H
#define DREAM_RADAR_3D_CAMERA_GATE_H
#include "game.h"

/* DSi camera hardware is optional: never initialize on DS, during menus,
 * or while an original radar search has not produced a sphere encounter. */
static inline int dr3d_camera_should_run(const Game *g, int dsi_mode) {
    return g && dsi_mode && g->save.camera_enabled &&
           g->screen == STATE_SPHERE;
}
/* A failed camera must remain off for this session, without stopping gameplay.
 * The failure latch can be reset only by a new explicit enable action. */
static inline int dr3d_camera_can_start(const Game *g, int dsi_mode,
                                        int failed_this_run, int active) {
    return !failed_this_run && !active && dr3d_camera_should_run(g,dsi_mode);
}
/* Y in an active DSi sphere encounter is an explicit camera control.
 * A failed transfer is retried without forcing the player to leave the
 * encounter; otherwise Y disables/enables the camera. DS never changes. */
static inline int dr3d_camera_toggle(Game *g, int dsi_mode, int *failed) {
    if(!g || !failed || !dsi_mode || g->screen != STATE_SPHERE)
        return 0;
    if(*failed) {
        *failed = 0;
        g->save.camera_enabled = 1;
    } else {
        g->save.camera_enabled = !g->save.camera_enabled;
    }
    g->camera_error = 0;
    return 1;
}
#endif
