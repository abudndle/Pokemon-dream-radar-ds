#include "dr_title_runtime.h"
/*
 * Geometry source: the owner's MnIf_S_TitleList.bclyt, extracted into
 * ui_mapping/original_pane_geometry.json. Four TouchXX bounds are 286x34,
 * anchored at origin=4, under SRT00 (Y=16), L00..03 (Y=130,90,50,10).
 * The source canvas is 320x240; scale .8 maps it to 256x192.
 *
 * The generated header is sourced from the recovered pane hierarchy.
 * The missing original BCLAN menu entrance still requires a provisional
 * vertical placement (center Y=175.4 DS px) to match the approved title
 * screenshot and existing four-row positions. Do not claim animation parity.
 * Y is inverted from 3DS pane coordinates to DS bitmap coordinates.
 */
#include "dr_title_pane_nodes_generated.h"
/* A privately staged source/private_title_clpa.h is optional. No original
 * BCLAN keyframe payload is included in this public repository. */
#if defined(__has_include)
# if __has_include("private_title_clpa.h")
#  include "private_title_clpa.h"
#  define DR_HAS_PRIVATE_TITLE_CLPA 1
# endif
#endif
#define title_nodes dr_title_source_nodes
static DrUiFrame title_frames[5];
static int title_ready;

int dr_title_runtime_frame(const DrUiAnimation *animation,float frame) {
    /* Atomically publish valid frames so a malformed private clip cannot
       move touch hitboxes independently of rendered menu elements. */
    DrUiFrame next[5];
#ifdef DR_HAS_PRIVATE_TITLE_CLPA
    if(!animation)animation=&dr_private_title_animation;
#endif
    if(!dr_ui_evaluate(title_nodes,5,animation,frame,next,5))return 0;
    for(unsigned i=0;i<5;i++)title_frames[i]=next[i];
    title_ready=1;
    return 1;
}
int dr_title_runtime_available(void) {
    if(!title_ready)dr_title_runtime_frame(0,0);
    return title_ready;
}
int dr_title_runtime_rect(int row,DrPaneRect *out) {
    if(row<0 || row>=4 || !out || !dr_title_runtime_available())return 0;
    const DrUiFrame *f=&title_frames[row+1];
    if(!f->visible)return 0;
    out->x=f->x;out->y=f->y;out->w=f->w;out->h=f->h;
    return 1;
}
int dr_title_runtime_hit(int x,int y) {
    if(!dr_title_runtime_available())return -1;
    for(int row=0;row<4;row++)
        if(dr_ui_hit(&title_frames[row+1],x,y))return row;
    return -1;
}
