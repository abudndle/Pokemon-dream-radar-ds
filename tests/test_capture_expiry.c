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
    /* Direct public capture calls must not bypass the expired timer either. */
    g.session_type=0;
    g.session_species=4;
    game_capture(&g);
    assert(g.screen==STATE_SPHERE && g.save.pending_count==0);
    assert(g.save.caught_count==0);
    g.session_type=1;
    g.session_species=-1;
    g.session_item=2;
    game_capture(&g);
    assert(g.screen==STATE_SPHERE && g.save.pending_items[0]==0);
    assert(g.save.caught_count==0);
    assert(g.save.caught_count==count);
    /* A captured-target timeout also forbids defensive shots. Check the
       primary and both side balls while the expired sphere is still shown;
       this does not call game_tick or directly end the encounter. */
    g.projectile_enabled=1;
    g.projectile_active=1;
    g.projectile_x=g.aim_x;g.projectile_y=g.aim_y;
    g.projectile_lifetime=60;
    g.projectile_cooldown=8;
    g.projectile_hits=0;
    g.projectile_extra[0].active=1;
    g.projectile_extra[0].x=90;g.projectile_extra[0].y=80;
    g.projectile_extra[0].ttl=60;
    g.projectile_extra[1].active=1;
    g.projectile_extra[1].x=160;g.projectile_extra[1].y=110;
    g.projectile_extra[1].ttl=60;
    for(int shot=0;shot<3;shot++) {
        if(shot==1){g.aim_x=90;g.aim_y=80;}
        if(shot==2){g.aim_x=160;g.aim_y=110;}
        game_fire(&g);
        assert(g.projectile_active && g.projectile_lifetime==60);
        assert(g.projectile_extra[0].active && g.projectile_extra[1].active);
        assert(g.projectile_cooldown==8 && g.projectile_hits==0);
        assert(g.capture_hp==239 && g.capture_timeout==0);
        assert(g.screen==STATE_SPHERE && g.save.pending_count==0);
    }
    /* A negative timer is also an already-expired capture. */
    g.capture_timeout=-1;
    g.aim_x=g.projectile_x;g.aim_y=g.projectile_y;
    game_fire(&g);
    assert(g.projectile_active && g.projectile_extra[0].active);
    g.capture_timeout=0;
    game_tick(&g);
    assert(g.screen==STATE_RESULTS && g.session_caught==-1);
    game_fire(&g);
    assert(g.save.caught_count==count);
    /* Unknown encounter types must never be treated as a Pokemon reward. */
    game_new(&g,30);
    g.screen=STATE_SPHERE;
    g.capture_timeout=100;
    g.session_type=2;
    g.session_species=4;
    game_capture(&g);
    assert(g.screen==STATE_SPHERE);
    assert(g.save.pending_count==0 && g.save.caught_count==0);
    g.session_type=-1;
    game_capture(&g);
    assert(g.screen==STATE_SPHERE);
    assert(g.save.pending_count==0 && g.save.caught_count==0);
    /* Simulator gameplay must reject a malformed encounter. Valid Simulator
       fights award their documented research item via the shared storage flow. */
    game_new(&g,31);
    g.screen=STATE_SPHERE;
    g.capture_timeout=100;
    g.ext_selection=EXT_SIM_TORNADUS;
    g.session_type=1; /* Invalid: simulator battle must depict a Therian. */
    g.session_species=15;
    g.session_item=2;
    game_capture(&g);
    assert(g.screen==STATE_SPHERE && g.session_caught==-1);
    assert(g.save.pending_count==0 && g.save.pending_items[0]==0);
    assert(g.save.caught_count==0);
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
