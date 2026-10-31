#include "game.h"
#include <assert.h>
#include <stdio.h>
#include <stdint.h>

static void search(Game *g,int clouds) {
    game_new(g,73);
    g->save.orbs=1000;
    g->save.total_orbs=1000;
    g->save.story_phase=1; /* Unlock the Dowsing extension. */
    g->save.cloud_count=(uint8_t)clouds;
    game_begin_search(g,EXT_DOWSING);
    assert(g->screen==STATE_RADAR);
    assert(g->active_clouds==clouds);
    assert(g->save.orbs==900); /* Charged only once for this outing. */
    for(int i=0;i<clouds;i++) {
        g->clouds[i].alive=1;
        g->clouds[i].kind=1;  /* Dowsing always opens a sphere. */
        g->clouds[i].x=55+i*65;
        g->clouds[i].y=85;
    }
}
static void shoot_cloud(Game *g,int index) {
    g->aim_x=g->clouds[index].x;
    g->aim_y=g->clouds[index].y;
    game_fire(g);
    assert(g->screen==STATE_SPHERE);
}
static void capture(Game *g) {
    g->capture_timeout=120;
    game_capture(g);
    assert(g->screen==STATE_RESULTS);
}
int main(void) {
    Game g;
    assert(!game_resume_radar(NULL) && !game_finish_pending_radar(NULL));
    search(&g,2);
    shoot_cloud(&g,0);
    assert(g.radar_resume_pending && g.clouds[1].alive);
    assert(g.save.searches==0);
    capture(&g);
    assert(g.radar_resume_pending && g.save.searches==1);
    assert(g.save.orbs==900);
    assert(game_resume_radar(&g));
    assert(g.screen==STATE_RADAR && !g.radar_resume_pending);
    assert(g.clouds[1].alive && !g.clouds[0].alive);
    assert(g.save.searches==1 && g.save.orbs==900);
    assert(!game_resume_radar(&g));
    shoot_cloud(&g,1);
    assert(!g.radar_resume_pending); /* Final cloud. */
    capture(&g);
    assert(!g.radar_resume_pending && g.save.searches==1);
    assert(!game_resume_radar(&g) && !game_finish_pending_radar(&g));

    /* A running cluster of colorful Orbs must survive a different cloud's
       encounter, including its entire lifetime while the sphere is active. */
    search(&g,2);
    g.clouds[0].kind=0;
    g.aim_x=g.clouds[0].x;g.aim_y=g.clouds[0].y;
    game_fire(&g);
    assert(g.screen==STATE_RADAR && game_active_dream_orbs(&g)>=3);
    int slot=-1;
    for(int i=0;i<MAX_DREAM_ORBS;i++)
        if(g.dream_orbs[i].alive){slot=i;break;}
    assert(slot>=0);
    g.aim_x=g.dream_orbs[slot].x;
    g.aim_y=g.dream_orbs[slot].y;
    game_fire(&g);
    assert(g.session_orbs==1);
    int remaining=game_active_dream_orbs(&g);
    assert(remaining>=2);
    shoot_cloud(&g,1);
    assert(g.radar_resume_pending && game_active_dream_orbs(&g)==remaining);
    int ttl[MAX_DREAM_ORBS];
    for(int i=0;i<MAX_DREAM_ORBS;i++)ttl[i]=g.dream_orbs[i].ttl;
    for(int i=0;i<60;i++)game_tick(&g);
    for(int i=0;i<MAX_DREAM_ORBS;i++)assert(ttl[i]==g.dream_orbs[i].ttl);
    capture(&g);
    assert(g.session_orbs==1 && g.radar_resume_pending && g.save.searches==1);
    assert(game_resume_radar(&g));
    assert(game_active_dream_orbs(&g)==remaining);
    assert(g.session_orbs==1);
    /* B on the results screen explicitly finishes this hunt and discards
       unfinished Orbs without inventing a second search or reward. */
    assert(game_leave_search(&g)); /* Exit resumed radar. */
    assert(g.save.searches==1 && !g.radar_resume_pending);
    assert(game_active_dream_orbs(&g)==0);
    assert(g.session_orbs==1);

    /* Expiring a capture still allows the rest of the outing to resume. */
    search(&g,3);
    shoot_cloud(&g,0);
    g.capture_timeout=1;
    game_tick(&g);
    assert(g.screen==STATE_RESULTS && g.radar_resume_pending);
    assert(g.save.searches==1);
    assert(game_resume_radar(&g));
    assert(g.clouds[1].alive && g.clouds[2].alive);
    shoot_cloud(&g,1);
    capture(&g);
    assert(g.radar_resume_pending && g.save.searches==1);
    assert(game_finish_pending_radar(&g));
    assert(g.screen==STATE_RESULTS && g.save.searches==1);
    assert(!game_resume_radar(&g));
    for(int i=0;i<g.active_clouds;i++)assert(!g.clouds[i].alive);

    /* Full storage pauses the encounter until a replacement decision;
       declining must not discard the other clouds or duplicate rewards. */
    search(&g,2);
    shoot_cloud(&g,0);
    g.session_type=0;g.session_species=2;g.session_item=-1;
    g.save.pending_count=MAX_CAUGHT;
    for(int i=0;i<MAX_CAUGHT;i++)g.save.pending[i]=(uint8_t)i;
    g.capture_timeout=100;
    game_capture(&g);
    assert(g.screen==STATE_REPLACE && g.radar_resume_pending);
    assert(g.save.searches==0);
    assert(game_cancel_pending_replace(&g));
    assert(g.screen==STATE_RESULTS && g.radar_resume_pending);
    assert(g.save.searches==1 && g.save.pending_count==MAX_CAUGHT);
    assert(game_resume_radar(&g));
    assert(g.clouds[1].alive && g.save.searches==1);

    /* One-cloud or single-use Extensions never offer a non-existent resume. */
    search(&g,1);
    shoot_cloud(&g,0);
    capture(&g);
    assert(!g.radar_resume_pending && g.save.searches==1);

    /* Direct callers starting another outing from an intermediate result
       must retire the old one before charging for the next one. */
    search(&g,2);
    shoot_cloud(&g,0);
    capture(&g);
    assert(g.radar_resume_pending && g.save.searches==1);
    /* A rejected attempt to launch a different Extension must not lose the
       uncollected clouds from the existing outing. */
    game_begin_search(&g,EXT_DIALGA);
    assert(g.screen==STATE_RESULTS && g.radar_resume_pending);
    assert(g.clouds[1].alive && g.save.searches==1);
    game_begin_search(&g,EXT_BASIC); /* No clouds in the recharge pool. */
    assert(g.screen==STATE_RESULTS && g.radar_resume_pending);
    assert(g.clouds[1].alive);
    g.save.cloud_count=1;
    game_begin_search(&g,EXT_BASIC);
    assert(g.screen==STATE_RADAR && !g.radar_resume_pending);
    assert(g.search_counted==0 && g.save.searches==1);
    assert(g.active_clouds==1);
    puts("PASS: multi-encounter radar resume, frozen Orbs, expiry, replacement and exactly-once search counting");
    return 0;
}
