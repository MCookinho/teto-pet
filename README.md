# Mate Helper

A virtual desktop pet with AI that chats, interacts with your system, and comments on what's happening on your screen.

## Features

- Animated desktop pet with speech bubbles and emotions
- AI chat (Groq, Gemini, HuggingFace, Ollama, or scripted phrases)
- Voice and text commands (open URLs, take screenshots, run commands, etc.)
- Speech-to-Text (continuous or push-to-talk)
- Automatic screen reading and desktop audio transcription
- Alarms with custom ringtones
- Multi-language character system (create your own pets)

## Requirements

- Python 3.10+
- GTK 3.0 + Cairo + Pango
- `requests` (for AI APIs)

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 libpulse0
pip install requests
```

(Optional) [Ollama](https://ollama.ai), or API keys for [Groq](https://console.groq.com) / [Gemini](https://aistudio.google.com).

## Quick Start

```bash
git clone https://github.com/your-username/mate-helper.git
cd mate-helper
python3 desktop_pet/main.py
```

Right-click the pet to open the context menu and configure your AI provider.

## Creating a Pet Model

Create your own character by adding a folder to `desktop_pet/models/`:

```
desktop_pet/models/my_pet/
├── __init__.py           # empty
├── model.py              # identity, prompts, settings
├── phrases.py            # fallback dialogue
├── strings.py            # UI translations
└── sprites/              # character images
    ├── Default.png
    ├── DefaultSpeaking.png
    ├── Happy.png
    └── ...
```

See the [template model](docs/custom_model/) for a complete example with comments.

## License

MIT — @MCookinho
