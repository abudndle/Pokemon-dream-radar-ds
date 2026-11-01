# Dream Radar firing controls: source evidence and port decision

## Verified external descriptions

- Smogon gameplay guide: https://www.smogon.com/ingame/guides/dream_radar — states pressing A fires the beam, including to destroy Dream Clouds and collect Dream Orbs; hold A during Sphere encounters.
- Contemporary Pocket Gamer walkthrough: https://www.pocketgamer.com/pokemon-dream-radar/how-to-catch-pokemon-and-items-with-pokemon-dream-radar-and-transfer-them-to-pok/ — describes aligning the reticle with a cloud and pressing A.
- Nintendo game description: https://www.nintendo.com/en-gb/Games/Nintendo-3DS-download-software/Pokemon-Dream-Radar-523679.html — confirms motion aiming and beam shooting but does not specify the firing button.

## Project constraint and conflict

The user explicitly requested that pressing A on the radar screen must not fire. That conflicts with the cited original-game descriptions. Do **not** silently change this control until the conflict is resolved with the user or verified original control evidence from their copy. The current port permits A firing only during STATE_SPHERE and has no working radar firing path, which blocks completing the real emulator cloud-to-capture sequence.

## Completion blocker and verification

Before closing issue #61: decide and document the accepted radar fire input, implement it in source/main.c, run source/host tests, and verify real melonDS radar shots through orb/encounter/results/save/restart with captured screenshots and logs. Host calls directly to game_fire() alone do not prove the interactive input path.
