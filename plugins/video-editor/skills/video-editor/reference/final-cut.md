# Final Cut Pro: build notes

Status: the kit's workflow was developed in Premiere. Phases 1, 2 and 4 (inventory, selects, paper edits, QC renders) don't depend on the editing app and work as-is. This file covers Phase 3 (build) and Phase 5 (learn) in Final Cut. Log findings in `~/Editing-Notes/LESSONS.md` and send good ones to the kit's author.

## How Claude works with Final Cut
Final Cut has very little scripting, so no tool can edit a live Final Cut timeline the way the Premiere and Resolve bridges do. The kit works **through FCPXML files** instead: Claude writes the cut as a file, the editor imports it (one menu command), and when the editor wants changes or is done polishing, they export the project back as FCPXML for Claude to read.

- Optional bridge: **fcp-mcp** (pypi.org/project/fcp-mcp, MIT). Install with `pipx install fcp-mcp`, then `claude mcp add-json fcp '{"type":"stdio","command":"fcp-mcp"}' --scope user`. It reads, checks and edits FCPXML (flash frames, gaps, duplicates, offline media, audio levels), converts FCPXML to FCP7 XML, and on a Mac can open libraries, read timeline info and run menu commands through AppleScript (some need Accessibility permission). It's useful but not required: the kit's own builder makes the files.

## Building the cut
1. Build with `scripts/fcpxml_from_spec.py SPEC.json OUT.fcpxml` (same spec as the other apps). It writes FCPXML 1.10 (Final Cut 10.6 and later) and validates against Apple's DTD: dialogue on the primary storyline with gaps between bites, b-roll as connected clips above (video only), VO bites below (audio only), logo stills on lane 2, per-bite gain to the target loudness, markers with notes.
2. Scale: `"auto"` sets Spatial Conform to **Fill** (horizontal footage fills a vertical project); a number sets Fit plus that scale.
3. The editor imports with **File > Import > XML**. It lands in a new event, "Claude Edit", with one project per sequence. Media links to the original files in place (nothing is copied).
4. **First import on a new machine: check it.** Confirm the project size and frame rate, that connected b-roll sits over the right words, and that mixed-rate clips start where the spec says. Note anything off in LESSONS.md.
5. Revisions: write a new versioned file (`<name>_v2.fcpxml`) and have the editor import it. Never ask them to replace their working project.
6. Rules that carry over: versioned projects, never overwrite; don't grade unless asked; markers for music, text and speed ramps (Final Cut's own retiming is better done by the editor).

## Learning from the editor's finish (Phase 5)
- Ask the editor to export the finished project: select it, then **File > Export XML** (FCPXML 1.10 or newer).
- Diff it against the file Claude handed over. With fcp-mcp, convert both to FCP7 XML and use `scripts/xml_stack_diff.py`; without it, read the two FCPXML files directly (spine order, connected clips, `offset`/`start`/`duration`, adjustments).
- Color and effects done in Final Cut appear in FCPXML as filters; read them, but confirm grade preferences with the editor.

## Delivery
- The editor shares from Final Cut (File > Share). Run the same QC on the exported file (loudness/true peak, black and frozen frames, short shots) before calling it done.
