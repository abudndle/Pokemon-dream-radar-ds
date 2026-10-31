#include "dr_mesh.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
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
    /* Repeated successful decodes replace existing allocations, while a
       malformed replacement leaves the original model intact. */
    DrMeshVertex *previous=m.vertex;
    assert(dr_mesh_decode(triangle,sizeof triangle,&m));
    assert(m.vertices==3 && m.triangles==1);
    assert(m.vertex[1].x==4096 && m.triangle[0].c==2);
    unsigned char invalid_replacement[sizeof triangle];
    memcpy(invalid_replacement,triangle,sizeof triangle);
    invalid_replacement[0]='X';
    DrMeshVertex *retained=m.vertex;
    assert(!dr_mesh_decode(invalid_replacement,sizeof invalid_replacement,&m));
    assert(m.vertex==retained && m.vertex[1].x==4096);
    (void)previous;
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
    /* Rotation is deterministic, depth-sensitive, and bounded to 16 steps. */
    DrMeshVertex depth={0,0,4096};
    assert(dr_mesh_project_vertex_yaw(&depth,128,96,32,0,&x,&y));
    assert(x==128 && y==96);
    assert(dr_mesh_project_vertex_yaw(&depth,128,96,32,4,&x,&y));
    assert(x==160 && y==96);
    assert(dr_mesh_project_vertex_yaw(&depth,128,96,32,8,&x,&y));
    assert(x==128 && y==96);
    assert(dr_mesh_project_vertex_yaw(&depth,128,96,32,12,&x,&y));
    assert(x==96 && y==96);
    assert(!dr_mesh_project_vertex_yaw(&depth,128,96,32,16,&x,&y));
    assert(!dr_mesh_project_vertex_yaw(NULL,128,96,32,0,&x,&y));
    assert(!dr_mesh_project_vertex_yaw(&depth,128,96,32,0,NULL,&y));
    uint16_t rotated[64*64]={0};
    m.vertex[2].z=4096;
    assert(dr_mesh_wireframe_yaw(&m,rotated,64,64,16,48,16,0xffff,4));
    assert(rotated[32*64+32]==0xffff);
    assert(rotated[40*64+24]==0xffff);
    assert(!dr_mesh_wireframe_yaw(&m,rotated,64,64,16,48,16,0xffff,16));
    /* The standalone model-file loader must accept only exact, complete
       DRM1 files and preserve an already loaded mesh after any failure. */
    char path[]="/tmp/dr_mesh_XXXXXX";
    int fd=mkstemp(path);assert(fd>=0);
    FILE *file=fdopen(fd,"wb");assert(file);
    assert(fwrite(triangle,1,sizeof triangle,file)==sizeof triangle);
    assert(fclose(file)==0);
    DrMesh from_file={0};
    assert(dr_mesh_load_file(path,&from_file));
    assert(from_file.vertices==3 && from_file.triangles==1);
    assert(from_file.vertex[1].x==4096);
    assert(!dr_mesh_load_file("",&from_file));
    assert(!dr_mesh_load_file("/tmp/dr_nonexistent_mesh_test_file.drm",&from_file));
    assert(from_file.vertices==3 && from_file.vertex[1].x==4096);
    file=fopen(path,"ab");assert(file);
    assert(fputc(0xAA,file)!=EOF && fclose(file)==0);
    assert(!dr_mesh_load_file(path,&from_file));
    assert(from_file.vertices==3 && from_file.vertex[1].x==4096);
    file=fopen(path,"wb");assert(file);
    assert(fwrite(triangle,1,sizeof triangle-1,file)==sizeof triangle-1);
    assert(fclose(file)==0);
    assert(!dr_mesh_load_file(path,&from_file));
    assert(from_file.vertex[1].x==4096);
    dr_mesh_free(&from_file);
    assert(unlink(path)==0);
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
