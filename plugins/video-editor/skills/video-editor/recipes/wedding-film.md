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
- AI-enhanced dialogue sounds like a booth: keep it and add the same mic's room tone underneath (`reference/premiere.md`, "room tone"); don't blend raw + enhanced without sample-accurate alignment.
- **Music under speech: one consistent depth, about 8 dB under the voice.** Duck before speech starts, bridge pauses < 1.5 s (no pumping), and don't duck crowd cheers over a musical hit.
- Lift quiet toasts with gentle compression (2:1) before levelling; keep speech-to-room-tone ≥ ~14 dB.
- Even mix across the film: measure short-term loudness per section (one outside cut swung 12 dB between toasts and the dance floor). Level dialogue, then bring music-only sections to match.
- After removing a shot, check short-term loudness across the gap; the music bed can dip.
- One studio's loudness target: **-10 LUFS integrated**, sections within a few LU of each other (louder than the -14 streaming norm; YouTube turns it down, Vimeo/downloads don't). Confirm the editor's target.

## Color
- **Correct, don't grade**, unless asked. "Too flat" usually means clip-level Lumetri Basic Correction (Highlights +15 to +45, Shadows 0 to +30, Tint/Temperature within ±3); the creative LUT lives on adjustment layers. `cc_match.py` matches untouched shots to the ones the editor already corrected.
- Split the creative adjustment layer by lighting: daytime/outdoor, indoor under window light (push blacks harder), evening and dance floor (go light), dusk portraits (lift highlights).
- Warm/pink uplighting (cake cutting, toasts) gets its own section correction; leave foliage greens and party-light colour alone. Uplit toast cameras often need Saturation ~80.
- Drone footage over haze reads desaturated next to the main camera: measure foliage chroma against nearby ground shots, then apply **one gentle value to the whole drone group** (~115-120), not per-shot values.

## Timeline the editor gets
- Main timeline in the editor's delivery size (one studio uses 3840x1900 letterbox from the 2160 frame), 23.976, **4K originals on the timeline with proxies attached**, not proxies as media.
- Flat timeline (no nests) for anything the editor will polish.
- Track layout: V1 ceremony & speeches, one b-roll track above, log-LUT layer, drone above the LUT, creative grade sections, title/end card. No hidden clips stacked underneath. Name the tracks.
- Expect the editor's own polish pass (clip Lumetri, straightening, slow push-ins on details, 40% slow motion on twirls, tightening vow pauses) and keep it in later versions. A vow-pause cut can be covered with the wide tripod angle synced to the words after the cut.
