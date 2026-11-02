# Recipe: Event recap (high-energy highlight reel, 9:16 + 16:9)

Read this with `recipes/social-short.md` (format, captions, vertical-first; this file's pacing overrides its shot lengths) before Phase 2 on festival, premiere, launch and party recaps. This file covers the "over the top but polished" style and the craft lessons behind it; SKILL.md still applies and the editor's `MY_PREFERENCES.md` overrides both. House defaults came from one studio's festival recap (two reels, each 9:16 + 16:9, about 16 versions).

## Benchmarks (measure the editor's own references)
Ask for 3-5 recaps they love and measure them (`style_profile.py` for cuts, `audio_tags.py` for sound, `tone_stats.py` for picture). Numbers from one set of pro event recaps:
- Median shot ~0.75 s (shortest ~0.2 s); bursts of 2-4 quick cuts, then a 3-7 s hero hold. Hook under 1.4 s.
- Ends on a wide establishing shot with a small logo or wordmark.
- Picture: warm and contrasty, but the black floor never hits true black (p1 luma ~9-13 full range, under 2% of pixels below 8). Chroma (max−min) ~22-24 for daytime, 50-66 only for neon night events.
- Sound: soundbites ducked hard; booms at section changes; camera shutters featured on flash moments; air swishes only on real whip cuts.

## Picture
- **Post pushes on every static shot (house default):** ~9% over the shot (about 6-9%/s), alternating in and out on neighbours; ~4% is too timid to read at 1-1.5 s cuts. **Skip shots where the camera already pushes in ≥ 7%** (measure ORB scale between the shot's first and last frame): a post zoom on a dolly-in doubles the speed and reads rushed. Leave stacks, crash zooms and title/end-card shots alone. Key Scale at source time (`reference/premiere.md`).
- **Crash / punch zoom:** Transform effect on the shot itself, not a baked overlay (overlays never match the camera clip's decode). Settings and the anchor maths are in `reference/premiere.md`. Land it on an impact frame (a hit, a pop, a flash).
- **Whip between shots:** Directional Blur keyed 0→100 over the outgoing shot's last 4 frames and 100→0 over the incoming's first 5, plus a ~8% Scale push, with a soft recorded swish under the cut.
- **Flash frames:** one 2-frame white pop (opacity 60→15) on a real photo moment. Editors found triple flashes and stutter punch-ins on people too much ("too revealing"); use one flash, and keep stutters for objects or performers.
- **Logo / detail shots:** pick the sharpest moment (Laplacian variance on the logo region; a static sign shot can sit in a focus hunt).
- **Re-takes inside one clip:** run `camera_moves.py` before picking an in-point on any moving shot; cut from the end of the hold before the move, not mid-move.
- **9:16 reframes of 16:9 shots:** `reframe_916.py` with a specific subject per shot ("bottles held by hands", not "main subject"); check its sheet and never batch-apply it.

## Colour
- **Black floor:** when an editor says a cut looks "a hair too dark", measure p1 and the share below luma 8. p1 0-5 with 4%+ crushed is the usual cause. Lift at the top look adjustment layer (its Blacks −15 → 0 gave p1 0 → 7-8, mean +3, colour intact), not per clip.
- **Dull daylight shots:** check the black point before adding saturation; midday haze lifts p5 luma to 30-80 (shots that read well sit at 0-30). On clip Lumetri under the look layers: Blacks −35, Contrast +10, Vibrance +15 (skip vibrance where saturation is already high; cap Blacks ~−80). Removing the creative look made things flatter, not richer.
- **Shadows lifts grey the blacks:** on log footage under a LUT stack, Shadows is the strong control and Blacks is weak (Blacks −10 moved graded p1 only 2-3 points; Shadows −20 moved it ~20). When lifting a dark shot, pair Shadows + with Blacks −30. Aim for p5 ~25-30 after the grade on people and day exteriors, and keep p1 above the black floor (~9-13).
- **Saturation:** compare chroma (max−min), not HSV S, which drops whenever the blacks lift.
- **Drones next to the main camera:** DJI footage reads flat (blacks 11-16 IRE, half the saturation). Contrast +20-25 and Blacks −40..−65 per clip until blacks sit at 1-7 IRE, and one Saturation value for the whole drone group (~125-130 here; weddings over haze needed only ~115-120); check grey neutrality after warming (Temperature drifts magenta; Tint −6). Match on grass RGB, low-saturation greys and Y p5/p95, not global averages.
- Run `scopes.py` on review frames for every colour pass.

## Stabilization
- **Gyroflow first** on cameras with embedded gyro data (Sony FX3 and similar): it fixes rolling-shutter wobble too. Light setting ≈ Smoothness 0.15, max zoom 110 (~9-10% crop); `presets/gyroflow_light_default.gyroflow` (copy to Gyroflow's `lens_profiles/default.gyroflow` and every scripted apply uses it). Default settings crop ~24%.
- **Not on slid or stacked clips in 9:16 timelines:** the plugin only renders the region a centred crop would show, so a clip slid with Position comes out with a transparent strip. 16:9 timelines: Gyroflow freely. 9:16: only centred full-height clips; everything else stays on Warp (Smoothness 2).
- Any clip with Rotation needs Scale ≥ cos(r) + (W/H)·sin(r) under Gyroflow (2° in 16:9 → 106.2). Sweep frames for alpha < 250 after a stabilizer swap.
- Timelines with ~40 Gyroflow instances can crash exports; queue them in Media Encoder (`reference/premiere.md`).

## Drone openers
- Speed ramps on drone pushes: `speed_ramp_lock.py` tracks one rigid, distant target (a facade, a sign) and keeps it on a smooth path; `--pin-end` keeps the landing composition. Pick a short, straight, steady flight range (vmax drops, side-to-side jitter fell from ~10 px to ~2 px). A drone that yaws at speed can't be rescued.
- Check the source's last second: pilots often stop and tilt up at the end of a push, and the slow end of a ramp stretches that into a visible pan-up.
- An ease to 0.8x at the end of a far approach reads as a stall; for a 2 s opener under a title, a constant 2x target-locked push was the most even.
- In the 16:9, make sure the closer isn't the same flight or view as the opener, and that end-card text sits on sky, not on the building.

## Sound
- **Subtle and in the background (house default):** effects ~7-20 dB under the music, no music dips just to feature a sound (only to avoid peaking). Synth whooshes, risers and sub booms read "corny, not high end"; one soft reverse-cymbal swell into a big cut (`reverse_cymbal.py`) and real camera pops are fine.
- **Recorded effects beat synthesized ones.** Freesound CC0 picks that worked: Canon DSLR click (167556), Leica M11 burst (720702), Canon AF double beep (851925), reverse cymbal (23127; it decays, so reverse it), bamboo swoosh (59988; layer a 0.84x copy 0.11 s later for a whip). Cut each to its transient, match the old file's body RMS and peak position so placements stay in sync.
- **Event camera audio is mostly crowd and PA bleed.** Find usable pops by spectral flux, not loudness (an axe thud, drumline hits, a cymbal crash and a helicopter rotor were clean; pours, corks and bells were chatter). Run `audio_tags.py` on any nat pick first; Demucs (`stems.py`) can pull a cheer out from under PA music, but DJ bleed usually won't separate.
- **Shutter clicks clip a hot master:** the spike sits ~15 dB above the body. Soft-clip the spike (tanh, knee at 0.16 × peak) and restore the body RMS rather than limiting the whole click.
- Songs peaking near −1 dBFS: test-mix offline at the planned gains and read the peaks before placing effects. No crowd chatter under an end card.
- **Starting a song later under a cut picture:** shift its in-point by a whole number of beats so every cut stays on the beat; place the drop on a meaningful cut; end on the song's last hit before its own breakdown, not a mid-phrase fade.

## Both ratios
Edit and finish the 9:16 first, then mirror it (`reference/premiere.md`, "Mirroring a graded 9:16 to 16:9"). Swap vertical-only pieces: native-vertical drones → the matching horizontal drone, a short stack → its main wide, a long stack → its panels one after another; a vertical-only drone can give a 16:9 by a time-varying crop that follows the subject, baked.

## Delivery
One file per video serves archive, client and social: 4K H.264 at ~100 Mbps from a ProRes 422 HQ master (SKILL.md section 5). 40 Mbps smeared grain in dark, high-contrast shots. −14 LUFS, true peak ≤ −1 dBTP.
