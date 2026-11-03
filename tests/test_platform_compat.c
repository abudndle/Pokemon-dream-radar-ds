#include "platform_compat.h"
#include <assert.h>
#include <limits.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

int main(void) {
    assert(dr_lab_count(0)==6 && dr_lab_count(1)==7);
    for(int i=0;i<6;i++)assert(dr_lab_action(0,i)==i);
    assert(dr_lab_action(0,6)==-1 && dr_lab_action(1,6)==6);
    assert(dr_settings_count(0)==2 && dr_settings_count(1)==3);
    for(int dsi=0;dsi<=1;dsi++) {
        for(int i=0;i<dr_settings_count(dsi);i++) {
            int y=16+28*i;
            assert(dr_settings_hit(10,y,dsi)==i);
            assert(dr_settings_hit(245,y+21,dsi)==i);
            assert(dr_settings_hit(128,y+22,dsi)==-1);
        }
        assert(dr_settings_hit(9,16,dsi)==-1);
        assert(dr_settings_hit(246,16,dsi)==-1);
        assert(dr_settings_hit(128,16+28*dr_settings_count(dsi),dsi)==-1);
    }
    assert(dr_settings_action(0,0)==DR_SETTING_CART);
    assert(dr_settings_action(0,1)==DR_SETTING_SD);
    assert(dr_settings_action(0,2)==-1);
    assert(dr_settings_action(1,0)==DR_SETTING_OPTICAL);
    assert(dr_settings_action(1,1)==DR_SETTING_CART);
    assert(dr_settings_action(1,2)==DR_SETTING_SD);
    assert(dr_settings_action(1,3)==-1);
    for(int dsi=0;dsi<=1;dsi++)
        for(int row=0;row<dr_settings_count(dsi);row++) {
            int action=dr_settings_action(dsi,row);
            assert(action!=DR_SETTING_CAMERA);
            assert(action!=DR_SETTING_PLACEHOLDER);
        }
    assert(!dr_camera_allowed(0,1) && !dr_camera_allowed(0,0));
    assert(!dr_camera_allowed(1,0) && dr_camera_allowed(1,1));
    assert(dr_camera_retry_latch(1,1)==0);
    /* Sphere beam: immediate press, bounded hold pulses, silence on release. */
    assert(dr_sphere_fire_repeat(1,1,1));
    assert(dr_sphere_fire_repeat(1,1,2));
    assert(dr_sphere_fire_repeat(1,1,3));
    assert(!dr_sphere_fire_repeat(1,0,1));
    assert(!dr_sphere_fire_repeat(1,0,2));
    assert(dr_sphere_fire_repeat(1,0,3));
    assert(dr_sphere_fire_repeat(1,0,6));
    assert(!dr_sphere_fire_repeat(1,0,7));
    assert(!dr_sphere_fire_repeat(0,0,3));
    /* A press edge sampled after release cannot create a phantom hit. */
    assert(!dr_sphere_fire_repeat(0,1,3));
    assert(!dr_sphere_fire_repeat(0,1,4));
    assert(dr_sphere_fire_repeat(1,1,4));
    assert(!dr_sphere_fire_repeat(1,0,4));
    assert(dr_sphere_fire_repeat(1,0,UINT_MAX-(UINT_MAX%3u)));

    assert(!dr_sphere_fire_repeat(0,0,6));
    int held_shots=0;
    for(unsigned frame=1;frame<=60;frame++)
        held_shots+=dr_sphere_fire_repeat(1,frame==1,frame);
    assert(held_shots==21);
    /* Radar remains protected from the A held to select an Extension. */
    int search_armed=0;
    assert(!dr_search_fire_gate(1,&search_armed));
    assert(!dr_search_fire_gate(1,&search_armed));
    assert(!dr_search_fire_gate(0,&search_armed));
    assert(dr_search_fire_gate(1,&search_armed));
    assert(dr_camera_retry_latch(0,1)==1);
    assert(dr_camera_retry_latch(1,0)==0);
    assert(dr_camera_next_frame_count(0)==1);
    assert(dr_camera_next_frame_count(1)==2);
    assert(dr_camera_next_frame_count(2147483646)==2147483647);
    assert(dr_camera_next_frame_count(2147483647)==2147483647);
    assert(dr_camera_next_frame_count(-1)==1);
    assert(dr_photo_capture_ready(1,1,1,1,1));
    assert(!dr_photo_capture_ready(0,1,1,1,1));
    assert(!dr_photo_capture_ready(1,0,1,1,1));
    assert(!dr_photo_capture_ready(1,1,0,1,1));
    assert(!dr_photo_capture_ready(1,1,1,0,1));
    assert(!dr_photo_capture_ready(1,1,1,1,0));
    /* Invalid or overlapping key masks cannot enable a one-key shortcut. */
    assert(!dr_camera_quick_open(1,1,1,1,1));
    assert(!dr_camera_quick_open(1,1,1,0,1));
    assert(!dr_camera_quick_open(1,1,1,1,0));
    assert(dr_camera_quick_open(1,3,2,1,2));
    /* Composite masks are not buttons; reject even disjoint combinations. */
    assert(!dr_camera_quick_open(1,7,1,3,4));
    assert(!dr_camera_quick_open(1,7,4,1,6));
    assert(!dr_camera_quick_open(1,3,1,-1,2));
    assert(!dr_camera_quick_open(1,3,1,1,-2));
    assert(!dr_camera_quick_open(1,3,4,1,2));
    assert(!dr_photo_shortcut(1,7,4,3,4));
    assert(!dr_photo_shortcut(1,7,1,1,6));
    assert(!dr_photo_shortcut(1,3,1,-1,2));
    assert(!dr_photo_shortcut(1,3,1,1,-2));
    assert(!dr_photo_shortcut(1,1,1,1,1));
    assert(!dr_photo_shortcut(1,1,1,0,1));
    assert(!dr_photo_shortcut(1,1,1,1,0));
    /* L+R is DSi-only and fires once on the second press, not while held. */
    const int L=1<<9,R=1<<8;
    assert(!dr_photo_shortcut(0,L|R,R,L,R));
    assert(!dr_photo_shortcut(1,L,L,L,R));
    assert(!dr_photo_shortcut(1,R,R,L,R));
    assert(dr_photo_shortcut(1,L|R,R,L,R));
    assert(dr_photo_shortcut(1,L|R,L,L,R));
    assert(!dr_photo_shortcut(1,L|R,0,L,R));
    assert(!dr_photo_shortcut(1,0,L|R,L,R));
    assert(strcmp(dr_storage_root(0),"fat:/")==0);
    assert(strcmp(dr_storage_root(1),"sd:/")==0);
    assert(!dr_storage_ready(NULL));
    assert(!dr_storage_ready("/this-dir-should-never-exist-xyz/"));
    char dir[]="/tmp/dreamradar-platform-XXXXXX";
    assert(mkdtemp(dir));
    char root[256];snprintf(root,sizeof root,"%s/",dir);
    assert(dr_storage_ready(root));
    assert(dr_storage_ready(root));
    /* Callers may pass an ordinary path without its trailing slash. */
    assert(dr_storage_ready(dir));
    char wrong_sibling[300];
    snprintf(wrong_sibling,sizeof wrong_sibling,"%sDreamRadarDSi",dir);
    assert(access(wrong_sibling,F_OK)!=0);
    char probe[300];snprintf(probe,sizeof probe,"%sDreamRadarDSi/.write_test.tmp",root);
    assert(access(probe,F_OK)!=0);
    assert(mkdir(probe,0700)==0);
    assert(!dr_storage_ready(root)); /* Must not overwrite existing probe */
    assert(rmdir(probe)==0);
    /* A pre-existing regular file must remain unchanged, not be truncated. */
    FILE *sentinel=fopen(probe,"wb");assert(sentinel);
    assert(fputs("keep",sentinel)>=0 && fclose(sentinel)==0);
    assert(!dr_storage_ready(root));
    char readback[8]={0};sentinel=fopen(probe,"rb");assert(sentinel);
    assert(fread(readback,1,4,sentinel)==4 && fclose(sentinel)==0);
    assert(strcmp(readback,"keep")==0);
    assert(remove(probe)==0);
    char sub[300];snprintf(sub,sizeof sub,"%sDreamRadarDSi",root);
    assert(rmdir(sub)==0);
    /* Redirecting DreamRadarDSi to another directory must not be considered
       writable game storage or create a probe in the external directory. */
    char outside[]="/tmp/dreamradar-outside-XXXXXX";
    assert(mkdtemp(outside));
    assert(symlink(outside,sub)==0);
    assert(!dr_storage_ready(root));
    char escaped_probe[320];
    snprintf(escaped_probe,sizeof escaped_probe,"%s/.write_test.tmp",outside);
    assert(access(escaped_probe,F_OK)!=0);
    assert(unlink(sub)==0);
    assert(rmdir(outside)==0);
    /* The storage path could also already be a regular file. */
    FILE *wrong=fopen(sub,"wb");assert(wrong);
    assert(fputs("untouched",wrong)>=0 && fclose(wrong)==0);
    assert(!dr_storage_ready(root));
    char unchanged[16]={0};
    wrong=fopen(sub,"rb");assert(wrong);
    assert(fread(unchanged,1,9,wrong)==9 && fclose(wrong)==0);
    assert(strcmp(unchanged,"untouched")==0);
    assert(remove(sub)==0);
    assert(dr_storage_ready(root));
    assert(rmdir(sub)==0);assert(rmdir(dir)==0);
    puts("PASS: camera-free DS/DSi menu routing and DLDI/SD filesystem detection");
    return 0;
}
