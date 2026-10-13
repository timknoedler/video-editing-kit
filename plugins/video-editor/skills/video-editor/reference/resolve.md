# DaVinci Resolve: build notes

Status: the kit's workflow was developed in Premiere. Phases 1, 2 and 4 (inventory, selects, paper edits, QC renders) don't depend on the editing app and work as-is. This file covers Phase 3 (build) and Phase 5 (learn) in Resolve. Log what works and what doesn't in `~/Editing-Notes/LESSONS.md`; those findings are the most useful thing to send back to the kit's author.

## Connection
- Bridge: **davinci-resolve-mcp** (github.com/samuelgursky/davinci-resolve-mcp, MIT). It drives Resolve through Blackmagic's official scripting API: timelines, media pool, markers, color, Fairlight, render queue.
- Install: `npx davinci-resolve-mcp setup` (sets up its Python environment, finds Resolve, registers with Claude). Needs Resolve 18.5+ and Python 3.10-3.12.
- In Resolve: Preferences > General > **External scripting using: Local**.
- **Resolve Studio** supports external scripting directly. **Free Resolve** doesn't; the bridge then connects through its in-app script (Workspace > Scripts). If no Resolve tools answer, check this first.
- Verify read-only first (list projects, timelines, media pool) before changing anything.

## Building the cut
1. **First assembly: FCP7 XML.** Build with `scripts/xml_from_spec.py` (the same spec as Premiere), then import in Resolve with File > Import > Timeline (or the bridge's interchange import). One import builds every sequence with in/outs, b-roll on V2, per-bite gain, punch-in scale and markers.
2. **Check mixed frame rates after import.** The builder counts clip in/outs at the sequence rate because Premiere reads them that way. Resolve may honour each clip's own rate instead. On the first job, compare a 59.94 or 29.97 clip's source in-point in Resolve with the spec; if it's off by 2.5x or 1.25x, note it in LESSONS.md and use the live bridge to place mixed-rate clips.
3. **Revisions: live bridge.** Small changes (swap a shot, nudge a cut, add markers, set clip gain) go through the bridge on a duplicate of the timeline. Never edit the editor's current timeline without a duplicate first.
4. **Rules that carry over unchanged:** new versioned timelines, never overwrite; a `01 LATEST` bin; handoff copies before the editor polishes; don't grade unless asked (Resolve editors usually grade on the Color page with their own node tree, so leave clip color alone).
5. Resolve's own **Scene Cut Detection, Smart Reframe, Voice Isolation and transcription** (Studio) can replace some kit steps; ask which the editor prefers.

## Learning from the editor's finish (Phase 5)
- Export the handoff timeline and the finished timeline as FCP7 XML (File > Export > Timeline), then compare with `scripts/xml_stack_diff.py` and read the edit changes from it.
- Color changes live in Resolve's node graph and won't show in XML; ask the editor about grade changes directly.

## Delivery
- Render through the Deliver page or the bridge's render tools. Run the same QC on the render (loudness/true peak, black and frozen frames, short shots) before calling it done.
