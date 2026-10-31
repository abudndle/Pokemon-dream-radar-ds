#include "reference_layout.h"
#include "title_panes_generated.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    const int quad[8]={100,70,130,100,100,130,70,100};
    assert(dr_quad_hit(quad,100,100));
    assert(!dr_quad_hit(quad,71,71));
    assert(!dr_quad_hit(quad,129,129));
    assert(!dr_quad_hit(quad,-1,100));
    assert(!dr_quad_hit(NULL,100,100));
    const int flat[8]={20,20,20,20,20,20,20,20};
    assert(!dr_quad_hit(flat,20,20));
    for(int count=6;count<=7;count++) {
        for(int i=0;i<count;i++) {
            int y=dr_lab_row_top(i);
            assert(dr_lab_hit(10,y,count)==i);
            assert(dr_lab_hit(245,y+21,count)==i);
            assert(dr_lab_hit(128,y+22,count)==-1);
        }
        assert(dr_lab_hit(9,3,count)==-1);
        assert(dr_lab_hit(246,3,count)==-1);
        assert(dr_lab_hit(128,dr_lab_row_top(count),count)==-1);
    }

    /* Shop rows use the shared quad hit tester without changing touch gaps. */
    for(int i=0;i<6;i++) {
        int top=dr_shop_row_top(i);
        assert(dr_shop_hit(10,top)==i);
        assert(dr_shop_hit(245,top+21)==i);
        assert(dr_shop_hit(128,top+22)==-1);
    }
    assert(dr_shop_hit(9,26)==-1);
    assert(dr_shop_hit(246,26)==-1);
    /* Original title layout: visual rectangles and touch targets must agree. */
    for(int i=0;i<4;i++) {
        const DrPaneRect *r=&dr_title_panes[i];
        assert(r->x>=0 && r->y>=0 && r->w>0 && r->h>0);
        assert(r->x+r->w<=256 && r->y+r->h<=192);
        assert(dr_title_hit(r->x+r->w/2,r->y+r->h/2)==i);
        assert(dr_title_hit(r->x,r->y)==i);
        assert(dr_title_hit(r->x+r->w-1,r->y+r->h-1)==i);
        /* 6px-wide/8px-high built-in glyphs must fit their source panes. */
        const char *labels[4]={"Start","Send Research Data","Credits","Records"};
        int glyph_width=0;
        for(const char *c=labels[i];*c;c++)glyph_width+=6;
        int label_x=r->x+(r->w-glyph_width)/2;
        int label_y=r->y+(r->h-8)/2;
        assert(label_x>=r->x && label_x+glyph_width<=r->x+r->w);
        assert(label_y>=r->y && label_y+8<=r->y+r->h);
        if(i>0)assert(dr_title_panes[i-1].y+dr_title_panes[i-1].h<=r->y);
    }
    assert(dr_title_hit(128,10)==-1);
    assert(dr_title_hit(128,185)==-1);
    /* Touch coordinates are bounded to the 256x192 DS viewport. */
    assert(dr_support_at(-2147483647,0)==-1);
    assert(dr_support_at(2147483647,0)==-1);
    assert(dr_support_at(0,-2147483647)==-1);
    assert(dr_support_at(0,2147483647)==-1);
    for(int i=0;i<3;i++) {
        int x,y;dr_support_center(i,&x,&y);
        assert(x>=0 && y>=0);
        assert(dr_support_at(x,y)==i);
    }
    {int x,y;dr_support_center(-1,&x,&y);assert(x==-1 && y==-1);}
    assert(dr_support_at(67,101)==0);
    assert(dr_support_at(190,101)==1);
    assert(dr_support_at(128,151)==2);
    assert(dr_support_at(128,26)==-1);
    assert(dr_support_at(245,179)==-1);
    assert(dr_support_at(-1,100)==-1);
    /* Footer control boundaries remain pixel-identical after quad integration. */
    assert(dr_transfer_button_at(9,157)==-1);
    assert(dr_transfer_button_at(120,157)==-1);
    assert(dr_transfer_button_at(137,157)==-1);
    assert(dr_transfer_button_at(246,157)==-1);
    assert(dr_transfer_button_at(119,189)==0);
    assert(dr_transfer_button_at(245,189)==1);
    assert(dr_transfer_button_at(27,171)==0);
    assert(dr_transfer_button_at(188,171)==1);
    assert(dr_transfer_button_at(125,20)==-1);
    assert(dr_transfer_button_at(10,157)==0);
    assert(dr_transfer_button_at(119,189)==0);
    assert(dr_transfer_button_at(138,157)==1);
    assert(dr_transfer_button_at(245,189)==1);
    assert(dr_transfer_button_at(127,171)==-1);
    assert(dr_transfer_button_at(9,171)==-1);
    assert(dr_transfer_button_at(246,171)==-1);
    assert(dr_transfer_button_at(40,156)==-1);
    assert(dr_transfer_button_at(40,190)==-1);
    for(int i=0;i<6;i++) {
        assert(dr_transfer_slot_at(30+i*33,45)==i);
        assert(dr_transfer_slot_at(30+i*33,88)==i+6);
    }
    assert(dr_transfer_slot_at(2,45)==-1);
    assert(dr_transfer_slot_at(200,160)==-1);
    for(int j=0;j<12;j++) {
        int x,y,w,h;
        dr_transfer_slot_rect(j,&x,&y,&w,&h);
        assert(w==28 && h==33);
        assert(dr_transfer_slot_at(x,y)==j);
        assert(dr_transfer_slot_at(x+w-1,y+h-1)==j);
        assert(dr_transfer_slot_at(x+w,y+h/2)!=j);
    }
    {int x,y,w,h;dr_transfer_slot_rect(12,&x,&y,&w,&h);assert(x==-1 && w==0); }
    for(int i=0;i<6;i++) {
        int y=dr_shop_row_top(i);
        assert(y==26+24*i);
        assert(dr_shop_hit(128,y+12)==i);
        assert(dr_shop_hit(10,y)==i);
        assert(dr_shop_hit(245,y+21)==i);
        assert(dr_shop_hit(128,y+22)==-1);
    }
    assert(dr_shop_hit(128,25)==-1);
    assert(dr_shop_hit(128,170)==-1);
    assert(dr_shop_hit(1,50)==-1);
    assert(dr_shop_hit(246,50)==-1);
    Game g;game_new(&g,0x4a51);
    game_begin_search(&g,EXT_BASIC);
    assert(g.screen==STATE_RADAR);
    int w,p;dr_radar_counts(&g,&w,&p);
    assert(w+p==dr_remaining_clouds(&g));
    /* kind=1 draws pink artwork; kind=0 draws white artwork. */
    int expected_white=0,expected_pink=0;
    for(int i=0;i<g.active_clouds;i++) {
        if(g.clouds[i].kind)expected_pink++;
        else expected_white++;
    }
    assert(w==expected_white && p==expected_pink);
    assert(dr_remaining_clouds(&g)==g.active_clouds);
    for(int i=0;i<g.active_clouds;i++){
        g.clouds[i].alive=0;
        assert(dr_remaining_clouds(&g)==g.active_clouds-i-1);
    }
    dr_radar_counts(&g,&w,&p);assert(!w&&!p);
    /* Malformed state or absent game must not read past cloud storage. */
    dr_radar_counts(NULL,&w,&p);
    assert(w==0 && p==0 && dr_remaining_clouds(NULL)==0);
    g.active_clouds=MAX_CLOUDS+500;
    for(int i=0;i<MAX_CLOUDS;i++){g.clouds[i].alive=1;g.clouds[i].kind=i%2;}
    dr_radar_counts(&g,&w,&p);
    assert(w+p==MAX_CLOUDS && dr_remaining_clouds(&g)==MAX_CLOUDS);
    g.active_clouds=-10;
    dr_radar_counts(&g,&w,&p);
    assert(!w && !p && !dr_remaining_clouds(&g));
    puts("PASS: screenshot-aligned support hitboxes, six-by-two archive tray and live radar counts");
    return 0;
}
