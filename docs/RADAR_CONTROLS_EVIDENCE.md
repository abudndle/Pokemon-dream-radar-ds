# Dream Radar firing controls: source evidence and port decision

## Verified external descriptions

- Smogon gameplay guide: https://www.smogon.com/ingame/guides/dream_radar — states pressing A fires the beam, including to destroy Dream Clouds and collect Dream Orbs; hold A during Sphere encounters.
- Contemporary Pocket Gamer walkthrough: https://www.pocketgamer.com/pokemon-dream-radar/how-to-catch-pokemon-and-items-with-pokemon-dream-radar-and-transfer-them-to-pok/ — describes aligning the reticle with a cloud and pressing A.
- Nintendo game description: https://www.nintendo.com/en-gb/Games/Nintendo-3DS-download-software/Pokemon-Dream-Radar-523679.html — confirms motion aiming and beam shooting but does not specify the firing button.

## Accepted port control decision (2026-11-01)

The user explicitly approved restoring A-button beam firing in radar search. The implementation now calls `game_fire(&game)` when A is held on both `STATE_RADAR` and `STATE_SPHERE`. The radar/encounter photo-capture shortcut was removed; A firing never saves a screenshot. Source regression tests cover the shared A firing path and absence of photo shortcuts.

## Completion blocker and verification

Before closing issue #61: run source/host tests and verify real melonDS radar shots through orb/encounter/results/save/restart with external test-run screenshots and logs (not in-game photo capture). Host calls directly to game_fire() alone do not prove the interactive input path.
