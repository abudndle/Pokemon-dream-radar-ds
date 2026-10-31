/* Auto-derived from ROM MnIf_S_TitleList.bclyt.
 * Coordinates are scaled from the source 320x240 pane coordinate system.
 * Vertical origin (45px) is provisional until BCLAN motion is decoded.
 */
#ifndef DREAM_RADAR_TITLE_PANES_H
#define DREAM_RADAR_TITLE_PANES_H
typedef struct { int x,y,w,h; } DrPaneRect;
static const DrPaneRect dr_title_panes[4] = {
    {13,45,229,27},
    {13,77,229,27},
    {13,109,229,27},
    {13,141,229,27},
 };
static int dr_title_hit(int x,int y) {
    for(int i=0;i<4;i++) {
        const DrPaneRect *r=&dr_title_panes[i];
        if(x>=r->x && x<r->x+r->w && y>=r->y && y<r->y+r->h)return i;
    }
    return -1;
}
#endif
