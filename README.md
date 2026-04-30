# Overleaf Client

An **unofficial** native macOS desktop client for [Overleaf](https://cn.overleaf.com/), built with **Python 3** and **PySide6 / QtWebEngine**.

> Looking for the 中文版? See **[README.zh.md](./README.zh.md)**.

---

## Why

Overleaf ships as a web app only. This project gives you a real Mac app — its own Dock icon, native menu bar, keyboard shortcuts, system notifications, and Keychain-backed credential storage — while still reusing the battle-tested Chromium engine under Qt so every Overleaf feature keeps working.

## Features

- **Persistent login** — cookies live in a QtWebEngine profile, and optional email/password autofill is stored in the **macOS Keychain** (never on disk in plaintext). The Keychain backend uses the `/usr/bin/security` CLI so it works even inside an unsigned `py2app` bundle.
- **Native menu bar** with standard Mac conventions:
  - `⌘R` Reload
  - `⌘,` Preferences
  - `⌘Q` Quit
  - `⌘F` Find on page (Chrome-style floating overlay; `⌘G` / `⇧⌘G` next/prev, `Esc` to close)
  - Overleaf's own in-page shortcuts (`⌘↩` Recompile, etc.) keep working.
- **In-window toolbar** with Back / Forward / Reload / Home / Downloads — readable font with configurable row height.
- **Close-to-background** (like Claude Desktop / Slack) — the red traffic light hides the main window but keeps the app alive; clicking the Dock icon re-reveals it. `⌘Q` still truly quits.
- **Downloads panel** — shares the same page-style chrome as Preferences (title + subtitle, SECTION label, divider, hint, footer button row) and lists active and completed downloads as Motrix-inspired cards with colored file-type badges, live speed / ETA, a progress bar, `Cancel` (also removes the card from the list), `Retry` for interrupted transfers, and `Show in Finder`. Long filenames scroll horizontally inside the card so the list never grows wider than the panel, and double-clicking a finished card opens the file in the default app.
- **Bilingual UI (English / 中文)** — a single **Language** preference (`Auto` follows the system locale / `English` / `中文`) retranslates the toolbar, menus, Preferences dialog, and Downloads panel live with no restart required. The same choice also switches the Overleaf mirror (`www` ↔ `cn`).
- **Modern global stylesheet** — a single parameterized QSS sheet drives the whole app; sizes scale proportionally from a single base point size so everything (titles, tabs, download cards) stays in visual harmony.
- **Appearance settings** — in Preferences you can tune:
  - Base font size (12–24 pt, re-applied live)
  - Window opacity for Preferences / Downloads (50–100 %, previewed as you drag)
  - Toolbar row height (padding 2–14 px)
- **Status bar clock + work timer** — the right side of the status bar shows the current wall-clock time and how long you've *actually* been working in the window this session. The counter pauses automatically when the window is hidden, when another app is frontmost, or when no keyboard / mouse / trackpad input has been seen for 2 minutes; it resumes the moment you touch something. Idle detection uses macOS's `CGEventSourceSecondsSinceLastEventType` via `ctypes` (no extra dependency).
- **System notifications** via `osascript` (Notification Center fallback).
- **Dock badge** (e.g. `!` when offline) via `NSApp.dockTile`.
- **Offline detection** — probes the home URL every 30 s so captive-portal / DNS failures surface as a status bar and notification.
- **One-click install** (`install.sh`) — venv → py2app → `/Applications`. Clean up build artifacts with `./clean.sh` (or `./clean.sh --deep` to also drop `.venv/`).
- **Preferences dialog** — iTerm2-style tabbed layout: home URL, zoom factor, **language** (`Auto` / `English` / `中文` — drives both UI text and the Overleaf mirror), download directory, toggle notifications / Dock badge / Keychain autosave.
- **Multi-window** support for `target="_blank"` links.
- **macOS-template app icon** — 1024×1024 canvas with the ~80% rounded-square tile and transparent outer margin Apple's template requires, so the Dock icon sits at the same visual size as stock apps.
- **Clean layered architecture** — `core/` (framework-agnostic), `ui/` (Qt), `platforms/mac/` (macOS integration).

## Requirements

- macOS 11 (Big Sur) or newer
- Python ≥ 3.10
- Xcode Command Line Tools (for `sips` / `iconutil` when rebuilding the icon)
- Optional: [`create-dmg`](https://github.com/create-dmg/create-dmg) via `brew install create-dmg` for DMG builds

## Install

### One-click (recommended)

```bash
git clone git@github.com:ZhiboRao/Overleaf.git
cd Overleaf
./install.sh
```

The script creates `.venv/`, installs all dependencies, builds the `.app` bundle, copies it to `/Applications/Overleaf Client.app`, and (if `create-dmg` is installed) produces a distributable DMG in `dist/`.

### From source (for development)

```bash
make install-dev
make run
```

### Common make targets

| Target | Description |
|---|---|
| `make run` | Run from source against your local Python venv |
| `make lint` | `ruff` + `mypy` |
| `make icon` | Regenerate `resources/icon.icns` |
| `make app` | Build the `.app` bundle only |
| `make dmg` | Build a distributable DMG |
| `make clean` | Remove build artifacts |
| `make distclean` | Also delete `.venv/` |

## Architecture

```
src/overleaf_client/
├── app.py              # Composition root / entry point
├── core/
│   ├── config.py       # AppConfig + JSON persistence
│   ├── credentials.py  # Keychain-backed credential store
│   ├── i18n.py         # UI string catalog + active-language switch
│   ├── network.py      # Reachability monitor (QNetworkAccessManager)
│   └── browser.py      # QtWebEngine profile + page
├── ui/
│   ├── main_window.py  # QMainWindow hosting QWebEngineView
│   ├── menu_bar.py     # Native menu construction
│   ├── shortcuts.py    # JS snippets that drive Overleaf's DOM
│   ├── notifications.py# osascript + QSystemTrayIcon fallback
│   ├── downloads.py    # Downloads panel (Preferences-style chrome + Motrix-inspired cards)
│   ├── find_bar.py     # ⌘F find-on-page floating overlay
│   ├── styles.py       # Global parameterized QSS stylesheet
│   └── preferences.py  # iTerm-style tabbed preferences dialog
└── platforms/mac/
    ├── dock.py         # NSApp.dockTile badge helper
    └── idle.py         # CoreGraphics idle-time probe (ctypes)
```

The three layers communicate one-way downward: `app.py` owns the dependency graph; UI imports core; `platforms/mac` is optional and never imported from `core/`.

## Data locations

| What | Where |
|---|---|
| JSON settings | `~/Library/Application Support/Overleaf Client/settings.json` |
| Cookies / cache / localStorage | `~/Library/Application Support/Overleaf Client/webengine-profile/` |
| Saved credentials | macOS Keychain, service `com.zhiborao.overleafclient` |
| Downloads | `~/Downloads` (configurable) |

## Privacy & security notes

- Passwords are stored in the system Keychain via the `/usr/bin/security` CLI — never written to disk in plaintext or transmitted beyond the HTTPS login request to Overleaf.
- Cookies live inside QtWebEngine's sandboxed profile directory.
- No analytics, no background phoning-home. The only network traffic is what the Overleaf site itself does, plus a periodic `HEAD` to your configured home URL for offline detection.

## Disclaimer

This is an **unofficial** wrapper. "Overleaf" is a trademark of Overleaf / Digital Science. This project is not affiliated with, endorsed by, or sponsored by Overleaf. You must have a valid account to use the service, and you are bound by Overleaf's own Terms of Service when using it through this client.

## License

[MIT](./LICENSE)
