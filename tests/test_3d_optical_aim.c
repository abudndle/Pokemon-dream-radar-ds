#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "game.h"
#include "../source_3d/optical_aim.h"

static uint16_t frame[256*192];
static void pattern(int dx) {
    for(int y=0;y<192;y++)for(int x=0;x<256;x++) {
        unsigned v=(unsigned)((x+dx)/8*17+(y/8)*37+((x+dx)/16)*19);
        unsigned p=(v^(v>>4))&31u;
        frame[y*256+x]=(uint16_t)(p | (p<<5) | (p<<10));
    }
}
int main(void) {
    Game g;Dr3dOpticalAim state={0};
    game_new(&g,7);
    g.screen=STATE_SPHERE;g.camera_ok=1;g.camera_active=1;
    g.save.optical_aim=1;
    int x=g.aim_x,y=g.aim_y;
    pattern(0);
    assert(!dr3d_optical_step(&state,&g,frame,0));
    assert(!state.valid && g.aim_x==x && g.aim_y==y);
    assert(!dr3d_optical_step(&state,&g,frame,1));
    assert(state.valid && g.aim_x==x && g.aim_y==y);
    pattern(0);
    assert(!dr3d_optical_step(&state,&g,frame,1));
    pattern(8);
    (void)dr3d_optical_step(&state,&g,frame,1);
    assert(g.aim_x>=6 && g.aim_x<=250 && g.aim_y>=6 && g.aim_y<=185);
    g.screen=STATE_RESULTS;
    assert(!dr3d_optical_step(&state,&g,frame,1));
    assert(!state.valid);
    g.screen=STATE_SPHERE;g.save.optical_aim=0;
    assert(!dr3d_optical_step(&state,&g,frame,1));
    assert(!state.valid);
    assert(!dr3d_optical_step(NULL,&g,frame,1));
    assert(!dr3d_optical_step(&state,NULL,frame,1));
    assert(!dr3d_optical_step(&state,&g,NULL,1));
    puts("PASS: camera optical sampling uses DS-only fallback, optional gating, and bounded aim");
    return 0;
}
