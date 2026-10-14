---
name: share-lessons
description: Package the editor's new, general editing lessons from ~/Editing-Notes into a short, scrubbed file they can send to Tim (the kit's author), so the best ones go into the next kit update for everyone. Use when the editor says "share my lessons", "send my lessons to Tim", or agrees to share at the end of a job. Never sends anything itself.
---

# Share my lessons

Goal: turn what this editor's Claude learned on their jobs into a short file they can send to Tim, with nothing private in it. Tim reviews every lesson and the good ones ship in the next kit update, so everyone's Claude gets better at editing. Nothing is sent automatically, and nothing reaches Tim unless the editor sends the file themselves.

## 1. Gather (read only)
- Read `~/Editing-Notes/LESSONS.md`. Its first line after the title is `Last shared: <date | never>`. Take only lessons dated after that date.
- Also offer reusable scripts in `~/Editing-Notes/scripts/` added since then. List them by name and ask which to include.
- Don't read client folders, `JOB_HISTORY.md`, transcripts, reports or anything in a job's `_edit/` folder. Leave `MY_PREFERENCES.md` out too, because it's personal taste, unless the editor asks to include a specific preference.
- If there's nothing new, say so in one line and stop.

## 2. Keep what helps everyone
Keep lessons that would help another editor on another job: app behavior and bugs, with the workaround; techniques for audio, color, pacing, QC and stabilization; setup fixes; and script fixes. Drop anything that only makes sense for one client or one shoot. Rewrite each lesson as:

- **[App + version or "any app"] What happened → what works.** One or two sentences. Example: *[Resolve 19.1] FCPXML import drops audio fades → re-add them after import, or build fades as volume keyframes.*

## 3. Scrub (release gate)
Remove or generalize:
- names of clients, couples, venues, companies and people (check every folder name in `~/Editing-Notes/clients/` and the names in each `CLIENT.md`)
- file paths, drive names and usernames
- emails, phone numbers, websites and social handles
- camera clip IDs (like `C1234` or `DJI_0001`), project names, prices and rates

Then search the finished file for every one of those names and patterns. If anything is left, fix it before showing the editor.

## 4. Show, then save
Show the editor the full list and let them cut anything. Ask one question: may Tim credit them by first name in the update notes? Then save `~/Editing-Notes/shared/lessons-for-tim-<YYYY-MM-DD>.md` in this format:

```
# Lessons for the video-editor kit
From: <first name, or "anonymous"> · Credit OK: <yes/no> · Date: <YYYY-MM-DD>
Kit version: <from the plugin's plugin.json> · App: <editing app + version> · OS: <Mac/Windows>

## Lessons
- **[App + version] What happened → what works.**

## Scripts (optional)
- <script name>: <one line on what it does> (attached)
```

Copy any scripts they chose, scrubbed the same way, into the same `shared/` folder. Then:
- Update `Last shared:` in `LESSONS.md` to today's date.
- Tell them where the file is and to text or email it to Tim, plus any scripts.
- Thank them: their lessons help everyone's Claude get better at editing.
