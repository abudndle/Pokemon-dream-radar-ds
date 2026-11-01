#include "dr_pane_runtime.h"
#include <math.h>
#include <string.h>

static int valid_float(float v) { return isfinite(v); }
static float minimum(float a,float b) { return a<b?a:b; }
static float maximum(float a,float b) { return a>b?a:b; }

int dr_ui_sample(const DrUiTrack *track,float frame,float *value) {
    if(!track || !value || !track->keys || !track->count ||
       track->count>DR_PANE_MAX_KEYS || track->curve>2 ||
       !valid_float(frame) || frame<0)return 0;
    const DrUiKey *k=track->keys;
    for(unsigned i=0;i<track->count;i++) {
        if(!valid_float(k[i].frame) || !valid_float(k[i].value) ||
           !valid_float(k[i].slope) || k[i].frame<0 ||
           (i && k[i].frame<k[i-1].frame))return 0;
    }
    unsigned left=0;
    while(left+1<track->count && k[left+1].frame<=frame)left++;
    if(left+1>=track->count || frame<k[0].frame || track->curve!=2) {
        *value=frame<k[0].frame?k[0].value:k[left].value;
        return 1;
    }
    const DrUiKey *a=&k[left],*b=&k[left+1];
    float span=b->frame-a->frame;
    if(span<=0) { *value=b->value;return 1; }
    float t=(frame-a->frame)/span,t2=t*t,t3=t2*t;
    float v=(2*t3-3*t2+1)*a->value +
            (t3-2*t2+t)*span*a->slope +
            (-2*t3+3*t2)*b->value +
            (t3-t2)*span*b->slope;
    if(!valid_float(v))return 0;
    *value=v;
    return 1;
}

static int put_track(DrUiPane *pane,unsigned property,float v) {
    if(!valid_float(v))return 0;
    switch(property) {
    case 0:pane->x=v;break;
    case 1:pane->y=v;break;
    case 5:pane->rotation_deg=v;break;
    case 6:pane->scale_x=v;break;
    case 7:pane->scale_y=v;break;
    case 8:pane->width=v;break;
    case 9:pane->height=v;break;
    /* No invented projection of Z translation or X/Y rotation onto DS. */
    default:return 0;
    }
    return 1;
}
int dr_ui_evaluate(const DrUiPane *panes,size_t count,
                   const DrUiAnimation *animation,float frame,
                   DrUiFrame *out,size_t output_count) {
    if(!panes || !out || count==0 || count>DR_PANE_MAX_NODES ||
       output_count<count || !valid_float(frame) || frame<0)return 0;
    DrUiPane nodes[DR_PANE_MAX_NODES];
    DrUiFrame result[DR_PANE_MAX_NODES];
    memcpy(nodes,panes,count*sizeof(nodes[0]));
    memset(result,0,count*sizeof(result[0]));
    if(animation) {
        if((animation->count && !animation->tracks) ||
           animation->count>DR_PANE_MAX_TRACKS ||
           !valid_float(animation->duration) || animation->duration<0 ||
           animation->loop>1 || (animation->loop && animation->duration<=0))
            return 0;
        float now=animation->loop?fmodf(frame,animation->duration):
                    minimum(frame,animation->duration);
        if(!valid_float(now))return 0;
        for(unsigned t=0;t<animation->count;t++) {
            const DrUiTrack *track=&animation->tracks[t];
            float value=0;
            if(track->pane>=count || !dr_ui_sample(track,now,&value) ||
               !put_track(&nodes[track->pane],track->property,value))return 0;
        }
    }
    for(size_t i=0;i<count;i++) {
        const DrUiPane *p=&nodes[i];
        DrUiFrame *f=&result[i];
        if(p->parent < -1 || (p->parent>=0 && (size_t)p->parent>=i))return 0;
        if(p->origin>8 || p->visible>1 || p->clip_children>1 ||
           !valid_float(p->x) || !valid_float(p->y) ||
           !valid_float(p->width) || !valid_float(p->height) ||
           !valid_float(p->scale_x) || !valid_float(p->scale_y) ||
           !valid_float(p->rotation_deg) || p->width<0 || p->height<0)return 0;
        float angle=p->rotation_deg*0.017453292519943295f;
        float cs=cosf(angle),sn=sinf(angle);
        float a=cs*p->scale_x,b=-sn*p->scale_y,
              c=sn*p->scale_x,d=cs*p->scale_y;
        if(p->parent>=0) {
            const DrUiFrame *par=&result[p->parent];
            f->a=par->a*a+par->b*c;
            f->b=par->a*b+par->b*d;
            f->c=par->c*a+par->d*c;
            f->d=par->c*b+par->d*d;
            f->tx=par->a*p->x+par->b*p->y+par->tx;
            f->ty=par->c*p->x+par->d*p->y+par->ty;
            f->alpha=(uint8_t)((par->alpha*p->alpha+127)/255);
            f->visible=(uint8_t)(par->visible && p->visible && f->alpha);
        } else {
            f->a=a;f->b=b;f->c=c;f->d=d;
            f->tx=p->x;f->ty=p->y;
            f->alpha=p->alpha;f->visible=(uint8_t)(p->visible && p->alpha);
        }
        /* Nine BCLYT origin anchors, with native center origin=4. */
        float lx=-((float)(p->origin%3)*0.5f)*p->width;
        float ly=-((float)(p->origin/3)*0.5f)*p->height;
        float minx=INFINITY,miny=INFINITY,maxx=-INFINITY,maxy=-INFINITY;
        for(unsigned v=0;v<4;v++) {
            float xx=lx+((v==1 || v==2)?p->width:0);
            float yy=ly+((v>=2)?p->height:0);
            float wx=f->a*xx+f->b*yy+f->tx;
            float wy=f->c*xx+f->d*yy+f->ty;
            if(!valid_float(wx)||!valid_float(wy))return 0;
            f->quad[2*v]=wx;f->quad[2*v+1]=wy;
            minx=minimum(minx,wx);miny=minimum(miny,wy);
            maxx=maximum(maxx,wx);maxy=maximum(maxy,wy);
        }
        if(minx < -100000.0f || miny < -100000.0f ||
           maxx > 100000.0f || maxy > 100000.0f)return 0;
        int left=(int)floorf(minx+0.0001f),top=(int)floorf(miny+0.0001f);
        int right=left+(int)floorf(maxx-minx+0.5f);
        int bottom=top+(int)floorf(maxy-miny+0.5f);
        if(left<0)left=0;
        if(top<0)top=0;
        if(right>256)right=256;
        if(bottom>192)bottom=192;
        if(p->parent>=0 && nodes[p->parent].clip_children) {
            const DrUiFrame *par=&result[p->parent];
            if(left<par->x)left=par->x;
            if(top<par->y)top=par->y;
            if(right>par->x+par->w)right=par->x+par->w;
            if(bottom>par->y+par->h)bottom=par->y+par->h;
        }
        f->x=left;f->y=top;
        f->w=right>left?right-left:0;
        f->h=bottom>top?bottom-top:0;
        if(!f->w || !f->h)f->visible=0;
    }
    memcpy(out,result,count*sizeof(result[0]));
    return 1;
}
int dr_ui_hit(const DrUiFrame *frame,int x,int y) {
    if(!frame || !frame->visible || x<0 || x>=256 || y<0 || y>=192)return 0;
    return x>=frame->x && y>=frame->y &&
           x<frame->x+frame->w && y<frame->y+frame->h;
}
