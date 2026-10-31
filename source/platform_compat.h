/* Runtime DS/DSi feature policy. No camera is EVER required for gameplay. */
#ifndef DR_PLATFORM_COMPAT_H
#define DR_PLATFORM_COMPAT_H

enum {DR_SETTING_CAMERA,DR_SETTING_OPTICAL,DR_SETTING_CART,DR_SETTING_SD};
int dr_lab_count(int dsi_mode);
int dr_lab_action(int dsi_mode,int selection);
int dr_settings_count(int dsi_mode);
int dr_settings_action(int dsi_mode,int selection);
int dr_camera_allowed(int dsi_mode,int camera_enabled);
const char *dr_storage_root(int dsi_mode);
/* Tests directory creation plus write access, but never touches retail .sav files. */
int dr_storage_ready(const char *root);
#endif
