/* Runtime DS/DSi feature policy. No camera is EVER required for gameplay. */
#ifndef DR_PLATFORM_COMPAT_H
#define DR_PLATFORM_COMPAT_H

enum {DR_SETTING_CAMERA,DR_SETTING_OPTICAL,DR_SETTING_CART,DR_SETTING_SD,DR_SETTING_PLACEHOLDER};
int dr_lab_count(int dsi_mode);
int dr_lab_action(int dsi_mode,int selection);
int dr_settings_count(int dsi_mode);
int dr_settings_hit(int x,int y,int dsi_mode);
int dr_settings_action(int dsi_mode,int selection);
int dr_camera_allowed(int dsi_mode,int camera_enabled);
/* Only an explicit camera-enable action clears a prior failure latch. */
int dr_camera_retry_latch(int camera_enabled,int previous_failure);
/* Fire once when L and R become jointly held, only in DSi mode. */
int dr_photo_shortcut(int dsi_mode,int held,int down,int l_mask,int r_mask);
/* Never save stale frames after the camera is stopped or unavailable. */
int dr_photo_capture_ready(int dsi_mode,int storage_ready,int camera_active,int camera_ok,int frame_count);
const char *dr_storage_root(int dsi_mode);
/* Tests directory creation plus write access, but never touches retail .sav files. */
int dr_storage_ready(const char *root);
#endif
