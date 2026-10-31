#include "dr_animation.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static const unsigned char frames[]={
    'D','R','A','1', 3,0, 2,4,
    0,0,0, 0,0,0, 0,0,0,
    0,64,0, 0,64,0, 0,64,0
};

int main(void) {
    DrMeshVertex vertex[3]={{0,0,0},{4096,0,0},{0,4096,0}};
    DrMeshTriangle triangle[1]={{0,1,2}};
    DrMesh mesh={3,1,vertex,triangle};
    DrAnimation animation={0};
    assert(dr_animation_decode(frames,sizeof frames,&mesh,&animation));
    assert(animation.vertices==3 && animation.frames==2);
    assert(animation.ticks_per_frame==4);
    assert(animation.delta && animation.scratch);
    const DrMesh *p=dr_animation_frame(&animation,&mesh,0);
    assert(p && p->triangle==triangle && p->vertex!=vertex);
    assert(p->vertex[0].y==0 && p->vertex[2].y==4096);
    p=dr_animation_frame(&animation,&mesh,2);
    assert(p && p->vertex[0].y==512 && p->vertex[2].y==4608);
    p=dr_animation_frame(&animation,&mesh,4);
    assert(p && p->vertex[0].y==1024 && p->vertex[2].y==5120);
    p=dr_animation_frame(&animation,&mesh,6);
    assert(p && p->vertex[0].y==512);
    p=dr_animation_frame(&animation,&mesh,8);
    assert(p && p->vertex[0].y==0);
    p=dr_animation_frame(&animation,&mesh,UINT32_MAX);
    assert(p && p->vertex[0].y==256);
    assert(vertex[0].y==0 && vertex[2].y==4096);

    /* Broken input preserves the last accepted keyframes and scratch. */
    int8_t *saved=animation.delta;
    assert(!dr_animation_decode(frames,sizeof frames-1,&mesh,&animation));
    assert(animation.delta==saved);
    unsigned char corrupted[sizeof frames];
    memcpy(corrupted,frames,sizeof frames);
    corrupted[0]='X';
    assert(!dr_animation_decode(corrupted,sizeof corrupted,&mesh,&animation));
    assert(animation.delta==saved);
    memcpy(corrupted,frames,sizeof frames);
    corrupted[6]=9;
    assert(!dr_animation_decode(corrupted,sizeof corrupted,&mesh,&animation));
    corrupted[6]=2;
    corrupted[7]=0;
    assert(!dr_animation_decode(corrupted,sizeof corrupted,&mesh,&animation));
    corrupted[7]=61;
    assert(!dr_animation_decode(corrupted,sizeof corrupted,&mesh,&animation));
    DrMesh bad={4,1,vertex,triangle};
    assert(!dr_animation_decode(frames,sizeof frames,&bad,&animation));
    assert(animation.delta==saved);
    assert(!dr_animation_frame(&animation,&bad,0));

    /* Signed delta, bounds clamping and atomic replacement. */
    memcpy(corrupted,frames,sizeof frames);
    corrupted[18]=(unsigned char)192; /* -64 units of Y */
    assert(dr_animation_decode(corrupted,sizeof corrupted,&mesh,&animation));
    p=dr_animation_frame(&animation,&mesh,4);
    assert(p && p->vertex[0].y==-1024);
    vertex[1].y=32767;
    p=dr_animation_frame(&animation,&mesh,4);
    assert(p && p->vertex[1].y==32767);
    vertex[1].y=0;

    char path[]="/tmp/dra1_animation_XXXXXX";
    int fd=mkstemp(path);
    assert(fd>=0);
    FILE *f=fdopen(fd,"wb");
    assert(f);
    assert(fwrite(frames,1,sizeof frames,f)==sizeof frames);
    assert(fclose(f)==0);
    DrAnimation file_animation={0};
    assert(dr_animation_load_file(path,&mesh,&file_animation));
    assert(dr_animation_frame(&file_animation,&mesh,4)->vertex[0].y==1024);
    f=fopen(path,"ab");
    assert(f);
    assert(fputc(7,f)!=EOF);
    assert(fclose(f)==0);
    int8_t *previous=file_animation.delta;
    assert(!dr_animation_load_file(path,&mesh,&file_animation));
    assert(file_animation.delta==previous);
    dr_animation_free(&file_animation);
    assert(unlink(path)==0);
    assert(!dr_animation_load_file(path,&mesh,&file_animation));

    dr_animation_free(&animation);
    assert(!animation.delta && !animation.scratch);
    assert(!dr_animation_frame(&animation,&mesh,0));
    puts("PASS: DRA1 keyframe decode, interpolation, looping, clamps and file safety");
    return 0;
}
