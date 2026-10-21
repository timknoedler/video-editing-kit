# Recipe: Ceremony film (full ceremony, 16:9)

Read this before Phase 2 on a full-ceremony film: the whole ceremony from start to finish, cut between the ceremony cameras. It should feel like raw footage, but polished. SKILL.md still applies; for vows audio, kisses and the end card see `wedding-film.md`. The editor's `MY_PREFERENCES.md` overrides both. These are one wedding studio's house rules (first worked through on a 3-camera, 2-lav ceremony in Oct 2026); treat them as strong defaults and ask where the editor's taste differs.

## Shape
- Processional → ceremony → recessional, in real time. Don't cut anything anyone says; trim only dead air before the processional and after the recessional music.
- **Opening:** portraits of the couple first, then the venue, guests arriving and details, then the processional (it flows more smoothly than mixing them), 30-60 s under the ceremony's own live music. End the intro on a shot of the musician synced to the music, then cut to real time. Opening straight on the processional also works; ask.
- End: linger, fade to black, then the studio's end card (the same one as their highlight films).

## Cutting
- Long holds: in one studio's past ceremony films the median shot ran 12-21 s, with holds up to 2-3 min; a single-angle film is fine too.
- Show whoever is speaking; cut to strong reactions and to the wide for structure (a reading starting, rings, the kiss). Don't cut during the kiss.
- Cover every move, whip pan or focus hunt on the handheld camera with a locked-off angle.
- No music under the ceremony, no slow motion, speed ramps or effects.
- **Before showing any cut, run a shake and crew pass** (an editor's first notes on a v1 were "a lot of shaky shots" and "cut around photographers if possible"): run `bg_shake.py` on every 2 s slice of the timeline (on proxies) and cover anything over ~0.8% with another angle (use 1 s slices to find the exact steady points; keep handheld walk-alongs only when no other angle shows the moment). Then make a contact sheet of the whole cut every 3 s and cut around every photographer, videographer, tripod camera, crossing guest or raised phone; a 120% crop can remove crew gear at a frame edge.
- **Crew in frame is normal at ceremonies** (a second shooter on a tripod, photographers): choose the angle without them where one exists and list the rest in the report.

## Benchmarks
- Measure 2-4 of the editor's past ceremony films (`style_profile.py`, ebur128). One studio's: delivered 1920x1080 full frame (not the letterboxed frame of their highlight films), 10-39 min long, older ones -17 to -23 LUFS integrated; they now deliver at **-16 LUFS**, true peak ≤ -1 dBTP. Confirm the editor's frame size and loudness.

## Workflow that worked (3 cameras + 2 lavs, about 2 h to a verified v1)
- **Sync first, by audio:** extract 16 kHz mono from every camera and recorder and run `audio_sync.py` against the longest-rolling camera (the back wide usually rolls first). Sidecar clocks were off by up to 40 min and one camera was set to another time zone. Check each lav against the nearest camera with a local cross-correlation at several points (3-11 ms of drift is fine).
- **Map the ceremony from levels and transcripts:** a 30 s RMS table per source shows music (processional, recessional) vs speech at a glance. Whisper loops on quiet lavs and room mics ("Thank you" every 30 s, one sentence repeated): use `-mc 0`, a `dynaudnorm`-boosted copy, and windows of a few minutes.
- **Check who wears which lav from what it hears,** not from the label: the "officiant" lav was the groom's (cued before his walk, a private chat after the recessional). The groom's lav caught the officiant cleanly; the officiant's own lav was 30 dB too quiet.
- **Place cuts from scans, not guesses:** side-by-side frames of all cameras every 10 s for the angle plan, then `cam_scan.py` + `cam_flags.py` on every proxy. Check every chosen window for whips, focus pulls and blockages (a crew monitor in front of the side camera, standing guests hiding the back wide, a photographer in the aisle) and move cuts off them.
- **Audio = one pre-mixed stereo track** built outside the editing app: the room camera for music and room sound, the clearest lav for speech (high-pass, 2:1 compression, a slow ±8 dB leveller, a peak limiter for hugs and bumps), a ride down at the kiss so the room carries the cheer, then a whole-mix normalize and true-peak limiter. Vows on a lav can run a few dB hot; ride them. Verify on a render from the editing app: stereo side channel, ebur128, and a null test against the mix file.
- **Intro bed:** a b-roll clip of the live musician gave 38 s of clean music. Portrait clips carry the shooter's directions, so keep them picture only.
