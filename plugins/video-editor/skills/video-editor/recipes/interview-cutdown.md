# Recipe: Interview piece / testimonial cutdown

Read this before Phase 2 on interview-led videos (testimonials, recaps built on bites). General rules in SKILL.md still apply; this file overrides them where they conflict.

- Lead with b-roll under the opening bites. Speaker on camera only for the hook line, the key line, and jump-cut cover; b-roll everywhere else, changing every ~2 s and matched to the words ("tomato" -> slicing tomatoes).
- Hide jump cuts with punch-ins when b-roll runs thin (`plan_emphasis_zoom_keyframes`, or a static 115% scale via the XML spec).
- Choose the *best* dialogue, even when the brief maps specific bites: keep the editor's must-haves, propose stronger lines as a v2 next to his version.
- Bite edges: follow SKILL.md section 4 Phase 2 "Dialogue" (snap to quiet frames, real pause after the out-word, confirm by re-transcribing).
- Check the **in** side of every join too: re-transcribe 1 s either side of each bite cut on the finished timeline. A bite that starts early carries the tail of the previous word (one reel had the tail of the previous word at a join; it read as a garbled cut-off). Fix by starting the bite in the quiet before the first word, or by filling the tail with the speaker's own room tone when sync must not move.
- Cut points 2-3 frames after the last word (check with `bites.py words`).
