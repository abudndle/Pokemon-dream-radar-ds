#include "game.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    Game g; game_new(&g, 0x20261030);
    g.screen = STATE_SPHERE;
    g.capture_timeout = 20000;
    g.sphere_x = 235; g.sphere_y = 163;
    g.sphere_vx = 9; g.sphere_vy = 11;
    game_tick(&g);
    assert(g.sphere_x == 236 && g.sphere_y == 164);
    assert(g.sphere_vx < 0 && g.sphere_vy < 0);
    for (int i=0;i<1000;i++) {
        game_tick(&g);
        assert(g.screen == STATE_SPHERE);
        assert(g.sphere_x >= 20 && g.sphere_x <= 236);
        assert(g.sphere_y >= 30 && g.sphere_y <= 164);
    }
    /* Corrupt signed velocities must clamp without integer overflow. */
    g.sphere_x=235;g.sphere_y=163;
    g.sphere_vx=2147483647;g.sphere_vy=2147483647;
    game_tick(&g);
    assert(g.sphere_x==236 && g.sphere_y==164);
    assert(g.sphere_vx<0 && g.sphere_vy<0);
    g.sphere_x=21;g.sphere_y=31;
    g.sphere_vx=-2147483647;g.sphere_vy=-2147483647;
    game_tick(&g);
    assert(g.sphere_x==20 && g.sphere_y==30);
    assert(g.sphere_vx>0 && g.sphere_vy>0);
    g.freeze_frames = 4;
    int x=g.sphere_x, y=g.sphere_y;
    for (int i=0;i<3;i++) { game_tick(&g); assert(g.sphere_x==x && g.sphere_y==y); }
    puts("PASS: capture target remains within DS viewport; freeze suspends movement");
    return 0;
}
