# Recipe: Wedding film (full film, 16:9)

Read this before Phase 2 on any wedding film or wedding re-edit. SKILL.md still applies; this file overrides it where they conflict, and the editor's `MY_PREFERENCES.md` overrides both. These are one working wedding studio's house rules, learned over many revision rounds on a real film. Treat them as strong defaults and ask the editor where their taste differs.

## Length and shape
- Sweet spot **5-8 min**, scaled to coverage hours. If the material supports a longer film, make it longer; cut weak or repetitive sections (dance floor), not good material.
- **Weight the front half**: establishing, details, anticipation, letters/vows, ceremony. Strong films reach the kiss 60-65% of the way through. Keep the dance floor short; no over-the-top dancing.
- Benchmarks: ask the editor for 2-4 of their favorite past films and measure them (`style_profile.py`, `tone_stats.py`). Reference numbers from one studio: ASL ~2.0 s overall, **2.0-2.8 s before the kiss**, ~1.2-1.7 s after, ~1.4 s in the last minute.

## Intro
- Build wide -> details -> people, holding establishing shots 2-6 s.
- It doesn't have to open on a drone (can be cliche); use one where it earns its place.
- Personal details beat generic ones (names on the welcome sign, monogram, rings, labelled bottles). Opening details should be about the couple, and every sign or label must read cleanly.
- Open with music building to a hit, or nat sound / a spoken line before the music; ask the editor. The opening shot itself is music only.
- Don't reuse a line in the intro that lands later unless deliberate.

## Cutting to music
- **Intro / builds:** cut on the beat, and land the drone or hero shot on the song's big hit (find it from loudness + onsets, not the section label).
- **Elsewhere:** don't cut on every beat; it gets predictable (a cut with 48% of shots on the beat vs ~20% by chance felt mechanical). Beat cuts in bursts; let shots ride across beats in emotional sections; land the big moments on the beat.
- **Fit the beat grid per section:** before the drums enter, the audible pulse can sit off the kick grid (an arpeggio a 16th ahead made cuts feel 5 frames late).
- Under the opening VO, merge 1-beat flashes into 2-beat holds; slow the final couple moment to 2+ s holds before the end.
- Give vows, tears and laughs room; tighten only in high-energy sections. Quiet sky/venue shots that let the film breathe are wanted, not filler.

## Story facts
- Verify moments (first look, getting ready) with synced clocks before naming them; don't infer from clip order.
- Letters/vows VO: check every recorder and lav; the cut often uses only part of the vows. A lav on the other partner picks up the vows quietly; plan Enhance Speech for it.

## Shot choices
- **Go easy on kissing:** keep the moments that matter (ceremony kiss, recessional, first dance, cake, the closer) plus one or two gentle ones; elsewhere use tender non-kiss beats from the same setups (head on shoulder, laughing, walking together). Count kisses across the film and never put two in a row. When a kiss shot is otherwise right, look at the seconds after it.
- Shots that just sit (holding hands, sitting on a porch) feel long past ~2 s: trim or split with a second angle. ~3.3 s per portrait shot.
- Two shots of the same setup type read as duplicates even from different clips.
- Put a detail next to the moment it belongs to, not in the intro.
- Portraits right after the recessional should show the couple; at most two cake-only shots; mix guys into the dance floor.
- **Reaction shots must come from the moment:** ceremony guests during the ceremony, actual listeners during speeches; hold ~2 s, split longer holds with a second listener. Never punch in on a guest for a reaction. After a toast's punchline, cut to the room laughing.
- Cut away from anyone on a phone; no phones in frame anywhere.
- If a speech has only one camera with whip pans, cut the whips out with non-sync cutaways and return in sync once the camera settles. Check locked-off second cameras first: over-the-shoulder reactions during vows are gold.
- Pick the steadiest part of a handheld walk (`bg_shake.py`), not just the first usable window.
- **Ending:** end on the couple looking at camera, linger, dissolve to black, then the studio's end card (~5 s, fading in and out on black). Not on a kiss.

## Audio
- All vows should sound like one recording and all speeches like another; quiet officiant lines (the pronouncement) need enhancing and lifting over the music. Profile with `dialogue_profile.py`.
- AI-enhanced dialogue sounds like a booth. **Blend the raw lav under the enhanced speech** (raw about −6 dB) and keep them on **separate tracks** (enhanced on A1, raw on A2, one gain curve per line) so the editor can ride the balance; this only works sample-aligned, so place both from the same timeline-aligned bus (see "Building from a script" below). Whispers and unscripted murmurs stay on the raw lav (`mumble_scan.py`).
- **Music under nearly the whole film, no near-silent gaps.** Under speech: about 8 dB under the voice (check the gap per line after the mix: ≥ 8 dB; loud song sections need a deeper duck). Scale the duck depth by the music's own level (full 9 dB at −24 dBFS, none at −34) and add a slow 3:1 leveller above the bed so choruses don't drive the limiter. Duck before speech starts, bridge pauses < 1.5 s (no pumping), don't duck crowd cheers over a musical hit, and **never let nat sound duck the music**; only dialogue does.
- Lift quiet toasts with gentle compression (2:1) before levelling; keep speech-to-room-tone ≥ ~14 dB.
- Even mix across the film: measure short-term loudness per section (one outside cut swung 12 dB between toasts and the dance floor). Level dialogue, then bring music-only sections to match.
- After removing a shot, check short-term loudness across the gap; the music bed can dip.
- One studio's loudness target: **-10 LUFS integrated**, sections within a few LU of each other (louder than the -14 streaming norm; YouTube turns it down, Vimeo/downloads don't). Confirm the editor's target.

## Color
- **Correct, don't grade**, unless asked. "Too flat" usually means clip-level Lumetri Basic Correction (Highlights +15 to +45, except bright or white-draped scenes, see `recipes/ceremony-film.md`; Shadows 0 to +30, Tint/Temperature within ±3); the creative LUT lives on adjustment layers. `cc_match.py` matches untouched shots to the ones the editor already corrected.
- Split the creative adjustment layer by lighting: daytime/outdoor, indoor under window light (push blacks harder), evening and dance floor (go light), dusk portraits (lift highlights).
- Warm/pink uplighting (cake cutting, toasts) gets its own section correction; leave foliage greens and party-light colour alone. Uplit toast cameras often need Saturation ~80.
- Drone footage over haze reads desaturated next to the main camera: measure foliage chroma against nearby ground shots, then apply **one gentle value to the whole drone group** (~115-120), not per-shot values.

## Timeline the editor gets
- Main timeline in the editor's delivery size (one studio uses 3840x1900 letterbox from the 2160 frame), 23.976, **4K originals on the timeline with proxies attached**, not proxies as media.
- Flat timeline (no nests) for anything the editor will polish.
- Track layout: V1 ceremony & speeches, one b-roll track above, log-LUT layer, drone above the LUT, creative grade sections, title/end card. No hidden clips stacked underneath. Name the tracks.
- Expect the editor's own polish pass (clip Lumetri, straightening, 40% slow motion on twirls, tightening vow pauses) and keep it in later versions. A vow-pause cut can be covered with the wide tripod angle synced to the words after the cut.

## Documentary / sentimental films
- More room to breathe and raw audio. Build the spine from the private first-look vows or letters and raw moments (a parent's first look, ceremony mishaps, toasts). Handheld shooters: give long holds to sound-carried sync moments (reactions, vows), keep ~2 s for b-roll, and use slow push-ins rather than long static wides. Reference documentary films averaged ~2 s per shot but spent 26-37% of runtime in ≥ 4 s holds.
- **Scenes, not single shots:** 3+ shots per scene. Getting ready in scenes (details → bridal party → groomsmen → parent + dress); ~10 min is fine when the material is good.
- **Their people:** when the couple says friends and family matter most, put guest moments in every act (bridal party, cocktail greetings, arrivals, toasts, reception). Light on dancing when asked; always the send-off if it was filmed.
- Include the processional and a reaction from the partner at the altar as the other walks the aisle.
- **Toasts:** in full sentences, with b-roll over most of each line matched to the words (cover speeches with unused couple footage). A-roll fragments under ~2 s between cutaways read as choppy: let the cutaway cover them.
- **Repeat-after-me vows:** use only the couple's repeats (cut the officiant's prompts, cutaway over the join) and auto-mix the two lavs (gain sharing on 30 ms power) so each voice is on its own mic. With several lavs, measure each line on every mic and take the loudest; don't guess who wears which.
- Group decor and detail shots together as a breather instead of spreading them over sentimental speeches.
- **No photographers or videographers in frame:** check every portrait (veil toss, by the car) and the edges of wide shots.
- Names title: spaced serif caps (~92 px Baskerville at 3840 wide, 0.5 em tracking, ~87% white) as a PNG on the top track with opacity fades (`title_png.py`). End card fades up the moment the picture reaches black.
- Music: main song + a slower second song in the same key (first look) + a mellow party song into the reception; ask which sections the editor likes. MusicBed can be searched by key + BPM (`/songs?keys=e-major&bpm=70:95&moods=love`).

## Movement and cut edges
- **Post moves on almost every static shot (house default):** b-roll 100 → 108 (every third a slow pan at 108), A-roll 100 → 107/110/112 by length, alternating in/out on back-to-back segments of one camera; rings and flat lays 100 → 112-114. **Cap the speed, not the amount:** ~1.2 %/s for b-roll, 0.8 %/s for A-roll (a fixed +8% on a 1.5 s shot reads as a snap zoom).
- **Review every cut's edges by eye before hand-back:** `edge_review.py` (frames around each visible shot's in and out, plus camera-move and jump-cut flags). "Cutting too soon / starting too soon" was mostly: a hug or kiss cut before it lands or releases (one ceremony kiss was 1.3 s early), a payoff just after the out, a nat line about something not yet in picture, an out on the first frames of a whip, a foreground walk-in at the out, a shot starting mid-motion that skips the setup, a reaction blocked by someone's back. Automatic passes (gap fill, flash cleanup, fragment cover) can re-create these, so give each shot a latest-usable out and lock in-points the passes must not pull, then review again.
- **Flash cuts:** after building, compute the top visible layer per frame and kill anything on screen under 1 s (A-roll peeking between two cutaways reads as a glitch). Gap-fill first, then the flash pass, then fill again.
- **Don't shed good material between versions:** diff each version's shot list against v1 and the tag log (hero/good shots never used); when a section shrinks, check what fell out.
- Pick drones by measured smoothness (frame-to-frame similarity, low jerk, no back-and-forth) and take the window where the move starts, not a static hover.

## Music transitions
- Let a song resolve at its phrase end (per-bar energy), ring out over 4-5 s, carry the gap on location sound (a J-cut of the next scene, guests chatting), and bring the next song in late with a 3-5 s fade on a phrase start. Never butt two songs or overlap two tempos for more than ~1 s.
- **Make room in the music, not the picture:** start the song at its intro for the cold open, run to a later section end, use a breakdown that was being skipped, or repeat chroma-matched bars (bars n and n+k > 0.95).
- For a speech section, play the song straight from its intro and put the chorus on the biggest line instead of looping the intro. Under a looping bed, a chord-following pad on its own track (`chord_pad.py`; brighter: `pulse_pad.py`) ducked half as much as the song.

## Building from a script
- Build the film as a script, not by hand: one `build_vN.py` holds every bite (lav file + in/out + camera sync offset → A-roll on V1 with its camera audio as room), every b-roll shot (V2), music segments with timeline anchors (put the song's hit on the moment) and markers; it writes the spec for `xml_from_spec.py` and a mix plan for an offline stem mix (dialogue / nat+room / music, one true-peak limiter on the sum). Then a fresh stereo import of the stems. Leave V3 + V4 empty for the editor's adjustment layers; `"move"` keyframes import as editable push/pan keys and `"fade_in"` gives a fade from black.
- **Cut every dialogue line from its words, not times:** write the line's text in the build and let `line_cut.py` find the edges (it re-transcribes a window with whisper DTW token times, snaps to pauses and verifies the cut by transcribing it alone). Whisper word times are word *starts* and drift 0.3-0.6 s between windows (up to ~10 s on a lav with long silences), so never use them as out points; `window_words.py` re-transcribes any window on the file's clock. When whisper can't time a spot (overlapping talkers), pass candidate edges to `verify()` in `line_cut.py` (it transcribes just the cut and reports missing words).
- **Fill picture gaps between bites:** extend the clip that ends before the gap (in-point unchanged, so sync holds) and check source length; `blackdetect` on the review render.
- **Dialogue chain:** gentle 2:1 above −30 dBFS and a crest cap (peaks ≤ RMS + 12 dB) per bite before the sum; one EQ target for all voices (1/3-octave match ±6 dB). FX3-style shotgun audio is often left-only: when one side is > 4 dB weaker, fill both sides with the louder one.
- **Enhance the whole film in one job:** dump the timeline-aligned dialogue bus (HPF + per-bite level only, mono, full length), upload once, rebuild each bite from the result at its timeline position. Re-edits find bites in the existing job by correlating raw audio against the uploaded bus: floor the energy normaliser and reject matches outside 0.8-1.05, and print every score (a silent mismatch dropped lines and the editor heard "toasts cutting out"). Adobe Enhance Speech result links expire about 3 h after the job finishes: download at once with `curl -f` and check each stem's length; if expired, re-run on the same asset (no new upload). Ask before uploading client audio (ground rule 6).
- Covering a shaky sync shot: keep the audio, cover only the shaky part (`bg_shake_slide.py` on the bite window) with a related cutaway.
