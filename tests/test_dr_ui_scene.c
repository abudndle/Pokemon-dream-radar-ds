#include <assert.h>
#include <stdio.h>
#include "dr_ui_scene.h"
static void base(const DrUiScene *s) {
    DrUiRect r[4];
    assert(dr_ui_title_rects(s,0,r));
    for(int i=0;i<4;i++) {
        assert(r[i].x==13);
        assert(r[i].y==45+32*i);
        assert(r[i].w==229);
        assert(r[i].h==27);
        assert(dr_ui_title_hit(r,r[i].x+r[i].w/2,r[i].y+r[i].h/2)==i);
    }
    assert(dr_ui_title_hit(r,0,0)==-1);
    assert(dr_ui_title_hit(r,256,192)==-1);
}
int main(int argc,char **argv){
    assert(argc==2 || argc==4);
    DrUiScene *s=dr_ui_scene_load(argv[1]);assert(s);
    base(s);dr_ui_scene_free(s);
    if(argc==4){
        s=dr_ui_scene_load(argv[2]);assert(s);
        DrUiRect r[4];
        assert(dr_ui_title_rects(s,5,r));
        assert(r[0].y==33); /* last duplicate-frame key: 145 */
        assert(r[1].y==77);
        assert(dr_ui_title_rects(s,10,r));assert(r[0].y==29);
        assert(dr_ui_title_rects(s,100,r));assert(r[0].y==29); /* one-shot clamp */
        assert(!dr_ui_title_rects(s,-1,r));
        dr_ui_scene_free(s);
        assert(!dr_ui_scene_load(argv[3]));
    }
    puts("PASS: BCLYT pane hierarchy, runtime CLPA sampling and title touch geometry");
    return 0;
}
