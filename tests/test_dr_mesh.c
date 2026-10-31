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
