/* Safe, portable BMP camera-photo helpers for the user's homebrew SD folder.
   No writes to retail game saves. */
#include "photo_album.h"
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

static uint16_t le16(const unsigned char *p) {
    return (uint16_t)((unsigned)p[0] | ((unsigned)p[1]<<8));
}
static uint32_t le32(const unsigned char *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8) |
           ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}
static void put16(unsigned char *p,uint16_t v) {
    p[0]=(unsigned char)v;p[1]=(unsigned char)(v>>8);
}
static void put32(unsigned char *p,uint32_t v) {
    for(int i=0;i<4;i++)p[i]=(unsigned char)(v>>(8*i));
}
static int photo_path(char *out,size_t cap,const char *folder,int slot) {
    if(!out || cap<20 || !folder || !*folder || slot<0 || slot>=DR_PHOTO_MAX)return 0;
    size_t n=strlen(folder);
    if(n>cap-20)return 0;
    int r=snprintf(out,cap,"%s%sphoto_%03d.bmp",folder,
                   n && folder[n-1]=='/'?"":"/",slot);
    return r>0 && (size_t)r<cap;
}
static int existing_photo(const char *folder,int slot) {
    char path[256];struct stat st;
    return photo_path(path,sizeof path,folder,slot) &&
           stat(path,&st)==0 && S_ISREG(st.st_mode);
}
int dr_photo_find(const char *folder,int from,int direction,int *slot_out) {
    if(!folder || !*folder || !slot_out || (direction!=1 && direction!=-1))return 0;
    /* from is the current slot, -1 starts a new forward search. */
    if(from<-1 || from>=DR_PHOTO_MAX)return 0;
    for(int n=0;n<DR_PHOTO_MAX;n++) {
        int slot=(from+direction*(n+1))%DR_PHOTO_MAX;
        if(slot<0)slot+=DR_PHOTO_MAX;
        if(existing_photo(folder,slot)) {*slot_out=slot;return 1;}
    }
    return 0;
}
int dr_photo_read(const char *filename,uint16_t *dst,size_t count) {
    if(!filename || !*filename || !dst || count<DR_PHOTO_W*DR_PHOTO_H)return 0;
    FILE *f=fopen(filename,"rb");if(!f)return 0;
    unsigned char head[54];int ok=0;
    if(fread(head,1,sizeof head,f)!=sizeof head)goto done;
    if(head[0]!='B' || head[1]!='M' ||
       le16(head+6)!=0 || le16(head+8)!=0 ||
       le32(head+2)!=54+DR_PHOTO_W*DR_PHOTO_H*3 ||
       le32(head+10)!=54 || le32(head+14)!=40 ||
       le32(head+18)!=DR_PHOTO_W || le32(head+22)!=DR_PHOTO_H ||
       le16(head+26)!=1 || le16(head+28)!=24 ||
       le32(head+30)!=0 ||
       le32(head+34)!=DR_PHOTO_W*DR_PHOTO_H*3)goto done;
    /* Check the real file length before touching the destination buffer.
       A truncated or oversized photo must leave the current image intact. */
    if(fseek(f,0,SEEK_END)!=0)goto done;
    long actual=ftell(f);
    if(actual!=(long)(54+DR_PHOTO_W*DR_PHOTO_H*3))goto done;
    if(fseek(f,54,SEEK_SET)!=0)goto done;
    /* A complete read into a temporary image prevents short reads from
       producing partially updated display pixels. Avoid large DS stack use. */
    static unsigned char encoded[DR_PHOTO_W*DR_PHOTO_H*3];
    if(fread(encoded,1,sizeof encoded,f)!=sizeof encoded)goto done;
    if(ferror(f))goto done;
    /* A failed close must not be reported as a successful photo load. */
    if(fclose(f)!=0)return 0;
    f=NULL;
    for(int y=0;y<DR_PHOTO_H;y++) {
        const unsigned char *row=encoded+(DR_PHOTO_H-1-y)*DR_PHOTO_W*3;
        for(int x=0;x<DR_PHOTO_W;x++) {
            unsigned b=row[x*3], g=row[x*3+1], r=row[x*3+2];
            dst[y*DR_PHOTO_W+x]=(uint16_t)(0x8000 | (r>>3) | ((g>>3)<<5) | ((b>>3)<<10));
        }
    }
    ok=1;
done:
    if(f)fclose(f);
    return ok;
}
int dr_photo_write(const char *filename,const uint16_t *src,size_t count) {
    if(!filename || !*filename || !src || count<DR_PHOTO_W*DR_PHOTO_H)return 0;
    /* Exclusive creation avoids overwriting a photo if another writer
       creates the filename after the album slot scan. */
    int fd=open(filename,O_WRONLY|O_CREAT|O_EXCL,0600);
    if(fd<0)return 0;
    FILE *f=fdopen(fd,"wb");
    if(!f) { close(fd);remove(filename);return 0; }
    unsigned char head[54]={0}, row[DR_PHOTO_W*3];
    head[0]='B';head[1]='M';
    put32(head+2,54+DR_PHOTO_W*DR_PHOTO_H*3);put32(head+10,54);
    put32(head+14,40);put32(head+18,DR_PHOTO_W);put32(head+22,DR_PHOTO_H);
    put16(head+26,1);put16(head+28,24);
    put32(head+34,DR_PHOTO_W*DR_PHOTO_H*3);
    int ok=fwrite(head,1,sizeof head,f)==sizeof head;
    for(int y=DR_PHOTO_H-1;y>=0 && ok;y--) {
        for(int x=0;x<DR_PHOTO_W;x++) {
            uint16_t p=src[y*DR_PHOTO_W+x];
            row[x*3]=(unsigned char)(((p>>10)&31)<<3);
            row[x*3+1]=(unsigned char)(((p>>5)&31)<<3);
            row[x*3+2]=(unsigned char)((p&31)<<3);
        }
        ok=fwrite(row,1,sizeof row,f)==sizeof row;
    }
    if(fclose(f))ok=0;
    if(!ok)remove(filename);
    return ok;
}
int dr_photo_save_new(const char *folder,int *next_slot,const uint16_t *src,size_t count) {
    if(!folder || !*folder || !next_slot || !src || count<DR_PHOTO_W*DR_PHOTO_H)return 0;
    int start=*next_slot;
    if(start<0 || start>=DR_PHOTO_MAX)start=0;
    for(int n=0;n<DR_PHOTO_MAX;n++) {
        int slot=(start+n)%DR_PHOTO_MAX;
        char file[256];
        if(!photo_path(file,sizeof file,folder,slot))return 0;
        struct stat st;if(stat(file,&st)==0)continue;
        if(!dr_photo_write(file,src,count)) {
            /* If another writer claimed the slot, try the next number;
               genuine I/O failures still stop the save. */
            if(stat(file,&st)==0)continue;
            return 0;
        }
        *next_slot=(slot+1)%DR_PHOTO_MAX;
        return 1;
    }
    return 0;
}
