#include "platform_compat.h"
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

int main(void) {
    assert(dr_lab_count(0)==6 && dr_lab_count(1)==7);
    for(int i=0;i<6;i++)assert(dr_lab_action(0,i)==i);
    assert(dr_lab_action(0,6)==-1 && dr_lab_action(1,6)==6);
    assert(dr_settings_count(0)==2 && dr_settings_count(1)==4);
    assert(dr_settings_action(0,0)==DR_SETTING_CART);
    assert(dr_settings_action(0,1)==DR_SETTING_SD);
    assert(dr_settings_action(0,2)==-1);
    assert(dr_settings_action(1,0)==DR_SETTING_CAMERA);
    assert(dr_settings_action(1,1)==DR_SETTING_OPTICAL);
    assert(!dr_camera_allowed(0,1) && !dr_camera_allowed(0,0));
    assert(!dr_camera_allowed(1,0) && dr_camera_allowed(1,1));
    assert(strcmp(dr_storage_root(0),"fat:/")==0);
    assert(strcmp(dr_storage_root(1),"sd:/")==0);
    assert(!dr_storage_ready(NULL));
    assert(!dr_storage_ready("/this-dir-should-never-exist-xyz/"));
    char dir[]="/tmp/dreamradar-platform-XXXXXX";
    assert(mkdtemp(dir));
    char root[256];snprintf(root,sizeof root,"%s/",dir);
    assert(dr_storage_ready(root));
    assert(dr_storage_ready(root));
    char probe[300];snprintf(probe,sizeof probe,"%sDreamRadarDSi/.write_test.tmp",root);
    assert(access(probe,F_OK)!=0);
    assert(mkdir(probe,0700)==0);
    assert(!dr_storage_ready(root)); /* Must not overwrite existing probe */
    assert(rmdir(probe)==0);
    char sub[300];snprintf(sub,sizeof sub,"%sDreamRadarDSi",root);
    assert(rmdir(sub)==0);assert(rmdir(dir)==0);
    puts("PASS: camera-free DS/DSi menu routing and DLDI/SD filesystem detection");
    return 0;
}
