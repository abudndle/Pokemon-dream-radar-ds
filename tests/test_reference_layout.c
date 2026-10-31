#include "reference_layout.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
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
    assert(dr_transfer_button_at(27,171)==0);
    assert(dr_transfer_button_at(188,171)==1);
    assert(dr_transfer_button_at(125,20)==-1);
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
    }
    assert(dr_shop_hit(128,25)==-1);
    assert(dr_shop_hit(128,170)==-1);
    assert(dr_shop_hit(1,50)==-1);
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
    puts("PASS: screenshot-aligned support hitboxes, six-by-two archive tray and live radar counts");
    return 0;
}
