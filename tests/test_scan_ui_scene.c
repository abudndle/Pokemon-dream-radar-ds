#include "dr_ui_scene.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

static void verify_source(const DrUiScene *scene,DrUiRect rows[4]) {
    assert(scene && dr_ui_rows_rects(scene,0,rows));
    for(int i=0;i<4;i++){
        /* Source MnIf_S_ScanList positions x=-5, y=157/117/77/37,
         * Touch width=300, height=36, 320x240 -> DS at y+45. */
        assert(rows[i].x>=2 && rows[i].x<=6);
        assert(rows[i].w>=237 && rows[i].w<=241);
        assert(abs(rows[i].y-(1+32*i))<=2);
        assert(rows[i].h>=27 && rows[i].h<=30);
        assert(dr_ui_rows_hit(rows,rows[i].x+rows[i].w/2,
                             rows[i].y+rows[i].h/2)==i);
        if(i>0)assert(rows[i-1].y+rows[i-1].h<=rows[i].y);
    }
    assert(dr_ui_rows_hit(rows,-1,0)==-1);
    assert(dr_ui_rows_hit(rows,128,174)==-1);
    assert(dr_ui_rows_hit(rows,256,191)==-1);
    assert(!dr_ui_rows_rects(scene,-1,rows));
    assert(!dr_ui_rows_rects(scene,NAN,rows));
}

int main(int argc,char **argv) {
    assert(argc==4);
    DrUiRect before[4], after[4];
    DrUiScene *scene=dr_ui_scene_load(argv[1]);
    verify_source(scene,before);
    dr_ui_scene_free(scene);
    scene=dr_ui_scene_load(argv[2]);
    verify_source(scene,before);
    assert(dr_ui_rows_rects(scene,10,after));
    assert(after[0].y<before[0].y);  /* pane's private translation moves up */
    assert(after[1].y==before[1].y);
    assert(after[2].y==before[2].y);
    assert(after[3].y==before[3].y);
    dr_ui_scene_free(scene);
    assert(!dr_ui_scene_load(argv[3]));
    puts("PASS: source ScanList four live touch panes, private CLPA motion and malformed rollback");
    return 0;
}
