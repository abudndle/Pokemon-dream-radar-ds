#include "game.h"
#include <assert.h>
#include <stdio.h>
#include <stdint.h>

static void fresh_cloud(Game *g,unsigned frames) {
    game_new(g,41);
    game_begin_search(g,EXT_BASIC);
    assert(g->screen==STATE_RADAR);
    g->active_clouds=1;g->cloud_hit=0;
    g->clouds[0].alive=1;g->clouds[0].kind=0;
    g->clouds[0].x=128;g->clouds[0].y=96;
    g->aim_x=128;g->aim_y=96;
    g->save.frames_played=frames;
    game_fire(g);
    assert(g->screen==STATE_RADAR && g->cloud_hit==1);
}

static int shoot_all(Game *g) {
    int hits=0;
    for(int shot=0;shot<DREAM_ORB_CHAIN_LIMIT+4 && g->screen==STATE_RADAR;shot++) {
        int index=-1;
        for(int i=0;i<MAX_DREAM_ORBS;i++)if(g->dream_orbs[i].alive){index=i;break;}
        if(index<0)break;
        g->aim_x=g->dream_orbs[index].x;
        g->aim_y=g->dream_orbs[index].y;
        game_fire(g);
        hits++;
    }
    return hits;
}
int main(void) {
    Game g;
    assert(game_active_dream_orbs(NULL)==0);
    assert(game_dream_orb_color(NULL,0)==ORB_PINK);
    assert(game_dream_orb_color(&g,-1)==ORB_PINK); /* no deref */
    /* A contracted cloud yields 3 collectible orbs. Shooting the cloud
       alone must never award currency or advance color progress. */
    fresh_cloud(&g,0);
    assert(game_active_dream_orbs(&g)==3);
    assert(g.save.orbs==0 && g.session_orbs==0);
    assert(g.save.searches==0 && g.screen==STATE_RADAR);
    int first=-1;
    for(int i=0;i<MAX_DREAM_ORBS;i++)if(g.dream_orbs[i].alive){first=i;break;}
    assert(first>=0);
    int start_x=g.dream_orbs[first].x;
    int start_ttl=g.dream_orbs[first].ttl;
    game_tick(&g);
    assert(g.dream_orbs[first].ttl==start_ttl-1);
    assert(g.dream_orbs[first].x!=start_x);
    assert(shoot_all(&g)==3);
    assert(g.session_orbs==3 && g.save.orbs==3);
    assert(g.save.total_orbs==3 && g.save.searches==1);
    assert(g.screen==STATE_RESULTS && game_active_dream_orbs(&g)==0);
    assert(game_active_dream_orbs(NULL)==0);

    /* Large cloud bursts produce chains that shrink their TTL, capped
       below 20 collected Dream Orbs per cloud in the DS adaptation. */
    fresh_cloud(&g,30);
    assert(g.orb_group_target==4 && game_active_dream_orbs(&g)==4);
    int initial_ttl=g.dream_orbs[first].ttl;
    int count=shoot_all(&g);
    assert(count>4 && count<=DREAM_ORB_CHAIN_LIMIT);
    assert(g.session_orbs==count);
    assert(g.screen==STATE_RESULTS && g.save.searches==1);
    assert(g.orb_chain_stage>0);
    assert(initial_ttl>=180);
    assert(g.session_color_counts[ORB_PINK]==count);

    /* Missing any one Orb breaks a chain, and expired Orbs are never
       automatically credited. */
    fresh_cloud(&g,30);
    assert(game_active_dream_orbs(&g)==4);
    int missed=-1;
    for(int i=0;i<MAX_DREAM_ORBS;i++)if(g.dream_orbs[i].alive){missed=i;break;}
    assert(missed>=0);
    g.dream_orbs[missed].ttl=1;
    game_tick(&g);
    assert(!g.dream_orbs[missed].alive && !g.orb_chain_valid);
    assert(shoot_all(&g)==3);
    assert(g.screen==STATE_RESULTS && g.session_orbs==3);

    /* When every remaining Orb times out, results appear with zero reward. */
    fresh_cloud(&g,0);
    for(int i=0;i<MAX_DREAM_ORBS;i++)if(g.dream_orbs[i].alive)g.dream_orbs[i].ttl=1;
    game_tick(&g);
    assert(g.screen==STATE_RESULTS);
    assert(g.session_orbs==0 && g.save.orbs==0);
    assert(g.save.searches==1 && game_active_dream_orbs(&g)==0);
    puts("PASS: separate moving Dream Orbs, timed misses, bounded split chains and no phantom currency");
    return 0;
}
