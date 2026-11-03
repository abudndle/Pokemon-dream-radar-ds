/* Experimental 3D presentation of the existing Dream Radar simulation.
 * Copyright-free test harness: NO Nintendo geometry or textures bundled.
 * Nitro Engine links DSMA internally for .dsm skeletal models/.dsa animations.
 * Original game.c remains the authoritative gameplay implementation. */
#include <nds.h>
#include <filesystem.h>
#include <fat.h>
#include <NEMain.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game.h"
#include "aim_input.h"

static Game game;
static NE_Camera *camera;
static NE_Model *model;
static NE_Animation *animation;
static NE_Material *material;
static int active_species = -2;
static int loaded;

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
    if(game.screen==STATE_TITLE) {
        if(down & KEY_A) game_begin_search(&game,EXT_BASIC);
    } else if(game.screen==STATE_RADAR || game.screen==STATE_SPHERE) {
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
    } else if(game.screen==STATE_RESULTS) {
        if(down & KEY_A) {
            if(!game_resume_radar(&game))game.screen=STATE_TITLE;
        }
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
    printf("Dream Radar / 3D adapter\\n");
    printf("Nitro Engine + DSMA\\n");
    printf("3D assets: %s\\n",asset_mount?"NitroFS":"unavailable");
    printf("A: search/fire  D-pad/touch: aim\\nB: leave search\\n");
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
        update_game(down,held);
        NE_ProcessArg(draw_3d,NULL);
    }
    release_model();
    NE_End();
    return 0;
}
