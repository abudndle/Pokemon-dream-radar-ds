#include "game.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
int main(void) {
    game_fire(NULL); /* Invalid caller must not crash. */
    game_tick(NULL); /* Invalid frame state must not crash. */
    Game g;
    game_new(&g,29);
    g.screen=STATE_SPHERE;
    g.capture_timeout=0;
    g.capture_hp=239;
    g.sphere_x=g.aim_x;
    g.sphere_y=g.aim_y;
    uint32_t count=g.save.caught_count;
    game_fire(&g);
    assert(g.screen==STATE_SPHERE && g.capture_hp==239);
    assert(g.save.caught_count==count);
    game_tick(&g);
    assert(g.screen==STATE_RESULTS && g.session_caught==-1);
    game_fire(&g);
    assert(g.save.caught_count==count);
    /* Corrupt negative timeouts must also resolve, not trap a capture. */
    game_new(&g,29);
    g.screen=STATE_SPHERE;
    g.capture_timeout=-42;
    g.freeze_frames=50;
    g.slow_frames=50;
    game_tick(&g);
    assert(g.screen==STATE_RESULTS && g.capture_timeout==0);
    assert(g.freeze_frames==0 && g.slow_frames==0);
    /* Invalid touchscreen coordinates never award shots or mutate clouds. */
    game_new(&g,91);
    game_begin_search(&g,EXT_BASIC);
    assert(g.screen==STATE_RADAR);
    g.active_clouds=1;
    g.clouds[0].alive=1;
    g.clouds[0].x=128;g.clouds[0].y=90;g.clouds[0].kind=0;
    g.aim_x=2147483647;g.aim_y=-2147483647;
    game_fire(&g);
    assert(g.clouds[0].alive && g.cloud_hit==0);
    g.screen=STATE_SPHERE;
    g.capture_timeout=100;
    g.capture_hp=0;
    g.sphere_x=128;g.sphere_y=90;
    game_fire(&g);
    assert(g.capture_hp==0);
    g.save.frames_played=UINT32_MAX-1u;
    game_tick(&g);
    assert(g.save.frames_played==UINT32_MAX);
    game_tick(&g);
    assert(g.save.frames_played==UINT32_MAX);
    /* Escaping at maximum persisted search count must not wrap progress. */
    game_new(&g,92);
    g.screen=STATE_SPHERE;
    g.capture_timeout=1;
    g.save.searches=UINT32_MAX;
    game_tick(&g);
    assert(g.screen==STATE_RESULTS);
    assert(g.save.searches==UINT32_MAX);
    puts("PASS: expired capture cannot be completed by a late shot");
    return 0;
}
