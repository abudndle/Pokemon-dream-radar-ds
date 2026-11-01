#include "dr_ui_scene.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

static void verify(const DrUiScene *s,DrUiRect rows[4]){
    assert(s && dr_ui_four_row_rects(s,0,rows));
    static const int expected_y[4]={0,44,79,114};
    for(int i=0;i<4;i++){
        assert(abs(rows[i].y-expected_y[i])<=2);
        assert(rows[i].x>=9 && rows[i].x<=23);
        assert(rows[i].w>=210 && rows[i].w<=237);
        assert(rows[i].h>=26 && rows[i].h<=40);
        assert(dr_ui_title_hit(rows,rows[i].x+rows[i].w/2,
                               rows[i].y+rows[i].h/2)==i);
        if(i)assert(rows[i-1].y+rows[i-1].h<=rows[i].y);
    }
    assert(dr_ui_title_hit(rows,128,170)==-1);
    assert(dr_ui_title_hit(rows,-1,50)==-1);
}
int main(int argc,char **argv){
    assert(argc==4);
    DrUiRect rows[4],animated[4];
    DrUiScene *base=dr_ui_scene_load(argv[1]);verify(base,rows);
    dr_ui_scene_free(base);
    DrUiScene *moving=dr_ui_scene_load(argv[2]);verify(moving,animated);
    assert(dr_ui_four_row_rects(moving,10,animated));
    assert(animated[3].y>=rows[3].y+7 && animated[3].y<=rows[3].y+9);
    for(int i=0;i<3;i++)assert(animated[i].y==rows[i].y);
    assert(dr_ui_four_row_rects(moving,100,animated)); /* one-shot clamp */
    assert(animated[3].y>=rows[3].y+7 && animated[3].y<=rows[3].y+9);
    assert(!dr_ui_four_row_rects(moving,-1,animated));
    dr_ui_scene_free(moving);
    assert(!dr_ui_scene_load(argv[3]));
    puts("PASS: authentic MainMenuList four rows, source bounds and private CLPA");
    return 0;
}
