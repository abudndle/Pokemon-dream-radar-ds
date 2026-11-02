#!/usr/bin/env python3
"""Find a visible pink-shadow cloud in an actual unscaled melonDS DS screenshot.

This is a provisional DS fallback targeting aid for emulator testing. It does
not recognize original proprietary sprites or prove that firing hits a cloud.
"""
import argparse
import json
from pathlib import Path
import subprocess

# Source-derived DS reticle center: main.c draws S_RETICLE at (112, 80)
# on a 256x192 screen; the renderer places world-space targets at
# (world_x - aim_x + 128, world_y - aim_y + 96). Keep these anchors in sync.
RETICLE_CENTER_X = 128
RETICLE_CENTER_Y = 96


def locate_clouds(pixels, width, height):
    if width != 256 or not 384 <= height <= 480 or len(pixels) != width * height * 3:
        raise ValueError("Expected an unscaled 256px-wide DS screenshot")
    offset = height - 384
    marked = set()
    for y in range(offset + 24, offset + 174):
        for x in range(12, 244):
            at = (y * width + x) * 3
            r, g, b = pixels[at:at + 3]
            if r >= 160 and b >= 150 and r >= g + 25 and b >= g + 25:
                marked.add((x, y))
    found = []
    while marked:
        first = marked.pop()
        stack = [first]
        component = [first]
        while stack:
            x, y = stack.pop()
            for ny in (y - 1, y, y + 1):
                for nx in (x - 1, x, x + 1):
                    p = (nx, ny)
                    if p in marked:
                        marked.remove(p)
                        stack.append(p)
                        component.append(p)
        if not 20 <= len(component) <= 500:
            continue
        xs, ys = zip(*component)
        if not 5 <= max(xs) - min(xs) <= 38 or not 3 <= max(ys) - min(ys) <= 32:
            continue
        cx = round(sum(xs) / len(xs))
        cy = round(sum(ys) / len(ys)) - offset
        found.append((cx, cy, len(component)))
    return sorted(found, key=lambda c: ((c[0] - RETICLE_CENTER_X) ** 2 + (c[1] - RETICLE_CENTER_Y) ** 2, -c[2]))



def locate_cloud_edge_markers(pixels, width, height):
    """Find 11px gold offscreen-cloud cues; these are NEVER fire targets.

    The DS fallback renderer clamps cloud direction markers to x=11/234
    or y=11/170. Reject ordinary gold HUD text and 7px Orb indicators.
    """
    if width != 256 or not 384 <= height <= 480 or len(pixels) != width * height * 3:
        raise ValueError("Expected an unscaled 256px-wide DS screenshot")
    offset = height - 384
    marked = set()
    for y in range(offset + 10, offset + 181):
        for x in range(5, 250):
            at = (y * width + x) * 3
            r, g, b = pixels[at:at + 3]
            if r >= 235 and g >= 210 and b <= 70:
                marked.add((x, y))
    found = []
    while marked:
        stack = [marked.pop()]
        component = []
        while stack:
            x, y = stack.pop()
            component.append((x, y))
            for ny in (y - 1, y, y + 1):
                for nx in (x - 1, x, x + 1):
                    p = (nx, ny)
                    if p in marked:
                        marked.remove(p)
                        stack.append(p)
        if len(component) < 25:
            continue
        xs, ys = zip(*component)
        left, right = min(xs), max(xs)
        top, bottom = min(ys) - offset, max(ys) - offset
        if not (9 <= right - left <= 11 and 8 <= bottom - top <= 11):
            continue
        if not (left in range(10, 13) or left in range(233, 236)
                or top in range(10, 13) or top in range(169, 172)):
            continue
        found.append((round((left + right) / 2),
                      round((top + bottom) / 2), len(component)))
    return sorted(found, key=lambda p: ((p[0] - RETICLE_CENTER_X) ** 2 +
                                       (p[1] - RETICLE_CENTER_Y) ** 2, -p[2]))



def plan(pixels, width, height):
    targets = locate_clouds(pixels, width, height)
    markers = [] if targets else locate_cloud_edge_markers(pixels, width, height)
    if not targets and not markers:
        raise ValueError("No visible cloud or offscreen cloud marker; aim unverified")
    x, y, count = (targets or markers)[0]
    dx, dy = x - RETICLE_CENTER_X, y - RETICLE_CENTER_Y
    visible = bool(targets)
    return {"target_screen": {"x": x, "y": y},
            "target_type": "cloud" if visible else "edge_marker",
            "offset": {"x": dx, "y": dy},
            "horizontal_key": "Right" if dx > 0 else "Left" if dx < 0 else "none",
            "vertical_key": "Down" if dy > 0 else "Up" if dy < 0 else "none",
            "horizontal_seconds": round(min(0.25, abs(dx) / 360), 3),
            "vertical_seconds": round(min(0.25, abs(dy) / 360), 3),
            "candidate_clouds": len(targets),
            "candidate_edge_markers": len(markers),
            "reticle_distance_squared": dx * dx + dy * dy,
            "within_safe_fire_radius": visible and dx * dx + dy * dy <= 14 * 14,
            "limitations": "Offscreen gold cues guide movement only; firing requires a fresh visible cloud within 14px and independent counter verification."}



def locate_orbs(pixels, width, height):
    """Locate the four 9px Dream Orb colors used by the DS fallback renderer.

    The old pink-only classifier lost moving targets as their color cycled
    to green, orange or blue (every 45 DS frames). These thresholds come
    from the four RGB555 fills in source/main.c, not from original 3DS art.
    Keep palettes separate so adjacent different-color orbs do not fuse.
    """
    if width != 256 or not 384 <= height <= 480 or len(pixels) != width * height * 3:
        raise ValueError("Expected an unscaled 256px-wide DS screenshot")
    offset = height - 384
    marked_by_color = {name: set() for name in ("pink", "green", "orange", "blue")}
    for y in range(offset + 24, offset + 174):
        for x in range(12, 244):
            at = (y * width + x) * 3
            r, g, b = pixels[at:at + 3]
            if r >= 235 and 75 <= g <= 155 and 90 <= b <= 180 and r >= g + 80:
                color = "pink"
            elif g >= 235 and r <= 30 and b <= 30:
                color = "green"
            elif r >= 235 and 135 <= g <= 195 and b <= 35:
                color = "orange"
            elif b >= 235 and r <= 30 and g <= 30:
                color = "blue"
            else:
                continue
            marked_by_color[color].add((x, y))
    found = []
    for color, marked in marked_by_color.items():
        while marked:
            first = marked.pop()
            stack = [first]
            component = [first]
            while stack:
                x, y = stack.pop()
                for ny in (y - 1, y, y + 1):
                    for nx in (x - 1, x, x + 1):
                        p = (nx, ny)
                        if p in marked:
                            marked.remove(p)
                            stack.append(p)
                            component.append(p)
            if not 20 <= len(component) <= 150:
                continue
            xs, ys = zip(*component)
            w, h = max(xs) - min(xs), max(ys) - min(ys)
            if not 4 <= w <= 16 or not 4 <= h <= 16:
                continue
            # The 11x11 white border is TWO pixels thick, covering the
            # outer edge of the 9x9 fill: real melonDS frames show a 7x7
            # interior (49 pixels), not 9x9. Reject tiny colored HUD glyphs
            # without discarding every real nonpink Orb.
            if color != "pink" and (w < 5 or h < 5 or len(component) < 30):
                continue
            found.append((round(sum(xs) / len(xs)),
                          round(sum(ys) / len(ys)) - offset, len(component)))
    return sorted(found, key=lambda c: ((c[0] - 128) ** 2 + (c[1] - 96) ** 2, -c[2]))


def plan_orb(pixels, width, height):
    targets = locate_orbs(pixels, width, height)
    if not targets:
        raise ValueError("No pink Dream Orb found; orb collection unverified")
    x, y, count = targets[0]
    dx, dy = x - RETICLE_CENTER_X, y - RETICLE_CENTER_Y
    return {"target_screen": {"x": x, "y": y},
            "offset": {"x": dx, "y": dy},
            "horizontal_key": "Right" if dx > 0 else "Left" if dx < 0 else "none",
            "vertical_key": "Down" if dy > 0 else "Up" if dy < 0 else "none",
            "horizontal_seconds": round(min(0.5, abs(dx) / 360), 3),
            "vertical_seconds": round(min(0.5, abs(dy) / 360), 3),
            "candidate_orbs": len(targets),
            "reticle_distance_squared": dx * dx + dy * dy,
            "within_safe_fire_radius": dx * dx + dy * dy <= 8 * 8,
            "limitations": "Approximate screenshot aim; Orb collection must be confirmed by counters."}




def plan_orb_motion(previous_pixels, pixels, width, height):
    """Predict short-lived Orb motion from stationary consecutive DS frames.

    Only a uniquely associated previous Orb may supply velocity. Camera
    panning between frames invalidates this assumption, so callers must
    sample both frames without moving the D-pad. A predicted position is
    never sufficient to authorize firing: within_safe_fire_radius is always
    computed from the CURRENT observed Orb, not its extrapolation.
    """
    current = plan_orb(pixels, width, height)
    observed = current["target_screen"].copy()
    current["observed_target_screen"] = observed
    current["motion_prediction"] = "previous_frame_unrecognized"
    previous = locate_orbs(previous_pixels, width, height)
    if not previous:
        return current
    now = locate_orbs(pixels, width, height)[0]
    candidates = []
    for px, py, area in previous:
        distance_sq = (observed["x"] - px) ** 2 + (observed["y"] - py) ** 2
        if distance_sq <= 36 ** 2 and 0.6 * now[2] <= area <= 1.5 * now[2]:
            candidates.append((distance_sq, px, py))
    candidates.sort()
    if not candidates:
        current["motion_prediction"] = "discontinuity"
        return current
    from math import sqrt
    if len(candidates) > 1 and sqrt(candidates[1][0]) - sqrt(candidates[0][0]) < 12:
        current["motion_prediction"] = "ambiguous_previous_target"
        return current
    _, px, py = candidates[0]
    dx, dy = observed["x"] - px, observed["y"] - py
    lead_x = max(-12, min(12, round(dx * 0.5)))
    lead_y = max(-12, min(12, round(dy * 0.5)))
    x = max(12, min(243, observed["x"] + lead_x))
    y = max(24, min(173, observed["y"] + lead_y))
    offset_x, offset_y = x - RETICLE_CENTER_X, y - RETICLE_CENTER_Y
    current.update({
        "target_screen": {"x": x, "y": y},
        "offset": {"x": offset_x, "y": offset_y},
        "horizontal_key": "Right" if offset_x > 0 else "Left" if offset_x < 0 else "none",
        "vertical_key": "Down" if offset_y > 0 else "Up" if offset_y < 0 else "none",
        "horizontal_seconds": round(min(0.5, abs(offset_x) / 360), 3),
        "vertical_seconds": round(min(0.5, abs(offset_y) / 360), 3),
        "motion_prediction": "bounded",
        "observed_displacement": {"x": dx, "y": dy},
    })
    return current


def locate_spheres(pixels, width, height):
    """Locate high-contrast DS fallback encounter art, NOT the white backdrop.

    The static white cloud in game_top.raw was previously mistaken for the
    moving sphere. Only a sufficiently large connected dark/saturated or pink sprite
    on the known flat backdrop is accepted; 13px hostile projectiles, reticle,
    HUD and arbitrary textured/original scenes are not tracked.
    """
    if width != 256 or not 384 <= height <= 480 or len(pixels) != width * height * 3:
        raise ValueError("Expected an unscaled 256px-wide DS screenshot")
    offset = height - 384

    def pixel(x, y):
        at = (y * width + x) * 3
        return pixels[at:at + 3]

    left = pixel(4, offset + 100)
    right = pixel(250, offset + 100)
    if max(abs(a - b) for a, b in zip(left, right)) > 12 or not (
            150 <= left[0] <= 225 and 150 <= left[1] <= 235 and
            150 <= left[2] <= 240):
        raise ValueError("Unknown or non-flat encounter backdrop; cannot safely track art")
    marked = set()
    # SWIFT encounter artwork can travel into the last 23 rows of the
    # TOP screen. Stop at offset+192 (exclusive), before touchscreen pixels.
    # The former y<169 scan missed a real lower-edge sphere in melonDS.
    for y in range(offset + 42, offset + 192):
        for x in range(12, 244):
            r, g, b = pixel(x, y)
            # The DS fallback background is grey/white/cyan. A target sprite
            # has dark and/or saturated colored pixels; the white background
            # cloud and pale reticle never satisfy these thresholds.
            if max(r, g, b) < 95 or (
                    max(r, g, b) - min(r, g, b) > 85 and
                    max(r, g, b) > 120 and min(r, g, b) < 150):
                marked.add((x, y))
    # Real emulator artwork can be split into blue upper and dark/orange
    # lower components by a thin white highlight. Neither fragment alone
    # spans 14px vertically, so the old detector rejected every one of
    # 160 live pursuit frames despite a visible 23x24 encounter sprite.
    fragments = []
    while marked:
        stack = [marked.pop()]
        xs, ys = [], []
        while stack:
            x, y = stack.pop()
            xs.append(x)
            ys.append(y)
            for nx, ny in ((x - 1, y), (x + 1, y),
                           (x, y - 1), (x, y + 1)):
                if (nx, ny) in marked:
                    marked.remove((nx, ny))
                    stack.append((nx, ny))
        if len(xs) >= 20 and max(xs) - min(xs) >= 5 and max(ys) - min(ys) >= 4:
            fragments.append((round(sum(xs) / len(xs)),
                              round(sum(ys) / len(ys)),
                              len(xs), (min(xs), min(ys), max(xs), max(ys))))

    # Merge only vertically adjacent fragments with substantial horizontal
    # overlap. This recognizes a single disconnected-color sprite without
    # merging side-by-side hostile projectiles or distant encounter objects.
    candidates = []
    pending = sorted(fragments, key=lambda p: -p[2])
    while pending:
        group = [pending.pop(0)]
        changed = True
        while changed:
            changed = False
            left = min(f[3][0] for f in group)
            top = min(f[3][1] for f in group)
            right = max(f[3][2] for f in group)
            bottom = max(f[3][3] for f in group)
            group_x = sum(f[0] * f[2] for f in group) / sum(f[2] for f in group)
            for fragment in pending:
                fx, fy, area, (fl, ft, fr, fb) = fragment
                overlap_x = max(0, min(right, fr) - max(left, fl) + 1)
                gap_y = max(0, max(top, ft) - min(bottom, fb) - 1)
                if (overlap_x >= 0.5 * min(right - left + 1, fr - fl + 1)
                        and gap_y <= 6 and abs(fx - group_x) <= 12):
                    group.append(fragment)
                    pending.remove(fragment)
                    changed = True
                    break
        left = min(f[3][0] for f in group)
        top = min(f[3][1] for f in group)
        right = max(f[3][2] for f in group)
        bottom = max(f[3][3] for f in group)
        area = sum(f[2] for f in group)
        if (35 <= area <= 800 and 14 <= right - left <= 42
                and 14 <= bottom - top <= 42):
            cx = round(sum(f[0] * f[2] for f in group) / area)
            cy = round(sum(f[1] * f[2] for f in group) / area) - offset
            candidates.append((cx, cy, area, (left, top, right, bottom)))
    # The real DS fallback DRIFTING sphere uses a pale pink 22x18 sprite,
    # not the dark 21x21 fixture. Its pixels have a pink-violet tint even
    # where it overlaps the large static white background cloud. Require
    # a compact connected silhouette and the same verified flat backdrop.
    # Scan down to y=183: the sphere can travel below the old y=168 cutoff.
    pink = set()
    for y in range(offset + 35, offset + 192):
        for x in range(12, 244):
            r, g, b = pixel(x, y)
            if r >= 245 and b >= 210 and r >= g + 10 and b >= g + 7:
                pink.add((x, y))
    while pink:
        stack = [pink.pop()]
        xs, ys = [], []
        while stack:
            x, y = stack.pop()
            xs.append(x)
            ys.append(y)
            for ny in (y - 1, y, y + 1):
                for nx in (x - 1, x, x + 1):
                    p = (nx, ny)
                    if p in pink:
                        pink.remove(p)
                        stack.append(p)
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if 40 <= len(xs) <= 700 and 10 <= w <= 36 and 8 <= h <= 35:
            candidates.append((round(sum(xs) / len(xs)),
                               round(sum(ys) / len(ys)) - offset, len(xs),
                               (min(xs), min(ys), max(xs), max(ys))))
    # Actual 2026-11-02 Linux melonDS ERRATIC frames show a 21x19
    # lavender sphere body (e.g. RGB 211,178,243), not the earlier
    # dark/orange or pale-pink silhouettes. Its color is too low-contrast
    # for the saturated pass and too blue-dominant for the pink pass.
    # On the verified flat DS fallback backdrop, detect only compact
    # lavender components; the static white cloud, cyan reticle and
    # 13px hostile projectiles must not become aim targets.
    violet = set()
    top_edge_violet = []
    for y in range(offset, offset + 192):
        for x in range(12, 244):
            r, g, b = pixel(x, y)
            if (180 <= r <= 245 and 135 <= g <= 215 and b >= 215
                    and b >= g + 35 and r >= g + 20):
                violet.add((x, y))
                if y < offset + 27:
                    top_edge_violet.append((x, y))
    while violet:
        stack = [violet.pop()]
        xs, ys = [], []
        while stack:
            x, y = stack.pop()
            xs.append(x)
            ys.append(y)
            for ny in (y - 1, y, y + 1):
                for nx in (x - 1, x, x + 1):
                    p = (nx, ny)
                    if p in violet:
                        violet.remove(p)
                        stack.append(p)
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if 70 <= len(xs) <= 700 and 12 <= w <= 36 and 10 <= h <= 35:
            candidates.append((round(sum(xs) / len(xs)),
                               round(sum(ys) / len(ys)) - offset, len(xs),
                               (min(xs), min(ys), max(xs), max(ys))))
    # Real ERRATIC encounters can cross the TOP viewport boundary. A
    # partially clipped violet sprite may split into two thin components
    # separated by white highlights, neither meeting the ordinary 10px
    # component-height gate. Reassemble only compact, contiguous COLUMN
    # runs at the top edge; ordinary HUD text is not violet, and separate
    # silhouettes remain separate candidates.
    if top_edge_violet:
        columns = {}
        for x, y in top_edge_violet:
            columns.setdefault(x, []).append(y)
        runs = []
        for x in sorted(columns):
            if not runs or x > runs[-1][-1] + 1:
                runs.append([x])
            else:
                runs[-1].append(x)
        for run in runs:
            points = [(x, y) for x in run for y in columns[x]]
            xs, ys = zip(*points)
            left, right = min(xs), max(xs)
            top, bottom = min(ys), max(ys)
            if (70 <= len(points) <= 700 and 12 <= right - left <= 36
                    and 7 <= bottom - top <= 26 and top <= offset + 3):
                candidates.append((round(sum(xs) / len(xs)),
                                   round(sum(ys) / len(ys)) - offset,
                                   len(points), (left, top, right, bottom)))
    # SWIFT encounter artwork can pass behind the black class-name HUD.
    # In real melonDS frames the exposed 24x7 lower rim contains adjacent
    # orange and green stripes at y=37..43. The ordinary >=14px-tall dark
    # component gate cannot see it. Require BOTH distinctive palette bands
    # in a compact horizontal run immediately below the HUD; plain yellow
    # HUD text, the cyan reticle and red projectiles cannot satisfy this.
    # This is a navigation hint only, never proof of a hit or reward.
    upper_columns = {}
    for y in range(offset + 28, offset + 56):
        for x in range(12, 244):
            r, g, b = pixel(x, y)
            if r >= 170 and 90 <= g <= 220 and b <= 110 and r >= g + 25:
                color = "orange"
            elif (60 <= g <= 230 and g >= r + 25 and g >= b + 10
                  and r <= 110 and b <= 110):
                color = "green"
            else:
                continue
            upper_columns.setdefault(x, []).append((x, y, color))
    upper_runs = []
    for x in sorted(upper_columns):
        if not upper_runs or x > upper_runs[-1][-1] + 2:
            upper_runs.append([x])
        else:
            upper_runs[-1].append(x)
    for run in upper_runs:
        points = [point for x in run for point in upper_columns[x]]
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        left, right, top, bottom = min(xs), max(xs), min(ys), max(ys)
        orange = sum(point[2] == "orange" for point in points)
        green = len(points) - orange
        if (orange >= 12 and green >= 8 and 14 <= right - left <= 32
                and 3 <= bottom - top <= 20
                and top <= offset + 42 and bottom <= offset + 55):
            candidates.append((round(sum(xs) / len(xs)),
                               round(sum(ys) / len(ys)) - offset,
                               len(points), (left, top, right, bottom)))
    # A single sprite can contain both dark/saturated edges and a pastel
    # interior. The independent palette passes then report two overlapping
    # components for one real target, causing the unique-target planner to
    # reject otherwise valid live frames. Deduplicate only nearly concentric,
    # strongly overlapping component bounds; keep distinct nearby targets.
    unique = []
    for cx, cy, area, bounds in sorted(candidates, key=lambda p: -p[2]):
        left, top, right, bottom = bounds
        duplicate = False
        for ox, oy, _, other in unique:
            if abs(cx - ox) > 8 or abs(cy - oy) > 8:
                continue
            overlap_width = max(0, min(right, other[2]) - max(left, other[0]) + 1)
            overlap_height = max(0, min(bottom, other[3]) - max(top, other[1]) + 1)
            overlap = overlap_width * overlap_height
            smaller = min((right - left + 1) * (bottom - top + 1),
                          (other[2] - other[0] + 1) * (other[3] - other[1] + 1))
            if overlap >= 0.7 * smaller:
                duplicate = True
                break
        if not duplicate:
            unique.append((cx, cy, area, bounds))
    return [(cx, cy, area) for cx, cy, area, _ in unique]


def plan_sphere(pixels, width, height):
    targets = locate_spheres(pixels, width, height)
    if len(targets) != 1:
        raise ValueError("No unique high-contrast encounter artwork; guided aim unverified")
    x, y, count = targets[0]
    dx, dy = x - RETICLE_CENTER_X, y - RETICLE_CENTER_Y
    return {"target_screen": {"x": x, "y": y},
            "offset": {"x": dx, "y": dy},
            "horizontal_key": "Right" if dx > 0 else "Left" if dx < 0 else "none",
            "vertical_key": "Down" if dy > 0 else "Up" if dy < 0 else "none",
            "horizontal_seconds": round(min(0.22, abs(dx) / 360), 3),
            "vertical_seconds": round(min(0.22, abs(dy) / 360), 3),
            "candidate_spheres": len(targets),
            "limitations": "High-contrast DS fallback artwork tracking only; a target position is not a hit or capture."}


def plan_sphere_motion(previous_pixels, pixels, width, height):
    """Track a moving DS fallback encounter using two actual screenshots.

    A second large foreground component can appear in the capture viewport.
    When the current frame has multiple candidates, recover the one matching
    the previously unique target *only* when distance, size and separation
    make that association unambiguous. Never turn an ambiguous frame into
    evidence of a hit, capture or original-game fidelity.
    """
    previous = None
    try:
        previous = plan_sphere(previous_pixels, width, height)
    except ValueError:
        pass

    try:
        current = plan_sphere(pixels, width, height)
        current["motion_match"] = "unique_current"
    except ValueError:
        # Unknown backgrounds and blank frames still fail closed.
        candidates = locate_spheres(pixels, width, height)
        if previous is None or len(candidates) < 2:
            raise
        old = previous["target_screen"]
        old_area = locate_spheres(previous_pixels, width, height)[0][2]
        matches = []
        for x, y, area in candidates:
            distance_sq = (x - old["x"]) ** 2 + (y - old["y"]) ** 2
            if distance_sq <= 50 ** 2 and 0.65 * old_area <= area <= 1.5 * old_area:
                matches.append((distance_sq, x, y, area))
        matches.sort()
        if not matches:
            raise ValueError("No continuous sphere target among multiple candidates")
        # Compare actual distances, not squared-distance differences: the
        # latter are too permissive for equally plausible close objects.
        from math import sqrt
        if len(matches) > 1 and (
                sqrt(matches[1][0]) - sqrt(matches[0][0]) < 18):
            raise ValueError("Ambiguous sphere motion association")
        _, x, y, _ = matches[0]
        dx, dy = x - RETICLE_CENTER_X, y - RETICLE_CENTER_Y
        current = {
            "target_screen": {"x": x, "y": y},
            "offset": {"x": dx, "y": dy},
            "horizontal_key": "Right" if dx > 0 else "Left" if dx < 0 else "none",
            "vertical_key": "Down" if dy > 0 else "Up" if dy < 0 else "none",
            "horizontal_seconds": round(min(0.22, abs(dx) / 360), 3),
            "vertical_seconds": round(min(0.22, abs(dy) / 360), 3),
            "candidate_spheres": len(candidates),
            "limitations": "Temporal match of fallback encounter artwork; not a verified hit or capture.",
            "motion_match": "previous_unique_target",
        }

    observed = current["target_screen"].copy()
    current["observed_target_screen"] = observed
    current["motion_prediction"] = "unavailable"
    if previous is None:
        current["motion_prediction"] = "previous_frame_unrecognized"
        return current
    dx = observed["x"] - previous["target_screen"]["x"]
    dy = observed["y"] - previous["target_screen"]["y"]
    # Scene changes, teleports and erratic turns cannot be extrapolated safely.
    if abs(dx) > 60 or abs(dy) > 60:
        current["motion_prediction"] = "discontinuity"
        return current
    lead_x = max(-18, min(18, round(dx * 0.5)))
    lead_y = max(-18, min(18, round(dy * 0.5)))
    x = max(20, min(236, observed["x"] + lead_x))
    # An ERRATIC target may be partly clipped by the DS viewport edge.
    # Never force a valid observed y=0..29 target down to y=30.
    y = max(0, min(183, observed["y"] + lead_y))
    offset_x, offset_y = x - RETICLE_CENTER_X, y - RETICLE_CENTER_Y
    current.update({
        "target_screen": {"x": x, "y": y},
        "offset": {"x": offset_x, "y": offset_y},
        "horizontal_key": "Right" if offset_x > 0 else "Left" if offset_x < 0 else "none",
        "vertical_key": "Down" if offset_y > 0 else "Up" if offset_y < 0 else "none",
        "horizontal_seconds": round(min(0.22, abs(offset_x) / 360), 3),
        "vertical_seconds": round(min(0.22, abs(offset_y) / 360), 3),
        "motion_prediction": "bounded",
        "observed_displacement": {"x": dx, "y": dy},
    })
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screenshot", type=Path)
    parser.add_argument("--target", choices=("cloud", "orb", "sphere"), default="cloud")
    parser.add_argument("--previous-screenshot", type=Path,
                        help="Earlier stationary Orb frame or sphere frame for bounded motion lead")
    args = parser.parse_args()
    size = subprocess.run(["identify", "-format", "%w %h", str(args.screenshot)],
                          capture_output=True, text=True, check=True, timeout=12)
    width, height = map(int, size.stdout.split())
    raw = subprocess.run(["convert", str(args.screenshot), "-depth", "8", "rgb:-"],
                         capture_output=True, check=True, timeout=12)
    planner = {"cloud": plan, "orb": plan_orb, "sphere": plan_sphere}[args.target]
    if args.previous_screenshot:
        if args.target not in ("orb", "sphere"):
            parser.error("--previous-screenshot is only valid with --target orb or sphere")
        previous_size = subprocess.run(
            ["identify", "-format", "%w %h", str(args.previous_screenshot)],
            capture_output=True, text=True, check=True, timeout=12)
        if tuple(map(int, previous_size.stdout.split())) != (width, height):
            raise ValueError("Aim frames have different dimensions")
        previous_raw = subprocess.run(
            ["convert", str(args.previous_screenshot), "-depth", "8", "rgb:-"],
            capture_output=True, check=True, timeout=12)
        result = (plan_orb_motion if args.target == "orb" else plan_sphere_motion)(
            previous_raw.stdout, raw.stdout, width, height)
    else:
        result = planner(raw.stdout, width, height)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
