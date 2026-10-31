#ifndef DREAM_RADAR_HOST_CAMERA_H
#define DREAM_RADAR_HOST_CAMERA_H
#include <nds.h>
enum { CAMERA_OUTER=1, MCUREG_APT_SEQ_CMD_PREVIEW=1 };
bool cameraInit(void);bool cameraSelect(int);bool cameraStartTransfer(u16*,u8,u8);
void cameraStopTransfer(void);bool cameraTransferActive(void);bool cameraDeinit(void);
#endif
