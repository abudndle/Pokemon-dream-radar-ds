#include "platform_compat.h"
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <sys/stat.h>
#include <errno.h>

int dr_camera_quick_icon_hit(int x,int y){
    return x>=3 && x<37 && y>=168 && y<192;
}
int dr_camera_quick_row_hit(int x,int y){
    if(x<12 || x>=244)return -1;
    if(y>=40 && y<68)return 0;
    if(y>=86 && y<114)return 1;
    return -1;
}
int dr_camera_quick_open(int is_title,int touched,int pressed_x,int x,int y){
    /* Neither keyboard nor touch may open the menu away from the title. */
    return is_title && (pressed_x || (touched && dr_camera_quick_icon_hit(x,y)));
}
int dr_placeholder_path(char *out,size_t cap,const char *storage_root){
    if(!out || !cap || !storage_root || !*storage_root)return 0;
    /* The UI intentionally offers no arbitrary path browsing: only this
       one user-owned filename can replace the camera-free background. */
    static const char suffix[]="DreamRadarDSi/placeholder.bmp";
    size_t n=strlen(storage_root);
    int length=snprintf(out,cap,"%s%s%s",storage_root,
                        storage_root[n-1]=='/'?"":"/",suffix);
    return length>0 && (size_t)length<cap;
}
int dr_lab_count(int dsi_mode){return dsi_mode?7:6;}
int dr_lab_action(int dsi_mode,int selection){
    if(selection<0 || selection>=dr_lab_count(dsi_mode))return -1;
    return selection;
}
int dr_settings_count(int dsi_mode){return dsi_mode?3:2;}
int dr_settings_hit(int x,int y,int dsi_mode){
    int count=dr_settings_count(dsi_mode);
    if(x<10 || x>=246 || y<16)return -1;
    int row=(y-16)/28;
    if(row>=count || y>=16+28*row+22)return -1;
    return row;
}
int dr_settings_action(int dsi_mode,int selection){
    if(selection<0 || selection>=dr_settings_count(dsi_mode))return -1;
    /* DSi Options retains optical aim and game pairing; no camera rows. */
    return dsi_mode?selection+1:selection+2;
}
int dr_camera_allowed(int dsi_mode,int camera_enabled){return dsi_mode && camera_enabled;}
int dr_camera_retry_latch(int camera_enabled,int previous_failure){
    return camera_enabled?0:previous_failure;
}
int dr_photo_shortcut(int dsi_mode,int held,int down,int l_mask,int r_mask){
    return dsi_mode && (held & (l_mask|r_mask))==(l_mask|r_mask) &&
           (down & (l_mask|r_mask))!=0;
}
int dr_photo_capture_ready(int dsi_mode,int storage_ready,int camera_active,int camera_ok,int frame_count){
    return dsi_mode && storage_ready && camera_active && camera_ok && frame_count>0;
}
int dr_camera_next_frame_count(int frame_count){
    return frame_count<0?1:frame_count<2147483647?frame_count+1:2147483647;
}
const char *dr_storage_root(int dsi_mode){return dsi_mode?"sd:/":"fat:/";}
int dr_storage_ready(const char *root){
    if(!root || !*root)return 0;
    char dir[128],probe[160];struct stat st;
    size_t root_len=strlen(root);
    /* Accept mounted roots (sd:/, fat:/) and paths without a trailing
       separator; never accidentally create a sibling directory. */
    const char *separator=(root[root_len-1]=='/')?"":"/";
    int dir_len=snprintf(dir,sizeof dir,"%s%sDreamRadarDSi",root,separator);
    if(dir_len<0 || dir_len>=(int)sizeof dir)return 0;
    if(mkdir(dir,0777)!=0) {
        /* Only an existing directory is acceptable. Do not silently
           proceed after permission, device, or other mkdir errors. */
        if(errno!=EEXIST || stat(dir,&st)!=0 || !S_ISDIR(st.st_mode))return 0;
    }
    int probe_len=snprintf(probe,sizeof probe,"%s/.write_test.tmp",dir);
    if(probe_len<0 || probe_len>=(int)sizeof probe)return 0;
    /* Never overwrite a pre-existing file, even one with this internal name. */
    if(stat(probe,&st)==0)return 0;
    /* EACCES and other lookup failures are not proof that the name is free. */
    if(errno!=ENOENT)return 0;
    /* Exclusive creation prevents replacing a file created after the stat check. */
    int fd=open(probe,O_WRONLY|O_CREAT|O_EXCL,0600);
    if(fd<0)return 0;
    unsigned char marker=0x52;
    int ok=write(fd,&marker,1)==1;
    if(close(fd)!=0)ok=0;
    if(remove(probe)!=0)ok=0;
    return ok;
}
