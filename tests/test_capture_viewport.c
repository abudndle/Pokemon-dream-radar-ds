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
    /* Exact minimum signed velocity must reverse without undefined negation. */
    g.sphere_x=21;g.sphere_y=31;
    g.sphere_vx=(-2147483647-1);g.sphere_vy=(-2147483647-1);
    game_tick(&g);
    assert(g.sphere_x==20 && g.sphere_y==30);
    assert(g.sphere_vx==2147483647 && g.sphere_vy==2147483647);
    g.freeze_frames = 4;
    int x=g.sphere_x, y=g.sphere_y;
    for (int i=0;i<3;i++) { game_tick(&g); assert(g.sphere_x==x && g.sphere_y==y); }
    /* Malformed sphere coordinates must never overflow the distance
       calculation or award an accidental capture. */
    game_new(&g,123);
    g.screen=STATE_SPHERE;
    g.capture_timeout=60;
    g.sphere_x=2147483647;
    g.sphere_y=(-2147483647-1);
    g.capture_hp=0;
    game_fire(&g);
    assert(g.screen==STATE_SPHERE && g.capture_hp==0);
    /* Both 32-bit aim coordinates can be corrupt at once. If either aim
       is off screen, not even a live hostile ball may be destroyed. This
       guards the projectile distance sum against signed 64-bit overflow. */
    game_new(&g,456);
    g.screen=STATE_SPHERE;
    g.capture_timeout=100;
    g.capture_hp=47;
    g.projectile_active=1;
    g.projectile_x=250;g.projectile_y=186;
    g.projectile_lifetime=66;
    g.projectile_hits=3;
    g.projectile_extra[0].active=1;
    g.projectile_extra[0].x=240;g.projectile_extra[0].y=180;
    g.projectile_extra[0].ttl=55;
    const int invalid_aims[][2]={{(-2147483647-1),(-2147483647-1)},
        {2147483647,2147483647},{-1,186},{250,-1},{256,186},{250,192}};
    for(unsigned i=0;i<sizeof invalid_aims/sizeof invalid_aims[0];i++) {
        g.aim_x=invalid_aims[i][0];g.aim_y=invalid_aims[i][1];
        game_fire(&g);
        assert(g.screen==STATE_SPHERE && g.capture_hp==47);
        assert(g.capture_timeout==100 && g.projectile_hits==3);
        assert(g.projectile_active && g.projectile_lifetime==66);
        assert(g.projectile_extra[0].active && g.projectile_extra[0].ttl==55);
    }
    /* Valid screen-space fire must still destroy the closest hostile ball. */
    g.aim_x=240;g.aim_y=180;
    game_fire(&g);
    assert(!g.projectile_extra[0].active && g.projectile_active);
    assert(g.capture_hp==47 && g.projectile_hits==3);
    g.aim_x=250;g.aim_y=186;
    game_fire(&g);
    assert(!g.projectile_active && g.projectile_hits==3);
    puts("PASS: capture viewport and corrupt aim cannot overflow projectile distances");
    return 0;
}
