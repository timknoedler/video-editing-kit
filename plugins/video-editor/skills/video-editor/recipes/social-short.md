# Recipe: Social short / recap reel (vertical)

Read this before Phase 2 on reels, recaps, promos and other short-form social cuts. General rules in SKILL.md still apply; this file overrides them where they conflict.

## Format
- Vertical 9:16, 2160x3840, frame rate matching the dominant source rate, under 60 s unless the brief says otherwise.
- Horizontal 4K in a 9:16 timeline: Scale 177.78 (`"broll_scale": "auto"` in the spec; Final Cut uses conform Fill); shift with `xoff` / normalized Position (`reference/premiere-bridge-notes.md`). Preview every pick as a centre crop with `vcrop_strip.py`.
- Vertical shoots: Vertical-native clips import as 2160x3840; confirm rotation in review frames (SKILL.md section 3).
- 3-clip stacked layout (4K vertical, 59.3% scale): X=1080 for all; Y top=640, middle=1920, bottom=3200.

## Shape and pacing
- Strong hook in the first 2-3 s; end on the most specific, visual line or shot.
- Even warm or emotional recaps open with energy: a kinetic first 6-8 s (running, splash), then slow down for the heart.
- Montages need a story arc: write 4-6 acts in `paper_edits.md` before picking shots, one act marker per section.
- **~1.6-2.4 s per shot** (hero/button shots up to ~4 s), b-roll heavy. Fast and beat-driven cutting is fine here, including some off-beat energy cuts.
- If there isn't enough clean b-roll, shorten the video (60 s -> 45 s) rather than pad it.
- Balance who's on screen (count who appears across the build - ages, groups - and avoid long runs of the same kind of shot).

## Captions and end
- No auto-generated SRTs; caption natively in the editing app after picture lock.
- Drone closers under a logo must be steady (<= ~0.3 px).
