#include "reference_layout.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void full_capture(Game *g,int item) {
    game_new(g,42);
    g->save.pending_count=MAX_CAUGHT;
    for(int i=0;i<MAX_CAUGHT;i++)g->save.pending[i]=(uint8_t)i;
    for(int i=0;i<MAX_ITEMS;i++) {
        g->save.pending_items[i]=MAX_ITEM_STACK;
        g->save.reserved[2+i]=(uint8_t)(i+1);
    }
    g->ext_selection=EXT_BASIC;
    g->screen=STATE_SPHERE;
    g->capture_timeout=100;
    g->session_type=item;
    g->session_species=item?-1:9;
    g->session_item=item?22:-1;
    game_capture(g);
    assert(g->screen==STATE_REPLACE);
    g->requested_save=0;
}
static void unchanged(Game *g,const SaveData *before) {
    assert(!memcmp(&g->save,before,sizeof *before));
    assert(!g->requested_save);
}
int main(void) {
    /* Match every selectable pixel to the actual 236x22 painted row.
       Margins, three-pixel row gaps and footer cannot arm replacement. */
    for(int y=0;y<192;y++)for(int x=0;x<256;x++) {
        int expected=-1;
        for(int row=0;row<6;row++) {
            int top=3+25*row;
            assert(dr_replace_row_top(row)==top);
            if(x>=10 && x<246 && y>=top && y<top+22)expected=row;
        }
        assert(dr_replace_hit(x,y)==expected);
    }
    assert(dr_replace_hit(-1,20)==-1 && dr_replace_hit(256,20)==-1);
    assert(dr_replace_hit(100,-1)==-1 && dr_replace_hit(100,192)==-1);
    assert(dr_replace_row_top(-1)==-1 && dr_replace_row_top(6)==-1);
    for(int item=0;item<2;item++) {
        Game g;full_capture(&g,item);
        SaveData before=g.save;
        int timer=g.capture_timeout;
        /* A first press merely arms, and the decision does not run the clock. */
        assert(game_confirm_pending_replace(&g)==REPLACE_ARMED);
        unchanged(&g,&before);
        game_tick(&g);
        assert(g.capture_timeout==timer && g.screen==STATE_REPLACE);
        /* Play-time accounting continues while encounter decisions pause. */
        before.frames_played++;
        unchanged(&g,&before);
        /* Navigation invalidates the first confirmation. */
        assert(game_select_pending_replace(&g,5));
        assert(g.replace_selected==5 && !g.replace_confirm);
        assert(game_confirm_pending_replace(&g)==REPLACE_ARMED);
        unchanged(&g,&before);
        assert(!game_select_pending_replace(&g,-1));
        assert(!game_select_pending_replace(&g,6));
        assert(g.replace_selected==5 && g.replace_confirm);
        /* Touching another row cannot spend the previous row's confirmation. */
        int selected=dr_replace_hit(128,dr_replace_row_top(2)+10);
        assert(game_select_pending_replace(&g,selected));
        assert(!g.replace_confirm);
        assert(game_confirm_pending_replace(&g)==REPLACE_ARMED);
        unchanged(&g,&before);
        char text[80],expected[80];
        if(item)snprintf(expected,sizeof expected,"OLD: %s x255",game_item_name(2));
        else snprintf(expected,sizeof expected,"OLD: %s",game_species_name(2));
        Game preview_before=g;
        dr_replace_old_label(&g,text,sizeof text);
        assert(!strcmp(text,expected));
        assert(!memcmp(&preview_before,&g,sizeof g));
        assert(game_select_pending_replace(&g,selected)); /* Same-row second tap. */
        assert(game_confirm_pending_replace(&g)==REPLACE_COMMITTED);
        assert(g.screen==STATE_RESULTS && g.replaced_slot==2 && g.requested_save);
        assert(!g.replace_confirm);
        assert(g.save.searches==before.searches+1);
        for(int i=0;i<6;i++) {
            assert(g.save.pending[i]==(item || i!=2?before.pending[i]:9));
            assert(g.save.pending_items[i]==(!item || i!=2?MAX_ITEM_STACK:1));
            assert(game_item_slot_kind(&g,i)==(item && i==2?22:i));
        }
        assert(g.save.caught_count==before.caught_count+(item?0:1));
        Game committed=g;
        assert(game_confirm_pending_replace(&g)==REPLACE_REJECTED);
        assert(!memcmp(&committed,&g,sizeof g));
        /* Cancel after arming retains all storage and awards no capture. */
        full_capture(&g,item);before=g.save;
        assert(game_confirm_pending_replace(&g)==REPLACE_ARMED);
        assert(game_cancel_pending_replace(&g));
        assert(g.save.caught_count==before.caught_count);
        assert(!memcmp(g.save.pending,before.pending,sizeof before.pending));
        assert(!memcmp(g.save.pending_items,before.pending_items,sizeof before.pending_items));
        assert(g.screen==STATE_RESULTS && !g.replace_confirm && g.session_caught==-4);
        /* A corrupt or stale selection cannot be armed or committed. */
        full_capture(&g,item);before=g.save;
        g.replace_selected=6;g.replace_confirm=1;
        assert(game_confirm_pending_replace(&g)==REPLACE_REJECTED && !g.replace_confirm);
        unchanged(&g,&before);
        g.replace_selected=0;g.replace_confirm=1;g.replace_value=-1;
        assert(game_confirm_pending_replace(&g)==REPLACE_REJECTED && !g.replace_confirm);
        unchanged(&g,&before);
    }
    assert(!game_select_pending_replace(NULL,0));
    assert(game_confirm_pending_replace(NULL)==REPLACE_REJECTED);
    char text[40];dr_replace_old_label(NULL,text,sizeof text);
    assert(!strcmp(text,"OLD: No valid slot selected"));
    char tiny[2]={'x','x'};dr_replace_old_label(NULL,tiny,sizeof tiny);assert(!tiny[1]);
    dr_replace_old_label(NULL,NULL,0);
    puts("PASS: replacement row geometry, preview, two-step decisions, cancellation and single commit");
    return 0;
}
