#include <assert.h>
#include <stdio.h>
#include "../source/title_panes_generated.h"
int main(void) {
    for(int i=0;i<4;i++) {
        DrPaneRect r=dr_title_panes[i];
        assert(dr_title_hit(r.x+r.w/2,r.y+r.h/2)==i);
        assert(dr_title_hit(0,r.y)==-1);
        if(i)assert(r.y-dr_title_panes[i-1].y==32);
    }
    assert(dr_title_hit(128,0)==-1);
    puts("ROM-derived title pane rectangles and hitboxes: PASS");
    return 0;
}
