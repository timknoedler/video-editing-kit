---
name: editor-setup
description: One-time setup for the video-editor kit on a new computer - asks which editing app they use (Premiere Pro, DaVinci Resolve or Final Cut Pro), installs ffmpeg, whisper.cpp and its model, Python and the kit venv, connects Claude to their editing app, and creates the editor's ~/Editing-Notes notebook. Use when someone first installs the kit, says "set me up", or when the video-editor skill finds something missing.
---

# Editor setup

Goal: get a new editor from "installed the plugin" to "Claude can see Premiere" with as little typing on their part as possible. Run every command yourself; only ask the person to click things you can't (installers that need a password, Premiere menus). Explain each step in one plain sentence. The kit's scripts live in the `video-editor` skill's `scripts/` folder (a sibling of this skill's folder).

Work through the checklist in order, skip anything already done, and finish with a short summary of what's ready and what's still missing.

## 1. Detect the machine and the app
Ask which editing app they use: Premiere Pro, DaVinci Resolve (free or Studio), or Final Cut Pro. Write it into the notebook in step 6.
`uname -s` (Darwin = Mac; MINGW/MSYS = Windows Git Bash). On Windows, if there's no bash at all, ask them to install Git for Windows (git-scm.com, default options) and reopen Claude.

## 2. Command-line tools
- **Mac:** Homebrew (`brew --version`; if missing, give them the one-line install command from brew.sh to paste into Terminal, since it asks for their password). Then `brew install ffmpeg whisper-cpp python`.
- **Windows:** `winget install Gyan.FFmpeg Python.Python.3.12` (tell them to tick "Add to PATH" if an installer asks). whisper.cpp: download the latest Windows release build from github.com/ggml-org/whisper.cpp/releases (the CUDA build if they have an NVIDIA GPU), unzip, and put the folder with `whisper-cli.exe` on PATH.
- Confirm: `ffmpeg -version`, `ffprobe -version`, `whisper-cli --help`.

## 3. Whisper model
Download `ggml-large-v3-turbo.bin` (about 1.6 GB) from huggingface.co/ggerganov/whisper.cpp into:
- Mac: `~/Library/Application Support/whisper.cpp/models/`
- Windows: `~/whisper.cpp/models/`
Ask before starting the download (it's large). Any other location works if they set `WHISPER_MODEL`.

## 4. Python venv
Run `<video-editor>/scripts/setup_venv.sh`. It creates `~/.editing-kit/venv` (outside the plugin, so updates don't wipe it). Expect "venv ready".

## 5. Connect the editing app
Read `<video-editor>/reference/<app>.md` for details. Run the commands yourself; after registering a bridge, Claude must be restarted before its tools appear, so tell them to restart and come back to finish.
- **Premiere Pro:** needs Node.js 20.19+ (`node -v`; Mac `brew install node`, Windows `winget install OpenJS.NodeJS.LTS`). Then `npm install -g premiere-pro-mcp`, `premiere-pro-mcp --install-cep` (installs the Premiere panel), `premiere-pro-mcp --doctor`, and register it: `claude mcp add premiere-pro --scope user -- premiere-pro-mcp`. They restart Premiere, open a project, and open Window > Extensions > MCP for Adobe Premiere Pro. Verify with `verify_premiere_connection` (read-only).
- **DaVinci Resolve:** `npx davinci-resolve-mcp setup` (needs Python 3.10-3.12 and Resolve 18.5+). In Resolve: Preferences > General > External scripting using: Local. Free Resolve connects through the bridge's in-app script (Workspace > Scripts); Studio connects directly. Verify by listing projects and timelines (read-only).
- **Final Cut Pro (Mac only):** nothing is required; the kit hands Final Cut files to import. Optional: `pipx install fcp-mcp` then `claude mcp add-json fcp '{"type":"stdio","command":"fcp-mcp"}' --scope user`, which lets Claude check FCPXML files and read the open library. Show them File > Import > XML and File > Export XML, the two commands they'll use.

## 6. Notebook
Create `~/Editing-Notes/` from `<video-editor>/templates/notebook/` if it doesn't exist (never overwrite an existing one). Write their editing app at the top of `MY_PREFERENCES.md`, then ask three quick questions and write the answers in: where they get music, how they caption, and their loudness targets (offer the kit defaults: -14 LUFS social, -10 LUFS wedding films).
Two computers? Offer to make `~/Editing-Notes` a private GitHub repo so both machines share it (needs `gh auth login`).

## 7. Smoke test (optional, ~2 min)
Point `probe_media.py` and `contact_sheets.py` at any folder with a few clips, with `EDIT_DIR` set to a temp folder, and show them one contact sheet. Then tell them how to start a real job: "make a folder with the footage, then tell Claude: edit this using the premiere-editor skill" (or fill in `templates/PROJECT_BRIEF.md`).
