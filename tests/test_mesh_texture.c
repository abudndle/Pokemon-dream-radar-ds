#include "dr_texture.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static const unsigned char texture[] = {
    'D','R','T','1',2,2,3,0,
    0,0,0,0, 0,16,0,0, 0,0,0,16,
    0,0x80, 0x1f,0x80, 0xe0,0x83, 0xff,0xff
};
int main(void) {
    DrMeshVertex verts[3]={{0,0,0},{4096,0,0},{0,4096,0}};
    DrMeshTriangle tris[1]={{0,1,2}};
    DrMesh mesh={3,1,verts,tris};
    DrTexture tex={0};
    assert(dr_texture_decode(texture,sizeof texture,&mesh,&tex));
    assert(tex.width==2 && tex.height==2 && tex.vertices==3);
    assert(tex.uv[1].u==4096 && tex.uv[2].v==4096);
    uint16_t *previous=tex.texels;
    unsigned char broken[sizeof texture];
    memcpy(broken,texture,sizeof broken);
    broken[0]='X';
    assert(!dr_texture_decode(broken,sizeof broken,&mesh,&tex));
    assert(tex.texels==previous);
    memcpy(broken,texture,sizeof broken);
    broken[12]=0x01;broken[13]=0x10;
    assert(!dr_texture_decode(broken,sizeof broken,&mesh,&tex));
    assert(tex.texels==previous);
    memcpy(broken,texture,sizeof broken);
    broken[24]=0;broken[25]=0;
    assert(!dr_texture_decode(broken,sizeof broken,&mesh,&tex));
    assert(tex.texels==previous);
    assert(!dr_texture_decode(texture,sizeof texture-1,&mesh,&tex));
    DrMesh mismatch={4,1,verts,tris};
    assert(!dr_texture_decode(texture,sizeof texture,&mismatch,&tex));
    uint16_t screen[64*64+2]={0};
    screen[0]=0x1234;screen[64*64+1]=0x5678;
    assert(dr_texture_render_yaw(&mesh,&tex,screen+1,64,64,16,48,16,0));
    assert(screen[1+46*64+18]==0x8000);
    assert(screen[1+46*64+30]==0x801f);
    assert(screen[1+34*64+18]==0x83e0);
    assert(screen[1+40*64+24]==0xffff);
    assert(screen[0]==0x1234 && screen[64*64+1]==0x5678);
    assert(!dr_texture_render_yaw(&mesh,&tex,screen+1,64,64,16,48,16,16));
    assert(!dr_texture_render_yaw(&mesh,NULL,screen+1,64,64,16,48,16,0));
    tris[0].c=3;
    assert(!dr_texture_render_yaw(&mesh,&tex,screen+1,64,64,16,48,16,0));
    tris[0].c=2;
    char path[]="/tmp/dr_texture_XXXXXX";
    int fd=mkstemp(path);assert(fd>=0);
    FILE *file=fdopen(fd,"wb");assert(file);
    assert(fwrite(texture,1,sizeof texture,file)==sizeof texture);
    assert(fclose(file)==0);
    DrTexture loaded={0};
    assert(dr_texture_load_file(path,&mesh,&loaded));
    assert(loaded.width==2 && loaded.texels[3]==0xffff);
    file=fopen(path,"ab");assert(file);
    assert(fputc(42,file)!=EOF && fclose(file)==0);
    assert(!dr_texture_load_file(path,&mesh,&loaded));
    assert(loaded.texels[3]==0xffff);
    dr_texture_free(&loaded);
    assert(unlink(path)==0);
    dr_texture_free(&tex);
    assert(!tex.uv && !tex.texels);
    puts("PASS: DRT1 texture parsing, UV mapping, and safety");
    return 0;
}
