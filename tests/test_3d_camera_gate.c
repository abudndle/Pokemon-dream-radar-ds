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
    puts("PASS: native DSi camera only runs in enabled sphere encounters");
    return 0;
}
