#include "dr_mesh.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#define DR_MESH_MAX_VERTICES 65535u
#define DR_MESH_MAX_TRIANGLES 2048u

static unsigned rd16(const unsigned char *p) {
    return (unsigned)p[0] | ((unsigned)p[1]<<8);
}
static int16_t signed16(const unsigned char *p) {
    unsigned n=rd16(p);
    return (int16_t)(n<32768u?(int)n:(int)n-65536);
}
void dr_mesh_free(DrMesh *mesh) {
    if(!mesh)return;
    free(mesh->vertex);free(mesh->triangle);
    memset(mesh,0,sizeof *mesh);
}
int dr_mesh_decode(const unsigned char *bytes,size_t size,DrMesh *out) {
    if(!bytes || !out || size<8 || memcmp(bytes,"DRM1",4)!=0)return 0;
    unsigned nv=rd16(bytes+4),nt=rd16(bytes+6);
    if(nv==0 || nv>DR_MESH_MAX_VERTICES || nt==0 || nt>DR_MESH_MAX_TRIANGLES)return 0;
    if(size!=8u+6u*(size_t)nv+6u*(size_t)nt)return 0;
    DrMesh tmp={0};
    tmp.vertex=(DrMeshVertex*)malloc(sizeof(DrMeshVertex)*nv);
    tmp.triangle=(DrMeshTriangle*)malloc(sizeof(DrMeshTriangle)*nt);
    if(!tmp.vertex || !tmp.triangle){dr_mesh_free(&tmp);return 0;}
    tmp.vertices=(uint16_t)nv;tmp.triangles=(uint16_t)nt;
    const unsigned char *p=bytes+8;
    for(unsigned i=0;i<nv;i++,p+=6){
        tmp.vertex[i].x=signed16(p);
        tmp.vertex[i].y=signed16(p+2);
        tmp.vertex[i].z=signed16(p+4);
    }
    for(unsigned i=0;i<nt;i++,p+=6){
        unsigned a=rd16(p),b=rd16(p+2),c=rd16(p+4);
        if(a>=nv || b>=nv || c>=nv || a==b || b==c || a==c){
            dr_mesh_free(&tmp);return 0;
        }
        const DrMeshVertex *v=tmp.vertex;
        int64_t abx=(int64_t)v[b].x-v[a].x,aby=(int64_t)v[b].y-v[a].y,abz=(int64_t)v[b].z-v[a].z;
        int64_t acx=(int64_t)v[c].x-v[a].x,acy=(int64_t)v[c].y-v[a].y,acz=(int64_t)v[c].z-v[a].z;
        if(aby*acz==abz*acy && abz*acx==abx*acz && abx*acy==aby*acx){
            dr_mesh_free(&tmp);return 0;
        }
        tmp.triangle[i].a=(uint16_t)a;
        tmp.triangle[i].b=(uint16_t)b;
        tmp.triangle[i].c=(uint16_t)c;
    }
    /* Out is changed only on success; caller owns decoded allocations. */
    *out=tmp;
    return 1;
}

/* The loader is deliberately read-only. The file must have the exact DRM1
 * size implied by its header before any bulk allocation is attempted. */
int dr_mesh_load_file(const char *path,DrMesh *out) {
    if(!path || !*path || !out)return 0;
    FILE *f=fopen(path,"rb");
    if(!f)return 0;
    unsigned char header[8];
    int ok=fread(header,1,sizeof header,f)==sizeof header &&
           memcmp(header,"DRM1",4)==0;
    size_t length=0;
    if(ok) {
        unsigned nv=rd16(header+4),nt=rd16(header+6);
        if(!nv || nv>DR_MESH_MAX_VERTICES ||
           !nt || nt>DR_MESH_MAX_TRIANGLES)ok=0;
        else length=8u+6u*(size_t)nv+6u*(size_t)nt;
    }
    if(ok) {
        if(fseek(f,0,SEEK_END)!=0 || ftell(f)!=(long)length ||
           fseek(f,0,SEEK_SET)!=0)ok=0;
    }
    unsigned char *bytes=NULL;
    if(ok) {
        bytes=(unsigned char*)malloc(length);
        if(!bytes || fread(bytes,1,length,f)!=length)ok=0;
    }
    if(fclose(f)!=0)ok=0;
    DrMesh next={0};
    if(ok)ok=dr_mesh_decode(bytes,length,&next);
    free(bytes);
    if(!ok)return 0;
    dr_mesh_free(out);
    *out=next;
    return 1;
}

/* No GPU dependencies: project packed Q12 mesh coordinates into screen space.
   Caller chooses the center and integer pixel scale (pixels per model unit).
   Limit scale so all intermediate products fit signed 32-bit arithmetic. */
int dr_mesh_project_vertex(const DrMeshVertex *v,int cx,int cy,int scale,int *x,int *y) {
    if(!v || !x || !y || scale<1 || scale>256 || cx<0 || cx>255 || cy<0 || cy>191)return 0;
    int64_t px=(int64_t)v->x*scale;
    int64_t py=(int64_t)v->y*scale;
    *x=cx+(int)(px/4096);
    *y=cy-(int)(py/4096);
    return 1;
}

/* Q12 sin/cos table: 16 fixed yaw orientations around vertical Y.
   Integer-only transforms avoid floating point/libm on DS ARM9. */
static const int16_t mesh_cos_yaw[16]={
    4096,3784,2896,1567,0,-1567,-2896,-3784,
    -4096,-3784,-2896,-1567,0,1567,2896,3784
};
static const int16_t mesh_sin_yaw[16]={
    0,1567,2896,3784,4096,3784,2896,1567,
    0,-1567,-2896,-3784,-4096,-3784,-2896,-1567
};
int dr_mesh_project_vertex_yaw(const DrMeshVertex *v,int cx,int cy,int scale,
                               unsigned yaw_step,int *x,int *y) {
    if(!v || !x || !y || yaw_step>=16 ||
       scale<1 || scale>256 || cx<0 || cx>255 || cy<0 || cy>191)return 0;
    /* x' = x*cos(yaw) + z*sin(yaw), preserving all signed Q12
       coordinates using 64-bit intermediates before dividing. */
    int64_t rotated=(int64_t)v->x*mesh_cos_yaw[yaw_step]+
                    (int64_t)v->z*mesh_sin_yaw[yaw_step];
    *x=cx+(int)(rotated*scale/(4096LL*4096LL));
    *y=cy-(int)((int64_t)v->y*scale/4096);
    return 1;
}

/* Bounded integer Bresenham rasterizer; clipped through guarded writes. */
static void mesh_line(uint16_t *pixels,int w,int h,int x0,int y0,int x1,int y1,uint16_t color) {
    int dx=abs(x1-x0),dy=abs(y1-y0);
    int sx=x0<x1?1:-1,sy=y0<y1?1:-1;
    int err=dx-dy;
    for(;;) {
        if(x0>=0 && x0<w && y0>=0 && y0<h)pixels[(size_t)y0*w+x0]=color;
        if(x0==x1 && y0==y1)break;
        int twice=2*err;
        if(twice>-dy){err-=dy;x0+=sx;}
        if(twice<dx){err+=dx;y0+=sy;}
    }
}
int dr_mesh_wireframe_yaw(const DrMesh *mesh,uint16_t *pixels,int width,int height,
                          int cx,int cy,int scale,uint16_t color,unsigned yaw_step) {
    if(!mesh || !pixels || !mesh->vertex || !mesh->triangle ||
       !mesh->vertices || !mesh->triangles || mesh->triangles>DR_MESH_MAX_TRIANGLES ||
       width<1 || width>256 || height<1 || height>192 ||
       cx<0 || cx>=width || cy<0 || cy>=height ||
       scale<1 || scale>256 || yaw_step>=16)return 0;
    for(unsigned i=0;i<mesh->triangles;i++) {
        DrMeshTriangle t=mesh->triangle[i];
        if(t.a>=mesh->vertices || t.b>=mesh->vertices || t.c>=mesh->vertices)return 0;
        int x[3],y[3];
        unsigned indices[3]={t.a,t.b,t.c};
        for(int j=0;j<3;j++)
            if(!dr_mesh_project_vertex_yaw(&mesh->vertex[indices[j]],cx,cy,scale,
                                           yaw_step,&x[j],&y[j]))return 0;
        for(int j=0;j<3;j++) {
            int k=(j+1)%3;
            mesh_line(pixels,width,height,x[j],y[j],x[k],y[k],color);
        }
    }
    return 1;
}

/* Keep existing consumers byte-for-byte compatible at zero yaw. */
int dr_mesh_wireframe(const DrMesh *mesh,uint16_t *pixels,int width,int height,
                      int cx,int cy,int scale,uint16_t color) {
    return dr_mesh_wireframe_yaw(mesh,pixels,width,height,cx,cy,scale,color,0);
}
