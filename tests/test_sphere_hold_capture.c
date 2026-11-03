#include "game.h"
#include "platform_compat.h"
#include <assert.h>
#include <stdio.h>

/* Host simulation of the actual held-A capture input policy, not a live
 * emulator test. Move/track a sphere using game_tick and shoot only when
 * the same input gate as the DS runtime authorizes a beam frame. */
static void begin_encounter(Game *g) {
    game_new(g, 51);
    g->screen=STATE_SPHERE;
    g->ext_selection=EXT_BASIC;
    g->capture_timeout=600;
    g->session_type=0;
    g->session_species=4; /* Riolu */
    g->session_item=-1;
    g->sphere_x=120;
    g->sphere_y=85;
    g->sphere_vx=2;
    g->sphere_vy=1;
    g->projectile_enabled=0;
}

int main(void) {
    Game g;
    begin_encounter(&g);
    int shots=0;
    int observed_movement=0;
    for(unsigned frame=1;frame<=300 && g.screen==STATE_SPHERE;frame++) {
        int before_x=g.sphere_x, before_y=g.sphere_y;
        game_tick(&g);
        if(g.sphere_x!=before_x || g.sphere_y!=before_y)
            observed_movement=1;
        /* A remains held after its first edge. Track the target as a
         * player would and let the ordinary hit/HP path do the capture. */
        g.aim_x=g.sphere_x;
        g.aim_y=g.sphere_y;
        if(dr_sphere_fire_repeat(1,frame==1,g.save.frames_played)) {
            game_fire(&g);
            shots++;
        }
    }
    assert(observed_movement);
    assert(shots>=80 && shots<=101);
    assert(g.screen==STATE_RESULTS);
    assert(g.session_caught==4);
    assert(g.save.pending_count==1 && g.save.pending[0]==4);

    /* Releasing A stops filling the meter, even on cadence frames. */
    begin_encounter(&g);
    game_tick(&g);
    g.aim_x=g.sphere_x;
    g.aim_y=g.sphere_y;
    assert(dr_sphere_fire_repeat(1,1,g.save.frames_played));
    game_fire(&g);
    int stopped_hp=g.capture_hp;
    assert(stopped_hp>0);
    for(int frame=0;frame<90;frame++) {
        game_tick(&g);
        g.aim_x=g.sphere_x;
        g.aim_y=g.sphere_y;
        if(dr_sphere_fire_repeat(0,0,g.save.frames_played))game_fire(&g);
    }
    assert(g.screen==STATE_SPHERE && g.capture_hp==stopped_hp);
    assert(g.save.pending_count==0);
    puts("PASS: held A captures moving sphere; release halts beam and preserves radar gate");
    return 0;
}
