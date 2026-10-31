#include "game.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

/* Verify that gameplay rewards survive the on-disk private save format. */
int main(void) {
    char path[]="/tmp/dr_progress_XXXXXX";
    int fd=mkstemp(path);
    assert(fd>=0);
    assert(close(fd)==0);
    Game g, loaded;
    game_new(&g,13579);
    g.screen=STATE_SPHERE;
    g.capture_timeout=100;
    g.session_type=0;
    g.session_species=15;
    g.ext_selection=EXT_TORNADUS;
    game_capture(&g);
    assert(g.screen==STATE_RESULTS && g.save.story_phase==1);
    g.screen=STATE_SPHERE;
    g.capture_timeout=100;
    g.session_type=1;
    g.session_item=7;
    g.ext_selection=EXT_RETRIEVAL;
    game_capture(&g);
    assert(g.screen==STATE_RESULTS);
    assert(g.save.pending_count==1 && g.save.pending[0]==15);
    assert(g.save.pending_items[0]==1);
    assert(game_item_slot_kind(&g,0)==7);
    uint32_t searches=g.save.searches;
    assert(game_save(&g,path));
    game_new(&loaded,98765);
    assert(game_load(&loaded,path));
    assert(loaded.save.story_phase==1);
    assert(loaded.save.caught_count==1);
    assert(loaded.save.pending_count==1 && loaded.save.pending[0]==15);
    assert(loaded.save.pending_items[0]==1);
    assert(game_item_slot_kind(&loaded,0)==7);
    assert(loaded.save.searches==searches);
    assert(loaded.save.reserved[8]==ITEM_LAYOUT_MARKER);
    assert(unlink(path)==0);
    puts("PASS: captured Pokémon, research items and progression survive save reload");
    return 0;
}
