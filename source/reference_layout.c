#include "reference_layout.h"
void dr_support_center(int index,int *x,int *y) {
    static const int cx[3]={67,190,128},cy[3]={101,101,151};
    if(x)*x=index>=0 && index<3?cx[index]:-1;
    if(y)*y=index>=0 && index<3?cy[index]:-1;
}
int dr_support_at(int x,int y) {
    if(x<0||x>255||y<0||y>191)return -1;
    for(int i=0;i<3;i++) {
        int sx,sy;dr_support_center(i,&sx,&sy);
        /* Use a shared quad as a broad-phase bound, then keep the original
           eight-sided support hit region exactly (not a narrower diamond). */
        const int quad[8]={sx-44,sy-39,sx+44,sy-39,sx+44,sy+39,sx-44,sy+39};
        if(!dr_quad_hit(quad,x,y))continue;
        int dx=x>sx?x-sx:sx-x,dy=y>sy?y-sy:sy-y;
        if(2*dx+dy<=105)return i;
    }
    return -1;
}
int dr_transfer_button_at(int x,int y) {
    /* Only the two visible footer controls are actionable. */
    if(y<157 || y>=190)return -1;
    /* Match the visible rectangular footer panes using the shared quad
       primitive. Coordinates use inclusive right/bottom touch edges. */
    const int archive[8]={10,157,119,157,119,189,10,189};
    const int back[8]={138,157,245,157,245,189,138,189};
    if(dr_quad_hit(archive,x,y))return 0;
    if(dr_quad_hit(back,x,y))return 1;
    return -1;
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
        const int quad[8]={sx,sy,sx+sw-1,sy,sx+sw-1,sy+sh-1,sx,sy+sh-1};
        if(dr_quad_hit(quad,x,y))return i;
    }
    return -1;
}
int dr_lab_row_top(int index) {
    return index>=0 && index<7 ? 3+23*index : -1;
}
int dr_lab_hit(int x,int y,int count) {
    if(count<1 || count>7 || x<10 || x>=246 || y<3)return -1;
    int index=(y-3)/23;
    if(index>=count)return -1;
    /* Shared runtime quad geometry preserves the 1px row separation. */
    int top=dr_lab_row_top(index);
    const int quad[8]={10,top,245,top,245,top+21,10,top+21};
    return dr_quad_hit(quad,x,y)?index:-1;
}
int dr_shop_row_top(int index) {
    if(index<0 || index>=6)return -1;
    return 26 + 24*index;
}
int dr_shop_hit(int x,int y) {
    if(x<10 || x>=246 || y<26 || y>=170)return -1;
    int index=(y-26)/24;
    if(index>=6)return -1;
    int top=dr_shop_row_top(index);
    const int quad[8]={10,top,245,top,245,top+21,10,top+21};
    return dr_quad_hit(quad,x,y)?index:-1;
}
/* Shared C-side convex quadrilateral picking for actual DS touchscreen menus.
   Vertex order is perimeter order; accepts either winding direction. */
int dr_quad_hit(const int xy[8],int x,int y) {
    if(!xy || x<0 || x>=256 || y<0 || y>=192)return 0;
    int positive=0,negative=0;
    int64_t twice_area=0;
    for(int i=0;i<4;i++) {
        int j=(i+1)%4;
        int64_t ax=xy[2*i],ay=xy[2*i+1],bx=xy[2*j],by=xy[2*j+1];
        int64_t cross=(bx-ax)*((int64_t)y-ay)-(by-ay)*((int64_t)x-ax);
        if(cross>0)positive=1;
        if(cross<0)negative=1;
        twice_area+=ax*by-bx*ay;
    }
    return twice_area!=0 && !(positive && negative);
}
int dr_remaining_clouds(const Game *g) {
    if(!g)return 0;
    int left=0;
    int count=g->active_clouds;
    if(count<0)count=0;
    if(count>MAX_CLOUDS)count=MAX_CLOUDS;
    for(int i=0;i<count;i++)if(g->clouds[i].alive)left++;
    return left;
}
void dr_radar_counts(const Game *g,int *white,int *pink) {
    int w=0,p=0;
    if(g) {
        int count=g->active_clouds;
        if(count<0)count=0;
        if(count>MAX_CLOUDS)count=MAX_CLOUDS;
        for(int i=0;i<count;i++) {
            if(!g->clouds[i].alive)continue;
            if(g->clouds[i].kind)p++;
            else w++;
        }
    }
    if(white)*white=w;
    if(pink)*pink=p;
}

const char *dr_research_save_status(int storage_ready,int save_pending) {
    if(!storage_ready)return "NO SAVE MEDIA - progress in RAM";
    return save_pending?"Saving research...":"Research progress saved.";
}
