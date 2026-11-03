/* Experimental 3D presentation of the existing Dream Radar simulation.
 * Copyright-free test harness: NO Nintendo geometry or textures bundled.
 * Nitro Engine links DSMA internally for .dsm skeletal models/.dsa animations.
 * Original game.c remains the authoritative gameplay implementation. */
#include <nds.h>
#include <nds/arm9/camera.h>
#include <filesystem.h>
#include <fat.h>
#include <NEMain.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game.h"
#include "aim_input.h"
#include "menu_input.h"
#include "camera_gate.h"

static Game game;
static NE_Camera *camera;
static NE_Model *model;
static NE_Animation *animation;
static NE_Material *material;
static int active_species = -2;
static int loaded;
/* Camera-only DSi capture. The Nitro Engine GPU retains exclusive VRAM
 * ownership; frames remain in regular aligned ARM9 memory for later input. */
#define DR3D_CAM_DMA 1
static u16 dsi_frame[256*192] __attribute__((aligned(32)));
static int dsi_camera_active, dsi_camera_busy, dsi_camera_failed;
static unsigned dsi_camera_frames;
static int running_dsi;

static void stop_dsi_camera(void) {
    if(dsi_camera_active) {
        if(dsi_camera_busy) {
            while(ndmaBusy(DR3D_CAM_DMA) || cameraTransferActive())
                swiWaitForVBlank();
            cameraStopTransfer();
        }
        cameraDeinit();
    }
    dsi_camera_active=0;
    dsi_camera_busy=0;
    game.camera_active=0;
    game.camera_ok=0;
}
static void update_dsi_camera(void) {
    if(!dr3d_camera_should_run(&game,running_dsi)) {
        stop_dsi_camera();
        return;
    }
    if(dr3d_camera_can_start(&game,running_dsi,dsi_camera_failed,
                             dsi_camera_active)) {
        if(!cameraInit()) goto failed;
        if(!cameraSelect(CAMERA_OUTER)) {
            cameraDeinit();
            goto failed;
        }
        dsi_camera_busy=cameraStartTransfer(dsi_frame,
                                            MCUREG_APT_SEQ_CMD_PREVIEW,
                                            DR3D_CAM_DMA);
        if(!dsi_camera_busy) { cameraDeinit(); goto failed; }
        dsi_camera_active=1;
        game.camera_active=1;
        game.camera_ok=1;
        game.camera_error=0;
    }
    if(!dsi_camera_active)return;
    if(dsi_camera_busy && !ndmaBusy(DR3D_CAM_DMA) &&
       !cameraTransferActive()) {
        cameraStopTransfer();
        dsi_camera_busy=0;
        DC_InvalidateRange(dsi_frame,sizeof dsi_frame);
        if(dsi_camera_frames<0xffffffffu)++dsi_camera_frames;
    }
    if(!dsi_camera_busy && (game.save.frames_played%3u)==0) {
        dsi_camera_busy=cameraStartTransfer(dsi_frame,
                                            MCUREG_APT_SEQ_CMD_PREVIEW,
                                            DR3D_CAM_DMA);
        if(!dsi_camera_busy) {
            stop_dsi_camera();
            goto failed;
        }
    }
    return;
failed:
    dsi_camera_failed=1;
    game.camera_error=1;
    game.camera_ok=0;
    game.camera_active=0;
    /* The existing stylus/D-pad fallback remains usable on any failure. */
}


static void release_model(void) {
    if(model) { NE_ModelDelete(model); model=NULL; }
    if(animation) { NE_AnimationDelete(animation); animation=NULL; }
    if(material) { NE_MaterialDelete(material); material=NULL; }
    loaded=0;
}
/* Use only authorized, locally staged DSMA assets. Never fake 3DS geometry. */
static void select_encounter_model(int species) {
    if(species==active_species)return;
    release_model();
    active_species=species;
    if(species<0 || species>25)return;
    char mesh[72],anim[72],texture[72];
    snprintf(mesh,sizeof(mesh),"nitro:/models/pokemon_%02d.dsm",species);
    snprintf(anim,sizeof(anim),"nitro:/models/pokemon_%02d.dsa",species);
    snprintf(texture,sizeof(texture),"nitro:/models/pokemon_%02d.img.bin",species);
    model=NE_ModelCreate(NE_Animated);
    if(!model || !NE_ModelLoadDSMFAT(model,mesh)) { release_model(); return; }
    animation=NE_AnimationCreate();
    /* DSMA's official converter names the exported base pose name.dsa,
       while a Walk.md5anim becomes name_walk.dsa. Prefer authentic motion. */
    char walk[72];
    snprintf(walk,sizeof(walk),"nitro:/models/pokemon_%02d_walk.dsa",species);
    if(animation && (NE_AnimationLoadFAT(animation,walk) ||
                     NE_AnimationLoadFAT(animation,anim))) {
        NE_ModelSetAnimation(model,animation);
        NE_ModelAnimStart(model,NE_ANIM_LOOP,floattof32(0.15));
    } else { release_model(); return; }
    /* Texture size must match the converter's --texture 128 128 argument.
     * A missing private texture leaves the model using its source material. */
    material=NE_MaterialCreate();
    if(material && NE_MaterialTexLoadFAT(material,NE_A1RGB5,128,128,
                                         NE_TEXGEN_TEXCOORD,texture))
        NE_ModelSetMaterial(model,material);
    NE_ModelScale(model,1.0,1.0,1.0);
    loaded=1;
}
static void draw_3d(void *arg) {
    (void)arg;
    NE_CameraUse(camera);
    if(game.screen==STATE_SPHERE && loaded) {
        NE_PolyFormat(31,0,NE_LIGHT_0,NE_CULL_NONE,0);
        NE_ModelDraw(model);
    }
}
static void update_game(unsigned down,unsigned held) {
    if(game.screen==STATE_RADAR || game.screen==STATE_SPHERE) {
        if(held & KEY_LEFT) game.aim_x-=2;
        if(held & KEY_RIGHT) game.aim_x+=2;
        if(held & KEY_UP) game.aim_y-=2;
        if(held & KEY_DOWN) game.aim_y+=2;
        if(game.aim_x<0)game.aim_x=0;
        if(game.aim_x>255)game.aim_x=255;
        if(game.aim_y<0)game.aim_y=0;
        if(game.aim_y>191)game.aim_y=191;
        if(down & KEY_A)game_fire(&game);
        if(down & KEY_B)game_leave_search(&game);
    } else {
        const Dr3dMenuInput input = {
            (down & KEY_A) != 0,
            (down & KEY_B) != 0,
            (down & KEY_UP) != 0,
            (down & KEY_DOWN) != 0
        };
        dr3d_menu_step(&game,input);
    }
    game_tick(&game);
    select_encounter_model(game.screen==STATE_SPHERE &&
                           game.session_type==0 ? game.session_species : -1);
}
int main(int argc,char **argv) {
    (void)argc;(void)argv;
    irqEnable(IRQ_HBLANK);
    irqSet(IRQ_VBLANK,NE_VBLFunc);
    irqSet(IRQ_HBLANK,NE_HBLFunc);
    if(NE_Init3D()!=0)return 1;
    NE_TextureSystemReset(0,0,NE_VRAM_AB);
    consoleDemoInit();
    const int asset_mount=nitroFSInit(NULL);
    (void)fatInitDefault();
    camera=NE_CameraCreate();
    if(!camera)return 2;
    NE_CameraSet(camera,0,2,-6,0,1,0,0,1,0);
    NE_LightSet(0,NE_White,0,-1,-1);
    NE_ClearColorSet(NE_Black,31,63);
    game_new(&game,0x44525344u);
    running_dsi=isDSiMode();
    if(!running_dsi)game.save.camera_enabled=0;
    printf("Dream Radar / 3D adapter\\n");
    printf("Nitro Engine + DSMA\\n");
    printf("3D assets: %s\\n",asset_mount?"NitroFS":"unavailable");
    printf("A: select/fire B: back\\n");
    printf("Lab -> extension -> radar\\n");
    printf("D-pad/touch: aim\\n");
    printf("Camera: DSi sphere only\\n");
    printf("Only private DSM/DSA renders.\\n");
    for(;;) {
        NE_WaitForVBL(NE_UPDATE_ANIMATIONS);
        scanKeys();
        if(keysDown() & KEY_START)break;
        const unsigned down=keysDown();
        const unsigned held=keysHeld();
        if(held & KEY_TOUCH) {
            touchPosition touch;
            touchRead(&touch);
            dr3d_apply_touch_aim(&game,1,touch.px,touch.py);
        }
        const GameScreen previous_screen = game.screen;
        const int previous_extension = game.ext_selection;
        update_game(down,held);
        update_dsi_camera();
        if(game.screen != previous_screen ||
           (game.screen == STATE_EXTENSIONS && game.ext_selection != previous_extension)) {
            printf("Scene %d\\n",(int)game.screen);
            if(game.screen == STATE_EXTENSIONS)
                printf("Extension: %s\\n",game_extension_name(game.ext_selection));
            else if(game.screen == STATE_LAB)
                printf("Lab: A extensions, B title\\n");
            else if(game.screen == STATE_INTRO)
                printf("Intro: A continue, B skip\\n");
        }
        NE_ProcessArg(draw_3d,NULL);
    }
    stop_dsi_camera();
    release_model();
    NE_End();
    return 0;
}
