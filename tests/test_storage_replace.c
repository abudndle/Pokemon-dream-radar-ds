/* Full storage must never overwrite stored Pokemon/items without a decision. */
#include "game.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static void fake_capture(Game *g,int kind,int id) {
    g->screen=STATE_SPHERE;
    g->session_type=kind;
    g->session_species=id;
    g->session_item=id;
    g->session_caught=-1;
    game_capture(g);
}

int main(void) {
    Game g;
    game_new(&g,0x123u);
    g.save.story_phase=3;
    g.save.pending_count=MAX_CAUGHT;
    for(int i=0;i<MAX_CAUGHT;i++)g.save.pending[i]=(uint8_t)i;
    g.ext_selection=EXT_HOOH;
    game_set_cart(&g,GAME_HEARTGOLD);
    uint8_t old_pokemon[MAX_CAUGHT];
    memcpy(old_pokemon,g.save.pending,sizeof old_pokemon);
    uint8_t old_legends=g.save.legends_caught;
    uint32_t old_caught=g.save.caught_count;
    fake_capture(&g,0,21); /* Ho-Oh */
    assert(g.screen==STATE_REPLACE && g.replace_kind==REPLACE_POKEMON);
    assert(!game_replace_pending(&g,-1));
    assert(!game_replace_pending(&g,MAX_CAUGHT));
    assert(!memcmp(g.save.pending,old_pokemon,sizeof old_pokemon));
    assert(g.save.legends_caught==old_legends && g.save.caught_count==old_caught);
    assert(game_cancel_pending_replace(&g));
    assert(!game_cancel_pending_replace(&g));
    assert(g.screen==STATE_RESULTS && g.session_caught==-4);
    assert(!memcmp(g.save.pending,old_pokemon,sizeof old_pokemon));
    assert(g.save.legends_caught==old_legends);
    assert(game_extension_unlocked(&g,EXT_HOOH)); /* still available */

    fake_capture(&g,0,21);
    assert(g.screen==STATE_REPLACE && g.replace_value==21);
    assert(game_replace_pending(&g,2));
    assert(g.screen==STATE_RESULTS && g.replaced_slot==2);
    assert(g.save.pending[2]==21 && g.save.pending_count==MAX_CAUGHT);
    assert(g.save.caught_count==old_caught+1);
    assert(g.save.legends_caught==(old_legends|(1<<3)));
    assert(!game_extension_unlocked(&g,EXT_HOOH));
    assert(!game_replace_pending(&g,0)); /* no duplicate resolution */
    for(int i=0;i<MAX_CAUGHT;i++)if(i!=2)assert(g.save.pending[i]==old_pokemon[i]);

    /* A new item joins its existing stack, then uses an unused stack slot. */
    Game items;game_new(&items,1);
    items.ext_selection=EXT_BASIC;
    fake_capture(&items,1,3);
    assert(items.screen==STATE_RESULTS && items.session_caught==-2);
    assert(game_item_slot_kind(&items,0)==3 && items.save.pending_items[0]==1);
    fake_capture(&items,1,3);
    assert(items.save.pending_items[0]==2);
    for(int i=0;i<MAX_ITEMS;i++) {
        items.save.pending_items[i]=MAX_ITEM_STACK;
        items.save.reserved[2+i]=(uint8_t)(i+1);
    }
    uint8_t snapshot[MAX_ITEMS];
    memcpy(snapshot,items.save.pending_items,sizeof snapshot);
    fake_capture(&items,1,4);
    assert(items.screen==STATE_REPLACE && items.replace_kind==REPLACE_ITEM);
    assert(!game_replace_pending(&items,MAX_ITEMS));
    assert(!memcmp(snapshot,items.save.pending_items,sizeof snapshot));
    assert(game_cancel_pending_replace(&items));
    assert(!memcmp(snapshot,items.save.pending_items,sizeof snapshot));
    fake_capture(&items,1,4);
    assert(game_replace_pending(&items,1));
    assert(items.save.pending_items[1]==1 && game_item_slot_kind(&items,1)==4);
    for(int i=0;i<MAX_ITEMS;i++)if(i!=1)
        assert(items.save.pending_items[i]==MAX_ITEM_STACK && game_item_slot_kind(&items,i)==i);
    assert(items.replaced_slot==1);

    /* Replacing something invalidates any existing archive-release proof. */
    char path[]="/tmp/dr_replacement_export.txt";
    assert(game_export(&items,path));
    assert(items.pending_export_signature);
    fake_capture(&items,1,4);
    assert(items.save.pending_items[1]==2);
    assert(!items.pending_export_signature);
    assert(!game_release_archived_pending(&items));
    unlink(path);

    /* Old version-3 homebrew saves used fixed indices as item types. Migrate. */
    Game old;game_new(&old,42);
    old.save.pending_items[4]=7;
    memset(old.save.reserved+2,0,7);
    assert(game_save(&old,path));
    Game migrated;game_new(&migrated,123);
    assert(game_load(&migrated,path));
    assert(migrated.requested_save);
    assert(migrated.save.reserved[8]==ITEM_LAYOUT_MARKER);
    assert(game_item_slot_kind(&migrated,4)==4);
    assert(migrated.save.pending_items[4]==7);
    assert(game_save(&migrated,path));
    Game again;game_new(&again,123);
    assert(game_load(&again,path));
    assert(again.save.pending_items[4]==7 && game_item_slot_kind(&again,4)==4);
    unlink(path);
    puts("PASS: full Pokemon/item replacement, cancellation, one-time legends, migration, archive safety");
    return 0;
}
