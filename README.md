# WorkPulse

A lightweight Windows system tray app for capturing your work activities throughout the day — so you never have to recall 8 hours from memory again.

## How it works

- Runs silently in your system tray
- Pings you every 15 minutes — "what are you working on?"
- You log in 5 seconds, it timestamps everything automatically
- End of day: clean summary ready to review and push to Clockify

## Features

- Global hotkey (Alt+L) to log anytime from anywhere
- Alt+Shift+L to log a quick side task without stopping your active timer
- 15-min smart ping with "still on this?" one-click confirm
- Idle detection — pauses pings when you're AFK
- Overdue warning when you've been active too long without logging
- Unaccounted gap detection (highlighted red in summary)
- Clockify integration — entries sync automatically
- Dark / light mode, configurable ping interval, sound themes
- All hotkeys are configurable in Settings

## Download

Grab the latest installer from [Releases](https://github.com/farhanjml/workpulse/releases). Run `WorkPulse Setup x.x.x.exe` — one-click install, launches automatically.

## Project Structure

```
workpulse/
├── src/
│   ├── main/                 ← Electron main process (Node.js)
│   │   ├── index.js          ← app lifecycle, windows, tray, hotkeys
│   │   ├── database.js       ← SQLite operations (better-sqlite3)
│   │   ├── config.js         ← settings (electron-store)
│   │   ├── clockify.js       ← Clockify REST API
│   │   ├── timer.js          ← ping timer + idle detection
│   │   └── ipc.js            ← IPC handler registrations
│   ├── preload/
│   │   └── index.js          ← contextBridge (window.api)
│   └── renderer/             ← React 18 + Tailwind CSS
│       └── src/
│           ├── main.jsx      ← React entry, window router
│           ├── windows/
│           │   ├── PingPopup.jsx
│           │   ├── QuickLog.jsx
│           │   ├── Interrupt.jsx
│           │   ├── Summary.jsx
│           │   ├── Settings.jsx
│           │   └── StatusBar.jsx
│           └── styles/
│               └── globals.css   ← Dotdash design tokens (CSS vars)
├── data/
│   └── projects.example.json ← project + task definitions template
├── assets/                   ← tray icons, fonts
├── sounds/                   ← .wav sound files
├── package.json
├── electron-builder.yml      ← packaging config
└── build.bat                 ← npm run build → installer
```

## Development

Requires Node.js 18+.

```bash
git clone https://github.com/farhanjml/workpulse.git
cd workpulse
npm install
npm run dev
```

## Build

```bash
npm run build
# Installer output: C:\BuildOutput\WorkPulse\WorkPulse Setup x.x.x.exe
```

## Data Storage

All data stored locally — never in the cloud:

```
C:\Users\<you>\AppData\Local\WorkPulse\
    workpulse.db    ← your log history (SQLite)
    config.json     ← your settings
```

Uninstalling the app does NOT delete this folder unless you explicitly choose to.

## Projects Config

Copy `data/projects.example.json` to `data/projects.json` and fill in your projects and task types. This file is gitignored (contains client names).

## Clockify Integration

1. Go to Clockify → Profile Settings → API Key
2. Copy your key
3. In WorkPulse → Settings → Clockify → paste key + workspace ID
4. Click "Sync Projects" to pull your projects
5. Entries sync automatically going forward

## Stack

- **Electron 33** — app shell, system tray, global hotkeys
- **React 18** — UI components
- **Tailwind CSS v3** — styling with Dotdash design tokens
- **better-sqlite3** — local database
- **electron-store** — config persistence
- **axios** — Clockify API calls

## Future

- [ ] Notion workspace sync (daily/weekly log pages)
- [ ] Monthly PDF/Word report export
- [ ] Week view in Summary window
