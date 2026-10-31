#include "game.h"
#include <assert.h>
#include <stdio.h>
#include <stdint.h>

static void start(Game *g, int ext) {
    g->screen=STATE_LAB;
    g->save.cloud_count=1;
    g->save.orbs=4000;
    g->save.total_orbs=4000;
    game_begin_search(g,ext);
    assert(g->screen==STATE_RADAR);
}
static void collect_cloud_color(Game *g,int color) {
    start(g,EXT_BASIC);
    g->active_clouds=1;
    g->clouds[0].alive=1;
    g->clouds[0].kind=0; /* No encounter: pure orb reward */
    g->clouds[0].x=105;
    g->clouds[0].y=90;
    g->aim_x=105;g->aim_y=90;
    g->save.frames_played=(uint32_t)(color*45+3);
    assert(game_orb_live_color(g)==(OrbColor)color);
    game_fire(g);
    assert(g->screen==STATE_RADAR && game_active_dream_orbs(g)>=3);
    assert(g->session_orbs==0); /* Breaking a cloud does not grant currency. */
    for(int shot=0;shot<DREAM_ORB_CHAIN_LIMIT && g->screen==STATE_RADAR;shot++) {
        int slot=-1;
        for(int i=0;i<MAX_DREAM_ORBS;i++)
            if(g->dream_orbs[i].alive){slot=i;break;}
        assert(slot>=0);
        g->aim_x=g->dream_orbs[slot].x;
        g->aim_y=g->dream_orbs[slot].y;
        /* Each separate orb changes color independently while waiting.
           Aim for the requested color before firing, without using time
           ticks that would move the orb out from under the reticle. */
        unsigned off=g->dream_orbs[slot].color_phase%4u;
        unsigned target=((unsigned)color+4u-off)%4u;
        g->save.frames_played=target*45u+3u;
        assert(game_dream_orb_color(g,slot)==(OrbColor)color);
        game_fire(g);
    }
    assert(g->screen==STATE_RESULTS && g->session_orbs>=3);
    assert(g->session_color_counts[color]==g->session_orbs);
    assert(game_orb_color(g)==(OrbColor)color);
}

int main(void) {
    Game g;
    game_new(&g,123);
    assert(game_orb_color(&g)==ORB_PINK);
    assert(game_orb_live_color(&g)==ORB_PINK);
    assert(game_orb_color_name(ORB_BLUE)[0]=='B');
    assert(game_orb_color_name((OrbColor)-1)[0]=='U');

    for(int phase=0;phase<4;phase++) {
        game_new(&g,99);
        g.save.story_phase=(uint8_t)phase;
        for(int color=0;color<=phase;color++) {
            g.save.frames_played=(uint32_t)(color*45+3);
            assert(game_orb_live_color(&g)==(OrbColor)color);
        }
        g.save.frames_played=(uint32_t)((phase+1)*45+3);
        assert(game_orb_live_color(&g)==ORB_PINK);
    }

    for(int color=0;color<4;color++) {
        game_new(&g,125);
        g.save.story_phase=3;
        collect_cloud_color(&g,color);
        assert(g.save.reserved[13]==ORB_COLOR_LAYOUT_MARKER);
        assert(g.save.reserved[12]==color);
        assert(g.requested_save==1);
        assert(g.save.searches==1);

        /* The next scan must use the previous search's dominant color. */
        start(&g,EXT_RETRIEVAL);
        assert(g.search_orb_color==color);
        assert(g.session_color_counts[color]==0);
        assert(game_leave_search(&g));
        assert(game_orb_color(&g)==(OrbColor)color); /* zero reward does not overwrite */

        /* Search color must survive game save/reload without a schema bump. */
        const char *file="build/test_orb_colors.sav";
        assert(game_save(&g,file));
        Game restored;
        game_new(&restored,7);
        assert(game_load(&restored,file));
        assert(game_orb_color(&restored)==(OrbColor)color);
        remove(file);
    }

    /* Older version-3 saves without the marker must migrate to pink. */
    game_new(&g,126);
    g.save.story_phase=3;
    g.save.reserved[12]=3;
    g.save.reserved[13]=0;
    const char *legacy="build/test_orb_colors_legacy.sav";
    assert(game_save(&g,legacy));
    Game migrated;
    game_new(&migrated,5);
    assert(game_load(&migrated,legacy));
    assert(game_orb_color(&migrated)==ORB_PINK);
    assert(migrated.save.reserved[13]==ORB_COLOR_LAYOUT_MARKER);
    assert(migrated.requested_save==1);
    remove(legacy);

    /* Original preferred-color table for basic species (0..14):
       pink allows 0..8 except Ralts, etc.; blue permits Smoochum or
       Spiritomb. Dedicated Extension Pokemon are unaffected. */
    static const unsigned color_masks[15]={
        1,3,3,3,3,3,3,5,5,6,3,2,8,9,5
    };
    int found_per_color[4]={0};
    for(unsigned seed=1;seed<512;seed++)for(int color=0;color<4;color++) {
        game_new(&g,seed);
        g.save.story_phase=3;
        g.save.reserved[12]=(uint8_t)color;
        start(&g,EXT_RETRIEVAL);
        assert(g.search_orb_color==color);
        g.aim_x=g.clouds[0].x;g.aim_y=g.clouds[0].y;
        game_fire(&g);
        assert(g.screen==STATE_SPHERE);
        if(g.session_type==0) {
            assert(g.session_species>=0 && g.session_species<15);
            assert(color_masks[g.session_species] & (1u<<color));
            found_per_color[color]++;
        } else {
            assert(g.session_species==-1 && g.session_item>=0);
        }
    }
    for(int color=0;color<4;color++)assert(found_per_color[color]>50);
    puts("PASS: unlocked Dream Orb hues, next-search preference, encounter masks, save migration");
    return 0;
}
