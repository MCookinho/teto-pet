# Mate Helper (Windows)

A virtual desktop pet with AI that chats, interacts with your system, and comments on what's happening on your screen.

Portabilidade oficial para Windows.

## Funcionalidades

- Animated desktop pet with speech bubbles and emotions
- AI chat (Groq, Gemini, HuggingFace, Ollama, or scripted phrases)
- Voice and text commands (open URLs, take screenshots, run commands, etc.)
- Speech-to-Text (continuous or push-to-talk)
- Automatic screen reading and desktop audio transcription
- Alarms with custom ringtones
- Multi-language character system (create your own pets)

## Requisitos

- Python 3.10+
- GTK 3.0 + Cairo + Pango (via MSYS2)
- `requests` (for AI APIs)

### Instalação no Windows

1. **Instalar MSYS2** em https://www.msys2.org/

2. **Abrir terminal UCRT64** e instalar GTK:
   ```bash
   pacman -S mingw-w64-ucrt-x86_64-gtk3 mingw-w64-ucrt-x86_64-cairo \
             mingw-w64-ucrt-x86_64-pango mingw-w64-ucrt-x86_64-python-gobject
   ```

3. **Instalar dependências Python**:
   ```bash
   pip install -r requirements-win.txt
   ```

4. **Executar**:
   ```powershell
   python desktop_pet/main.py
   ```
   Ou clique duas vezes em `run.ps1`.

## Uso

Clique com o botão direito no pet para abrir o menu de contexto e configurar seu provedor de IA.

### Atalhos

- **Win+V**: Gravação por voz (push-to-talk)
- **Duplo clique**: Abrir chat
- **Arrastar**: Mover o pet pela tela

## Audio

No Windows, o microfone usa PyAudio (WASAPI). A captura de áudio do desktop usa loopback WASAPI.

## Criando um Modelo de Pet

Veja o [modelo de exemplo](docs/custom_model/) em `docs/custom_model/`.

## Licença

MIT — @MCookinho
