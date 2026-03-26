# WorkPulse

A lightweight Windows system tray app for capturing your work activities throughout the day — so you never have to recall 8 hours from memory again.

## How it works

- Runs silently in your system tray
- Pings you every 15 minutes — "what are you working on?"
- You log in 5 seconds, it timestamps everything automatically
- End of day: clean summary ready to copy into Clockify

## Features

- Global hotkey (Alt+L) to log anytime from anywhere
- 15-min smart ping with "still on this?" one-click confirm
- Idle detection — pauses pings when you're AFK
- Consecutive same-task entries auto-merged in summary
- Unaccounted gap detection (highlighted red in summary)
- Clockify integration (paste your API key in settings)
- Dark mode, configurable ping interval, sound themes
- Export to .txt or Clockify-formatted CSV

## Project Structure

```
workpulse/
├── main.py               ← entry point
├── core/
│   ├── database.py       ← SQLite operations
│   ├── timer.py          ← ping timer + idle detection
│   ├── clockify.py       ← Clockify API integration
│   └── config.py         ← settings management
├── ui/
│   ├── tray.py           ← system tray icon + menu
│   ├── ping_popup.py     ← 15-min ping popup
│   ├── quick_log.py      ← hotkey quick log popup
│   ├── summary.py        ← today's log window
│   └── settings.py       ← settings window
├── data/
│   └── projects.json     ← project + task definitions
├── assets/               ← tray icon files
├── sounds/               ← .wav sound files
├── .env.example          ← config template (safe to commit)
├── requirements.txt
├── setup.bat             ← one-time Windows setup script
└── build.bat             ← PyInstaller packaging script
```

## Setup (First Time)

```bash
git clone https://github.com/farhanjml/workpulse.git
cd workpulse
setup.bat
```

That's it. App runs, tray icon appears, shortcut on desktop, starts on boot.

## Setup (Development)

```bash
pip install -r requirements.txt
python main.py
```

## Data Storage

All data stored locally — never in the cloud:

```
C:\Users\<you>\AppData\Local\WorkPulse\
    workpulse.db    ← your log history (SQLite)
    config.env      ← your settings
```

Uninstalling the app does NOT delete this folder unless you explicitly choose to.

## Clockify Integration

1. Go to Clockify → Profile Settings → API Key
2. Copy your key
3. In WorkPulse → Settings → Clockify → paste key
4. Entries sync automatically going forward

## Future Integrations

- [ ] Notion workspace sync (daily/weekly/monthly log pages)
- [ ] Monthly PDF/Word report export
