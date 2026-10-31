#include "platform_compat.h"
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

int dr_lab_count(int dsi_mode){return dsi_mode?7:6;}
int dr_lab_action(int dsi_mode,int selection){
    if(selection<0 || selection>=dr_lab_count(dsi_mode))return -1;
    return selection;
}
int dr_settings_count(int dsi_mode){return dsi_mode?4:2;}
int dr_settings_action(int dsi_mode,int selection){
    if(selection<0 || selection>=dr_settings_count(dsi_mode))return -1;
    return dsi_mode?selection:selection+2;
}
int dr_camera_allowed(int dsi_mode,int camera_enabled){return dsi_mode && camera_enabled;}
const char *dr_storage_root(int dsi_mode){return dsi_mode?"sd:/":"fat:/";}
int dr_storage_ready(const char *root){
    if(!root || !*root)return 0;
    char dir[128],probe[160];struct stat st;
    if(snprintf(dir,sizeof dir,"%sDreamRadarDSi",root)>=(int)sizeof dir)return 0;
    if(mkdir(dir,0777)!=0 && (stat(dir,&st)!=0 || !S_ISDIR(st.st_mode)))return 0;
    if(snprintf(probe,sizeof probe,"%s/.write_test.tmp",dir)>=(int)sizeof probe)return 0;
    /* Never overwrite a pre-existing file, even one with this internal name. */
    if(stat(probe,&st)==0)return 0;
    FILE *f=fopen(probe,"wb");if(!f)return 0;
    int ok=fputc(0x52,f)!=EOF;
    if(fclose(f)!=0)ok=0;
    if(remove(probe)!=0)ok=0;
    return ok;
}
