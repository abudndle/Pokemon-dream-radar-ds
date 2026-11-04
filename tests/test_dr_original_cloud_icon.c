#include "dr_original_cloud_icon.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

enum { DS_W=256, DS_H=192 };
static uint16_t framebuffer[DS_W*DS_H + 2];

static void mkdir_checked(const char *path) {
    int rc=mkdir(path,0700);
    assert(rc==0);
}
static void make_file(const char *root, int corrupted) {
    char path[1024];
    const char *directories[]={
        "DreamRadarDSi","DreamRadarDSi/UI",
        "DreamRadarDSi/UI/OriginalSprites",
        "DreamRadarDSi/UI/OriginalSprites/Ui",
        "DreamRadarDSi/UI/OriginalSprites/Ui/MnIf_S_TitleCloudCount",
        "DreamRadarDSi/UI/OriginalSprites/Ui/MnIf_S_TitleCloudCount/timg"
    };
    for(unsigned i=0;i<sizeof directories/sizeof directories[0];i++) {
        assert(snprintf(path,sizeof path,"%s/%s",root,directories[i])>0);
        mkdir_checked(path);
    }
    assert(snprintf(path,sizeof path,
        "%s/DreamRadarDSi/UI/OriginalSprites/Ui/MnIf_S_TitleCloudCount/timg/CloudCountIcon00.spr",
        root)>0);
    FILE *f=fopen(path,"wb");
    assert(f);
    uint16_t header[2]={DR_ORIGINAL_CLOUD_ICON_W,DR_ORIGINAL_CLOUD_ICON_H};
    assert(fwrite(header,sizeof header[0],2,f)==2);
    for(int i=0;i<DR_ORIGINAL_CLOUD_ICON_W*DR_ORIGINAL_CLOUD_ICON_H;i++) {
        uint16_t pixel=i==0?0u:0x801fu; /* transparent corner; opaque blue */
        assert(fwrite(&pixel,sizeof pixel,1,f)==1);
    }
    if(corrupted)assert(fwrite("TRAIL",1,5,f)==5);
    assert(fclose(f)==0);
}
int main(void) {
    char good[]="/tmp/dr-private-cloud-good-XXXXXX";
    char bad[]="/tmp/dr-private-cloud-bad-XXXXXX";
    assert(mkdtemp(good)!=NULL && mkdtemp(bad)!=NULL);
    make_file(good,0);
    make_file(bad,1);
    DrOriginalCloudIcon icon;
    memset(&icon,0,sizeof icon);
    assert(dr_original_cloud_icon_load(good,&icon));
    assert(icon.loaded);
    assert(icon.pixels[0]==0 && icon.pixels[1]==0x801fu);
    DrOriginalCloudIcon before=icon;
    assert(!dr_original_cloud_icon_load(bad,&icon));
    assert(memcmp(&before,&icon,sizeof icon)==0);
    for(unsigned i=0;i<DS_W*DS_H+2;i++)framebuffer[i]=0x8421u;
    framebuffer[0]=0x1234u;
    framebuffer[DS_W*DS_H+1]=0x5678u;
    uint16_t *fb=framebuffer+1;
    assert(dr_original_cloud_icon_draw(fb,&icon,10,5));
    assert(fb[5*DS_W+10]==0x8421u); /* transparent first texel */
    assert(fb[5*DS_W+11]==0x801fu);
    assert(fb[4*DS_W+11]==0x8421u);
    assert(!dr_original_cloud_icon_draw(fb,&icon,-1,0));
    assert(!dr_original_cloud_icon_draw(fb,&icon,193,5));
    assert(!dr_original_cloud_icon_draw(fb,&icon,0,161));
    assert(!dr_original_cloud_icon_draw(NULL,&icon,1,1));
    assert(framebuffer[0]==0x1234u && framebuffer[DS_W*DS_H+1]==0x5678u);
    puts("PASS: source-backed original cloud-counter icon loads atomically and renders safely");
    return 0;
}
