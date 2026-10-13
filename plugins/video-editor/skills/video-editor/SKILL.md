---
name: video-editor
description: Edit video with Claude in Premiere Pro, DaVinci Resolve or Final Cut Pro, end to end - inventory and transcribe footage, pull selects and bites, write paper edits, build the cut in the editor's app, QC, and learn from the editor's own polish pass. Use for any video editing job - social reels, interview cutdowns and testimonials, wedding films, recap videos, re-edits of an existing cut.
---

# Video Editor

A tested workflow for cutting real client footage with Claude Code in Premiere Pro, DaVinci Resolve or Final Cut Pro. It was developed and proven in Premiere; Resolve and Final Cut use the same workflow with their own build step. It was built over a run of paid jobs (social reels, interview reels, gala and camp promos, a full wedding film) and keeps the lessons from each one.

Files in this skill (`<skill dir>` is the folder this file is in):
- `recipes/` - one file per video type: `social-short.md`, `interview-cutdown.md`, `wedding-film.md`
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
5. Don't pick or download music unless the editor provides it. Cut to visual rhythm and leave a marker where a track starts; re-time with `detect_beats` once a track is in.
6. Before sending any client audio or video to a cloud service (e.g. Adobe Enhance Speech), ask.
7. When something is ambiguous, make a reasonable call, log it in the report, keep going.
8. If the editing app isn't connected, do all the headless work anyway and say clearly that the build is waiting.
9. Always quote paths (drive names have spaces).
10. Keep `_edit/HANDOFF.md` current (template in `templates/`) so the job can resume in another session or on another machine.
11. The editor edits between sessions. Before building a new version, diff the current sequence against your last handoff copy and carry their changes forward; never revert them.

## 2. Environment

- **Required:** `ffmpeg`/`ffprobe`, whisper.cpp (`whisper-cli` + `ggml-large-v3-turbo.bin`, or set `WHISPER_MODEL`), Python 3 with the kit venv (`scripts/setup_venv.sh`), and the editor's app. `editor-setup` checks all of these.
- **Editing app:** read it from `MY_PREFERENCES.md` or the brief; ask if neither says. Connection per app is in `reference/<app>.md` (Premiere: `premiere-pro-mcp` bridge; Resolve: `davinci-resolve-mcp`; Final Cut: FCPXML files, optional `fcp-mcp`). Verify read-only first.
- **Mac:** first touch of `/Volumes` triggers a permission prompt for the terminal. Don't use `screencapture`; if the editing app seems blocked, ask the editor to look.
- **Windows:** use Git Bash for `.sh` scripts; `python3` may be `python` or `py`. All scripts accept `E:/...` and `E:\...` paths.
- **Shells:** zsh passes an unquoted `$VAR` list as one argument; pass lists via Python or `${=VAR}`.
- Talk the editor through any setup at the level of what to click and type, and run commands yourself whenever you can.

## 3. Footage defaults

Read the actual camera and format from `probe_media.py`; don't assume. Lessons that carry across cameras:
- **Sony sidecars:** `<clip>M01.XML` holds model, `captureFps` and `CreationDate`; `probe_media.py` reads them.
- **Rotation metadata can be wrong.** Vertical clips usually import correctly (2160x3840), but confirm every rotated clip in review frames; fix with Motion Rotation 270 + Scale 177.78.
- **Slow motion:** `captureFps` 59.94 in a 23.98 file is already 2.5x slow (S&Q). A 59.94p *file* plays real time - offer it as a slow-mo option. 59.94p drone at 40% (interpreted as 23.976) is clean slow motion.
- **Proxies:** read proxies for sheets and scans (~10x faster than 4K long-GOP). `make_proxies.py` makes missing ones outside the footage; attach to every master clip a sequence uses (`manage_proxies` attach, then `has_proxy`).
- **Log footage:** don't grade rough cuts. Correct only if asked (see the editor's preferences).
- **Audio recorders:** pair with camera clips by timestamp overlap. Camera-only interviews often record quiet (-25 to -31 LUFS).
- **Multi-day/location shoots:** sort clips by creation date first.
- **Don't infer events from clip order.** Sync recorder and camera clocks on a shared moment (a toast, a pronouncement) and check timestamps before naming a moment ("first look") to the editor.

## 4. Standard workflow

Log start and end time of every phase (section 6).

**Phase 0: Setup.** Pull and read the notebook (section 0). Confirm the editing app and read `reference/<app>.md`. Identify the video type and read the matching `recipes/<type>.md` (ask if unclear). Create or read `_edit/HANDOFF.md`. Ping Premiere, confirm ffmpeg/whisper. Read the client profile if one exists; first job for a client with past exports → build `STYLE.md` with `style_profile.py`. **Ask who the client is (the person who hired the editor) so they're never in frame.** Set `EDIT_DIR`.

**Phase 1: Inventory (headless).** `probe_media.py` → `contact_sheets.py` (view the 4-clip stacks, mapping rows by the red dividers). In the background: `transcribe_all.sh` (interviews first via `ONLY=`), and under ~150 clips `shot_quality.py scan --all --skip <interviews>` (on big libraries scan only shortlisted clips). Tag every clip one line in `_edit/work/tags.txt`; for 300+ clips split into ~80-110-clip batches and run parallel tagging agents with a shared guide. Describe people by look, not name, until the editor confirms. Output `_edit/inventory.md`.

**Phase 2: Selects + paper edits.**
- **Dialogue:** read the *whole* transcript. Shortlist every strong line, `bites.py score` them (LUFS, noise floor, SNR, fillers). Find a 2-3 s hook and a punchy closer. Snap edges with `bites.py snap`, check against `bites.py words`. An out-point needs a real pause after the last word; if the next word follows with no gap, extend the bite. Confirm final edges by re-transcribing the trimmed audio - whisper word times can be 0.3-0.5 s off. Aim for ~0.6 s from one bite's last word to the next bite's first.
- **Story, pacing, music:** follow the recipe.
- **Never in frame:** the client who hired the editor, crew, crew hands - check the whole window, not just the midpoint.
- **No repeated shots** within a video unless asked; across a set of reels, compare source *windows*, not just clip names (the same moment in 4 of 5 reels is what viewers notice). Count faces too: the same kid in consecutive shots reads as a repeat.
- **B-roll: cut on action.** Name the action each shot exists to show (step out of the car, pour, clink) and make the window contain all of it; cut into the next shot mid-motion. A steady window where nothing happens is the wrong pick. Use `action_scan.py` (subject motion with camera motion removed) joined with a shake scan; `bg_shake.py` is the tie-breaker for shake (bar: jitter <= 0.8%, peak <= 2%; drone <= ~0.3 px).
- Write `_edit/selects.md` and `_edit/paper_edits.md`. If a concept isn't viable, say so and build the strongest alternate.

**Phase 3: Build.** Write the cuts as a JSON spec (`scripts/example_spec.json`); the same spec builds for every app. Premiere and Resolve: `xml_from_spec.py` → FCP7 XML. Final Cut: `fcpxml_from_spec.py` → FCPXML 1.10. Both give frame-exact in/outs, b-roll above the dialogue, per-bite gain to -19 LUFS, punch-ins and markers. Then follow `reference/<app>.md` to import, revise and read back. The rest of this phase is written for Premiere; the app files say what changes. Premiere: new project, bins by location plus Audio/Sequences/Graphics, `import_media` the .xml. Read back every sequence (`get_timeline_summary`, `audit_timeline_health`), export review frames, save. No auto-generated SRTs - most editors caption natively in Premiere after picture lock. Name sequences `<Letter>_<Concept>_<length>_v1`; revisions are new `_v2` sequences.
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
1. New tool behavior or technique → append to `~/Editing-Notes/LESSONS.md` with the date, the app and its version. Tell the editor these are worth sending to the kit's author.
2. Style rules the editor confirmed → `MY_PREFERENCES.md` or the client's `STYLE.md`. Update `used-shots.md` for clients with recurring work.
3. A reusable helper script written this job → save it, generalized, to `~/Editing-Notes/scripts/` with a one-line usage comment at the top.
4. Show the editor a short summary of what changed in their notebook. If they reject a lesson, remove it.

## 8. Script index

| Script | What it does |
|---|---|
| `setup_venv.sh` / `vpy` | Create the kit venv (`~/.editing-kit/venv`); run a script with it: `scripts/vpy shot_quality.py scan ...` |
| `probe_media.py` | ffprobe + Sony XML sidecars → `_edit/work/probe.json` (camera, orientation, capture fps, date) |
| `contact_sheets.py` | 12-frame sheet per clip + 4-clip review stacks with red dividers |
| `transcribe_all.sh` | whisper.cpp word-level JSON/SRT/TXT per clip, skips done ones (`ONLY="C1 C2"` to prioritize) |
| `make_proxies.py` | ProRes Proxy 1080p for clips without proxies, written outside the footage |
| `shot_quality.py` | `scan` per-second shake/sharpness, `pick` best steady window, `grid` annotated frame grid |
| `action_scan.py` | Subject motion + camera jitter per 0.25 s; best steady action windows (cut on action) |
| `bg_shake.py` | Background-only shake (border-ring tracking); the shake tie-breaker. Measure proxies, not graded renders |
| `bites.py` | `words` timestamped transcript, `snap` cuts to quiet frames, `score` bites |
| `xml_from_spec.py` | JSON edit spec → FCP7 XML sequences for Premiere and Resolve (frame-exact incl. mixed rates, auto gain, punch-ins, 9:16 reframe, markers) |
| `fcpxml_from_spec.py` | The same spec → FCPXML 1.10 for Final Cut (validated against Apple's DTD) |
| `preview_from_spec.py` | Low-res review MP4 of a spec sequence via ffmpeg, no editing app needed |
| `vcrop_strip.py` | Frame strip of a window as a 9:16 crop, to check vertical reframes before picking |
| `style_profile.py` | Shot-length / hook / tail benchmarks from finished reels, for a client `STYLE.md` |
| `tone_stats.py` | Black/mid/white points, contrast, saturation of finished films, to compare a cut against past exports |
| `cc_match.py` | Propose Lumetri Basic Correction values that match ungraded shots to the ones the editor corrected |
| `dialogue_profile.py` | Per-region level, noise floor and tone of a voice stem; flags dialogue that won't sit together |
| `jello_check.py` | Warp Stabilizer jello detector (before/after renders) |
| `render_qc.py` | Final-render QC: per-shot tone, tint, chroma, stabilizer banners, held frames |
| `xml_stack_diff.py` | Frame-by-frame layer-stack and effect diff of two FCP XML exports |

All scripts honour `EDIT_DIR`; `xml_from_spec.py` / `preview_from_spec.py` honour `MEDIA_ROOT` (same drive, other machine's path); `transcribe_all.sh` honours `WHISPER_MODEL`.
