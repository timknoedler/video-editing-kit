# Releasing a new version (for Tim)

The private toolkit (`~/Editing-Toolkit`) stays the source of truth and keeps growing every job. This repo is a scrubbed snapshot of it. Friends only ever get what's here.

## When: every 3 finished projects
The private playbook's closeout step counts finished jobs since the last release (job history rows dated after the newest CHANGELOG entry below). At 3 or more, Claude runs a release as the last step of that closeout. Tim can also ask any time: "release the editing kit now."

## How Claude releases
1. `git pull` this repo and the toolkit. Diff the toolkit against the toolkit commit noted in the newest CHANGELOG entry.
2. Carry over the general parts: playbook workflow changes → `SKILL.md`; Premiere tool lessons → `reference/premiere.md`; app-neutral audio, color and QC techniques → the matching recipe or `reference/premiere.md`; recipe rules → `recipes/`; new or fixed general scripts → `scripts/`. Anything Tim learned about Resolve or Final Cut → `reference/resolve.md` / `final-cut.md`.
3. Scrub as it goes. **Never ship:** client, couple or contact names; client folders; job history; timing logs; transcripts; real file paths; the studio end card or logo; music licensing accounts; job-specific scripts with hardcoded paths. Personal taste becomes a "house default" the friend's own `MY_PREFERENCES.md` can override.
4. **Name sweep (release gate):** grep the whole repo for every client and couple name in the toolkit's `clients/` folder, job history and recipes, plus clip IDs from real jobs in prose. Any hit stops the release until it's fixed.
5. Run `claude plugin validate .`, rebuild the FCPXML test spec and validate it against Apple's DTD if `fcpxml_from_spec.py` changed.
6. Bump `version` in `plugins/video-editor/.claude-plugin/plugin.json` (friends don't get changes until it changes): patch for fixes and lessons, minor for new scripts or recipes. Add a CHANGELOG line with the toolkit commit, then commit and push.
7. Tell Tim in two or three lines what's in the release, and update the "What's new" section of the shared Setup Guide doc.

## CHANGELOG
- 1.0.0 (2026-10-13): first release, from toolkit commit b74f3f7. Workflow as of mid-October 2026 (five client jobs). Premiere Pro (proven), DaVinci Resolve and Final Cut Pro (new: shared FCP7 XML / new FCPXML builder, app notes).
