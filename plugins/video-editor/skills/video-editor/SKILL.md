---
name: video-editor
description: The Sunday Cut, a video editing kit. Edit video with Claude in Premiere Pro, DaVinci Resolve or Final Cut Pro, end to end - inventory and transcribe footage, pull selects and bites, write paper edits, build the cut in the editor's app, QC, and learn from the editor's own polish pass. Use for any video editing job - social reels, interview cutdowns and testimonials, wedding films, recap videos, re-edits of an existing cut.
---

# Video Editor

A tested workflow for cutting real client footage with Claude Code in Premiere Pro, DaVinci Resolve or Final Cut Pro. It was developed and proven in Premiere; Resolve and Final Cut use the same workflow with their own build step. It was built over a run of paid jobs (social reels, interview reels, gala and camp promos, a full wedding film) and keeps the lessons from each one.

Files in this skill (`<skill dir>` is the folder this file is in):
- `recipes/` - one file per video type: `social-short.md`, `interview-cutdown.md`, `wedding-film.md`, `ceremony-film.md`
- `reference/premiere.md`, `reference/resolve.md`, `reference/final-cut.md` - how to build and revise the cut in each app, what works and the workarounds. **Read the one for the editor's app before Phase 3.** (The Premiere file also holds most of the kit's audio, color and QC techniques; skim it whatever the app.)
- `scripts/` - helper scripts (section 8). Run Python ones through `scripts/vpy`.
- `templates/` - project brief, handoff, and the starting files for the editor's notebook.

## 0. Two layers: this kit and the editor's notebook

This skill is shared and gets updated by its author, so **never edit files inside the skill folder** - an update replaces them. Everything that belongs to the person editing lives in their own notebook folder:

**`~/Editing-Notes/`** (override with `EDIT_NOTES`)
- `MY_PREFERENCES.md` - this editor's style and rules. **Overrides the recipes and this file wherever they conflict.**
- `clients/<client>/CLIENT.md`, `STYLE.md`, `used-shots.md` - per-client profile, style benchmarks, shots already used
- `LESSONS.md` - new tool behavior and techniques found on jobs (worth sending back to the kit's author)
- `JOB_HISTORY.md` and `timing-log.csv` - one row per job / phase

If `~/Editing-Notes/` doesn't exist, run the `editor-setup` skill first (or create it from `templates/notebook/`).

**Every session:** if `~/Editing-Notes` is a git repo (editors who work on two machines), `git -C ~/Editing-Notes pull --rebase` before reading it, and commit + push whenever it changes. Then read `MY_PREFERENCES.md`.

**Job files** (probe, sheets, transcripts, specs, proxies, review frames, `REPORT.md`, `HANDOFF.md`, the project/library) live with the footage in `<FOOTAGE_ROOT>/_edit/` (or `EDIT_DIR`), never on an internal drive and never in the notebook. If the editor moves drives between a Mac and a PC, the drive must be exFAT.

## 1. Ground rules (every job)

1. Never modify, move, rename or delete source media. All outputs go in `_edit/`.
2. Never overwrite an existing project, timeline or library. Make new versioned ones (`<Project>_ClaudeEdit_v1`, `<Sequence>_v2`...).
3. Before any timeline change on a sequence that already has work in it, checkpoint or duplicate it first.
4. Nothing is exported for publishing, uploaded or sent anywhere unless the editor asks. Review frames and low-res review renders are fine.
5. Never download or license music. When the editor asks, suggest options from their licensing service and let them pick (check which license fits the job: some are wedding-only, others cover commercial and client social work). Music sites that render client-side need a scroll before reading the page; fetch song pages one at a time about 1.5 s apart, as rapid searching gets the browser rate-limited (HTTP 429). Once a track is in, cut on its beat grid (librosa) and make bar-aligned music edits as WAVs in `_edit/music/`; without one, cut to visual rhythm and leave a marker where the track starts.
6. Before sending any client audio or video to a cloud service (e.g. Adobe Enhance Speech), ask.
7. When something is ambiguous, make a reasonable call, log it in the report, keep going.
8. If the editing app isn't connected, do all the headless work anyway and say clearly that the build is waiting.
9. Always quote paths (drive names have spaces).
10. Keep `_edit/HANDOFF.md` current (template in `templates/`) so the job can resume in another session or on another machine.
11. The editor edits between sessions. Before building a new version, diff the current sequence against your last handoff copy and carry their changes forward; never revert them.
12. Never delete anything the editor hasn't asked you to delete by name: no files or folders (in `_edit/` or anywhere else), and no project items, bins, sequences, timelines or render/preview files in the editing app. When they do ask, list exactly what will go, back it up first (duplicate the project, or copy the files to `_edit/backup/`), and wait for their OK. The only exception is the temporary files the kit's own scripts create and clean up.
13. Check free space on the drive before proxies, renders or long transcodes. If the job would leave less than about 50 GB free, say so and ask before starting. Never free up space by removing anything.

## 2. Environment

- **Required:** `ffmpeg`/`ffprobe`, whisper.cpp (`whisper-cli` + `ggml-large-v3-turbo.bin`, or set `WHISPER_MODEL`), Python 3 with the kit venv (`scripts/setup_venv.sh`), and the editor's app. `editor-setup` checks all of these.
- **Editing app:** read it from `MY_PREFERENCES.md` or the brief; ask if neither says. Connection per app is in `reference/<app>.md` (Premiere: `premiere-pro-mcp` bridge; Resolve: `davinci-resolve-mcp`; Final Cut: FCPXML files, optional `fcp-mcp`). Verify read-only first.
- **Mac:** first touch of `/Volumes` triggers a permission prompt for the terminal. Don't use `screencapture`; if the editing app seems blocked, ask the editor to look.
- **Windows:** use Git Bash for `.sh` scripts; `python3` may be `python` or `py`. All scripts accept `E:/...` and `E:\...` paths.
- **Shells:** zsh passes an unquoted `$VAR` list as one argument; pass lists via Python or `${=VAR}`.
- **Kit updates (check at the start of every job):** in `~/.claude/settings.json`, `extraKnownMarketplaces` → `sunday-strolls-editing-kit` should have `"autoUpdate": true`. If it's missing or false, fix it the way `editor-setup` step 7 does (back up, edit only that key, read it back) and tell the editor in one line. Then compare the `version` in `~/.claude/plugins/marketplaces/sunday-strolls-editing-kit/plugins/video-editor/.claude-plugin/plugin.json` with this kit's own `plugin.json`. If the marketplace copy is newer, say a kit update is waiting and arrives when they restart Claude.
- **Latest setup guide:** when the editor asks for the newest Sunday Cut guide (or wants to send it to someone), download it into their notes folder: `curl -fL -o ~/Editing-Notes/The-Sunday-Cut-Setup-Guide.pdf https://github.com/timknoedler/video-editing-kit/releases/latest/download/The-Sunday-Cut-Setup-Guide.pdf`, check that it's a PDF, then open it or tell them where it is. To share it, give the link instead of the file, since the link always serves the newest version.
- Talk the editor through any setup at the level of what to click and type, and run commands yourself whenever you can.

## 3. Footage defaults

Read the actual camera and format from `probe_media.py`; don't assume. Lessons that carry across cameras:
- **Sony sidecars:** `<clip>M01.XML` holds model, `captureFps` and `CreationDate`; `probe_media.py` reads them.
- **Rotation metadata can be wrong.** Vertical clips usually import correctly (2160x3840), but confirm every rotated clip in review frames; fix with Motion Rotation 270 + Scale 177.78.
- **Slow motion:** `captureFps` 59.94 in a 23.98 file is already 2.5x slow (S&Q). A 59.94p *file* plays real time - offer it as a slow-mo option. 59.94p drone at 40% (interpreted as 23.976) is clean slow motion.
- **Proxies:** read proxies for sheets and scans (~10x faster than 4K long-GOP). `make_proxies.py` makes missing ones outside the footage; attach to every master clip a sequence uses (`manage_proxies` attach, then `has_proxy`). **Timing (hard rule): proxy encodes and other heavy scans never overlap work in the editing app** (import, build, render, export) or the editor working in it. When they compete the app stalls and the bridge drops (five parallel ProRes encodes on an M1 crashed the Adobe background services). Make proxies in Phase 1 with the app closed or idle, only for the clips the scans need (big libraries: shortlisted clips via `--only`), or after the build is verified for the clips the cut uses. `make_proxies.py` runs at low priority with 2 workers by default.
- **59.94p left at real speed in a 23.976 timeline judders** (the app drops source frames 3-2-3-2; editors see it as "choppy" drone). `drone_cadence.py` shows it as a period-2 pattern (alternating diffs, e.g. 12/9) even when its verdict says smooth, so read the diff row. Fix: render every 2nd frame at 23.976 (0.8x: `-vf "select='not(mod(n\,2))',setpts=N/(24000/1001)/TB" -r 24000/1001`) or 0.4x with `render_slowmo.py`. Transcode 4K HEVC drone windows to ProRes so timeline playback doesn't stutter.
- **Vertical drone clips** (DJI rotation 90): `render_slowmo.py` (ffmpeg autorotate) writes upright 2160x3840 ProRes; place them at scale 100 in 9:16 sequences instead of cropping a horizontal shot.
- **Log footage:** don't grade rough cuts. Correct only if asked (see the editor's preferences).
- **Audio recorders:** pair with camera clips by timestamp overlap. Camera-only interviews often record quiet (-25 to -31 LUFS).
- **Multi-day/location shoots:** sort clips by creation date first.
- **Don't infer events from clip order.** Sync recorder and camera clocks on a shared moment (a toast, a pronouncement) and check timestamps before naming a moment ("first look") to the editor.
- **Multi-camera / recorder sync by audio:** camera clocks can be off by tens of minutes (one camera was even in another time zone). Extract 16 kHz mono from every camera and recorder and run `audio_sync.py` against the longest-rolling camera; it prints each file's start on that camera's clock. Spot-check a lav against the nearest camera at several points for drift (a few ms is fine).

## 4. Standard workflow

Log start and end time of every phase (section 6).

**Phase 0: Setup.** Pull and read the notebook (section 0). Confirm the editing app and read `reference/<app>.md`. Identify the video type and read the matching `recipes/<type>.md` (ask if unclear). Create or read `_edit/HANDOFF.md`. Ping Premiere, confirm ffmpeg/whisper. Read the client profile if one exists; first job for a client with past exports → build `STYLE.md` with `style_profile.py`. **Ask who the client is (the person who hired the editor) so they're never in frame.** Set `EDIT_DIR`.

**Phase 1: Inventory (headless).** `probe_media.py` → `contact_sheets.py` (view the 4-clip stacks, mapping rows by the red dividers). In the background: `transcribe_all.sh` (interviews first via `ONLY=`), and under ~150 clips `shot_quality.py scan --all --skip <interviews>` (on big libraries scan only shortlisted clips). Tag every clip one line in `_edit/work/tags.txt`; for 300+ clips split into ~80-110-clip batches and run parallel tagging agents with a shared guide. Describe people by look, not name, until the editor confirms. Output `_edit/inventory.md`.

**Phase 2: Selects + paper edits.**
- **Dialogue:** read the *whole* transcript. Shortlist every strong line, `bites.py score` them (LUFS, noise floor, SNR, fillers). Find a 2-3 s hook and a punchy closer. Snap edges with `bites.py snap`, check against `bites.py words`. An out-point needs a real pause after the last word; if the next word follows with no gap, extend the bite. Confirm final edges by re-transcribing the trimmed audio - whisper word times can be 0.3-0.5 s off. Aim for ~0.6 s from one bite's last word to the next bite's first.
- **Story, pacing, music:** follow the recipe.
- **Never in frame:** the client who hired the editor, crew, crew hands - check the whole window, not just the midpoint. Check it for passers-by in the foreground too (a guest crossed the lens for 1.4 s right in one chosen window).
- **Dialogue- or reaction-driven cuts (bloopers, BTS):** find the moments in the audio, not the frames. Transcribe every clip and add per-clip loudness peaks (ebur128 momentary), then re-transcribe a short window around each candidate for real word times (clip-level whisper timestamps drift by seconds when speech is sparse, and can loop-hallucinate). Transcribe the review render too: it catches clipped line endings.
- **No repeated shots** within a video unless asked; across a set of reels, compare source *windows*, not just clip names (the same moment in 4 of 5 reels is what viewers notice). Count faces too: the same kid in consecutive shots reads as a repeat.
- **B-roll: cut on action.** Name the action each shot exists to show (step out of the car, pour, clink) and make the window contain all of it; cut into the next shot mid-motion. A steady window where nothing happens is the wrong pick. Use `action_scan.py` (subject motion with camera motion removed) joined with a shake scan; `bg_shake.py` is the tie-breaker for shake (bar: jitter <= 0.8%, peak <= 2%; drone <= ~0.3 px); `bg_shake_slide.py` finds the steadiest window of a given length that still has the action.
- **9:16 crops of 16:9 shots:** the crop shows only 31.6% of the frame width, so shake looks about 3x worse than `bg_shake` reports (a 0.76% window that "passed" looked shaky on the vertical): use a bar of about 0.3-0.4% for cropped shots. Before building, grid candidate frames with the crop box drawn (centre ± 0.158 of the width) and check the action is inside it (the pour, the landing, whole sign letters); shift with `xoff` = (crop centre - 0.5) x 3840. Text wider than ~56% of the frame can't fit a 9:16 crop; a subject that crosses the frame needs a compromise centre checked at both ends of the shot.
- Write `_edit/selects.md` and `_edit/paper_edits.md`. If a concept isn't viable, say so and build the strongest alternate.

**Phase 3: Build.** Write the cuts as a JSON spec (`scripts/example_spec.json`); the same spec builds for every app. Premiere and Resolve: `xml_from_spec.py` → FCP7 XML. Final Cut: `fcpxml_from_spec.py` → FCPXML 1.10. Both give frame-exact in/outs, b-roll above the dialogue, per-bite gain to -19 LUFS, punch-ins and markers. Then follow `reference/<app>.md` to import, revise and read back. The rest of this phase is written for Premiere; the app files say what changes. Premiere: new project, bins by location plus Audio/Sequences/Graphics, `import_media` the .xml. Read back every sequence (`get_timeline_summary`, `audit_timeline_health`), export review frames, save. **On the first review render of every XML-built video, check the audio is stereo and in range** (side channel `pan=mono|c0=c0-c1,volumedetect` well above -90 dB, plus ebur128): Premiere renders XML-built music as mono, and a music master at 0 dB lands far too hot (see `reference/premiere.md`). Captions only when the editor asks; then build an audio-anchored burned-in layer (`recipes/social-short.md`), never a raw whisper SRT. Name sequences `<Letter>_<Concept>_<length>_v1`; revisions are new `_v2` sequences.
**Keep the project findable every round:** a `01 LATEST` bin holds only the current version of each video (distinct label colour); older ones go to `02 Previous versions/<video>`; subclips go in a `Subclips` bin.

**Handoff snapshot (end of Phase 3, required):** save each finished sequence as XML to `_edit/snapshots/<seq>_handoff.xml` (Premiere: `export_as_fcp_xml`; Resolve: export the timeline; Final Cut: the file you built), and in Premiere/Resolve keep a `[handoff] <seq>` duplicate in a `_handoff copies (do not edit)` bin. The editor edits the original.

**Phase 4: QC, report, closeout.** Render every video and check automatically before calling it done: loudness and true peak (`ebur128=peak=true`), `blackdetect`, `freezedetect`, shots under 0.3 s, single black frames, Warp Stabilizer "analyzing" banners (`render_qc.py`), drone judder. Then the report (section 7).

**Phase 5: Learn from the editor's finish** (a later session, when the editor says they're done polishing). The most valuable learning in the workflow:
1. Get each finished sequence as XML (per `reference/<app>.md`) and diff it against the handoff snapshot (`xml_stack_diff.py`, or `diff_sequence_snapshots` in Premiere).
2. Translate the diff into editing patterns, not a change log ("replaced 3 of 4 opening shots with tighter details", "cut every bite over 8 s to under 6 s").
3. **Show the editor the proposed lessons and wait for their OK.** A diff shows what changed, not why.
4. Write confirmed lessons to `~/Editing-Notes/MY_PREFERENCES.md` (or the client's `STYLE.md`), add a row to `JOB_HISTORY.md`, commit if the notebook is a git repo.

## 5. Delivery defaults (override in MY_PREFERENCES.md)

- Social / vertical: about -14 LUFS integrated, true peak <= -1 dBTP, for every reel in a set (interview reels at -19 read as quiet next to montage reels).
- Dialogue bites levelled to -19 LUFS before the final mix; music bed ~15 dB under dialogue in interview pieces, ~8 dB under speech in wedding films.
- Fade music out over ~1 s at the end; trim adjustment layers to the last clip (longer layers leave black at the end).
- Export: H.264 at the sequence frame size, ~40 Mbps VBR, AAC 320 (Premiere preset: `presets/H264_MatchSource_40Mbps_AAC320.epr`).

## 6. Timing log

Append one row per phase per job to `~/Editing-Notes/timing-log.csv`:
`date,project,phase,minutes,footage_gb,clip_count,notes`
At closeout, compare against past jobs and name the bottleneck phase.

## 7. Report and closeout

Every job ends with `_edit/REPORT.md`: what got built (names, durations); concepts swapped and why; judgment calls; markers left (music, speed ramps, text, weak shots); footage gaps; suggested 15-20 s cutdown points; blockers; tools and techniques (what worked, what failed and the workaround, what was slow); phase timings.

Then:
1. New tool behavior or technique → append to `~/Editing-Notes/LESSONS.md` with the date, the app and its version.
2. Style rules the editor confirmed → `MY_PREFERENCES.md` or the client's `STYLE.md`. Update `used-shots.md` for clients with recurring work.
3. A reusable helper script written this job → save it, generalized, to `~/Editing-Notes/scripts/` with a one-line usage comment at the top.
4. Show the editor a short summary of what changed in their notebook. If they reject a lesson, remove it.
5. **Offer to share (once, lightly).** If step 1 added general lessons this job and `MY_PREFERENCES.md` doesn't say `Sharing lessons: don't ask`, end with one line, for example: *"You picked up N new lessons on this job. Sharing them helps everyone's Claude get better at editing: Tim reviews them and adds the best to the next kit update. Want me to package them for Tim? (yes / not now / don't ask again)"*. "Yes" runs the `share-lessons` skill. "Not now": drop it until the next job with new lessons. "Don't ask again": add `Sharing lessons: don't ask` under "Every video" in `MY_PREFERENCES.md` and never bring it up again. They can still say "share my lessons" any time.

## 8. Script index

| Script | What it does |
|---|---|
| `setup_venv.sh` / `vpy` | Create the kit venv (`~/.editing-kit/venv`); run a script with it: `scripts/vpy shot_quality.py scan ...` |
| `probe_media.py` | ffprobe + Sony XML sidecars → `_edit/work/probe.json` (camera, orientation, capture fps, date) |
| `contact_sheets.py` | 12-frame sheet per clip + 4-clip review stacks with red dividers |
| `transcribe_all.sh` | whisper.cpp word-level JSON/SRT/TXT per clip, skips done ones (`ONLY="C1 C2"` to prioritize) |
| `make_proxies.py` | ProRes Proxy 1080p for clips without proxies, written outside the footage; low priority, 2 workers, `--only` for a clip list. Never alongside work in the editing app |
| `shot_quality.py` | `scan` per-second shake/sharpness, `pick` best steady window, `grid` annotated frame grid |
| `action_scan.py` | Subject motion + camera jitter per 0.25 s; best steady action windows (cut on action) |
| `bg_shake.py` | Background-only shake (border-ring tracking); the shake tie-breaker. Measure proxies, not graded renders |
| `bites.py` | `words` timestamped transcript, `snap` cuts to quiet frames, `score` bites |
| `audio_sync.py` | Audio-sync cameras and recorders to a reference (speech-band envelope cross-correlation, refined on raw audio); prints each file's start on the reference clock |
| `cam_scan.py` / `cam_flags.py` | 6 fps camera motion + sharpness per clip or proxy, then flagged seconds (whips, focus pulls, blockages) on a shared clock, for multicam angle plans |
| `proxy_scan.py` | Per-frame action, jitter, pan and sharpness (12 fps) + an 8-frame labelled strip per clip from proxies in any folder; feeds tagging agents |
| `scan_summary.py` | One line per clip of per-second action/jitter/sharpness from a `proxy_scan.py` output folder, for tagging agents |
| `bg_shake_slide.py` | Sliding-window `bg_shake`: the steadiest windows of a given length that still have action (same bar) |
| `reel_repeats.py` | Cross-reel repeat check: frame-matches every planned shot's whole source clip (9:16 crop candidates) against delivered exports and reports where it already aired and whether it's the same window. Expect about one false positive per two real hits at 0.85-0.9; confirm with side-by-side frames before swapping |
| `speech_regions.py` | Per-shot speech onsets and offsets from the final mix, for caption timing |
| `caption_layer.py` | Cues JSON → bold burned-in caption PNGs → one frame-exact ProRes 4444 alpha layer (lead, wrap, 2-line check) |
| `mumble_scan.py` | Finds Enhance Speech artefacts (enhanced stem loud where the raw lav is quiet: whispers, unscripted chatter) so those stretches can use the raw lav |
| `splice_find.py` | Best join for a trim inside live music (chroma + mel match of the 3 s before each side), for a harmony-matched crossfade |
| `chord_pad.py` | Chord-following ambient pad from a chords JSON (each chord swells and crossfades into the next, soft detuned voices, long dark reverb); use instead of `pad_synth.py` when a static drone sounds like an organ |
| `pad_synth.py` | Static ambient pad in a key (open root + fifth, detuned voices, slow filter, `--cents` tuning to match live music) |
| `piano_synth.py` | Soft felt-piano part from a notes JSON, fully synthetic (no samples needed) |
| `piano_sampler.py` | Felt-piano part from a notes JSON using Logic Pro's factory Steinway sampler; sounds far more like a real piano. **macOS with Logic Pro installed only** (else use `piano_synth.py`) |
| `harp_synth.py` | Plucked-harp part from a notes JSON (Karplus-Strong, body resonances, `--env` gain automation); blends with a live harp |
| `music_profile.py` | Length, BPM, onset density, build and brightness of music files, to describe a client's music taste |
| `xml_from_spec.py` | JSON edit spec → FCP7 XML sequences for Premiere and Resolve (frame-exact incl. mixed rates and any NTSC rate, auto gain, punch-ins, 9:16 reframe with `xoff` crop offsets, stacked layers via `track`, disabled clips via `"enabled": false` (stacked multicam), a music track, one track per stem via `audio_tracks`, absolute-path renders, markers) |
| `fcpxml_from_spec.py` | The same spec → FCPXML 1.10 for Final Cut (validated against Apple's DTD; doesn't read the newer `music`, `track`, `xoff`, `enabled` and `audio_tracks` fields yet) |
| `preview_from_spec.py` | Low-res review MP4 of a spec sequence via ffmpeg, no editing app needed; frame-exact (segments by frame count, gaps as black), accepts absolute paths; mux the music or mix yourself |
| `render_slowmo.py` | Frame-exact slow-motion ProRes from a high-fps window (59.94 → 40% at 23.976), keeps orientation (upright vertical drone) |
| `speed_ramp.py` | Baked speed ramp (fast → eased → slow, motion blur) from high-fps source → ProRes, for apps whose speed tools can't be scripted |
| `pan_crop.py` | Baked moving 9:16 crop (pans, subject tracking) over a 16:9 source → ProRes |
| `stabilize.py` | OpenCV path smoothing for genuinely handheld pushes (not gimbal drones) → ProRes |
| `drone_cadence.py` | Judder/stutter check of a rendered range (duplicate frames, every-Nth-frame spikes) |
| `vcrop_strip.py` | Frame strip of a window as a 9:16 crop, to check vertical reframes before picking |
| `style_profile.py` | Shot-length / hook / tail benchmarks from finished reels, for a client `STYLE.md` |
| `tone_stats.py` | Black/mid/white points, contrast, saturation of finished films, to compare a cut against past exports |
| `lut_apply.py` | Applies a .cube LUT to a frame offline at a given intensity (e.g. 115%), to measure colour in the graded domain without a render |
| `cc_match.py` | Propose Lumetri Basic Correction values that match ungraded shots to the ones the editor corrected |
| `dialogue_profile.py` | Per-region level, noise floor and tone of a voice stem; flags dialogue that won't sit together |
| `jello_check.py` | Warp Stabilizer jello detector (before/after renders) |
| `render_qc.py` | Final-render QC: per-shot tone, tint, chroma, stabilizer banners, held frames |
| `xml_stack_diff.py` | Frame-by-frame layer-stack and effect diff of two FCP XML exports |

All scripts honour `EDIT_DIR`; `xml_from_spec.py` / `preview_from_spec.py` honour `MEDIA_ROOT` (same drive, other machine's path); `transcribe_all.sh` honours `WHISPER_MODEL`.
