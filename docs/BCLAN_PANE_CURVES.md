# Native BCLAN pane transform curves

`tools/decode_bclan_panes.py` reads the original Nintendo CLAN/pai1 entry,
tag, channel and key offsets. For pane-target `CLPA` tracks it decodes local
translation, rotation, scale and size properties. It samples cubic Hermite
curves using the stored slopes, and constant/step keys without interpolation.
Queries outside a track clamp to its endpoint values.

Original clips can have several keys at the same frame. The decoder preserves
them; sampling selects the last equal-time key at the boundary. This is an
explicit, deterministic sampling policy and avoids zero-duration division.
Native clip loop flags are exposed, but loop wrapping, parent transforms,
material binding and DS coordinates are not implicitly applied.

```sh
python3 tools/decode_bclan_panes.py \
  /private/resources/Ui/MnIf_S_TitleList/anim/MnIf_S_TitleList_In.bclan \
  /private/title-pane-curves.json
```

The JSON includes original source keyframes and must remain private. No
original animation payloads or decoded curve arrays are shipped in the public
repository. The synthetic host fixtures are independent test data.

The decoder applies byte/key budgets, section and nested-offset bounds,
supported channel/curve checks, finite-number checks and ordered frame checks.
Non-pane and non-CLPA tags are explicitly listed under `unsupported_tags`.
They are not converted into transform curves or silently counted as playable.

Local source validation succeeded on the user's 417 private BCLAN files:
4,871 CLPA transform tracks, 11,957 keys, 1,284 equal-time key pairs, and
3,902 other target tags reported as unsupported. Sampling the start, midpoint
and end of every decoded track completed without failures. Synthetic tests
also cover nonlinear slope interpolation, step boundaries, clamping,
equal-time keys, non-finite values and malformed nested offsets/counts.

This does **not** implement the DS pane compositor, texture/material binding,
animation layering, original skeletal animation, or frame-accurate playback.
The original sprites and existing gameplay remain unchanged. The public
format reference used to check the layout was the independent
[Switch-Toolbox CTR BCLAN reader](https://github.com/KillzXGaming/Switch-Toolbox/blob/master/File_Format_Library/FileFormats/Layout/CTR/BCLAN.cs).
