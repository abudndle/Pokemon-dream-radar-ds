/* Host-only API declarations for a C syntax smoke test. NOT a libnds replacement. */
#ifndef DREAM_RADAR_HOST_NDS_H
#define DREAM_RADAR_HOST_NDS_H
#include <stdint.h>
#include <stdbool.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef struct { int px,py; } touchPosition;
enum { IRQ_VBLANK=1, MODE_5_2D=5, VRAM_A_MAIN_BG=1, VRAM_C_SUB_BG=2,
       BgType_Bmp16=1, BgSize_B16_256x256=2 };
enum {KEY_A=1,KEY_B=2,KEY_X=4,KEY_Y=8,KEY_UP=16,KEY_DOWN=32,
      KEY_LEFT=64,KEY_RIGHT=128,KEY_L=256,KEY_R=512,KEY_START=1024,
      KEY_SELECT=2048,KEY_TOUCH=4096};
void irqInit(void);void irqEnable(int);
void videoSetMode(int);void videoSetModeSub(int);void vramSetBankA(int);void vramSetBankC(int);
int bgInit(int,int,int,int,int);int bgInitSub(int,int,int,int,int);
void *bgGetGfxPtr(int);void bgSetPriority(int,int);void lcdMainOnTop(void);
bool nitroFSInit(const char *);bool isDSiMode(void);
void swiWaitForVBlank(void);void scanKeys(void);int keysDown(void);int keysHeld(void);
void touchRead(touchPosition *);void cardReadHeader(void *);
void DC_InvalidateRange(void *,unsigned int);
#endif
