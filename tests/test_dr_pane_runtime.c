#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "../source/dr_pane_runtime.h"
#include "../source/dr_title_runtime.h"

static void title_geometry(void) {
    assert(dr_title_runtime_available());
    for(int i=0;i<4;i++) {
        DrPaneRect r={0},reference=dr_title_panes[i];
        assert(dr_title_runtime_rect(i,&r));
        assert(r.x==reference.x && r.y==reference.y);
        assert(r.w==reference.w && r.h==reference.h);
        assert(dr_title_runtime_hit(r.x+r.w/2,r.y+r.h/2)==i);
        assert(dr_title_runtime_hit(r.x,r.y)==i);
        assert(dr_title_runtime_hit(r.x+r.w,r.y)==-1);
        if(i)assert(r.y-dr_title_panes[i-1].y==32);
    }
    assert(dr_title_runtime_hit(0,0)==-1);
    assert(!dr_title_runtime_rect(4,0));
    assert(!dr_title_runtime_rect(-1,0));
    assert(!dr_title_runtime_rect(1,0));
    assert(dr_title_runtime_hit(127,191)==-1);
}
static void curve_sampling(void) {
    const DrUiKey keys[]={{0,0,2},{10,10,0}};
    DrUiTrack hermite={1,0,2,2,keys};
    float x=999;
    assert(dr_ui_sample(&hermite,0,&x) && x==0);
    assert(dr_ui_sample(&hermite,5,&x) && fabsf(x-7.5f)<0.0001f);
    assert(dr_ui_sample(&hermite,10,&x) && x==10);
    assert(dr_ui_sample(&hermite,20,&x) && x==10);
    const DrUiKey repeated[]={{0,1,0},{5,2,0},{5,3,0},{10,4,0}};
    DrUiTrack step={1,0,1,4,repeated};
    assert(dr_ui_sample(&step,4,&x) && x==1);
    assert(dr_ui_sample(&step,5,&x) && x==3);
    assert(dr_ui_sample(&step,9,&x) && x==3);
    DrUiTrack bad={1,0,2,4,repeated};
    assert(dr_ui_sample(&bad,5,&x) && x==3);
    const DrUiKey unordered[]={{5,1,0},{4,2,0}};
    bad.keys=unordered;bad.count=2;
    assert(!dr_ui_sample(&bad,5,&x));
    const DrUiKey nan_keys[]={{0,NAN,0}};
    bad.keys=nan_keys;bad.count=1;
    assert(!dr_ui_sample(&bad,0,&x));
    assert(!dr_ui_sample(&hermite,-1,&x));
    assert(!dr_ui_sample(&hermite,NAN,&x));
    assert(!dr_ui_sample(0,1,&x));
}
static void hierarchy_and_animation(void) {
    DrUiPane nodes[3]={
        {-1,128,96,200,100,1,1,0,4,1,255,1},
        {0,0,0,20,10,1,1,0,4,1,128,0},
        {1,6,0,20,10,1,1,0,4,1,128,0}
    };
    DrUiFrame frames[3]={0};
    assert(dr_ui_evaluate(nodes,3,0,0,frames,3));
    assert(frames[0].x==28 && frames[0].y==46);
    assert(frames[1].x==118 && frames[1].y==91);
    assert(frames[2].x==124 && frames[2].y==91);
    assert(frames[2].alpha==64 && frames[2].visible);
    assert(dr_ui_hit(&frames[2],125,95));
    assert(!dr_ui_hit(&frames[2],100,100));
    const DrUiKey moving[]={{0,0,0},{10,20,0}};
    DrUiTrack track={1,0,2,2,moving};
    DrUiAnimation loop={&track,1,10,1};
    assert(dr_ui_evaluate(nodes,3,&loop,15,frames,3));
    assert(frames[1].x==128); /* moved +10 and retained center anchor */
    assert(frames[2].x==134); /* child inherits translation */
    assert(dr_ui_evaluate(nodes,3,&loop,25,frames,3));
    assert(frames[1].x==128);
    /* Original source geometry remains immutable while animation plays. */
    assert(nodes[1].x==0);
    nodes[1].rotation_deg=90;
    assert(dr_ui_evaluate(nodes,3,0,0,frames,3));
    assert(frames[1].w==10 && frames[1].h==20);
    nodes[1].rotation_deg=0;
    nodes[0].visible=0;
    assert(dr_ui_evaluate(nodes,3,0,0,frames,3));
    assert(!frames[1].visible && !frames[2].visible);
    nodes[0].visible=1;
    nodes[2].x=100;
    assert(dr_ui_evaluate(nodes,3,0,0,frames,3));
    assert(!frames[2].visible || frames[2].w==0); /* clipped to parent */
    nodes[2].x=6;
    nodes[2].parent=2;
    frames[0].x=777;
    assert(!dr_ui_evaluate(nodes,3,0,0,frames,3));
    assert(frames[0].x==777); /* fail atomically */
    nodes[2].parent=1;
    nodes[0].origin=255;
    assert(!dr_ui_evaluate(nodes,3,0,0,frames,3));
    nodes[0].origin=4;
    const DrUiTrack ztrack={1,2,2,2,moving}; /* unsupported Z */
    const DrUiAnimation unsupported={&ztrack,1,10,0};
    assert(!dr_ui_evaluate(nodes,3,&unsupported,1,frames,3));
    assert(!dr_ui_evaluate(nodes,DR_PANE_MAX_NODES+1,0,0,frames,3));
}
int main(void) {
    title_geometry();
    curve_sampling();
    hierarchy_and_animation();
    puts("PASS: title BCLYT buttons, affine pane trees, clipping, touch and Hermite/step animation");
    return 0;
}
