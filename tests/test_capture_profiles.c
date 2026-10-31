#include "game.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>

/* All battle profile values are provisional DS/DSi adaptations, not
   recovered Pokémon Dream Radar original species parameter data. */
static Game base(int species,int ext,int kind) {
    Game g;
    game_new(&g,123);
    g.ext_selection=ext;
    g.session_type=kind;
    g.session_species=species;
    g.screen=STATE_SPHERE;
    g.capture_timeout=2000;
    g.capture_hp=0;
    g.sphere_x=128;g.sphere_y=96;
    g.aim_x=128;g.aim_y=96;
    g.projectile_enabled=0;
    return g;
}

int main(void) {
    CaptureProfile default_profile=game_capture_profile(NULL);
    assert(default_profile.type==CAPTURE_DRIFT);
    for(int type=0;type<3;type++) {
        Game g=base(type,EXT_BASIC,0);
        CaptureProfile p=game_capture_profile(&g);
        assert(p.type==(CaptureClass)type);
        assert(p.hit_radius>=12 && p.hit_radius<=24);
        assert(p.attack_interval>0 && p.attack_penalty>0);
        assert(p.attack_burst>=1 && p.attack_burst<=3);
        assert(p.speed>0 && p.speed<=3);
    }
    Game g=base(18,EXT_DIALGA,0);
    CaptureProfile legendary=game_capture_profile(&g);
    assert(legendary.type==CAPTURE_LEGENDARY);
    assert(legendary.speed>=default_profile.speed);
    assert(legendary.attack_interval<default_profile.attack_interval);
    assert(legendary.attack_penalty>default_profile.attack_penalty);
    assert(legendary.attack_burst==3);
    g.session_type=1;
    assert(game_capture_profile(&g).type==CAPTURE_LEGENDARY);
    g=base(-1,EXT_DOWSING,1);
    assert(game_capture_profile(&g).type==CAPTURE_ITEM);
    g=base(25,EXT_BASIC,0);
    assert(game_capture_profile(&g).type==CAPTURE_SWIFT);
    g=base(INT_MAX,EXT_BASIC,0);
    assert(game_capture_profile(&g).type==CAPTURE_DRIFT);

    /* A size/accuracy difference must have visible hit-test consequences. */
    g=base(0,EXT_BASIC,0);
    g.sphere_x=147;g.aim_x=128;g.sphere_y=96;g.aim_y=96;
    game_fire(&g);
    assert(g.capture_hp>0);
    g=base(2,EXT_BASIC,0);
    g.sphere_x=147;g.aim_x=128;
    game_fire(&g);
    assert(g.capture_hp==0);

    /* True encounter initialization selects the profile AFTER species roll. */
    game_new(&g,411);
    g.save.story_phase=3;
    g.save.orbs=4000;
    g.save.total_orbs=4000;
    game_begin_search(&g,EXT_SIM_TORNADUS);
    assert(g.screen==STATE_RADAR);
    g.aim_x=g.clouds[0].x;
    g.aim_y=g.clouds[0].y;
    game_fire(&g);
    assert(g.screen==STATE_SPHERE);
    assert(g.session_species==15);
    assert(game_capture_profile(&g).type==CAPTURE_LEGENDARY);
    assert(g.sphere_vx==legendary.speed && g.sphere_vy==legendary.speed-1);
    assert(g.projectile_cooldown==legendary.attack_interval);
    assert(g.projectile_queued==0 && g.capture_motion_ticks==0);
    /* For the first turn, the target follows a straight trajectory.
       Freezing the sphere suspends turning without consuming the timer. */
    g.projectile_enabled=0;
    g.freeze_frames=5;
    int x=g.sphere_x;
    for(int i=0;i<5;i++)game_tick(&g);
    assert(g.sphere_x==x && g.capture_motion_ticks==0);
    for(int i=0;i<legendary.turn_frames;i++)game_tick(&g);
    assert(g.capture_motion_ticks==legendary.turn_frames);
    assert(g.sphere_vx==-legendary.speed);
    assert(g.sphere_vy==legendary.speed);
    /* Dragnet's slowdown must apply to steering, not just position. */
    g.slow_frames=15;
    int moves=g.capture_motion_ticks;
    for(int i=0;i<15;i++)game_tick(&g);
    assert(g.capture_motion_ticks-moves<=5);

    /* Legendary projectiles are issued in three-ball staggered volleys.
       Destroying one via the beam leaves the remaining volleys pending. */
    g=base(18,EXT_DIALGA,0);
    g.projectile_enabled=1;
    g.projectile_cooldown=0;
    g.aim_x=220;g.aim_y=170;
    game_tick(&g);
    assert(g.projectile_active && g.projectile_queued==2);
    g.aim_x=g.projectile_x;g.aim_y=g.projectile_y;
    game_fire(&g);
    assert(!g.projectile_active && g.projectile_queued==2);
    assert(g.projectile_cooldown==12);
    g.aim_x=220;g.aim_y=170;
    for(int i=0;i<13;i++)game_tick(&g);
    assert(g.projectile_active && g.projectile_queued==1);
    g.aim_x=g.projectile_x;g.aim_y=g.projectile_y;
    game_fire(&g);
    g.aim_x=220;g.aim_y=170;
    for(int i=0;i<13;i++)game_tick(&g);
    assert(g.projectile_active && g.projectile_queued==0);

    /* An actual impact deducts a profile-specific bounded amount. */
    g=base(18,EXT_DIALGA,0);
    g.projectile_enabled=1;g.projectile_active=1;
    g.projectile_x=g.aim_x=100;g.projectile_y=g.aim_y=100;
    g.projectile_vx=0;g.projectile_vy=0;g.projectile_lifetime=20;
    g.capture_timeout=1000;
    game_tick(&g);
    assert(g.projectile_hits==1);
    assert(g.capture_timeout==999-legendary.attack_penalty);
    assert(!g.projectile_active);
    assert(g.screen==STATE_SPHERE);
    puts("PASS: class-specific sphere hitboxes, movement, turning, volleys and time penalties");
    return 0;
}
