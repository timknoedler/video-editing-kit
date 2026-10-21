# Recipe: Social short / recap reel (vertical)

Read this before Phase 2 on reels, recaps, promos and other short-form social cuts. General rules in SKILL.md still apply; this file overrides them where they conflict.

## Format
- Vertical 9:16, 2160x3840, frame rate matching the dominant source rate, under 60 s unless the brief says otherwise.
- Horizontal 4K in a 9:16 timeline: Scale 177.78 (`"broll_scale": "auto"` in the spec; Final Cut uses conform Fill); shift with `xoff` / normalized Position (`reference/premiere.md`). Preview every pick as a centre crop with `vcrop_strip.py`.
- Vertical shoots: Vertical-native clips import as 2160x3840; confirm rotation in review frames (SKILL.md section 3).
- 3-clip stacked layout (4K vertical, 59.3% scale): X=1080 for all; Y top=640, middle=1920, bottom=3200.

## Shape and pacing
- **Vertical is the master when both ratios ship:** edit the 9:16 first and make the 16:9 match it slot for slot. A stack becomes its main wide, and a native-vertical drone becomes the matching horizontal drone. To mirror a long vertical stack, play its three panels one after another rather than holding one wide for 3 s.
- **Group shots into blocks** (arrival, food, activities, music, people) rather than alternating food/person/food/person. Each block gets 3-11 shots, ordered by the music's sections.
- **Start fast:** skip a long quiet music intro (start the music file at the bar where the build begins) and cut the build at 2 beats; the first hit should land within about 6 s.
- Strong hook in the first 2-3 s; end on the most specific, visual line or shot.
- Even warm or emotional recaps open with energy: a kinetic first 6-8 s (running, splash), then slow down for the heart.
- Montages need a story arc: write 4-6 acts in `paper_edits.md` before picking shots, one act marker per section.
- **~1.6-2.4 s per shot** (hero/button shots up to ~4 s), b-roll heavy. Fast and beat-driven cutting is fine here, including some off-beat energy cuts.
- If there isn't enough clean b-roll, shorten the video (60 s -> 45 s) rather than pad it.
- Balance who's on screen (count who appears across the build - ages, groups - and avoid long runs of the same kind of shot).

## Captions and end
- Don't caption unasked. When the editor asks: words from whisper, timing from `speech_regions.py` on the final mix (raw whisper SRTs drift up to ~1 s), cues led by 3 frames, then a burned-in layer from `caption_layer.py`. House style: `--px 135 --maxw 0.70 --stroke 0 --shadow 0 --cy 0.50` (Arial Black, white, no outline, no punctuation except apostrophes and hyphens, centred vertically, at most 2 lines with manual `|` breaks). Lines must stay inside the middle 70% of the width or the Reels like/share rail covers them (Premiere: `check_caption_safe_zone` instagram_reels on the union of the PNGs' boxes). Make a 1080p ProRes 4444 proxy of the layer for playback, and put it on the top track above any adjustment layer.
- Drone closers under a logo must be steady (<= ~0.3 px).
