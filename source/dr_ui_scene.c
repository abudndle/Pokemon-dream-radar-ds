#include "dr_ui_scene.h"
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Little-endian, bounded DRUI v1: 22-byte header, 66-byte pane records,
 * 8-byte CLPA track records and 12-byte keyframes. No pointer fields. */
#define DRUI_MAX_BYTES 65536u
#define DRUI_MAX_PANES 96
#define DRUI_MAX_TRACKS 256
#define DRUI_MAX_KEYS 2048
#define DRUI_PANE_BYTES 66u
#define DRUI_TRACK_BYTES 8u
#define DRUI_KEY_BYTES 12u
#define DRUI_HEADER_BYTES 22u

typedef struct { char name[21]; int parent,origin,flags,alpha; float value[10]; } DrUiPane;
typedef struct { uint16_t pane,first,count; uint8_t prop,curve; } DrUiTrack;
typedef struct { float frame,value,slope; } DrUiKey;
struct DrUiScene {
    int pane_count,track_count,key_count,source_w,source_h,frames,offset_y,loop;
    DrUiPane *panes;
    DrUiTrack *tracks;
    DrUiKey *keys;
};
static uint16_t u16le(const uint8_t *p){return (uint16_t)((unsigned)p[0]|((unsigned)p[1]<<8));}
static float f32le(const uint8_t *p){
    uint32_t bits=(uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
    float value;
    memcpy(&value,&bits,4);
    return value;
}
static int good_value(float v){return isfinite(v)&&fabsf(v)<=100000.0f;}
void dr_ui_scene_free(DrUiScene *scene){
    if(!scene)return;
    free(scene->panes);free(scene->tracks);free(scene->keys);free(scene);
}
DrUiScene *dr_ui_scene_load(const char *path){
    if(!path || !*path)return NULL;
    FILE *f=fopen(path,"rb");if(!f)return NULL;
    DrUiScene *s=NULL;
    uint8_t *data=NULL;
    if(fseek(f,0,SEEK_END)!=0)goto done;
    long length=ftell(f);
    if(length<(long)DRUI_HEADER_BYTES || length>(long)DRUI_MAX_BYTES)goto done;
    if(fseek(f,0,SEEK_SET)!=0)goto done;
    data=malloc((size_t)length);if(!data)goto done;
    if(fread(data,1,(size_t)length,f)!=(size_t)length)goto done;
    if(memcmp(data,"DRUI",4)!=0 || u16le(data+4)!=1)goto done;
    unsigned pn=u16le(data+6),tn=u16le(data+8),kn=u16le(data+10);
    unsigned w=u16le(data+12),h=u16le(data+14),frames=u16le(data+16);
    int off=(int16_t)u16le(data+18);
    unsigned flags=u16le(data+20);
    if(!pn || pn>DRUI_MAX_PANES || tn>DRUI_MAX_TRACKS || kn>DRUI_MAX_KEYS ||
       w<1 || w>1024 || h<1 || h>1024 || frames>4096 || (flags&~1u) ||
       off < -384 || off > 384 ||
       DRUI_HEADER_BYTES+pn*DRUI_PANE_BYTES+tn*DRUI_TRACK_BYTES+kn*DRUI_KEY_BYTES!=(size_t)length)goto done;
    s=calloc(1,sizeof *s);if(!s)goto done;
    s->pane_count=(int)pn;s->track_count=(int)tn;s->key_count=(int)kn;
    s->source_w=(int)w;s->source_h=(int)h;s->frames=(int)frames;s->offset_y=off;s->loop=(flags&1u)!=0;
    s->panes=calloc(pn,sizeof *s->panes);
    s->tracks=calloc(tn?tn:1,sizeof *s->tracks);
    s->keys=calloc(kn?kn:1,sizeof *s->keys);
    if(!s->panes || !s->tracks || !s->keys)goto invalid;
    size_t pos=DRUI_HEADER_BYTES;
    for(unsigned i=0;i<pn;i++,pos+=DRUI_PANE_BYTES){
        const uint8_t *p=data+pos;
        DrUiPane *pane=&s->panes[i];
        memcpy(pane->name,p,20);
        if(!memchr(pane->name,0,20))goto invalid;
        pane->parent=(int16_t)u16le(p+20);
        pane->origin=p[22];pane->flags=p[23];pane->alpha=p[24];
        if(p[25]!=0 || pane->parent>=(int)i || pane->parent< -1 || pane->origin>8)goto invalid;
        for(unsigned k=0;k<10;k++){
            pane->value[k]=f32le(p+26+4*k);
            if(!good_value(pane->value[k]))goto invalid;
        }
        if(pane->value[6]==0 || pane->value[7]==0 || pane->value[8]<=0 || pane->value[9]<=0)goto invalid;
        for(unsigned j=0;j<i;j++)if(strcmp(pane->name,s->panes[j].name)==0)goto invalid;
    }
    for(unsigned i=0;i<tn;i++,pos+=DRUI_TRACK_BYTES){
        const uint8_t *p=data+pos;DrUiTrack *t=&s->tracks[i];
        t->pane=u16le(p);t->prop=p[2];t->curve=p[3];
        t->first=u16le(p+4);t->count=u16le(p+6);
        if(t->pane>=pn || t->prop>=10 || t->curve>2 || !t->count ||
           t->first>kn || t->count>kn-t->first)goto invalid;
        for(unsigned j=0;j<i;j++)if(t->pane==s->tracks[j].pane && t->prop==s->tracks[j].prop)goto invalid;
    }
    for(unsigned i=0;i<kn;i++,pos+=DRUI_KEY_BYTES){
        DrUiKey *k=&s->keys[i];k->frame=f32le(data+pos);
        k->value=f32le(data+pos+4);k->slope=f32le(data+pos+8);
        if(!good_value(k->frame)||!good_value(k->value)||!good_value(k->slope)||k->frame<0)goto invalid;
    }
    for(unsigned i=0;i<tn;i++){
        DrUiTrack *t=&s->tracks[i];
        for(unsigned k=1;k<t->count;k++)
            if(s->keys[t->first+k].frame<s->keys[t->first+k-1].frame)goto invalid;
    }
    goto done;
invalid:
    dr_ui_scene_free(s);s=NULL;
done:
    free(data);fclose(f);return s;
}
static float track_sample(const DrUiScene *s,const DrUiTrack *t,float frame){
    const DrUiKey *k=s->keys+t->first;
    if(frame<k[0].frame)return k[0].value;
    if(frame>=k[t->count-1].frame)return k[t->count-1].value;
    unsigned lo=0,hi=t->count;
    /* Upper bound selects the last duplicate-frame key. */
    while(lo<hi){unsigned m=lo+(hi-lo)/2;if(k[m].frame<=frame)lo=m+1;else hi=m;}
    unsigned i=lo-1;
    if(t->curve!=2)return k[i].value;
    const DrUiKey *a=&k[i],*b=&k[i+1];
    float dt=b->frame-a->frame;
    if(dt<=0)return b->value;
    float u=(frame-a->frame)/dt,u2=u*u,u3=u2*u;
    return (2*u3-3*u2+1)*a->value+(u3-2*u2+u)*dt*a->slope+
           (-2*u3+3*u2)*b->value+(u3-u2)*dt*b->slope;
}
typedef struct {float m00,m01,m10,m11,x,y;int alpha,visible;} DrUiWorld;
static int compute(const DrUiScene *s,float frame,DrUiRect out[4]){
    DrUiWorld world[DRUI_MAX_PANES];
    int found[4]={0};
    if(!isfinite(frame)||frame<0)return 0;
    if(s->loop&&s->frames>0)frame=fmodf(frame,(float)s->frames);
    else if(s->frames>0 && frame>s->frames)frame=(float)s->frames;
    for(int i=0;i<s->pane_count;i++){
        const DrUiPane *p=&s->panes[i];float v[10];memcpy(v,p->value,sizeof v);
        for(int j=0;j<s->track_count;j++)if(s->tracks[j].pane==i){
            const DrUiTrack *t=&s->tracks[j];v[t->prop]=track_sample(s,t,frame);
        }
        if(!good_value(v[0])||!good_value(v[1])||!good_value(v[5])||
           !good_value(v[6])||!good_value(v[7])||!good_value(v[8])||!good_value(v[9]))return 0;
        const DrUiWorld *parent=p->parent<0?NULL:&world[p->parent];
        float radians=v[5]*0.01745329251994329577f,cs=cosf(radians),sn=sinf(radians);
        DrUiWorld *w=&world[i];
        float a=cs*v[6],b=-sn*v[7],c=sn*v[6],d=cs*v[7];
        if(parent){
            w->m00=parent->m00*a+parent->m01*c;w->m01=parent->m00*b+parent->m01*d;
            w->m10=parent->m10*a+parent->m11*c;w->m11=parent->m10*b+parent->m11*d;
            w->x=parent->x+parent->m00*v[0]+parent->m01*v[1];
            w->y=parent->y+parent->m10*v[0]+parent->m11*v[1];
            w->alpha=(parent->alpha*p->alpha+127)/255;
            w->visible=parent->visible && (p->flags&1)!=0;
        }else{
            w->m00=a;w->m01=b;w->m10=c;w->m11=d;
            w->x=v[0];w->y=v[1];w->alpha=p->alpha;w->visible=(p->flags&1)!=0;
        }
        if(!good_value(w->x)||!good_value(w->y)||!good_value(w->m00)||
           !good_value(w->m01)||!good_value(w->m10)||!good_value(w->m11))return 0;
        if(strncmp(p->name,"Touch",5)!=0 || p->name[5]!='0' ||
           p->name[6]<'0' || p->name[6]>'3' || p->name[7]!=0)continue;
        int index=p->name[6]-'0';
        if(found[index]||!w->visible||w->alpha<=0)return 0;
        found[index]=1;
        float left=(-0.5f*(float)(p->origin%3))*v[8];
        float right=left+v[8];
        float bottom=(-0.5f*(float)(2-p->origin/3))*v[9];
        float top=bottom+v[9];
        float bx[4]={left,right,right,left},by[4]={bottom,bottom,top,top};
        float minx=1e30f,miny=1e30f,maxx=-1e30f,maxy=-1e30f;
        for(int k=0;k<4;k++){
            float x=128.0f+(w->x+w->m00*bx[k]+w->m01*by[k])*256.0f/s->source_w;
            float y=96.0f-(w->y+w->m10*bx[k]+w->m11*by[k])*192.0f/s->source_h+s->offset_y;
            if(x<minx)minx=x;
            if(x>maxx)maxx=x;
            if(y<miny)miny=y;
            if(y>maxy)maxy=y;
        }
        if(!good_value(minx)||!good_value(maxx)||!good_value(miny)||!good_value(maxy))return 0;
        int x0=(int)floorf(fmaxf(0,minx)),x1=(int)floorf(fminf(256,maxx));
        int y0=(int)floorf(fmaxf(0,miny)),y1=(int)floorf(fminf(192,maxy));
        if(x0<0||x1>256||y0<0||y1>192||x1<=x0||y1<=y0)return 0;
        out[index]=(DrUiRect){x0,y0,x1-x0,y1-y0};
    }
    for(int i=0;i<4;i++){
        if(!found[i])return 0;
        for(int j=0;j<i;j++){
            const DrUiRect *a=&out[i],*b=&out[j];
            if(a->x<b->x+b->w && a->x+a->w>b->x && a->y<b->y+b->h && a->y+a->h>b->y)return 0;
        }
    }
    return 1;
}
int dr_ui_four_row_rects(const DrUiScene *s,float frame,DrUiRect out[4]){
    if(!s||!out)return 0;
    DrUiRect temp[4];
    if(!compute(s,frame,temp))return 0;
    memcpy(out,temp,sizeof temp);return 1;
}
int dr_ui_title_rects(const DrUiScene *s,float frame,DrUiRect out[4]){
    return dr_ui_four_row_rects(s,frame,out);
}
int dr_ui_title_hit(const DrUiRect r[4],int x,int y){
    if(!r || x<0 || x>=256 || y<0 || y>=192)return -1;
    for(int i=0;i<4;i++)if(x>=r[i].x && x<r[i].x+r[i].w &&
                          y>=r[i].y && y<r[i].y+r[i].h)return i;
    return -1;
}
