#include "dr_mesh.h"
#include <stdlib.h>
#include <string.h>
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
