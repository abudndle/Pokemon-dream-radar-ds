#include "dr_mesh.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static const unsigned char triangle[]={
 'D','R','M','1',3,0,1,0,
 0,0,0,0,0,0, 0,16,0,0,0,0, 0,0,0,16,0,0,
 0,0,1,0,2,0
};
int main(void){
    DrMesh m={0};
    assert(dr_mesh_decode(triangle,sizeof triangle,&m));
    assert(m.vertices==3 && m.triangles==1);
    assert(m.vertex[1].x==4096 && m.vertex[2].y==4096);
    assert(m.triangle[0].c==2);
    int x=-1,y=-1;
    assert(dr_mesh_project_vertex(&m.vertex[0],128,96,32,&x,&y) && x==128 && y==96);
    assert(dr_mesh_project_vertex(&m.vertex[1],128,96,32,&x,&y) && x==160 && y==96);
    assert(dr_mesh_project_vertex(&m.vertex[2],128,96,32,&x,&y) && x==128 && y==64);
    assert(!dr_mesh_project_vertex(NULL,128,96,32,&x,&y));
    assert(!dr_mesh_project_vertex(&m.vertex[0],128,96,0,&x,&y));
    assert(!dr_mesh_project_vertex(&m.vertex[0],128,96,257,&x,&y));
    assert(!dr_mesh_project_vertex(&m.vertex[0],128,96,32,NULL,&y));
    uint16_t framebuffer[64*64]={0};
    assert(dr_mesh_wireframe(&m,framebuffer,64,64,16,48,16,0xffff));
    assert(framebuffer[48*64+16]==0xffff);
    assert(framebuffer[48*64+32]==0xffff);
    assert(framebuffer[32*64+16]==0xffff);
    assert(framebuffer[40*64+24]==0xffff);
    assert(!dr_mesh_wireframe(&m,framebuffer,0,64,16,48,16,0xffff));
    assert(!dr_mesh_wireframe(&m,NULL,64,64,16,48,16,0xffff));
    assert(!dr_mesh_wireframe(NULL,framebuffer,64,64,16,48,16,0xffff));
    dr_mesh_free(&m);
    assert(!m.vertex && !m.triangle);
    unsigned char bad[sizeof triangle];
    memcpy(bad,triangle,sizeof bad);bad[0]='X';
    assert(!dr_mesh_decode(bad,sizeof bad,&m));
    memcpy(bad,triangle,sizeof bad);bad[28]=3;
    assert(!dr_mesh_decode(bad,sizeof bad,&m));
    memcpy(bad,triangle,sizeof bad);bad[30]=1;
    assert(!dr_mesh_decode(bad,sizeof bad,&m));
    memcpy(bad,triangle,sizeof bad);
    bad[20]=0;bad[21]=32;bad[22]=0;bad[23]=0;
    assert(!dr_mesh_decode(bad,sizeof bad,&m));
    assert(!dr_mesh_decode(triangle,sizeof triangle-1,&m));
    assert(!dr_mesh_decode(triangle,sizeof triangle,NULL));
    assert(!dr_mesh_decode(NULL,sizeof triangle,&m));
    dr_mesh_free(&m);
    puts("PASS: DRM1 loader validates bounds and geometry");
    return 0;
}
