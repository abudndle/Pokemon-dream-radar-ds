/* Original message labels, 23-type item queue, full-stack replace and v3 saves. */
#include "game.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static void item_capture(Game *g,int item) {
    g->screen=STATE_SPHERE;
    g->capture_timeout=100; /* A captured item requires an active encounter. */
    g->session_type=1;
    g->session_item=item;
    g->session_caught=-1;
    game_capture(g);
}
int main(void) {
    Game g;game_new(&g,9);
    assert(RESEARCH_ITEM_TYPES==23 && MAX_ITEMS==6);
    const char *names[]={"Red Shard","Blue Shard","Yellow Shard","Green Shard",
        "PP Up","Leppa Berry","Revive","Max Revive","Sun Stone","Moon Stone",
        "Fire Stone","Water Stone","Thunderstone","Leaf Stone","Sacred Ash",
        "Rare Candy","Star Piece","Heart Scale","Dawn Stone","King's Rock",
        "Life Orb","Focus Sash","Eviolite"};
    for(int i=0;i<RESEARCH_ITEM_TYPES;i++)assert(strcmp(game_item_name(i),names[i])==0);
    assert(strcmp(game_item_name(-1),"Unknown item")==0);
    assert(strcmp(game_item_name(23),"Unknown item")==0);

    /* High-ID research item types can be stored without expanding the six slots. */
    for(int i=0;i<MAX_ITEMS;i++) {
        item_capture(&g,17+i);
        assert(g.screen==STATE_RESULTS && g.session_caught==-2);
        assert(game_item_slot_kind(&g,i)==17+i);
    }
    item_capture(&g,22);
    assert(g.screen==STATE_RESULTS && g.save.pending_items[5]==2);
    uint8_t old[MAX_ITEMS];memcpy(old,g.save.pending_items,sizeof old);
    item_capture(&g,7);
    assert(g.screen==STATE_REPLACE && g.replace_value==7);
    assert(!memcmp(old,g.save.pending_items,sizeof old));
    assert(game_cancel_pending_replace(&g));
    assert(!memcmp(old,g.save.pending_items,sizeof old));
    item_capture(&g,7);
    assert(game_replace_pending(&g,2));
    assert(game_item_slot_kind(&g,2)==7 && g.save.pending_items[2]==1);
    assert(game_item_slot_kind(&g,5)==22 && g.save.pending_items[5]==2);

    char path[]="/tmp/dr_original_item_catalog_test.sav";
    assert(game_save(&g,path));
    Game loaded;game_new(&loaded,7);
    assert(game_load(&loaded,path));
    assert(game_item_slot_kind(&loaded,5)==22 && loaded.save.pending_items[5]==2);
    assert(game_item_slot_kind(&loaded,2)==7);
    /* A matching checksum is insufficient if item metadata isn't valid. */
    loaded.save.reserved[2+5]=RESEARCH_ITEM_TYPES+1;
    assert(!game_save(&loaded,path)); /* Invalid metadata cannot overwrite progress. */
    /* Simulate externally corrupted but checksummed item metadata to check
       that the loader independently rejects it. */
    loaded.save.checksum=game_checksum(&loaded.save);
    FILE *corrupt=fopen(path,"wb");assert(corrupt);
    assert(fwrite(&loaded.save,1,sizeof loaded.save,corrupt)==sizeof loaded.save);
    assert(fclose(corrupt)==0);
    assert(!game_load(&g,path));
    unlink(path);

    /* A text export identifies high-index items by their ORIGINAL names. */
    assert(game_export(&g,"/tmp/dr_original_item_catalog_export.txt"));
    FILE *f=fopen("/tmp/dr_original_item_catalog_export.txt","rb");assert(f);
    char text[3000]={0};assert(fread(text,1,sizeof(text)-1,f)>100);fclose(f);
    assert(strstr(text,"Max Revive") && strstr(text,"Eviolite"));
    unlink("/tmp/dr_original_item_catalog_export.txt");
    puts("PASS: 23 ROM-localized item names, six-stack limits, replacement, v3 migration, exports");
    return 0;
}
