#include "title_panes_generated.h"
/* Pokémon Dream Radar DSi: BlocksDS ARM9. Original art converted from player's NCCH.
 * This is a homebrew prototype, NOT a 1:1 port. No retail save writes.
 */
#include <nds.h>
#include <nds/arm9/camera.h>
#include <nds/ndma.h>
#include <fat.h>
#include <filesystem.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/stat.h>
#include "font6.h"
#include "game.h"
#include "twilight_saves.h"
#include "save_backend.h"
#include "photo_album.h"
#include "platform_compat.h"
#include "dialogue_generated.h"
#include "story_dialogue.h"
#include "reference_layout.h"
#include "cloud_animation.h"
#include "burnet_tips_generated.h"
#include "dr_mesh.h"

#define SW 256
#define SH 192
#define PIXELS (SW*SH)
#define CAM_DMA 0
#define EXPORT_DIR export_dir


static Game game;
static TwilightSaveIndex sd_index;
static SaveBackend save_backend;
static int sd_selected;
static TwilightSaveEntry active_sd_entry;
static int active_sd_entry_valid;
static char active_rom_dir[TW_MAX_PATH];
static u16 top[PIXELS] __attribute__((aligned(32)));
static u16 bottom[PIXELS] __attribute__((aligned(32)));
static u16 camera_frame[PIXELS] __attribute__((aligned(32)));
/* The NDMA frame is never sampled while a new camera transfer overwrites it. */
static u16 camera_last_frame[PIXELS] __attribute__((aligned(32)));
static const char *const bg_files[] = {
    "title_top.raw","menu_top.raw","menu_bottom.raw","game_top.raw","game_bottom.raw",
    "title_menu_bottom.raw","development_top.raw","title_original_top.raw",
    "radar_overview.raw","transfer_top.raw","transfer_bottom.raw"
};
static u16 bg_cache[11][PIXELS] __attribute__((aligned(32)));
static u8 bg_valid[11];
static u16 *top_vram, *bottom_vram;
static int have_storage, have_romfs, camera_busy, camera_frames, photo_index;
static int running_dsi, camera_failed_this_run;
static const char *storage_root;
static char export_dir[64];
static char photo_dir[96];
static int photo_storage_ready;
static u16 custom_background[PIXELS] __attribute__((aligned(32)));
static int custom_background_loaded, custom_background_slot=-1;
static int placeholder_preview_slot=-1;
static u16 placeholder_preview[PIXELS] __attribute__((aligned(32)));
static int placeholder_preview_loaded;
#define CUSTOM_BG_MARKER 0xB6
static int load_custom_background(int slot) {
    char filename[128];
    if(!running_dsi || !photo_storage_ready || slot<0 || slot>=DR_PHOTO_MAX)return 0;
    int n=snprintf(filename,sizeof filename,"%s/photo_%03d.bmp",photo_dir,slot);
    if(n<0 || n>=(int)sizeof filename)return 0;
    if(!dr_photo_read(filename,custom_background,PIXELS))return 0;
    custom_background_loaded=1;
    custom_background_slot=slot;
    return 1;
}
static int preview_custom_background(int slot) {
    char filename[128];
    if(!running_dsi || !photo_storage_ready || slot<0 || slot>=DR_PHOTO_MAX)return 0;
    int n=snprintf(filename,sizeof filename,"%s/photo_%03d.bmp",photo_dir,slot);
    if(n<0 || n>=(int)sizeof filename)return 0;
    if(!dr_photo_read(filename,placeholder_preview,PIXELS))return 0;
    placeholder_preview_slot=slot;
    placeholder_preview_loaded=1;
    return 1;
}
static void restore_custom_background(void) {
    if(game.save.reserved[11]!=CUSTOM_BG_MARKER)return;
    int slot=(int)game.save.reserved[9] | ((int)game.save.reserved[10]<<8);
    load_custom_background(slot);
}
static void select_custom_background(int slot) {
    game.save.reserved[9]=(uint8_t)slot;
    game.save.reserved[10]=(uint8_t)(slot>>8);
    game.save.reserved[11]=CUSTOM_BG_MARKER;
    game.requested_save=1;
}
static int album_slot=-1, album_loaded;
static u8 old_samples[32*24], now_samples[32*24];
static int old_sample_valid;
static int keyframes;
static int top_changed, bottom_changed;
static int export_unique_research(void) {
    if(!have_storage)return 0;
    char path[128];struct stat st;
    for(int slot=1;slot<=9999;slot++) {
        snprintf(path,sizeof path,"%s/research_%04d.txt",EXPORT_DIR,slot);
        if(stat(path,&st)!=0)return game_export(&game,path);
    }
    return 0;
}

typedef struct {u16 w,h;u16 *pixels;} Sprite;
static Sprite sprites[68];
/* The bundled Pokemon/item sprites were converted from the original 3DS
   game. Their ordering follows the actual NitroFS sprite manifest. */
enum {S_ORIGINAL_POKEMON_FIRST=17,S_ORIGINAL_ITEM_FIRST=43};
enum {S_LOGO,S_CLOUD,S_YELLOW,S_RETICLE,S_ORB,S_SHOP,S_ICON,S_BURNET,S_UP_BEAM,S_UP_ENERGY,S_UP_SCOPE,S_GOOD0,S_GOOD1,S_GOOD2,S_RADAR_PINK,S_RADAR_DARK,S_RADAR_ARROW,S_CLOUD_WHITE=66,S_CLOUD_PINK=67};
static const char *sprite_files[]={"logo.spr","cloud.spr","cloud_yellow.spr","reticle.spr","orb.spr","shop.spr","icon.spr","burnet.spr","upgrade_beam.spr","upgrade_energy.spr","upgrade_scope.spr",
    "support_0.spr","support_1.spr","support_2.spr",
    "radar_marker_pink.spr","radar_marker_dark.spr","radar_arrow.spr",
    "pokemon_00.spr","pokemon_01.spr","pokemon_02.spr","pokemon_03.spr","pokemon_04.spr","pokemon_05.spr","pokemon_06.spr","pokemon_07.spr",
    "pokemon_08.spr","pokemon_09.spr","pokemon_10.spr","pokemon_11.spr","pokemon_12.spr","pokemon_13.spr","pokemon_14.spr","pokemon_15.spr",
    "pokemon_16.spr","pokemon_17.spr","pokemon_18.spr","pokemon_19.spr","pokemon_20.spr","pokemon_21.spr","pokemon_22.spr","pokemon_23.spr",
    "pokemon_24.spr","pokemon_25.spr",
    "item_00.spr","item_01.spr","item_02.spr","item_03.spr","item_04.spr","item_05.spr","item_06.spr","item_07.spr",
    "item_08.spr","item_09.spr","item_10.spr","item_11.spr","item_12.spr","item_13.spr","item_14.spr","item_15.spr",
    "item_16.spr","item_17.spr","item_18.spr","item_19.spr","item_20.spr","item_21.spr","item_22.spr","radar_cloud_white.spr","radar_cloud_pink.spr"};
static const u16 WHITE=0xFFFF, AQUA=0xFEE0, CYAN=0xF7C0, PINK=0xFC1F, GOLD=0x83FF, DARK=0x8000, GRAY=0xBDEF;

static void load_sprite(int id) {
    char path[128]; snprintf(path,sizeof path,"nitro:/%s",sprite_files[id]);
    FILE *f=fopen(path,"rb");if(!f)return;
    Sprite *s=&sprites[id];
    if(fread(&s->w,2,1,f)!=1 || fread(&s->h,2,1,f)!=1) {fclose(f);return;}
    if(!s->w || !s->h || s->w>256 || s->h>192) {fclose(f);s->w=0;s->h=0;return;}
    /* Validate the complete file before allocating. NitroFS sprites use a
       four-byte geometry header followed by exactly w*h RGB555 pixels. */
    size_t payload=(size_t)s->w*(size_t)s->h*2u;
    if(fseek(f,0,SEEK_END)!=0 || ftell(f)!=(long)(4u+payload) ||
       fseek(f,4,SEEK_SET)!=0) {
        fclose(f);s->w=0;s->h=0;return;
    }
    s->pixels=malloc(payload);
    if(!s->pixels || fread(s->pixels,1,payload,f)!=payload) {
        free(s->pixels);s->pixels=NULL;s->w=0;s->h=0;
    } else {
        /* The original sprite converter uses zero for transparency and
           bit 15 for visible RGB555 pixels. Reject other values and
           entirely invisible files rather than silently showing garbage. */
        int visible=0,valid=1;
        size_t pixels=payload/2u;
        for(size_t i=0;i<pixels;i++) {
            u16 pixel=s->pixels[i];
            if(pixel & 0x8000u)visible=1;
            else if(pixel!=0){valid=0;break;}
        }
        if(!visible || !valid) {
            free(s->pixels);s->pixels=NULL;s->w=0;s->h=0;
        }
    }
    fclose(f);
}
static void cache_backgrounds(void) {
    if(!have_romfs)return;
    for(int i=0;i<11;i++) {
        char name[80];snprintf(name,sizeof name,"nitro:/%s",bg_files[i]);
        FILE *f=fopen(name,"rb");
        if(!f)continue;
        /* Original fullscreen raw backgrounds are exactly 256x192
           little-endian RGB555 pixels, without any trailing payload. */
        bg_valid[i]=0;
        if(fseek(f,0,SEEK_END)==0 && ftell(f)==(long)(PIXELS*2u) &&
           fseek(f,0,SEEK_SET)==0)
            bg_valid[i]=(fread(bg_cache[i],2,PIXELS,f)==PIXELS);
        if(bg_valid[i]) {
            /* A background is opaque RGB555; transparent pixels in
               extracted assets must not silently render as black. */
            for(int pixel=0;pixel<PIXELS;pixel++) {
                if(!(bg_cache[i][pixel]&0x8000u)) {
                    bg_valid[i]=0;
                    break;
                }
            }
        }
        if(fclose(f)!=0)bg_valid[i]=0;
    }
}
static void load_bg(const char *filename, u16 *dest, u16 fallback) {
    for(int i=0;i<11;i++) {
        if(strcmp(filename,bg_files[i])==0 && bg_valid[i]) {
            memcpy(dest,bg_cache[i],sizeof(bg_cache[i]));
            return;
        }
    }
    for(int i=0;i<PIXELS;i++)dest[i]=fallback;
}
static void rect(u16 *v,int x,int y,int w,int h,u16 c) {
    if(x<0){w+=x;x=0;}if(y<0){h+=y;y=0;}
    if(x+w>SW)w=SW-x;
    if(y+h>SH)h=SH-y;
    if(w<=0 || h<=0)return;
    for(int iy=y;iy<y+h;iy++) for(int ix=x;ix<x+w;ix++)v[iy*SW+ix]=c;
}
static void border(u16 *v,int x,int y,int w,int h,u16 c) {
    rect(v,x,y,w,2,c);rect(v,x,y+h-2,w,2,c);
    rect(v,x,y,2,h,c);rect(v,x+w-2,y,2,h,c);
}
static void draw_sprite(u16 *v,int id,int x,int y) {
    Sprite *s=&sprites[id];if(!s->pixels)return;
    for(int iy=0;iy<s->h;iy++){
        int yy=y+iy;if(yy<0||yy>=SH)continue;
        for(int ix=0;ix<s->w;ix++){
            int xx=x+ix;if(xx<0||xx>=SW)continue;
            u16 p=s->pixels[iy*s->w+ix];if(p & 0x8000)v[yy*SW+xx]=p;
        }
    }
}
/* Optional converted geometry: no models are packaged by default.
   Cache one species per encounter and preserve authentic 2D art fallback. */
static DrMesh encounter_mesh;
static int encounter_mesh_species=-1;
static int encounter_mesh_attempted;
static int draw_encounter_mesh(int species,int x,int y) {
    if(species<0 || species>=26 || !have_romfs)return 0;
    if(species!=encounter_mesh_species) {
        dr_mesh_free(&encounter_mesh);
        encounter_mesh_species=species;
        encounter_mesh_attempted=0;
    }
    if(!encounter_mesh_attempted) {
        encounter_mesh_attempted=1;
        char name[64];
        snprintf(name,sizeof name,"nitro:/pokemon_%02d.drm",species);
        FILE *f=fopen(name,"rb");
        if(f) {
            if(fseek(f,0,SEEK_END)==0) {
                long length=ftell(f);
                /* Same 2048-triangle limit as the portable DRM1 decoder. */
                if(length>=20 && length<=8+6*65535+6*2048 &&
                   fseek(f,0,SEEK_SET)==0) {
                    unsigned char *data=malloc((size_t)length);
                    if(data) {
                        if(fread(data,1,(size_t)length,f)==(size_t)length)
                            dr_mesh_decode(data,(size_t)length,&encounter_mesh);
                        free(data);
                    }
                }
            }
            fclose(f);
        }
    }
    if(!encounter_mesh.vertex)return 0;
    /* Rotate only converted optional DRM1 geometry. Original 2D artwork and
       item sprites retain their existing fallback behavior. A full turn
       takes 192 frames; no original skeletal animation is implied. */
    unsigned yaw_step=(unsigned)((game.save.frames_played/12u)&15u);
    return dr_mesh_wireframe_yaw(&encounter_mesh,top,SW,SH,x,y,24,CYAN,yaw_step);
}
/* Source-authentic 3DS thumbnail fallback until real geometry has been
   imported and optimized for the DS GPU. Keep both camera paths identical. */
static void draw_original_encounter_art(void) {
    int art=-1;
    if(game.session_type==0 && game.session_species>=0 && game.session_species<26)
        art=S_ORIGINAL_POKEMON_FIRST+game.session_species;
    else if(game.session_type==1 && game.session_item>=0 && game.session_item<23)
        art=S_ORIGINAL_ITEM_FIRST+game.session_item;
    int px=game.sphere_x-game.aim_x+128;
    int py=game.sphere_y-game.aim_y+96;
    if(game.session_type==0 && draw_encounter_mesh(game.session_species,px,py))
        return;
    if(art>=0 && art<(int)(sizeof sprites/sizeof sprites[0]) && sprites[art].pixels)
        draw_sprite(top,art,px-(int)sprites[art].w/2,py-(int)sprites[art].h/2);
    else draw_sprite(top,S_ORB,px-29,py-29);
}
static void glyph(u16 *v, int x,int y,char c,u16 color) {
    int ch=(unsigned char)c;if(ch<32 || ch>=128)ch='?';
    for(int row=0;row<8;row++){
        unsigned mask=font6[(ch-32)*8+row];
        for(int b=0;b<6;b++)if(mask & (1u << (5-b))) {
            int px=x+b, py=y+row;
            if(px>=0 && px<SW && py>=0 && py<SH) v[py*SW+px]=color;
        }
    }
}
static void print(u16 *v,int x,int y,u16 c,const char *s) {
    int start=x;
    for(;*s;s++){
        if(*s=='\n'){y+=10;x=start;continue;}
        glyph(v,x,y,*s,c);x+=6;
        if(x>=249){x=start;y+=10;}
        if(y>=SH-6)break;
    }
}
static void print_wrapped(u16 *v,int x,int y,int max_chars,u16 c,const char *s,int max_lines) {
    char line[52];int lines=0;
    while(*s && lines<max_lines){
        while(*s=='\n') {y+=10;lines++;s++;if(lines>=max_lines)return;}
        int n=0;
        while(s[n] && s[n]!='\n' && n<max_chars)n++;
        int take=n;
        if(n==max_chars && s[n] && s[n]!='\n') {
            for(int j=n-1;j>n/2;j--)if(s[j]==' ') {take=j;break;}
        }
        if(take>50)take=50;
        memcpy(line,s,take);line[take]=0;
        print(v,x,y,c,line);s+=take;
        while(*s==' ')s++;
        if(*s=='\n')s++;
        y+=10;lines++;
    }
}
static void label_bar(u16 *v,const char *name) {
    rect(v,0,0,256,23,0x8844);border(v,0,0,256,24,CYAN);
    print(v,10,8,WHITE,name);
}
static void button(u16 *v,int y,const char *name,int selected) {
    /* Preserve the texture beneath each label rather than painting over it
       with opaque generic bars. Only selection focus is overlaid live. */
    if(selected) {
        border(v,10,y,236,22,WHITE);
        border(v,12,y+2,232,18,CYAN);
    }
    print(v,19,y+8,WHITE,name);
}
static void coins(int y) {
    char text[45];snprintf(text,sizeof text,"Dream Orbs: %lu",(unsigned long)game.save.orbs);
    print(top,11,y,GOLD,text);
}
static void top_title(const char *s) {rect(top,0,0,256,24,0x8844);print(top,10,8,WHITE,s);}
static void progress_bar(int x,int y,int w,int numerator,int denominator,u16 color) {
    border(top,x,y,w,13,WHITE);
    if(denominator)rect(top,x+2,y+2,(w-4)*numerator/denominator,9,color);
}
/* Reference screenshots: original English main menu and search touch-screen.
   Gameplay counters, selections, costs, and quantities are drawn live. */
static const int upgrade_prices[5]={0,100,500,1000,1500};
static const char *shop_names[6]={"Beam","Energy Pack","Visoscope",
                                  "Vortex Charge","Dragnet Charge","Energy Recharge"};
static const char *shop_descriptions[6]={
    "Pulls in Pokemon to a place\nthat makes them easy to catch.",
    "Increases capture time.","Increases Dream Clouds.",
    "Holds Pokemon in place.","Slows Pokemon movement.","Restores capture time."
};
static void render_shop_top(void) {
    load_bg("development_top.raw",top,0x8844);
    const int rows_y[3]={2,65,128};
    const int costs[3]={100,50,50};
    char text[70];
    for(int i=0;i<3;i++) {
        int y=rows_y[i],lev=game.save.upgrades[i];
        draw_sprite(top,S_UP_BEAM+i,105,y+5);
        print(top,141,y+8,WHITE,shop_names[i]);
        for(int j=0;j<5;j++) {
            rect(top,110+j*16,y+31,14,7,0x8000);
            border(top,110+j*16,y+31,14,7,0xC210);
            if(j<lev)rect(top,112+j*16,y+33,10,3,0x83C0);
        }
        snprintf(text,sizeof text,lev>=5?"Lv. MAX":"Lv. %d",lev);
        print(top,208,y+33,WHITE,text);
        if(i==1) {
            print(top,109,y+44,CYAN,"Support");
            for(int j=0;j<3;j++) {
                draw_sprite(top,S_GOOD0+j,159+j*29,y+38);
                snprintf(text,sizeof text,"%d",game.save.goods[j]);
                print(top,175+j*28,y+50,WHITE,text);
            }
        }
    }
    /* Like the source 3DS reference: a dark translucent information bubble
       overlaps the selected equipment panel instead of switching art. */
    int chosen=game.selection;
    if(chosen<0||chosen>=6)chosen=0;
    rect(top,7,27,242,30,0x8421);border(top,7,27,242,30,CYAN);
    print_wrapped(top,13,33,38,WHITE,shop_descriptions[chosen],2);
    if(chosen<3) {
        int lev=game.save.upgrades[chosen];
        snprintf(text,sizeof text,lev>=5?"MAX":"NEXT %d",upgrade_prices[lev<5?lev:4]);
    } else snprintf(text,sizeof text,"COST %d",costs[chosen-3]);
    rect(top,180,0,75,10,0x8000);
    print(top,186,1,GOLD,text);
}
static void render_search_bottom(void) {
    /* Extracted original hexagon control art, retained on camera AND cloud-only searches. */
    load_bg("game_bottom.raw",bottom,0x8844);
    char text[40];
    rect(bottom,53,4,38,16,0x8000);
    snprintf(text,sizeof text,"%d",dr_remaining_clouds(&game));
    print(bottom,60,8,WHITE,text);
    /* Display live white/pink cloud counts using the original radar palette.
       These counts update when a cloud is collected, not just on entry. */
    if(game.screen==STATE_RADAR) {
        int white=0,pink=0;
        dr_radar_counts(&game,&white,&pink);
        rect(bottom,98,4,103,16,0x8000);
        snprintf(text,sizeof text,"W:%d",white);
        print(bottom,103,8,WHITE,text);
        snprintf(text,sizeof text,"P:%d",pink);
        print(bottom,151,8,PINK,text);
    }
    rect(bottom,207,4,45,16,0x8000);
    snprintf(text,sizeof text,"%lu",(unsigned long)game.save.orbs);
    print(bottom,214,8,WHITE,text);
    /* Counters appear inside the three original support-item control hexagons. */
    for(int i=0;i<3;i++) {
        int sx,sy;dr_support_center(i,&sx,&sy);
        snprintf(text,sizeof text,"%d",game.save.goods[i]);
        rect(bottom,sx-10,sy-7,20,14,0x8842);
        print(bottom,sx-7,sy-5,WHITE,text);
    }
    /* Original bottom-screen art only. D-pad aims and A fires; no new joystick. */
    /* Keep the original Back hotspot at the bottom right. */
}
/* Camera-free virtual view using the existing fallback artwork on DS/DS Lite. */
static void render_ds_search_sandbox(int show_clouds) {
    if(custom_background_loaded && (!running_dsi || !game.camera_active || !game.camera_ok))
        memcpy(top,custom_background,sizeof top);
    else load_bg("game_top.raw",top,0x8844);
    const int pan_x=(game.aim_x-128)/5;
    const int pan_y=(game.aim_y-96)/5;
    static u16 scene[PIXELS];
    memcpy(scene,top,sizeof scene);
    for(int y=0;y<SH;y++)for(int x=0;x<SW;x++) {
        int sx=x+pan_x,sy=y+pan_y;
        if(sx<0)sx=0;
        if(sx>=SW)sx=SW-1;
        if(sy<0)sy=0;
        if(sy>=SH)sy=SH-1;
        top[y*SW+x]=scene[sy*SW+sx];
    }
    if(show_clouds) for(int i=0;i<game.active_clouds;i++) {
        const Cloud *c=&game.clouds[i];
        if(!c->alive)continue;
        const int sx=c->x-game.aim_x+128;
        const int sy=c->y-game.aim_y+96;
        if(sx>=-32 && sx<SW && sy>=-32 && sy<SH)
            draw_sprite(top,c->kind ? S_CLOUD_PINK : S_CLOUD_WHITE,
                        sx-16,sy-16+dr_cloud_bob(game.save.frames_played,i));
    }
    if(show_clouds) {
        draw_sprite(top,S_RETICLE,112,80);
        char line[32];
        snprintf(line,sizeof line,"CLOUDS %d/%d",dr_remaining_clouds(&game),game.active_clouds);
        rect(top,2,2,121,17,0x8421);
        print(top,6,6,WHITE,line);
    }
}
static void render_camera_background(void);
static void render_radar_top(void) {
    if(!running_dsi || !game.camera_active || !game.camera_ok) {
        render_ds_search_sandbox(1);
        return;
    }
    /* DSi camera provides the backdrop while world-space clouds follow aim. */
    render_camera_background();
    for(int i=0;i<game.active_clouds;i++) {
        const Cloud *c=&game.clouds[i];
        if(!c->alive)continue;
        int sx=c->x-game.aim_x+128;
        int sy=c->y-game.aim_y+96;
        if(sx>=-32 && sx<SW && sy>=-32 && sy<SH)
            draw_sprite(top,c->kind ? S_CLOUD_PINK : S_CLOUD_WHITE,
                        sx-16,sy-16+dr_cloud_bob(game.save.frames_played,i));
    }
    draw_sprite(top,S_RETICLE,112,80);
    char line[32];
    snprintf(line,sizeof line,"CLOUDS %d/%d",dr_remaining_clouds(&game),game.active_clouds);
    rect(top,2,2,121,17,0x8421);
    print(top,6,6,WHITE,line);
}
static void render_transfer_bottom(void) {
    load_bg("transfer_bottom.raw",bottom,0x8844);
    char label[28];
    for(int i=0;i<6;i++) {
        int px,py,pw,ph,ix,iy,iw,ih;
        dr_transfer_slot_rect(i,&px,&py,&pw,&ph);
        dr_transfer_slot_rect(i+6,&ix,&iy,&iw,&ih);
        if(i<game.save.pending_count && game.save.pending[i]<26)
            draw_sprite(bottom,17+game.save.pending[i],px+2,py+5);
        int kind=game_item_slot_kind(&game,i);
        if(kind>=0 && kind<23) {
            draw_sprite(bottom,43+kind,ix+2,iy+3);
            snprintf(label,sizeof label,"%u",game.save.pending_items[i]);
            rect(bottom,ix+10,iy+22,16,10,0x8844);
            print(bottom,ix+11,iy+23,WHITE,label);
        }
    }
    if(game.selection>=0 && game.selection<12) {
        int sx,sy,sw,sh;
        dr_transfer_slot_rect(game.selection,&sx,&sy,&sw,&sh);
        border(bottom,sx,sy,sw,sh,GOLD);
    }
    print(bottom,12,167,WHITE,"A ARCHIVE");
    print(bottom,146,167,WHITE,"B BACK");
}
static void render_camera_background(void) {
    if(game.camera_active && game.camera_ok && camera_frames>0)
        memcpy(top,camera_last_frame,sizeof top);
    else if(custom_background_loaded)memcpy(top,custom_background,sizeof top);
    else load_bg("game_top.raw",top,0x88C4);
}
/* Extension rows are generated from the active game identity, not placeholders.
 * The corresponding legendary is absent entirely until one active source has
 * been identified and the associated story requirement is satisfied. */
static int extension_visible(int ext) {
    if(ext>=EXT_DIALGA && ext<=EXT_LUGIA)
        return game.cart_source!=CART_SOURCE_NONE &&
               game.cart==(CartGame)(ext-EXT_DIALGA) &&
               game.save.story_phase>=3 &&
               !(game.save.legends_caught & (1u<<(ext-EXT_DIALGA)));
    return 1;
}
static int extension_visible_count(void) {
    int n=0;
    for(int i=0;i<EXT_COUNT;i++) if(extension_visible(i)) n++;
    return n;
}
static int extension_at_row(int row) {
    for(int i=0;i<EXT_COUNT;i++) if(extension_visible(i) && row--==0) return i;
    return EXT_BASIC;
}
static int extension_row_of(int ext) {
    int row=0;
    for(int i=0;i<EXT_COUNT;i++) {
        if(!extension_visible(i))continue;
        if(i==ext)return row;
        row++;
    }
    return 0;
}
static void extension_ensure_selected(void) {
    if(!extension_visible(game.ext_selection)) game.ext_selection=EXT_BASIC;
}
static void render(void) {
    switch(game.screen) {
    case STATE_TITLE: {
        load_bg("title_original_top.raw",top,0x8824);
        draw_sprite(top,S_LOGO,13,22);
        print(top,12,166,GRAY,"(c) 2012 Pokemon / Creatures");
        print(top,50,179,GRAY,"GAME FREAK inc.");
        load_bg("title_menu_bottom.raw",bottom,0x8424);
        char tx[45];
        int max_clouds=5*(game.save.upgrades[2]+1);
        snprintf(tx,sizeof tx,"CLOUDS %d/%d",game.save.cloud_count,max_clouds);
        print(bottom,29,19,WHITE,tx);
        const char *opts[]={"Start","Send Research Data","Credits","Records"};
        for(int i=0;i<4;i++) {
            const DrPaneRect *r=&dr_title_panes[i];
            /* Original blue title panels use a bright white/cyan focus edge,
               not the gold selection outline from the development UI. */
            if(game.selection==i) {
                border(bottom,r->x,r->y,r->w,r->h,WHITE);
                border(bottom,r->x+2,r->y+2,r->w-4,r->h-4,CYAN);
            }
            /* Center each label within its actual extracted menu pane, not
               the full screen; preserve the original pane positions. */
            int label_width=(int)strlen(opts[i])*6;
            int x=r->x+(r->w-label_width)/2;
            if(x<r->x+3)x=r->x+3;
            int y=r->y+(r->h-8)/2;
            print(bottom,x,y,WHITE,opts[i]);
        }
        print(bottom,41,179,CYAN,"B: OPTIONS  A: SELECT");
        break; }
    case STATE_INTRO: {
        load_bg("menu_top.raw",top,0x8824);
        draw_sprite(top,S_BURNET,59,29);
        top_title("PROFESSOR BURNET");
        load_bg("menu_bottom.raw",bottom,0x8424);
        border(bottom,8,14,240,146,CYAN);
        print_wrapped(bottom,16,23,35,WHITE,intro_pages[game.intro_page % INTRO_PAGES],11);
        print(bottom,47,171,CYAN,"A: NEXT    B: SKIP");
        break; }
    case STATE_DIALOGUE: {
        load_bg("menu_top.raw",top,0x8824);
        draw_sprite(top,S_BURNET,59,29);
        top_title("PROFESSOR BURNET");
        load_bg("menu_bottom.raw",bottom,0x8424);
        border(bottom,8,14,240,146,CYAN);
        int stage=game.story_event;
        if(stage>=1 && stage<=3) {
            const char *page=story_stages[stage][game.story_event_page];
            print_wrapped(bottom,16,23,35,WHITE,page,12);
        }
        print(bottom,40,171,CYAN,"A: NEXT    B: SKIP");
        break; }
    case STATE_TIPS: {
        load_bg("menu_top.raw",top,0x8824);
        draw_sprite(top,S_BURNET,59,29);
        top_title("PROFESSOR BURNET");
        load_bg("menu_bottom.raw",bottom,0x8424);
        border(bottom,8,14,240,146,CYAN);
        print_wrapped(bottom,16,23,35,WHITE,burnet_tips[game.page % BURNET_TIP_COUNT],12);
        print(bottom,13,169,CYAN,"A: NEXT  B: LAB");
        break;
    }
    case STATE_CREDITS:
        load_bg("title_original_top.raw",top,0x8824);draw_sprite(top,S_LOGO,13,20);
        load_bg("menu_bottom.raw",bottom,0x8424);
        print(bottom,38,30,WHITE,"POKEMON DREAM RADAR");
        print(bottom,28,56,CYAN,"Original game (c) 2012");
        print(bottom,28,76,WHITE,"Nintendo / Creatures");
        print(bottom,28,91,WHITE,"GAME FREAK / Pokemon");
        print(bottom,14,127,GOLD,"Unofficial DS/DSi prototype");
        print(bottom,60,173,WHITE,"B: MAIN MENU");
        break;
    case STATE_LAB:
        load_bg("menu_top.raw",top,0x8824);
        top_title("RESEARCH LAB");
        draw_sprite(top,S_BURNET,89,38);
        coins(159);
        { char t[70];snprintf(t,sizeof t,"Dream Clouds: %d / %d",game.save.cloud_count,5*(game.save.upgrades[2]+1));
          print(top,11,176,CYAN,t); }
        { char t[68];snprintf(t,sizeof t,"GAME: %s [%s]",game_cart_name(game.cart),
            game.cart_source==CART_SOURCE_SLOT1?"CART":game.cart_source==CART_SOURCE_TWILIGHT_SD?"SD":"NONE");
          rect(top,3,143,250,13,0x8844);print(top,8,146,WHITE,t); }
        load_bg("menu_bottom.raw",bottom,0x8424);
        {const char *opts[]={"START SEARCH","DEVELOPMENT LAB","SEND RESEARCH DATA",
                             "RECORDS","OPTIONS","TALK TO BURNET","PHOTO ALBUM"};
         for(int i=0;i<dr_lab_count(running_dsi);i++)
             button(bottom,dr_lab_row_top(i),opts[dr_lab_action(running_dsi,i)],game.selection==i);}
        print(bottom,11,176,GRAY,"Y: CHECK DS CART  B: TITLE");
        break;
    case STATE_SHOP: {
        render_shop_top();
        load_bg("menu_bottom.raw",bottom,0x8424);
        char tx[70];
        snprintf(tx,sizeof tx,"Development Lab  ORBS %lu",(unsigned long)game.save.orbs);
        print(bottom,8,8,GOLD,tx);
        for(int i=0;i<6;i++) {
            char lbl[64];
            if(i<3) {
                int lev=game.save.upgrades[i];
                snprintf(lbl,sizeof lbl,lev>=5?"%s - MAX":"%s Lv.%d -> %d",shop_names[i],lev,
                         upgrade_prices[lev<5?lev:4]);
            } else snprintf(lbl,sizeof lbl,"%s x%d  %d",shop_names[i],
                            game.save.goods[i-3],i==3?100:50);
            button(bottom,dr_shop_row_top(i),lbl,game.selection==i);
        }
        print(bottom,12,177,CYAN,"A: PURCHASE    B: RETURN");
        break; }
    case STATE_EXTENSIONS: {
        extension_ensure_selected();
        load_bg("menu_top.raw",top,0x8824);top_title("SEARCH EXTENSIONS");
        coins(35);
        char desc[70];snprintf(desc,sizeof desc,"%s",game_extension_name(game.ext_selection));
        print_wrapped(top,13,77,35,WHITE,desc,3);
        print(top,13,119,CYAN,game_extension_unlocked(&game,game.ext_selection) ? "AVAILABLE":"LOCKED");
        if (game_extension_price(game.ext_selection)>0) {
            snprintf(desc,sizeof desc,"Cost: %d Orbs",game_extension_price(game.ext_selection));
            print(top,13,145,GOLD,desc);
        }
        load_bg("menu_bottom.raw",bottom,0x8424);
        int base=(extension_row_of(game.ext_selection)/5)*5;
        for(int row=base;row<base+5 && row<extension_visible_count();row++) {
            int ext=extension_at_row(row);
            button(bottom,10+(row-base)*30,game_extension_name(ext),game.ext_selection==ext);
        }
        print(bottom,10,170,GRAY,"UP/DOWN: SELECT  A: START");
        print(bottom,28,181,GRAY,"B: BACK");
        break;}
    case STATE_RADAR:
    case STATE_SPHERE: {
        if(game.screen==STATE_RADAR) {
            render_radar_top();
        } else {
            if(!running_dsi || !game.camera_active || !game.camera_ok) {
                /* DS and camera-disabled DSi retain the same camera-free aiming
                 * perspective during the capture encounter. */
                render_ds_search_sandbox(0);
                draw_original_encounter_art();
                /* Draw sight after the orb so the target cannot hide the crosshair. */
                draw_sprite(top,S_RETICLE,112,80);
            } else {
                render_camera_background();
                /* Use the same world-to-view transform as cloud hunting.
                 * A centered shot now matches game_fire() in both modes. */
                draw_original_encounter_art();
            }
            progress_bar(9,4,181,game.capture_hp,240,GOLD);
            char tx[32];snprintf(tx,sizeof tx,"%d",game.capture_timeout/60);
            rect(top,199,2,55,18,0x8421);
            print(top,213,7,WHITE,tx);
            if(running_dsi && game.camera_active && game.camera_ok)
                draw_sprite(top,S_RETICLE,112,80);
        }
        render_search_bottom();
        break;}
    case STATE_RESULTS: {
        load_bg("menu_top.raw",top,0x8824);top_title("RESEARCH RESULTS");
        draw_sprite(top,S_ICON,83,40);
        coins(167);
        load_bg("menu_bottom.raw",bottom,0x8824);
        border(bottom,8,22,240,124,CYAN);
        char txt[90];snprintf(txt,sizeof txt,"Dream Orbs collected: %d",game.session_orbs);
        print(bottom,16,38,WHITE,txt);
        if(game.session_caught>=0) {
            snprintf(txt,sizeof txt,"Caught: %s",game_species_name(game.session_caught));
            print(bottom,16,68,GOLD,txt);
        } else if(game.session_caught==-2) {
            snprintf(txt,sizeof txt,"Item: %s",game_item_name(game.session_item));
            print(bottom,16,68,WHITE,txt);
        }
        else if(game.session_caught==-3)print(bottom,16,68,WHITE,"Simulator challenge complete.");
        else if(game.session_caught==-4)print(bottom,16,68,GOLD,"New capture was not stored.");
        else print(bottom,16,68,WHITE,"Search complete.");
        if(game.replaced_slot>=0) {
            snprintf(txt,sizeof txt,"Replaced storage slot %d",game.replaced_slot+1);
            print(bottom,16,92,PINK,txt);
        }
        print(bottom,16,112,have_storage?CYAN:PINK,
              dr_research_save_status(have_storage,game.requested_save));
        print(bottom,38,165,WHITE,"A: RETURN TO LAB");
        break;}
    case STATE_REPLACE: {
        load_bg("menu_top.raw",top,0x8824);
        top_title("FULL STORAGE - YOUR CHOICE");
        char line[70];
        if(game.replace_kind==REPLACE_POKEMON)
            snprintf(line,sizeof line,"NEW: %s",game_species_name(game.replace_value));
        else snprintf(line,sizeof line,"NEW: %s x1",game_item_name(game.replace_value));
        print_wrapped(top,10,43,37,GOLD,line,2);
        print(top,10,78,WHITE,"Choose an occupied slot.");
        print(top,10,93,WHITE,"It will be overwritten ONLY");
        print(top,10,106,WHITE,"after you confirm twice.");
        if(game.replace_confirm) {
            rect(top,6,124,245,58,0x8844);
            border(top,6,124,245,58,PINK);
            print(top,12,134,PINK,"CONFIRM: Previous content lost!");
            print(top,12,148,WHITE,"Press A again to replace.");
            print(top,12,163,WHITE,"B keeps all existing slots.");
        } else {
            print(top,10,139,CYAN,"No transfer is performed.");
            print(top,10,153,GRAY,"B cancels with no data loss.");
        }
        load_bg("menu_bottom.raw",bottom,0x8824);
        for(int i=0;i<6;i++) {
            if(game.replace_kind==REPLACE_POKEMON)
                snprintf(line,sizeof line,"%d. %s",i+1,
                    game_species_name(game.save.pending[i]));
            else snprintf(line,sizeof line,"%d. %s x%d",i+1,
                game_item_name(game_item_slot_kind(&game,i)),game.save.pending_items[i]);
            button(bottom,3+i*25,line,game.replace_selected==i);
        }
        print(bottom,6,157,game.replace_confirm?PINK:CYAN,
              game.replace_confirm?"A: CONFIRM REPLACE":"A: CHOOSE SLOT");
        print(bottom,6,171,WHITE,"B / SELECT: KEEP OLD DATA");
        break; }
    case STATE_RECORDS: {
        load_bg("menu_top.raw",top,0x8824);top_title("RESEARCH RECORDS");
        draw_sprite(top,S_ICON,82,38);
        load_bg("menu_bottom.raw",bottom,0x8824);
        char tx[80];
        snprintf(tx,sizeof tx,"Searches: %lu",(unsigned long)game.save.searches);print(bottom,12,20,WHITE,tx);
        snprintf(tx,sizeof tx,"Total Orbs: %lu",(unsigned long)game.save.total_orbs);print(bottom,12,39,GOLD,tx);
        snprintf(tx,sizeof tx,"Captured: %lu",(unsigned long)game.save.caught_count);print(bottom,12,58,WHITE,tx);
        snprintf(tx,sizeof tx,"Story progress: %u / 3",game.save.story_phase);print(bottom,12,77,CYAN,tx);
        snprintf(tx,sizeof tx,"Legendary captures: %u",__builtin_popcount((unsigned)game.save.legends_caught));print(bottom,12,96,WHITE,tx);
        snprintf(tx,sizeof tx,"Pending Pokemon: %u / 6",game.save.pending_count);print(bottom,12,115,WHITE,tx);
        print(bottom,12,150,CYAN,"A / X: VIEW STORED RESEARCH");
        print(bottom,12,166,GRAY,"B: RETURN TO LAB");
        break;}
    case STATE_STORAGE: {
        load_bg("menu_top.raw",top,0x8824);
        top_title("PENDING RESEARCH STORAGE");
        draw_sprite(top,S_ICON,86,37);
        coins(160);
        load_bg("menu_bottom.raw",bottom,0x8824);
        char line[72];
        int is_items=(game.page==1);
        print(bottom,12,6,GOLD,is_items?"ITEM STACKS (6 SLOTS)":"POKEMON (6 SLOTS)");
        for(int i=0;i<6;i++) {
            if(is_items){
                int type=game_item_slot_kind(&game,i);
                if(type>=0)snprintf(line,sizeof line,"%d. %s  x%u",i+1,
                    game_item_name(type),game.save.pending_items[i]);
                else snprintf(line,sizeof line,"%d. -- empty --",i+1);
            } else {
                if(i<game.save.pending_count)
                    snprintf(line,sizeof line,"%d. %s",i+1,game_species_name(game.save.pending[i]));
                else snprintf(line,sizeof line,"%d. -- empty --",i+1);
            }
            rect(bottom,8,24+i*22,240,20,i%2?0x8844:0x8C64);
            print(bottom,14,31+i*22,WHITE,line);
        }
        print(bottom,8,164,CYAN,"L / R / A: SWITCH TAB");
        print(bottom,8,179,GRAY,"B: RESEARCH RECORDS");
        break;
    }
    case STATE_ALBUM: {
        if(album_loaded) {
            /* Display every pixel of the original captured frame; navigation
               and metadata belong on the lower screen, not over the photo. */
            memcpy(top,camera_last_frame,sizeof top);
        } else {
            load_bg("menu_top.raw",top,0x8824);
            top_title("DSi CAMERA PHOTO ALBUM");
            print_wrapped(top,16,72,35,WHITE,
                "No valid Dream Radar photos found on this SD card.",5);
        }
        /* Album navigation is read-only and never modifies saved pictures. */
        load_bg("menu_bottom.raw",bottom,0x8824);
        char line[80];
        if(album_loaded) snprintf(line,sizeof line,"PHOTO %03d  -  256 x 192",album_slot);
        else snprintf(line,sizeof line,"NO PHOTO SELECTED");
        print(bottom,19,30,GOLD,line);
        print_wrapped(bottom,18,62,35,WHITE,
            "Photos from the DSi outer camera are saved as numbered BMP files.",7);
        print(bottom,12,137,CYAN,"LEFT / RIGHT: PREVIOUS / NEXT");
        print(bottom,12,154,WHITE,"X: REFRESH PHOTOS");
        print(bottom,12,171,GRAY,"B: RESEARCH LAB");
        break;}
    case STATE_TRANSFER: {
        /* 3DS screenshot: outlined question on top, research tray on touch screen.
           The visual layout is reproduced, but live retail transfers are NOT implemented. */
        load_bg("transfer_top.raw",top,0x8844);
        if(game.cart==GAME_WHITE2 || game.cart==GAME_BLACK2) {
            print(top,13,20,WHITE,"Research data for");
            print(top,13,39,WHITE,game.cart==GAME_WHITE2?"Pokemon White Version 2":"Pokemon Black Version 2");
            print(top,13,59,WHITE,"is ready to archive.");
        } else {
            print(top,13,24,WHITE,"Send research data to");
            print(top,13,44,WHITE,"Pokemon Black/White 2?");
        }
        print(top,10,103,GOLD,"Retail transfer not available.");
        print_wrapped(top,10,124,38,WHITE,"A saves a text archive only. No Pokemon retail save will be modified.",6);
        if(game.selection>=0 && game.selection<12) {
            int selected=game.selection%6;
            const char *name=NULL;
            if(game.selection<6 && selected<game.save.pending_count)
                name=game_species_name(game.save.pending[selected]);
            else if(game.selection>=6) {
                int kind=game_item_slot_kind(&game,selected);
                if(kind>=0)name=game_item_name(kind);
            }
            if(name) {
                char detail[43];snprintf(detail,sizeof detail,"SLOT %d: %.26s",game.selection+1,name);
                print(top,10,164,CYAN,detail);
            }
        }
        render_transfer_bottom();
        if(game.archive_confirm) {
            rect(bottom,18,117,219,30,0x8842);border(bottom,18,117,219,30,GOLD);
            print(bottom,23,123,PINK,"START: clear archived queue");
            print(bottom,23,134,WHITE,"B: keep your Pokemon/items");
        } else if(game.pending_export_signature) {
            print(bottom,18,135,CYAN,"SELECT: prepare queue clear");
        }
        break;}
    case STATE_SD_SAVES: {
        load_bg("menu_top.raw",top,0x8824);top_title("TWILIGHT SD GAME SAVES");
        draw_sprite(top,S_ICON,91,35);
        char line[70];snprintf(line,sizeof line,"Available pairs: %u",sd_index.with_saves);
        print(top,14,126,CYAN,line);
        print(top,14,140,WHITE,"ONE active game at a time");
        print(top,14,153,GRAY,"SD saves are not inserted cards");
        load_bg("menu_bottom.raw",bottom,0x8824);
        if(!sd_index.count)print_wrapped(bottom,12,17,35,WHITE,
            "No supported .nds/.sav pairs found. Place matching games and saves on the SD card.",7);
        int start=(sd_selected/5)*5;
        for(int i=start;i<start+5 && i<(int)sd_index.count;i++) {
            const TwilightSaveEntry *e=&sd_index.entries[i];
            if(e->location)
                snprintf(line,sizeof line,"%s [SAV%u]",game_cart_name(e->game),e->save_slot);
            else snprintf(line,sizeof line,"%s [NO SAVE]",game_cart_name(e->game));
            button(bottom,6+(i-start)*30,line,sd_selected==i);
        }
        print(bottom,9,158,CYAN,"A: SET ACTIVE  X: RESCAN");
        print(bottom,9,169,GRAY,"Y: SLOT-1  SELECT: CLEAR");
        print(bottom,9,181,GRAY,"B: BACK");
        break; }
    case STATE_PLACEHOLDER: {
        char line[70]; /* Photo preview label is local to this screen. */
        load_bg("menu_top.raw",top,0x8824);
        if(placeholder_preview_loaded)memcpy(top,placeholder_preview,sizeof top);
        else top_title("CAMERA-FREE BACKGROUND");
        load_bg("menu_bottom.raw",bottom,0x8824);
        print(bottom,10,12,WHITE,"CUSTOM BACKGROUND");
        print_wrapped(bottom,10,31,39,WHITE,
            "Put 256x192 BMP files named photo_000.bmp etc. in sd:/DreamRadarDSi/Photos/",6);
        if(placeholder_preview_slot>=0)
            snprintf(line,sizeof line,"PHOTO %03d",placeholder_preview_slot);
        else snprintf(line,sizeof line,"NO VALID PHOTO");
        print(bottom,10,105,CYAN,line);
        print(bottom,10,116,WHITE,game.save.camera_enabled ?
              "CAMERA ON: LIVE VIEW HAS PRIORITY" :
              "CAMERA OFF: PHOTO MODE ACTIVE");
        print(bottom,10,128,WHITE,"LEFT/RIGHT: BROWSE   A: USE");
        print(bottom,10,141,WHITE,"X: CAMERA ON/OFF");
        print(bottom,10,154,WHITE,"SELECT: BUILT-IN BACKGROUND");
        print(bottom,10,177,GRAY,"B: BACK TO OPTIONS");
        break;
    }
    case STATE_SETTINGS: {
        load_bg("menu_top.raw",top,0x8824);top_title(running_dsi?"DSi RADAR OPTIONS":"DS RADAR OPTIONS");
        draw_sprite(top,S_RETICLE,110,68);
        load_bg("menu_bottom.raw",bottom,0x8824);
        char tx[70];
        for(int i=0;i<dr_settings_count(running_dsi);i++) {
            int action=dr_settings_action(running_dsi,i);
            if(action==DR_SETTING_CAMERA)
                snprintf(tx,sizeof tx,"CAMERA: %s",game.save.camera_enabled?"ON":"OFF");
            else if(action==DR_SETTING_OPTICAL)
                snprintf(tx,sizeof tx,"OPTICAL AIM: %s",game.save.optical_aim?"ON":"OFF");
            else if(action==DR_SETTING_CART)
                snprintf(tx,sizeof tx,"READ INSERTED DS GAME");
            else snprintf(tx,sizeof tx,"SELECT ONE SD GAME");
            if(action==DR_SETTING_PLACEHOLDER)snprintf(tx,sizeof tx,"CUSTOM CAMERA-FREE IMAGE");
            button(bottom,16+i*28,tx,game.selection==i);
        }
        print(bottom,12,158,CYAN,game_cart_name(game.cart));
        print(bottom,12,169,GRAY,game_cart_source_name(game.cart_source));
        print(bottom,12,181,GRAY,"B: LAB");
        break;}
    }
    if(game.messages>0) {
        rect(top,5,145,246,42,0x88C4);border(top,5,145,246,42,GOLD);
        print_wrapped(top,10,150,38,WHITE,game.message,3);
    }
    memcpy(top_vram,top,sizeof top);
    memcpy(bottom_vram,bottom,sizeof bottom);
}
static u8 sample_luma(u16 p) {
    int r=p&31,g=(p>>5)&31,b=(p>>10)&31;
    return (u8)((r*3+g*6+b)/10);
}
static void update_optical_motion(void) {
    if(!game.save.optical_aim)return;
    for(int y=0;y<24;y++)for(int x=0;x<32;x++)now_samples[y*32+x]=sample_luma(camera_last_frame[(y*8+3)*256+x*8+3]);
    if(old_sample_valid){
        unsigned best=0xffffffffu;int bestx=0,besty=0;
        for(int dy=-2;dy<=2;dy++)for(int dx=-2;dx<=2;dx++) {
            unsigned error=0;
            for(int y=3;y<21;y+=2)for(int x=3;x<29;x+=2){
                int d=now_samples[y*32+x]-old_samples[(y+dy)*32+(x+dx)];
                error+=(unsigned)(d*d);
            }
            if(error<best){best=error;bestx=dx;besty=dy;}
        }
        // Extremely crude optical-flow estimate, not a gyro replacement.
        if(best<150000) {
            game.aim_x+=bestx*3;game.aim_y+=besty*3;
            if(game.aim_x<6)game.aim_x=6;
            if(game.aim_x>250)game.aim_x=250;
            if(game.aim_y<6)game.aim_y=6;
            if(game.aim_y>185)game.aim_y=185;
        }
    }
    memcpy(old_samples,now_samples,sizeof old_samples);old_sample_valid=1;
}
static void camera_off(void) {
    if(game.camera_ok){
        if(camera_busy){while(ndmaBusy(CAM_DMA)||cameraTransferActive())swiWaitForVBlank();cameraStopTransfer();}
        cameraDeinit();
    }
    game.camera_ok=0;game.camera_active=0;camera_busy=0;camera_frames=0;
    old_sample_valid=0;
}
static void camera_on(void) {
    if(!dr_camera_allowed(running_dsi,game.save.camera_enabled) ||
       camera_failed_this_run || game.camera_ok)return;
    if(!cameraInit())goto failed;
    if(!cameraSelect(CAMERA_OUTER)) {cameraDeinit();goto failed;}
    camera_frames=0;
    camera_busy=cameraStartTransfer(camera_frame,MCUREG_APT_SEQ_CMD_PREVIEW,CAM_DMA);
    if(!camera_busy){cameraDeinit();goto failed;}
    game.camera_ok=1;game.camera_active=1;
    game.camera_error=0; /* Successful retry clears the previous failure. */
    return;
failed:
    camera_failed_this_run=1;
    game.camera_error=1;game.camera_ok=0;game.camera_active=0;camera_busy=0;
    snprintf(game.message,sizeof game.message,
        "Camera unavailable. Playing with stylus/D-pad aiming.");
    game.messages=180;
}
static void update_camera(void) {
    if(!game.camera_ok)return;
    if(camera_busy && !ndmaBusy(CAM_DMA) && !cameraTransferActive()){
        cameraStopTransfer();
        camera_busy=0;
        DC_InvalidateRange(camera_frame,sizeof camera_frame);
        memcpy(camera_last_frame,camera_frame,sizeof camera_last_frame);
        /* Leave the frame-ready counter positive without signed overflow
           after very long DSi sessions. Only readiness, not total frames,
           is needed by the photo saver. */
        camera_frames=dr_camera_next_frame_count(camera_frames);
        if(game.save.optical_aim)update_optical_motion();
    }
    if(!camera_busy && (game.save.frames_played%3==0)) {
        camera_busy=cameraStartTransfer(camera_frame,MCUREG_APT_SEQ_CMD_PREVIEW,CAM_DMA);
        if(!camera_busy){
            camera_off();camera_failed_this_run=1;game.camera_error=1;
            snprintf(game.message,sizeof game.message,
                "Camera stopped. Stylus/D-pad aiming still works.");
            game.messages=180;
        }
    }
}
static int save_photo(void) {
    if(!dr_photo_capture_ready(running_dsi,photo_storage_ready,
                               game.camera_active,game.camera_ok,camera_frames))return 0;
    return dr_photo_save_new(photo_dir, &photo_index,
                             camera_last_frame, PIXELS);
}
static void album_select(int direction) {
    /* Visit each numbered slot only once. Calling dr_photo_find repeatedly
       for corrupt BMPs previously performed up to one million stat() calls. */
    if(photo_storage_ready) {
        int step=direction<0?-1:1;
        int start=direction==0 || album_slot<0
                ? (step<0?DR_PHOTO_MAX-1:0)
                : (album_slot+step+DR_PHOTO_MAX)%DR_PHOTO_MAX;
        for(int attempt=0;attempt<DR_PHOTO_MAX;attempt++) {
            int slot=(start+step*attempt+DR_PHOTO_MAX)%DR_PHOTO_MAX;
            char path[128];
            snprintf(path,sizeof path,"%s/photo_%03d.bmp",photo_dir,slot);
            /* Failed decoding must not overwrite the displayed photograph. */
            if(dr_photo_read(path,camera_frame,PIXELS)) {
                memcpy(camera_last_frame,camera_frame,sizeof camera_last_frame);
                album_slot=slot;album_loaded=1;return;
            }
        }
    }
    if(direction==0) {album_slot=-1;album_loaded=0;}
}

static void check_cartridge(void) {
    // Read-only header identification. Running via DSi SD recommended. Never touches EEPROM.
    active_sd_entry_valid=0;
    u8 hdr[0x200]={0};
    if (!running_dsi) {
        game_set_cart(&game,GAME_UNKNOWN);
        snprintf(game.message,sizeof game.message,
            "On DS, select one game from the flashcart save browser.");
        game.messages=150;return;
    }
    cardReadHeader(hdr);
    char code[5]={0};memcpy(code,hdr+12,4);
    game_set_cart(&game,game_identify_cart(code));
    snprintf(game.message,sizeof game.message,"Game Card: %s (%s)",game_cart_name(game.cart),code);
    game.messages=180;
}
static void scan_sd_saves(void) {
    if (!have_storage) { memset(&sd_index,0,sizeof sd_index);sd_selected=0;return; }
    twilight_scan(&sd_index,storage_root,active_rom_dir[0]?active_rom_dir:NULL);
    if (sd_selected >= (int)sd_index.count) sd_selected=0;
}
static void activate_sd_save(int index) {
    if (index<0 || index>=(int)sd_index.count) return;
    const TwilightSaveEntry *e=&sd_index.entries[index];
    if (!twilight_validate_entry(e)) {
        snprintf(game.message,sizeof game.message,"SD game/save unavailable or changed. Rescan with X.");
    } else {
        /* Only one active game; never read or modify Pokemon save contents. */
        game_set_cart_source(&game,e->game,CART_SOURCE_TWILIGHT_SD);
        active_sd_entry=*e;
        active_sd_entry_valid=1;
        if(e->location==TW_SAVE_NONE)
            snprintf(game.message,sizeof game.message,"Active ROM: %s (read-only).",game_cart_name(game.cart));
        else
            snprintf(game.message,sizeof game.message,"Active: %s, save slot %d.",game_cart_name(game.cart),e->save_slot);
    }
    game.messages=180;
}
/* The SD save and physical cartridge may have changed since selection.
 * Revalidate before spending Orbs or starting a cartridge-specific encounter. */
static int validate_active_source(void) {
    if(game.cart_source==CART_SOURCE_TWILIGHT_SD) {
        if(active_sd_entry_valid && twilight_validate_entry(&active_sd_entry) &&
           active_sd_entry.game==game.cart)return 1;
        active_sd_entry_valid=0;
    } else if(game.cart_source==CART_SOURCE_SLOT1) {
        if(running_dsi) {
            u8 header[0x200]={0};cardReadHeader(header);
            char code[5]={0};memcpy(code,header+12,4);
            if(game_identify_cart(code)==game.cart)return 1;
        }
    } else return 1;
    game_set_cart_source(&game,GAME_UNKNOWN,CART_SOURCE_NONE);
    snprintf(game.message,sizeof game.message,
        "Active game changed or missing. Select exactly one game again.");
    game.messages=180;
    return 0;
}
static void switch_screen(GameScreen next) {
    const int was_search=game.screen==STATE_RADAR || game.screen==STATE_SPHERE;
    const int is_search=next==STATE_RADAR || next==STATE_SPHERE;
    /* Keep the camera stream alive across cloud-to-encounter transitions.
       Restarting it here discards the live preview and can briefly blank it. */
    if(was_search && !is_search)camera_off();
    game.screen=next;game.selection=0;
    if(next!=STATE_TRANSFER)game.archive_confirm=0;
    if(!was_search && is_search)camera_on();
}
static void finish_story_dialogue(void) {
    if(game.story_event>0 && game.story_event<=3 &&
       game.save.reserved[0]<(unsigned)game.story_event) {
        game.save.reserved[0]=(uint8_t)game.story_event;
        game.requested_save=1;
    }
    switch_screen(STATE_LAB);
}
static void from_results(void) {
    unsigned stage=game.save.reserved[0]+1;
    if(stage<=3 && game.save.story_phase>=stage) {
        game.story_event=(int)stage;
        game.story_event_page=0;
        switch_screen(STATE_DIALOGUE);
    } else switch_screen(STATE_LAB);
}
static void handle_key(int keys,int down,touchPosition *touch) {
    if(game.screen==STATE_LAB){
        const int bits[]={KEY_Y,KEY_X,KEY_A,KEY_X,KEY_LEFT,KEY_RIGHT,KEY_UP,KEY_DOWN,KEY_L,KEY_R};
        (void)bits;
        int code=0;
        if(down&KEY_UP)code=6;else if(down&KEY_RIGHT)code=5;else if(down&KEY_DOWN)code=7;
        else if(down&KEY_LEFT)code=4;else if(down&KEY_X)code=3;else if(down&KEY_Y)code=2;
        else if(down&KEY_R)code=9;else if(down&KEY_L)code=8;
        if(code)game_secret_key(&game,code);
    }
    if(game.screen==STATE_RADAR || game.screen==STATE_SPHERE){
        int back_touch = (down & KEY_TOUCH) && touch->px>=188 && touch->py>=174;
        /* Hardware controls work in BOTH cloud search and Pokémon/item encounters.
           No stylus aiming or synthetic joystick overrides the original touch UI. */
        if(keys&KEY_LEFT) game.aim_x-=3;
        if(keys&KEY_RIGHT)game.aim_x+=3;
        if(keys&KEY_UP)   game.aim_y-=3;
        if(keys&KEY_DOWN) game.aim_y+=3;
        if(game.aim_x<6)game.aim_x=6;
        if(game.aim_x>249)game.aim_x=249;
        if(game.aim_y<6)game.aim_y=6;
        if(game.aim_y>184)game.aim_y=184;
        /* A fires at clouds or at revealed encounter targets. Touch is reserved
           for the original support-item and Back controls. */
        if((keys&KEY_A) && (game.save.frames_played%5==0))game_fire(&game);
        if((down&KEY_TOUCH) && game.screen==STATE_SPHERE && touch->py>=58 && !back_touch) {
            int best=dr_support_at(touch->px,touch->py);
            if(best>=0) game_use_support(&game,best);
        }
        /* DSi-enhanced players can press L+R together to photograph the
           current outer-camera view. Only trigger on a new shoulder press,
           not every frame while both buttons remain held. */
        if(running_dsi && ((down&KEY_X) ||
           dr_photo_shortcut(running_dsi,keys,down,KEY_L,KEY_R))) {
            if(save_photo())snprintf(game.message,sizeof game.message,"Photo saved on DSi SD card.");
            else snprintf(game.message,sizeof game.message,"Camera photo unavailable.");
            game.messages=120;
        }
        if((down&KEY_B) || ((down&KEY_TOUCH) && touch->px>=188 && touch->py>=174)){
            game_leave_search(&game);
        }
        return;
    }
    if(game.screen==STATE_INTRO){
        if(down&KEY_B){game.save.intro_seen=1;game.requested_save=1;switch_screen(STATE_LAB);}
        if(down&(KEY_A|KEY_TOUCH)){
            game.intro_page++;
            if(game.intro_page>=(int)INTRO_PAGES){game.save.intro_seen=1;game.requested_save=1;switch_screen(STATE_LAB);}
        }
        return;
    }
    if(game.screen==STATE_TITLE){
        if(down&KEY_UP)game.selection=(game.selection+3)%4;
        if(down&KEY_DOWN)game.selection=(game.selection+1)%4;
        int title_touch=(down&KEY_TOUCH)?dr_title_hit(touch->px,touch->py):-1;
        if(title_touch>=0)game.selection=title_touch;
        if((down&KEY_A)||(down&KEY_START)||title_touch>=0) {
            switch(game.selection){
            case 0: switch_screen(game.save.intro_seen?STATE_LAB:STATE_INTRO);break;
            case 1: switch_screen(STATE_TRANSFER);break;
            case 2: switch_screen(STATE_CREDITS);break;
            case 3: switch_screen(STATE_RECORDS);break;
            }
        }
        if(down&KEY_B)switch_screen(STATE_SETTINGS);
        return;
    }
    if(game.screen==STATE_CREDITS){
        if(down&(KEY_B|KEY_A|KEY_TOUCH))switch_screen(STATE_TITLE);
        return;
    }
    if(game.screen==STATE_REPLACE) {
        if(down&(KEY_B|KEY_SELECT) ||
           ((down&KEY_TOUCH) && touch->py>=161)) {
            game_cancel_pending_replace(&game);
            return;
        }
        if(down&KEY_UP) {
            game.replace_selected=(game.replace_selected+5)%6;
            game.replace_confirm=0;
        }
        if(down&KEY_DOWN) {
            game.replace_selected=(game.replace_selected+1)%6;
            game.replace_confirm=0;
        }
        if((down&KEY_TOUCH) && touch->py>=3 && touch->py<153) {
            int selected=(touch->py-3)/25;
            if(selected!=game.replace_selected)game.replace_confirm=0;
            game.replace_selected=selected;
            if(game.replace_confirm)game_replace_pending(&game,game.replace_selected);
            else game.replace_confirm=1;
        } else if(down&KEY_A) {
            if(game.replace_confirm)game_replace_pending(&game,game.replace_selected);
            else game.replace_confirm=1;
        }
        return;
    }
    if(game.screen==STATE_RESULTS){if(down&(KEY_A|KEY_B|KEY_TOUCH))from_results();return;}
    if(game.screen==STATE_ALBUM) {
        if(down&KEY_RIGHT)album_select(1);
        if(down&KEY_LEFT)album_select(-1);
        if(down&KEY_X)album_select(0);
        if(down&KEY_B)switch_screen(STATE_LAB);
        return;
    }
    if(game.screen==STATE_DIALOGUE) {
        if(down&KEY_B)finish_story_dialogue();
        else if(down&(KEY_A|KEY_TOUCH)) {
            game.story_event_page++;
            if(game.story_event_page>=story_page_counts[game.story_event])finish_story_dialogue();
        }
        return;
    }
    if(game.screen==STATE_EXTENSIONS){
        extension_ensure_selected();
        int count=extension_visible_count();
        if(down&KEY_DOWN)game.ext_selection=extension_at_row((extension_row_of(game.ext_selection)+1)%count);
        if(down&KEY_UP)game.ext_selection=extension_at_row((extension_row_of(game.ext_selection)+count-1)%count);
        if((down&KEY_TOUCH) && touch->px>=8 && touch->px<248 && touch->py>=10 && touch->py<160) {
            int row=(extension_row_of(game.ext_selection)/5)*5+(touch->py-10)/30;
            if(row<count)game.ext_selection=extension_at_row(row);
        }
        if(down&KEY_A && validate_active_source()) {
            GameScreen prev=game.screen;
            game_begin_search(&game,game.ext_selection);
            /* Cloud radar first; camera starts only on capture encounter. */
            (void)prev;
        }
        if(down&KEY_B)switch_screen(STATE_LAB);
        return;
    }
    if(game.screen==STATE_SHOP){
        if(down&KEY_DOWN)game.selection=(game.selection+1)%6;
        if(down&KEY_UP)game.selection=(game.selection+5)%6;
        if(down&KEY_TOUCH) {
            int row=dr_shop_hit(touch->px,touch->py);
            if(row>=0)game.selection=row;
        }
        if((down&KEY_A) || ((down&KEY_TOUCH) && dr_shop_hit(touch->px,touch->py)>=0))
            game_buy(&game,game.selection<3?0:1,game.selection<3?game.selection:game.selection-3);
        if(down&KEY_B)switch_screen(STATE_LAB);
        return;
    }
    if(game.screen==STATE_TRANSFER){
        if(down&KEY_LEFT)game.selection=(game.selection+11)%12;
        if(down&KEY_RIGHT)game.selection=(game.selection+1)%12;
        if(down&KEY_UP)game.selection=(game.selection+6)%12;
        if(down&KEY_DOWN)game.selection=(game.selection+6)%12;
        if(down&KEY_TOUCH) {
            int slot=dr_transfer_slot_at(touch->px,touch->py);
            if(slot>=0)game.selection=slot;
        }
        if((down&KEY_TOUCH) && dr_transfer_button_at(touch->px,touch->py)==1){
            switch_screen(STATE_LAB);return;
        }
        if((down&KEY_TOUCH) && dr_transfer_button_at(touch->px,touch->py)==0)
            down|=KEY_A;
        if(down&KEY_A){
            game.archive_confirm=0;
            snprintf(game.message,sizeof game.message,
                export_unique_research()?"New text archive saved to storage. NOT transferred.":
                "Archive failed. Demo queue remains unchanged.");
            game.messages=180;
        }
        if(down&KEY_SELECT) {
            if(game.pending_export_signature){
                game.archive_confirm=1;
                snprintf(game.message,sizeof game.message,
                    "Press START to clear ONLY the local demo queue. NOT a transfer.");
            } else {
                snprintf(game.message,sizeof game.message,
                    "First press A to save the pending data to a text archive.");
            }
            game.messages=180;
        }
        if((down&KEY_START) && game.archive_confirm) {
            int released=game_release_archived_pending(&game);
            game.archive_confirm=0;
            snprintf(game.message,sizeof game.message,released?
                "Archived demo queue cleared; no retail data transferred.":
                "Queue changed. Export again before clearing.");
            game.messages=180;
        }
        if(down&KEY_B)switch_screen(STATE_LAB);
        return;
    }
    if(game.screen==STATE_SD_SAVES) {
        if(down&KEY_DOWN && sd_index.count)sd_selected=(sd_selected+1)%sd_index.count;
        if(down&KEY_UP && sd_index.count)sd_selected=(sd_selected+sd_index.count-1)%sd_index.count;
        if((down&KEY_TOUCH) && touch->py>=6 && touch->py<156) {
            int next=(sd_selected/5)*5+(touch->py-6)/30;
            if(next<(int)sd_index.count){sd_selected=next;activate_sd_save(next);}
        }
        if(down&KEY_A)activate_sd_save(sd_selected);
        if(down&KEY_X)scan_sd_saves();
        if(down&KEY_Y)check_cartridge(); /* Replaces SD selection, if any. */
        if(down&KEY_SELECT){active_sd_entry_valid=0;
            game_set_cart_source(&game,GAME_UNKNOWN,CART_SOURCE_NONE);
            snprintf(game.message,sizeof game.message,"Active game cleared.");game.messages=120;}
        if(down&KEY_B)switch_screen(STATE_SETTINGS);
        return;
    }
    if(game.screen==STATE_PLACEHOLDER) {
        if(down&KEY_X) {
            game.save.camera_enabled=!game.save.camera_enabled;
            /* A deliberate OFF->ON toggle is permission to retry a failed
               camera initialization. Never retry automatically every frame. */
            camera_failed_this_run=dr_camera_retry_latch(game.save.camera_enabled,camera_failed_this_run);
            game.requested_save=1;
            snprintf(game.message,sizeof game.message,game.save.camera_enabled ?
                     "DSi camera enabled." : "Camera off: using custom image if selected.");
            game.messages=120;
        }
        if(down&(KEY_LEFT|KEY_RIGHT)) {
            int slot=-1;
            int direction=(down&KEY_RIGHT)?1:-1;
            int found=0;
            int cursor=placeholder_preview_slot;
            int first=-1;
            /* The album index checks BMP headers. The full decoder can
               still reject a truncated or unreadable file, so skip it. */
            while(photo_storage_ready && dr_photo_find(photo_dir,cursor,direction,&slot)) {
                if(slot==first)break;
                if(first<0)first=slot;
                if(preview_custom_background(slot)){found=1;break;}
                cursor=slot;
            }
            if(!found) {
                snprintf(game.message,sizeof game.message,"No readable 256x192 BMP photos found.");
                game.messages=120;
            }
        }
        if(down&KEY_A) {
            if(placeholder_preview_slot>=0 && load_custom_background(placeholder_preview_slot)) {
                select_custom_background(placeholder_preview_slot);
                snprintf(game.message,sizeof game.message,"Camera-free photo selected.");
            } else snprintf(game.message,sizeof game.message,"No valid photo selected.");
            game.messages=120;
        }
        if(down&KEY_SELECT) {
            custom_background_loaded=0;
            custom_background_slot=-1;
            placeholder_preview_slot=-1;
            placeholder_preview_loaded=0;
            game.save.reserved[11]=0;
            game.requested_save=1;
            snprintf(game.message,sizeof game.message,"Original background restored.");
            game.messages=120;
        }
        if(down&KEY_B){placeholder_preview_loaded=0;switch_screen(STATE_SETTINGS);}
        return;
    }
    if(game.screen==STATE_SETTINGS){
        int count=dr_settings_count(running_dsi);
        if(down&KEY_DOWN)game.selection=(game.selection+1)%count;
        if(down&KEY_UP)game.selection=(game.selection+count-1)%count;
        int touched=(down&KEY_TOUCH) ? dr_settings_hit(touch->px,touch->py,running_dsi) : -1;
        if(touched>=0)game.selection=touched;
        if((down&KEY_A) || touched>=0){
            int action=dr_settings_action(running_dsi,game.selection);
            if(action==DR_SETTING_CAMERA){
                game.save.camera_enabled=!game.save.camera_enabled;
                camera_failed_this_run=dr_camera_retry_latch(game.save.camera_enabled,camera_failed_this_run);
                game.requested_save=1;
            }
            if(action==DR_SETTING_OPTICAL){game.save.optical_aim=!game.save.optical_aim;game.requested_save=1;}
            if(action==DR_SETTING_CART)check_cartridge();
            if(action==DR_SETTING_SD){scan_sd_saves();switch_screen(STATE_SD_SAVES);}
            if(action==DR_SETTING_PLACEHOLDER) {
                placeholder_preview_slot=-1;
                placeholder_preview_loaded=0;
                if(custom_background_slot>=0)
                    preview_custom_background(custom_background_slot);
                if(!placeholder_preview_loaded && photo_storage_ready) {
                    int found=-1, cursor=-1, first=-1;
                    while(dr_photo_find(photo_dir,cursor,1,&found)) {
                        if(found==first)break;
                        if(first<0)first=found;
                        if(preview_custom_background(found))break;
                        cursor=found;
                    }
                }
                switch_screen(STATE_PLACEHOLDER);
            }
        }
        if(down&KEY_B)switch_screen(STATE_LAB);
        return;
    }
    if(game.screen==STATE_TIPS){
        if(down&KEY_B)switch_screen(STATE_LAB);
        else if(down&(KEY_A|KEY_TOUCH))game.page=(game.page+1)%BURNET_TIP_COUNT;
        return;
    }
    if(game.screen==STATE_RECORDS){
        if(down&(KEY_A|KEY_X|KEY_TOUCH)){game.page=0;switch_screen(STATE_STORAGE);}
        if(down&KEY_B)switch_screen(STATE_LAB);
        return;
    }
    if(game.screen==STATE_STORAGE){
        if(down&(KEY_A|KEY_L|KEY_R|KEY_LEFT|KEY_RIGHT|KEY_TOUCH))game.page^=1;
        if(down&KEY_B)switch_screen(STATE_RECORDS);
        return;
    }
    if(game.screen==STATE_LAB){
        int count=dr_lab_count(running_dsi);
        if(down&KEY_DOWN)game.selection=(game.selection+1)%count;
        if(down&KEY_UP)game.selection=(game.selection+count-1)%count;
        int touched=(down&KEY_TOUCH) ? dr_lab_hit(touch->px,touch->py,count) : -1;
        if(touched>=0)game.selection=touched;
        if(down&KEY_Y)check_cartridge();
        if(down&KEY_B)switch_screen(STATE_TITLE);
        if((down&KEY_A) || touched>=0){
            GameScreen pages[]={STATE_EXTENSIONS,STATE_SHOP,STATE_TRANSFER,
                                STATE_RECORDS,STATE_SETTINGS,STATE_TIPS,STATE_ALBUM};
            int action=dr_lab_action(running_dsi,game.selection);
            if(action==0)game.ext_selection=0;
            if(action==5)game.page=(int)(game.save.searches % BURNET_TIP_COUNT);
            if(action==6)album_select(0);
            switch_screen(pages[action]);
        }
        return;
    }
}
int main(int argc, char **argv) {
    irqInit();irqEnable(IRQ_VBLANK);
    videoSetMode(MODE_5_2D);videoSetModeSub(MODE_5_2D);
    vramSetBankA(VRAM_A_MAIN_BG);vramSetBankC(VRAM_C_SUB_BG);
    int top_layer=bgInit(3,BgType_Bmp16,BgSize_B16_256x256,0,0);
    int bottom_layer=bgInitSub(3,BgType_Bmp16,BgSize_B16_256x256,0,0);
    top_vram=(u16*)bgGetGfxPtr(top_layer);bottom_vram=(u16*)bgGetGfxPtr(bottom_layer);
    bgSetPriority(top_layer,0);bgSetPriority(bottom_layer,0);
    lcdMainOnTop();
running_dsi=isDSiMode();
    /* Initialise the launcher filesystem before mounting NitroFS.  When
       launched from TWiLight Menu++ the ROM's NitroFS may be backed by SD;
       mounting it first can fail even when the bundled art is present. */
    /* TWiLight Menu++/nds-bootstrap and flashcart loaders may expose the
       ROM's NitroFS even when writable DLDI storage is unavailable.
       Keep asset mounting independent of save-media availability. */
    have_storage=fatInitDefault();
    have_romfs=nitroFSInit(NULL);
    cache_backgrounds();
    if(have_storage){
        /* DSi internal SD and DS/DS Lite flashcart DLDI are different mounts. */
        const char *preferred=dr_storage_root(running_dsi);
        storage_root=dr_storage_ready(preferred)?preferred:NULL;
        if(!storage_root){
            const char *alternate=dr_storage_root(!running_dsi);
            if(dr_storage_ready(alternate))storage_root=alternate;
        }
        have_storage=storage_root!=NULL;
        if(have_storage) {
            int export_len=snprintf(export_dir,sizeof export_dir,"%sDreamRadarDSi",storage_root);
            if(export_len<0 || export_len>=(int)sizeof export_dir) {
                have_storage=0;
                storage_root=NULL;
            }
            /* Camera photos belong only on actual DSi SD storage. Skip
               formatting the album path if export storage was rejected. */
            if(have_storage && running_dsi && storage_root &&
               strcmp(storage_root,"sd:/")==0) {
                int photo_len=snprintf(photo_dir,sizeof photo_dir,"%s/Photos",export_dir);
                if(photo_len<0 || photo_len>=(int)sizeof photo_dir) {
                    photo_storage_ready=0;
                } else {
                struct stat st;
                /* mkdir() cannot create Photos if its parent is absent.
                   Ensure both directories exist on a freshly formatted SD. */
                int parent_ok=mkdir(export_dir,0777)==0 ||
                    (stat(export_dir,&st)==0 && S_ISDIR(st.st_mode));
                if(parent_ok)
                    photo_storage_ready=mkdir(photo_dir,0777)==0 ||
                        (stat(photo_dir,&st)==0 && S_ISDIR(st.st_mode));
                }
            }
        }
    }
    if(have_storage && argc>0 && argv && argv[0] &&
       strncmp(argv[0],storage_root,strlen(storage_root))==0){
        const char *slash=strrchr(argv[0],'/');
        if(slash && (size_t)(slash-argv[0])<sizeof active_rom_dir){
            memcpy(active_rom_dir,argv[0],(size_t)(slash-argv[0]));
            active_rom_dir[slash-argv[0]]=0;
        }
    }
    if(have_storage)save_backend_init(&save_backend,storage_root,argc>0?argv[0]:NULL);
    for(int i=0;i<68;i++)load_sprite(i);
    time_t now=time(NULL);
    game_new(&game, ((uint32_t)now)^0xa15f009u);
    if(have_storage)save_backend_load(&save_backend,&game);
    restore_custom_background();
    game_regen_clouds(&game,(uint32_t)now);
    // Camera only starts when actively searching and the mode supports DSi.
    while(1){
        swiWaitForVBlank();
        scanKeys();int down=keysDown(), keys=keysHeld();
        touchPosition t;touchRead(&t);
        game_tick(&game);
        handle_key(keys,down,&t);
        if((game.save.frames_played%60)==0){
            time_t current=time(NULL);if(current>0)game_regen_clouds(&game,(uint32_t)current);
        }
        if(game.screen!=STATE_SPHERE && game.screen!=STATE_RADAR && game.camera_active)camera_off();
        if((game.screen==STATE_SPHERE || game.screen==STATE_RADAR) && !game.camera_active)camera_on();
        if(game.screen==STATE_SPHERE || game.screen==STATE_RADAR)update_camera();
        render();
        if(game.requested_save && have_storage && (game.save.frames_played%30)==0){
            if(save_backend_write(&save_backend,&game))game.requested_save=0;
            else {snprintf(game.message,sizeof game.message,"Could not save Dream Radar progress.");game.messages=120;}
        }
    }
    return 0;
}
