#include <assert.h>
#include <stdio.h>
#include "game.h"
#include "../source_3d/camera_gate.h"

int main(void) {
    Game g;
    game_new(&g,1);
    assert(!dr3d_camera_should_run(NULL,1));
    assert(!dr3d_camera_should_run(&g,1));
    assert(!dr3d_camera_should_run(&g,0));
    g.screen=STATE_SPHERE;
    assert(!dr3d_camera_should_run(&g,0));
    assert(dr3d_camera_should_run(&g,1));
    assert(dr3d_camera_can_start(&g,1,0,0));
    assert(!dr3d_camera_can_start(&g,1,1,0));
    assert(!dr3d_camera_can_start(&g,1,0,1));
    g.save.camera_enabled=0;
    assert(!dr3d_camera_can_start(&g,1,0,0));
    g.save.camera_enabled=1;
    g.screen=STATE_RADAR;
    assert(!dr3d_camera_can_start(&g,1,0,0));
    g.screen=STATE_RESULTS;
    assert(!dr3d_camera_should_run(&g,1));
    /* Failure latches must not strand the player without camera aiming.
     * Y retries a failed DSi transfer; later Y presses toggle on/off. */
    int failed=1;
    g.screen=STATE_SPHERE;
    g.save.camera_enabled=1;
    g.camera_error=1;
    assert(!dr3d_camera_toggle(NULL,1,&failed));
    assert(!dr3d_camera_toggle(&g,1,NULL));
    assert(!dr3d_camera_toggle(&g,0,&failed));
    assert(failed==1 && g.camera_error==1);
    g.screen=STATE_RADAR;
    assert(!dr3d_camera_toggle(&g,1,&failed));
    assert(failed==1);
    g.screen=STATE_SPHERE;
    assert(dr3d_camera_toggle(&g,1,&failed));
    assert(!failed && !g.camera_error && g.save.camera_enabled);
    assert(dr3d_camera_can_start(&g,1,failed,0));
    assert(dr3d_camera_toggle(&g,1,&failed));
    assert(!g.save.camera_enabled);
    assert(!dr3d_camera_should_run(&g,1));
    assert(dr3d_camera_toggle(&g,1,&failed));
    assert(g.save.camera_enabled);
    assert(dr3d_camera_can_start(&g,1,failed,0));
    puts("PASS: native DSi camera gating, explicit retry and fallback toggling");
    return 0;
}
