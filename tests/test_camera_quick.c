#include "platform_compat.h"
#include "photo_album.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define PIXELS (DR_PHOTO_W*DR_PHOTO_H)
static uint16_t original[PIXELS],loaded[PIXELS];

int main(void) {
    for(int y=0;y<192;y++)for(int x=0;x<256;x++)
        original[y*256+x]=(uint16_t)(0x8000u |
                            ((unsigned)(x/8)&31u) |
                            (((unsigned)(y/6)&31u)<<5) |
                            (((unsigned)(x/8+y/6)&31u)<<10));
    for(int y=0;y<192;y++)for(int x=0;x<256;x++) {
        int hit=dr_camera_quick_icon_hit(x,y);
        assert(hit==(x>=3 && x<37 && y>=168 && y<192));
        int row=dr_camera_quick_row_hit(x,y);
        assert(row==((x>=12 && x<244 && y>=40 && y<68)?0:
                     (x>=12 && x<244 && y>=86 && y<114)?1:-1));
    }
    assert(!dr_camera_quick_icon_hit(-1,180));
    assert(!dr_camera_quick_icon_hit(33,192));
    assert(dr_camera_quick_row_hit(244,50)==-1);
    assert(dr_camera_quick_row_hit(11,90)==-1);
    assert(dr_camera_quick_row_hit(100,68)==-1);

    /* Real emulator coverage: Start is already proven routable at title.
     * The new shortcut is strictly confined to intro, never to gameplay. */
    assert(dr_camera_intro_start_shortcut(1,0x10,0x10));
    assert(dr_camera_intro_start_shortcut(1,0x30,0x10));
    assert(!dr_camera_intro_start_shortcut(0,0x10,0x10));
    assert(!dr_camera_intro_start_shortcut(1,0x08,0x10));
    assert(!dr_camera_intro_start_shortcut(1,0x10,0));

    char pathname[128];
    assert(dr_placeholder_path(pathname,sizeof pathname,"sd:/"));
    assert(strcmp(pathname,"sd:/DreamRadarDSi/placeholder.bmp")==0);
    assert(dr_placeholder_path(pathname,sizeof pathname,"fat:/"));
    assert(strcmp(pathname,"fat:/DreamRadarDSi/placeholder.bmp")==0);
    assert(dr_placeholder_path(pathname,sizeof pathname,"/tmp/example"));
    assert(strcmp(pathname,"/tmp/example/DreamRadarDSi/placeholder.bmp")==0);
    assert(!dr_placeholder_path(pathname,8,"sd:/"));
    assert(!dr_placeholder_path(NULL,sizeof pathname,"sd:/"));
    assert(!dr_placeholder_path(pathname,sizeof pathname,NULL));
    assert(!dr_placeholder_path(pathname,sizeof pathname,""));
    char dir[]="/tmp/dr-camera-settings-XXXXXX";
    assert(mkdtemp(dir));
    char folder[256], file[320];
    snprintf(folder,sizeof folder,"%s/DreamRadarDSi",dir);
    assert(mkdir(folder,0700)==0);
    assert(dr_placeholder_path(file,sizeof file,dir));
    assert(dr_photo_write(file,original,PIXELS));
    memset(loaded,0,sizeof loaded);
    assert(dr_photo_read(file,loaded,PIXELS));
    for(int i=0;i<PIXELS;i++)assert(original[i]==loaded[i]);
    /* The quick import uses the same strict 24-bit BMP decoder as DSi
       photos, rejecting wrong dimensions and appended file data. */
    FILE *f=fopen(file,"ab");assert(f);
    assert(fputc(0,f)!=EOF && fclose(f)==0);
    loaded[0]=0xCDEF;
    assert(!dr_photo_read(file,loaded,PIXELS));
    assert(loaded[0]==0xCDEF);
    assert(remove(file)==0);
    assert(rmdir(folder)==0);
    assert(rmdir(dir)==0);
    puts("PASS: bottom-left camera quick settings, fixed BMP path and strict import");
    return 0;
}
