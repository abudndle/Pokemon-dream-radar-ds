#include "game.h"
#include <assert.h>
#include <stdio.h>
/* One real gameplay sequence: scan -> cloud hit -> timed sphere ->
   support activation -> capture -> queued item reward -> results. */
int main(void) {
    Game g;
    game_new(&g, 12345);
    g.screen=STATE_RADAR;
    g.ext_selection=EXT_DOWSING;
    g.active_clouds=1;
    g.cloud_hit=0;
    g.clouds[0].alive=1;
    g.clouds[0].kind=1;
    g.clouds[0].x=120;
    g.clouds[0].y=80;
    g.aim_x=120;
    g.aim_y=80;
    g.save.goods[0]=1;
    g.save.upgrades[0]=5;
    uint32_t searches=g.save.searches;
    game_fire(&g);
    assert(g.screen==STATE_SPHERE);
    assert(g.session_type==1);
    assert(g.session_species==-1);
    assert(g.session_item>=0 && g.session_item<RESEARCH_ITEM_TYPES);
    assert(g.cloud_hit==1);
    assert(game_use_support(&g,0)==1);
    assert(g.save.goods[0]==0);
    assert(g.freeze_frames==300);
    g.aim_x=g.sphere_x;
    g.aim_y=g.sphere_y;
    for(int i=0;i<10 && g.screen==STATE_SPHERE;i++)
        game_fire(&g);
    assert(g.screen==STATE_RESULTS);
    assert(g.session_caught==-2);
    assert(g.save.searches==searches+1);
    assert(g.freeze_frames==0);
    assert(g.save.pending_items[0]==1);
    assert(game_item_slot_kind(&g,0)==g.session_item);
    assert(game_use_support(&g,0)==0);
    assert(g.requested_save==1);
    /* Pokémon capture through the same gameplay shot path. */
    game_new(&g,23456);
    g.screen=STATE_SPHERE;
    g.ext_selection=EXT_BASIC;
    g.session_type=0;
    g.session_species=4;
    g.session_item=-1;
    g.sphere_x=g.aim_x=128;
    g.sphere_y=g.aim_y=96;
    g.capture_timeout=100;
    g.capture_hp=225;
    g.save.upgrades[0]=5;
    searches=g.save.searches;
    game_fire(&g);
    assert(g.screen==STATE_RESULTS);
    assert(g.session_caught==4);
    assert(g.save.pending_count==1 && g.save.pending[0]==4);
    assert(g.save.caught_count==1);
    assert(g.save.searches==searches+1);

    /* When Pokémon storage is full, a hit must open a deliberate replacement
       prompt rather than silently overwriting captured Pokémon. */
    game_new(&g,34567);
    g.screen=STATE_SPHERE;
    g.ext_selection=EXT_BASIC;
    g.session_type=0;
    g.session_species=5;
    g.session_item=-1;
    g.sphere_x=g.aim_x=128;
    g.sphere_y=g.aim_y=96;
    g.capture_timeout=100;
    g.capture_hp=225;
    g.save.upgrades[0]=5;
    g.save.pending_count=MAX_CAUGHT;
    for(int i=0;i<MAX_CAUGHT;i++)g.save.pending[i]=(uint8_t)i;
    game_fire(&g);
    assert(g.screen==STATE_REPLACE);
    assert(g.replace_kind==REPLACE_POKEMON);
    assert(g.save.pending[0]==0 && g.save.pending[1]==1);
    assert(game_replace_pending(&g,2)==1);
    assert(g.screen==STATE_RESULTS);
    assert(g.save.pending_count==MAX_CAUGHT);
    assert(g.save.pending[2]==5);
    assert(g.save.caught_count==1);
    assert(g.session_caught==5);
    assert(g.requested_save==1);

    /* A cancellation must preserve all original storage slots. */
    game_new(&g,45678);
    g.screen=STATE_SPHERE;
    g.ext_selection=EXT_BASIC;
    g.session_type=0;
    g.session_species=6;
    g.sphere_x=g.aim_x=128;
    g.sphere_y=g.aim_y=96;
    g.capture_timeout=100;
    g.capture_hp=225;
    g.save.upgrades[0]=5;
    g.save.pending_count=MAX_CAUGHT;
    for(int i=0;i<MAX_CAUGHT;i++)g.save.pending[i]=(uint8_t)i;
    game_fire(&g);
    assert(g.screen==STATE_REPLACE);
    assert(game_cancel_pending_replace(&g)==1);
    assert(g.screen==STATE_RESULTS && g.session_caught==-4);
    assert(g.save.caught_count==0);
    for(int i=0;i<MAX_CAUGHT;i++)assert(g.save.pending[i]==i);
    /* All six research item stacks are full: capture must request a choice. */
    game_new(&g,56789);
    g.screen=STATE_SPHERE;
    g.ext_selection=EXT_RETRIEVAL;
    g.session_type=1;
    g.session_item=6;
    g.session_species=-1;
    g.capture_timeout=100;
    for(int i=0;i<MAX_ITEMS;i++) {
        g.save.pending_items[i]=MAX_ITEM_STACK;
        g.save.reserved[2+i]=(uint8_t)(i+1);
    }
    game_capture(&g);
    assert(g.screen==STATE_REPLACE && g.replace_kind==REPLACE_ITEM);
    assert(g.replace_value==6);
    for(int i=0;i<MAX_ITEMS;i++)assert(g.save.pending_items[i]==MAX_ITEM_STACK);
    assert(game_replace_pending(&g,3)==1);
    assert(g.screen==STATE_RESULTS && g.session_caught==-2);
    assert(g.save.pending_items[3]==1);
    assert(game_item_slot_kind(&g,3)==6);
    for(int i=0;i<MAX_ITEMS;i++)if(i!=3)assert(g.save.pending_items[i]==MAX_ITEM_STACK);

    /* Declining a full item-store choice keeps every original item stack. */
    game_new(&g,67890);
    g.screen=STATE_SPHERE;
    g.ext_selection=EXT_DOWSING;
    g.session_type=1;
    g.session_item=8;
    g.session_species=-1;
    g.capture_timeout=100;
    for(int i=0;i<MAX_ITEMS;i++) {
        g.save.pending_items[i]=MAX_ITEM_STACK;
        g.save.reserved[2+i]=(uint8_t)(i+1);
    }
    game_capture(&g);
    assert(g.screen==STATE_REPLACE && g.replace_kind==REPLACE_ITEM);
    assert(game_cancel_pending_replace(&g)==1);
    assert(g.screen==STATE_RESULTS && g.session_caught==-4);
    for(int i=0;i<MAX_ITEMS;i++) {
        assert(g.save.pending_items[i]==MAX_ITEM_STACK);
        assert(game_item_slot_kind(&g,i)==i);
    }
    /* Corrupt queue lengths must not permit an out-of-bounds replacement. */
    game_new(&g,78901);
    g.screen=STATE_REPLACE;
    g.replace_kind=REPLACE_POKEMON;
    g.replace_value=7;
    g.save.pending_count=MAX_CAUGHT+1;
    for(int i=0;i<MAX_CAUGHT;i++)g.save.pending[i]=(uint8_t)i;
    assert(!game_replace_pending(&g,MAX_CAUGHT));
    assert(!game_replace_pending(&g,0));
    assert(g.screen==STATE_REPLACE && g.save.caught_count==0);
    for(int i=0;i<MAX_CAUGHT;i++)assert(g.save.pending[i]==i);
    g.save.pending_count=MAX_CAUGHT;
    assert(!game_replace_pending(&g,MAX_CAUGHT));
    assert(game_replace_pending(&g,5));
    assert(g.screen==STATE_RESULTS && g.save.pending[5]==7);
    puts("PASS: Pokémon/item captures, bounded storage replacement and results");
    return 0;
}
