#include "game.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

/* End-to-end portable gameplay acceptance, not an emulator test.
 * Exercise a genuine search, Orb shot, sphere capture, resumed search,
 * and persistent save/reload with a fixed RNG seed.
 */
int main(void) {
    Game g, restored;
    char path[]="/tmp/dr_capture_milestone_XXXXXX";
    int fd=mkstemp(path);
    assert(fd>=0);
    assert(close(fd)==0);
    game_new(&g,73);
    g.save.orbs=1000;
    g.save.total_orbs=1000;
    g.save.story_phase=1;
    g.save.cloud_count=2;
    game_begin_search(&g,EXT_DOWSING);
    assert(g.screen==STATE_RADAR && g.active_clouds==2);
    assert(g.save.orbs==900);
    g.clouds[0].alive=1;
    g.clouds[0].kind=0;
    g.clouds[0].x=55;
    g.clouds[0].y=85;
    g.clouds[1].alive=1;
    g.clouds[1].kind=1;
    g.clouds[1].x=190;
    g.clouds[1].y=85;
    g.aim_x=55;
    g.aim_y=85;
    game_fire(&g);
    assert(g.screen==STATE_RADAR);
    assert(game_active_dream_orbs(&g)>=3);
    int orb=-1;
    for(int i=0;i<MAX_DREAM_ORBS;i++)
        if(g.dream_orbs[i].alive){orb=i;break;}
    assert(orb>=0);
    g.aim_x=g.dream_orbs[orb].x;
    g.aim_y=g.dream_orbs[orb].y;
    game_fire(&g);
    assert(g.session_orbs==1);
    g.aim_x=190;
    g.aim_y=85;
    game_fire(&g);
    assert(g.screen==STATE_SPHERE);
    assert(g.radar_resume_pending==0); /* Last cloud has been opened. */
    g.capture_timeout=120;
    game_capture(&g);
    assert(g.screen==STATE_RESULTS);
    assert(g.save.searches==1);
    assert(g.save.orbs>=900);
    assert(!game_resume_radar(&g));
    assert(game_save(&g,path));
    game_new(&restored,123);
    assert(game_load(&restored,path));
    assert(restored.save.searches==g.save.searches);
    assert(restored.save.orbs==g.save.orbs);
    assert(restored.save.story_phase==g.save.story_phase);
    assert(unlink(path)==0);
    puts("PASS: cloud search, orb, sphere, results, save and reload");
    return 0;
}
