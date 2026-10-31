#include "game.h"
#include <assert.h>
#include <stdio.h>

/* This synthetic encounter verifies DS rules, not retail 3DS attack timing. */
static Game legendary(void) {
    Game g;
    game_new(&g,42);
    g.screen=STATE_SPHERE;
    g.ext_selection=EXT_DIALGA;
    g.session_species=18;
    g.session_type=0;
    g.capture_timeout=2000;
    g.aim_x=100;g.aim_y=90;
    g.sphere_x=200;g.sphere_y=150;
    g.sphere_vx=0;g.sphere_vy=0;
    g.projectile_enabled=1;
    g.projectile_cooldown=60;
    g.projectile_active=1;
    g.projectile_x=100;g.projectile_y=90;
    g.projectile_vx=0;g.projectile_vy=0;
    g.projectile_lifetime=30;
    for(int i=0;i<MAX_EXTRA_PROJECTILES;i++) {
        g.projectile_extra[i].active=1;
        g.projectile_extra[i].x=100;
        g.projectile_extra[i].y=90;
        g.projectile_extra[i].vx=0;
        g.projectile_extra[i].vy=0;
        g.projectile_extra[i].ttl=30;
    }
    return g;
}
int main(void) {
    Game g=legendary();
    int penalty=game_capture_profile(&g).attack_penalty;
    assert(penalty>0);
    game_tick(&g);
    assert(g.projectile_hits==1 && g.capture_timeout==1999-penalty);
    assert(!g.projectile_extra[0].active);
    assert(g.projectile_extra[1].active && g.projectile_active);
    game_tick(&g);
    assert(g.projectile_hits==2 && g.capture_timeout==1998-2*penalty);
    assert(!g.projectile_extra[1].active && g.projectile_active);
    game_tick(&g);
    assert(g.projectile_hits==3 && g.capture_timeout==1997-3*penalty);
    assert(!g.projectile_active && g.screen==STATE_SPHERE);

    /* Primary ball is nearest even though side balls are checked too. */
    g=legendary();
    g.projectile_extra[0].x=108;
    g.projectile_extra[1].x=160;
    game_fire(&g);
    assert(!g.projectile_active);
    assert(g.projectile_extra[0].active && g.projectile_extra[1].active);
    assert(g.projectile_hits==0 && g.capture_hp==0);
    g.aim_x=108;
    game_fire(&g);
    assert(!g.projectile_extra[0].active && g.projectile_extra[1].active);

    /* Right side wins over left side when it is closer to reticle. */
    g=legendary();
    g.projectile_extra[0].x=110;
    g.projectile_extra[1].x=101;
    g.projectile_x=115;
    game_fire(&g);
    assert(g.projectile_extra[0].active && !g.projectile_extra[1].active);
    assert(g.projectile_active);

    /* Lethal collision cleans all siblings without awarding a Pokémon. */
    g=legendary();
    g.capture_timeout=penalty;
    game_tick(&g);
    assert(g.screen==STATE_RESULTS && g.capture_timeout==0);
    assert(g.projectile_hits==1);
    assert(!g.projectile_enabled && !g.projectile_active);
    for(int i=0;i<MAX_EXTRA_PROJECTILES;i++)
        assert(!g.projectile_extra[i].active);
    assert(g.save.pending_count==0);
    puts("PASS: one projectile impact/frame, nearest beam defense, safe timeout");
    return 0;
}
