# Teto Pet

A desktop companion featuring Kasane Teto, the eternal UTAU mascot.
Think Bonzi Buddy, but with twin drills and red eyes.

![screenshot](https://img.shields.io/badge/status-alpha-orange)

> **Alpha software.** Things will break, features are missing, and the Teto might
> occasionally clip through reality. Expect rough edges.

## Features

- **Always-on-top character** — Teto lives on your desktop, rendered on a
  transparent window that stays above everything else.
- **Chat** — Right-click > "Conversar" to open a chat window. Teto responds
  with pre-written phrases based on keywords (Portuguese only for now).
- **Local AI support** — Enable it in the right-click menu to use
  [Ollama](https://ollama.com/) or llama.cpp. Requires a local server running
  on `localhost:11434`.
- **Draggable** — Click and drag Teto anywhere on your screen. Position is
  persisted across sessions.
- **Random speech** — Teto blurts out occasional lines on her own.
- **Custom sprites** — Drop any PNG images into `assets/teto/` and they'll be
  loaded automatically as character sprites.

## Requirements

- Python 3.10+
- GTK 3
- PyGObject (`python-gobject`)
- PyCairo (`python-cairo`)

### Arch Linux

```bash
sudo pacman -S python-gobject gtk3
```

### Ubuntu / Debian

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0
```

## Usage

```bash
./run.sh
```

Or directly:

```bash
python3 main.py
```

Right-click on Teto for the context menu with chat, settings, and quit
options.

## Configuration

Settings are stored in `~/.config/teto-pet/config.json`. You can edit it
manually or use the right-click menu.

| Key | Default | Description |
|-----|---------|-------------|
| `window_x`, `window_y` | `100`, `100` | Window position on screen |
| `always_on_top` | `true` | Keep window above others |
| `ai_enabled` | `false` | Enable local AI chat |
| `ai_endpoint` | `http://localhost:11434/api/generate` | Ollama/llama.cpp API |
| `ai_model` | `llama3.2` | Model name for the API |

## Project Structure

```
teto-pet/
├── main.py                    # Entry point
├── run.sh                     # Convenience launcher
├── requirements.txt
├── README.md
├── assets/
│   └── teto/                  # Drop PNG sprites here
└── teto_pet/
    ├── app.py                 # Main window, drag, context menu
    ├── character.py           # Sprite loading & Cairo fallback renderer
    ├── chat.py                # Chat dialog
    ├── ai.py                  # Local AI integration with fallback
    ├── phrases.py             # Pre-written responses (pt-BR)
    └── config.py              # JSON config handler
```

## Roadmap

- [ ] Proper idle animations (blinking, bouncing)
- [ ] Alarm / reminder system
- [ ] Feed and mood mechanics (virtual pet style)
- [ ] English chat support
- [ ] Multiple expressions / poses
- [ ] AUR package
- [ ] Audio playback (Teto UTAU voicebank)

## License

MIT
