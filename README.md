# The Sunday Cut

*A video editing kit for Claude, by Tim Knoedler.*

Cut real client footage with Claude in **Premiere Pro, DaVinci Resolve or Final Cut Pro**. Claude logs and transcribes your footage, pulls the best moments and interview lines, plans the edit, builds a rough cut in your app, checks it, and learns your style from the changes you make. Built by Tim Knoedler over a run of paid client jobs.

**Full setup guide (start here):** [The Sunday Cut Setup Guide (PDF, always the newest)](https://github.com/timknoedler/video-editing-kit/releases/latest/download/The-Sunday-Cut-Setup-Guide.pdf). Drop it into Claude Code and say "Set this up for me." The short version:

## Install
In Claude Code (inside the Claude desktop app, or the terminal version):
```
/plugin marketplace add timknoedler/video-editing-kit
/plugin install video-editor@sunday-strolls-editing-kit
```
Restart Claude, then type:
```
/video-editor:editor-setup
```
Claude asks which editing app you use, installs what's needed (asking before anything big), connects to your app, and creates your notebook folder, `~/Editing-Notes`.

Updates: setup turns on auto-update for you and checks it again at the start of every job, so new versions arrive when Claude starts.

## First edit
> Edit the footage in /Volumes/MyDrive/Smith Gala into three 30-second vertical reels using the video-editor skill. The client is the woman in the red dress; keep her out of frame.

## How each app works
| App | How Claude builds the cut | Bridge |
|---|---|---|
| Premiere Pro | Live in Premiere, plus an XML import for the first assembly | [premiere-pro-mcp](https://github.com/leancoderkavy/premiere-pro-mcp) |
| DaVinci Resolve | XML import for the first assembly, live changes after | [davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp) |
| Final Cut Pro | Claude writes an FCPXML file; you import it (File > Import > XML) | none needed; [fcp-mcp](https://pypi.org/project/fcp-mcp/) optional |

The workflow was built and proven in Premiere. Resolve and Final Cut use the same workflow with their own build step and are newer; your notes on what works help everyone.

## Good to know
- Your preferences and lessons live in `~/Editing-Notes`; kit updates never touch them.
- Claude never picks music, never exports for publishing, and never sends client media anywhere without asking. It never touches your original footage.
- When you've finished polishing, say **"I'm done polishing, learn from my changes."** That's where it gets good.
- Learned something useful? Say **"share my lessons"**. Claude packages your new lessons, with client details removed, into a file you send to Tim. The best ones go into the next update, so everyone's Claude gets better at editing.

## License
Free to use, including on paid client work, under the [PolyForm Perimeter License 1.0.1](LICENSE.md). The one thing it doesn't allow is offering a competing product built from this kit, such as repackaging or reselling it. Copyright 2026 Timothy Knoedler, Sunday Strolls Productions.
