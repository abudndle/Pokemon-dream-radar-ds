#include "game.h"
#include <assert.h>
#include <stdio.h>

static void begin(Game *g) {
    game_new(g,37);
    g->save.total_orbs=4000;
    g->save.orbs=4000;
    g->save.story_phase=3;
    game_begin_search(g,EXT_SIM_TORNADUS);
    assert(g->screen==STATE_RADAR);
    g->aim_x=g->clouds[0].x;
    g->aim_y=g->clouds[0].y;
    game_fire(g);
    assert(g->screen==STATE_SPHERE);
    assert(g->projectile_enabled && !g->projectile_active);
    assert(g->projectile_cooldown==game_capture_profile(g).attack_interval);
}

int main(void) {
    Game g;
    begin(&g);
    g.sphere_x=40;g.sphere_y=40;
    g.sphere_vx=0;g.sphere_vy=0;
    g.aim_x=100;g.aim_y=40;
    g.capture_timeout=1000;
    g.projectile_cooldown=0;
    game_tick(&g);
    assert(g.projectile_active);
    assert(g.projectile_x==40 && g.projectile_y==40);
    assert(g.projectile_vx>0 && g.projectile_vy==0);
    int hits_before=g.projectile_hits;
    for(int i=0;i<100 && !g.projectile_hits;i++)game_tick(&g);
    assert(g.projectile_hits==hits_before+1);
    /* A side ball may strike first in a simultaneous legendary fan; only
       the colliding projectile is removed, not the entire volley. */
    assert(!g.projectile_active ||
           !g.projectile_extra[0].active || !g.projectile_extra[1].active);
    assert(g.capture_timeout<820); /* bounded hit penalty plus ticks */

    /* Shooting the incoming projectile consumes that shot, not capture HP. */
    begin(&g);
    g.sphere_x=40;g.sphere_y=40;
    g.sphere_vx=0;g.sphere_vy=0;
    g.projectile_active=1;
    g.projectile_x=100;g.projectile_y=90;
    g.projectile_vx=1;g.projectile_vy=0;
    g.projectile_lifetime=60;
    g.aim_x=100;g.aim_y=90;
    int hp=g.capture_hp;
    game_fire(&g);
    assert(!g.projectile_active && g.capture_hp==hp);
    assert(g.projectile_hits==0);

    /* Frozen attacks remain stationary; Vortex prevents movement/launch. */
    begin(&g);
    g.freeze_frames=3;
    g.projectile_cooldown=0;
    g.projectile_active=0;
    for(int i=0;i<3;i++)game_tick(&g);
    assert(!g.projectile_active && g.projectile_cooldown==0);
    game_tick(&g);
    assert(g.projectile_active);

    /* A last-second projectile hit triggers the normal escape path; it
       cannot produce a captured Pokémon or research-item reward. */
    begin(&g);
    g.capture_timeout=100;
    g.projectile_active=1;
    g.projectile_lifetime=60;
    g.projectile_x=101;g.projectile_y=90;
    g.projectile_vx=-1;g.projectile_vy=0;
    g.aim_x=100;g.aim_y=90;
    game_tick(&g);
    assert(g.screen==STATE_RESULTS);
    assert(g.capture_timeout==0 && !g.projectile_active);
    assert(!g.projectile_enabled && g.projectile_hits==1);
    assert(g.save.pending_count==0 && g.save.pending_items[0]==0);

    /* Leaving the scene always clears an active projectile. */
    begin(&g);
    g.projectile_active=1;
    assert(game_leave_search(&g));
    assert(!g.projectile_enabled && !g.projectile_active);
    puts("PASS: sphere projectile spawn, timer penalty, beam defense, freezing and cleanup");
    return 0;
}
