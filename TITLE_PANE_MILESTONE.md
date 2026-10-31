# ROM-derived title list integration

This milestone integrates `MnIf_S_TitleList.bclyt` pane measurements into both the displayed selection outline and stylus hit detection on the title menu.

Original `Touch00` size: [286.0, 34.0] in 320 × 240 layout coordinates. The DS-scaled width is **229** and height **27**. Original list row separation is 40 units, scaled to **32 px**.

DS pane rectangles: [(13, 45, 229, 27), (13, 77, 229, 27), (13, 109, 229, 27), (13, 141, 229, 27)].

**Caveat:** the y origin of 45px is retained from the screenshot-aligned prototype. BCLAN animation positioning and texture bindings still need decoding, and this does not establish pixel-accurate rendering or touch timings. The remaining layouts and actual DS booting have not been verified.
