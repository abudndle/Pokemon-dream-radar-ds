#include "photo_album.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
int main(void) {
    char dir[]="/tmp/dr-photo-test-XXXXXX";
    assert(mkdtemp(dir));
    static uint16_t src[DR_PHOTO_W*DR_PHOTO_H],dst[DR_PHOTO_W*DR_PHOTO_H];
    for(int y=0;y<DR_PHOTO_H;y++)for(int x=0;x<DR_PHOTO_W;x++)
        src[y*DR_PHOTO_W+x]=(uint16_t)(0x8000 | ((x/8)&31) | (((y/6)&31)<<5) | (((x+y)/16&31)<<10));
    assert(!dr_photo_read("",dst,DR_PHOTO_W*DR_PHOTO_H));
    assert(!dr_photo_write("",src,DR_PHOTO_W*DR_PHOTO_H));
    int untouched=7;
    assert(!dr_photo_save_new("",&untouched,src,DR_PHOTO_W*DR_PHOTO_H));
    assert(!dr_photo_save_new(dir,&untouched,src,0));
    assert(untouched==7);
    int next=0, found=-1;
    assert(!dr_photo_find(dir,-1,1,&found));
    assert(dr_photo_save_new(dir,&next,src,DR_PHOTO_W*DR_PHOTO_H) && next==1);
    assert(dr_photo_find(dir,-1,1,&found) && found==0);
    char path[256];snprintf(path,sizeof path,"%s/photo_000.bmp",dir);
    assert(dr_photo_read(path,dst,DR_PHOTO_W*DR_PHOTO_H));
    for(size_t i=0;i<DR_PHOTO_W*DR_PHOTO_H;i++) {
        /* BMP24 discards the low 3 bits in 5-to-8-to-5 conversion. */
        assert(src[i]==dst[i]);
    }
    /* Nonzero BMP reserved bytes indicate a malformed album header. */
    FILE *reserved=fopen(path,"r+b");assert(reserved);
    assert(fseek(reserved,6,SEEK_SET)==0);
    assert(fputc(1,reserved)!=EOF);
    assert(fclose(reserved)==0);
    assert(!dr_photo_read(path,dst,DR_PHOTO_W*DR_PHOTO_H));
    reserved=fopen(path,"r+b");assert(reserved);
    assert(fseek(reserved,6,SEEK_SET)==0);
    assert(fputc(0,reserved)!=EOF);
    assert(fclose(reserved)==0);
    assert(dr_photo_read(path,dst,DR_PHOTO_W*DR_PHOTO_H));
    assert(!dr_photo_write(path,src,DR_PHOTO_W*DR_PHOTO_H));
    /* An otherwise valid BMP with a forged declared filesize is rejected. */
    FILE *badsize=fopen(path,"r+b");assert(badsize);
    assert(fseek(badsize,2,SEEK_SET)==0);
    unsigned char zero[4]={0,0,0,0};
    assert(fwrite(zero,1,4,badsize)==4);
    assert(fclose(badsize)==0);
    for(size_t i=0;i<DR_PHOTO_W*DR_PHOTO_H;i++)dst[i]=0x2468;
    assert(!dr_photo_read(path,dst,DR_PHOTO_W*DR_PHOTO_H));
    for(size_t i=0;i<DR_PHOTO_W*DR_PHOTO_H;i++)assert(dst[i]==0x2468);
    /* A saved image with the correct header remains readable. */
    assert(unlink(path)==0);
    assert(dr_photo_write(path,src,DR_PHOTO_W*DR_PHOTO_H));
    assert(dr_photo_save_new(dir,&next,src,DR_PHOTO_W*DR_PHOTO_H) && next==2);
    assert(dr_photo_find(dir,0,1,&found) && found==1);
    assert(dr_photo_find(dir,0,-1,&found) && found==1);
    assert(dr_photo_find(dir,1,1,&found) && found==0);
    assert(!dr_photo_find(dir,0,0,&found));
    assert(!dr_photo_read(path,dst,2));
    FILE *f=fopen(path,"r+b");assert(f);assert(fputc('X',f)!=EOF);assert(!fclose(f));
    assert(!dr_photo_read(path,dst,DR_PHOTO_W*DR_PHOTO_H));
    char other[256];snprintf(other,sizeof other,"%s/photo_001.bmp",dir);
    assert(!truncate(other,63));
    for(size_t i=0;i<DR_PHOTO_W*DR_PHOTO_H;i++)dst[i]=0x1357;
    assert(!dr_photo_read(other,dst,DR_PHOTO_W*DR_PHOTO_H));
    for(size_t i=0;i<DR_PHOTO_W*DR_PHOTO_H;i++)assert(dst[i]==0x1357);
    unlink(path);unlink(other);rmdir(dir);
    puts("PASS: indexed SD photo album, no overwrites, BMP pixel roundtrip, corrupt/truncated rejects");
    return 0;
}
