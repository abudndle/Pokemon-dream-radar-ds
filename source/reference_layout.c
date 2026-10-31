#include "reference_layout.h"
static int absval(int v) { return v<0?-v:v; }
void dr_support_center(int index,int *x,int *y) {
    static const int cx[3]={67,190,128},cy[3]={101,101,151};
    if(x)*x=index>=0 && index<3?cx[index]:-1;
    if(y)*y=index>=0 && index<3?cy[index]:-1;
}
int dr_support_at(int x,int y) {
    if(x<0||x>255||y<0||y>191)return -1;
    for(int i=0;i<3;i++) {
        int sx,sy;dr_support_center(i,&sx,&sy);
        int dx=absval(x-sx),dy=absval(y-sy);
        if(dx<=44 && dy<=39 && 2*dx+dy<=105)return i;
    }
    return -1;
}
int dr_transfer_button_at(int x,int y) {
    if(x<5||x>250||y<157||y>189)return -1;
    return x<127?0:1;
}
/* One transfer geometry source for icons, selection outline and touch input. */
void dr_transfer_slot_rect(int index,int *x,int *y,int *w,int *h) {
    int valid=index>=0 && index<12;
    if(x)*x=valid?28+(index%6)*33:-1;
    if(y)*y=valid?30+(index/6)*47:-1;
    if(w)*w=valid?28:0;
    if(h)*h=valid?33:0;
}
int dr_transfer_slot_at(int x,int y) {
    if(x<0||x>=256||y<0||y>=192)return -1;
    for(int i=0;i<12;i++) {
        int sx,sy,sw,sh;
        dr_transfer_slot_rect(i,&sx,&sy,&sw,&sh);
        if(x>=sx && x<sx+sw && y>=sy && y<sy+sh)return i;
    }
    return -1;
}
int dr_shop_row_top(int index) {
    if(index<0 || index>=6)return -1;
    return 26 + 24*index;
}
int dr_shop_hit(int x,int y) {
    if(x<4 || x>251 || y<26 || y>=170)return -1;
    int index=(y-26)/24;
    return index<6?index:-1;
}
int dr_remaining_clouds(const Game *g) {
    int left=0;
    for(int i=0;i<g->active_clouds && i<MAX_CLOUDS;i++)if(g->clouds[i].alive)left++;
    return left;
}
void dr_radar_counts(const Game *g,int *white,int *pink) {
    int w=0,p=0;
    for(int i=0;i<g->active_clouds && i<MAX_CLOUDS;i++) {
        if(!g->clouds[i].alive)continue;
        if(g->clouds[i].kind)p++;
        else w++;
    }
    if(white)*white=w;
    if(pink)*pink=p;
}
