#include "dr_texture.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define DRT_MAX_DIM 64u
static unsigned read16(const unsigned char *p) {
    return (unsigned)p[0] | ((unsigned)p[1]<<8);
}
void dr_texture_free(DrTexture *texture) {
    if(!texture)return;
    free(texture->uv);
    free(texture->texels);
    memset(texture,0,sizeof *texture);
}
static size_t expected_size(unsigned width,unsigned height,unsigned vertices) {
    return 8u+4u*(size_t)vertices+2u*(size_t)width*height;
}
int dr_texture_decode(const unsigned char *bytes,size_t size,
                      const DrMesh *mesh,DrTexture *out) {
    if(!bytes || !mesh || !mesh->vertex || !mesh->triangle || !out || size<8 ||
       memcmp(bytes,"DRT1",4)!=0)return 0;
    unsigned width=bytes[4],height=bytes[5],vertices=read16(bytes+6);
    if(width<1 || width>DRT_MAX_DIM || height<1 || height>DRT_MAX_DIM ||
       vertices<3 || vertices!=mesh->vertices ||
       size!=expected_size(width,height,vertices))return 0;
    DrTexture next={0};
    next.uv=(DrTextureUV*)malloc(vertices*sizeof *next.uv);
    next.texels=(uint16_t*)malloc(width*height*sizeof *next.texels);
    if(!next.uv || !next.texels){dr_texture_free(&next);return 0;}
    next.width=(uint16_t)width;
    next.height=(uint16_t)height;
    next.vertices=(uint16_t)vertices;
    for(unsigned i=0;i<vertices;i++){
        unsigned u=read16(bytes+8u+4u*i),v=read16(bytes+10u+4u*i);
        if(u>4096u || v>4096u){dr_texture_free(&next);return 0;}
        next.uv[i].u=(uint16_t)u;
        next.uv[i].v=(uint16_t)v;
    }
    const unsigned char *texels=bytes+8u+4u*vertices;
    for(unsigned i=0;i<width*height;i++){
        unsigned color=read16(texels+2u*i);
        if(!(color&0x8000u)){dr_texture_free(&next);return 0;}
        next.texels[i]=(uint16_t)color;
    }
    dr_texture_free(out);
    *out=next;
    return 1;
}
int dr_texture_load_file(const char *path,const DrMesh *mesh,DrTexture *out) {
    if(!path || !*path || !mesh || !out)return 0;
    FILE *f=fopen(path,"rb");
    if(!f)return 0;
    unsigned char header[8];
    int ok=fread(header,1,sizeof header,f)==sizeof header &&
           memcmp(header,"DRT1",4)==0;
    size_t length=0;
    if(ok){
        unsigned w=header[4],h=header[5],n=read16(header+6);
        if(w<1 || w>DRT_MAX_DIM || h<1 || h>DRT_MAX_DIM ||
           n<3 || n!=mesh->vertices || !mesh->vertex || !mesh->triangle)ok=0;
        else length=expected_size(w,h,n);
    }
    if(ok && (fseek(f,0,SEEK_END)!=0 || ftell(f)!=(long)length ||
              fseek(f,0,SEEK_SET)!=0))ok=0;
    unsigned char *bytes=NULL;
    if(ok){
        bytes=(unsigned char*)malloc(length);
        if(!bytes || fread(bytes,1,length,f)!=length)ok=0;
    }
    if(fclose(f)!=0)ok=0;
    if(ok)ok=dr_texture_decode(bytes,length,mesh,out);
    free(bytes);
    return ok;
}
static int64_t edge(int ax,int ay,int bx,int by,int px,int py) {
    return ((int64_t)px-ax)*(by-ay)-((int64_t)py-ay)*(bx-ax);
}
int dr_texture_render_yaw(const DrMesh *mesh,const DrTexture *texture,
                          uint16_t *pixels,int width,int height,
                          int cx,int cy,int scale,unsigned yaw_step) {
    if(!mesh || !texture || !pixels || !mesh->vertex || !mesh->triangle ||
       !texture->uv || !texture->texels || mesh->vertices<3 ||
       !mesh->triangles || mesh->triangles>2048 ||
       texture->vertices!=mesh->vertices ||
       texture->width<1 || texture->width>DRT_MAX_DIM ||
       texture->height<1 || texture->height>DRT_MAX_DIM ||
       width<1 || width>256 || height<1 || height>192 ||
       cx<0 || cx>=width || cy<0 || cy>=height ||
       scale<1 || scale>256 || yaw_step>=16)return 0;
    /* Validate before writing so corrupted triangle indices cannot leave
       a partly drawn frame. */
    for(unsigned i=0;i<mesh->vertices;i++)
        if(texture->uv[i].u>4096 || texture->uv[i].v>4096)return 0;
    for(unsigned i=0;i<mesh->triangles;i++){
        DrMeshTriangle t=mesh->triangle[i];
        if(t.a>=mesh->vertices || t.b>=mesh->vertices || t.c>=mesh->vertices)
            return 0;
    }
    for(unsigned i=0;i<mesh->triangles;i++){
        DrMeshTriangle t=mesh->triangle[i];
        unsigned index[3]={t.a,t.b,t.c};
        int x[3],y[3];
        for(int j=0;j<3;j++)
            if(!dr_mesh_project_vertex_yaw(&mesh->vertex[index[j]],cx,cy,scale,
                                           yaw_step,&x[j],&y[j]))return 0;
        int minx=x[0],maxx=x[0],miny=y[0],maxy=y[0];
        for(int j=1;j<3;j++){
            if(x[j]<minx)minx=x[j];
            if(x[j]>maxx)maxx=x[j];
            if(y[j]<miny)miny=y[j];
            if(y[j]>maxy)maxy=y[j];
        }
        if(minx<0)minx=0;
        if(miny<0)miny=0;
        if(maxx>=width)maxx=width-1;
        if(maxy>=height)maxy=height-1;
        if(minx>maxx || miny>maxy)continue;
        int64_t area=edge(x[0],y[0],x[1],y[1],x[2],y[2]);
        if(!area)continue;
        DrTextureUV a=texture->uv[t.a],b=texture->uv[t.b],c=texture->uv[t.c];
        for(int py=miny;py<=maxy;py++)for(int px=minx;px<=maxx;px++){
            int64_t w0=edge(x[1],y[1],x[2],y[2],px,py);
            int64_t w1=edge(x[2],y[2],x[0],y[0],px,py);
            int64_t w2=edge(x[0],y[0],x[1],y[1],px,py);
            if(area>0?(w0<0 || w1<0 || w2<0):
                      (w0>0 || w1>0 || w2>0))continue;
            int64_t u=(w0*a.u+w1*b.u+w2*c.u)/area;
            int64_t v=(w0*a.v+w1*b.v+w2*c.v)/area;
            if(u<0)u=0;
            if(u>4096)u=4096;
            if(v<0)v=0;
            if(v>4096)v=4096;
            unsigned tx=(unsigned)((u*(texture->width-1)+2048)/4096);
            unsigned ty=(unsigned)((v*(texture->height-1)+2048)/4096);
            pixels[(size_t)py*width+px]=texture->texels[ty*texture->width+tx];
        }
    }
    return 1;
}
