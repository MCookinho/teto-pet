# 🎀 Mate Helper

Um **pet virtual de desktop** com inteligência artificial que conversa, interage com seu sistema e comenta sobre o que acontece na sua tela.

![Teto](desktop_pet/models/kasane_teto/sprites/Happy.png)

## ✨ Funcionalidades

### Gerais
- **Pet na área de trabalho** — personagem animado com sprites, balão de fala e emoções
- **Chat com IA** — integração com Groq, Gemini, HuggingFace, Ollama ou frases scriptadas
- **Comandos de voz/texto** — abra sites, pastas, tire screenshot, execute comandos, leia arquivos
- **Perfil do usuário** — a IA te chama pelo nome e sabe seus detalhes
- **Multi-provedor** — alterna entre provedores de IA sem precisar reiniciar
- **Múltiplos modelos de pet** — troque de personagem com um clique
- **Histórico por modelo** — cada personagem mantém seu próprio histórico de conversa

### Acessibilidade & Automação
- **Leitura automática da tela** — o pet comenta sobre o que está na sua tela em intervalos configuráveis
- **Áudio do sistema** — transcrição e comentário sobre áudios do desktop
- **Falas aleatórias** — o pet puxa assunto sozinho, como um amigo virtual

### Áudio & Microfone
- **STT (Speech-to-Text)** — fale com o pet usando o microfone
- **Modo contínuo** — microfone sempre ouvindo (transcrição a cada 5s)
- **Pressionar pra Falar** — segure uma tecla (ou Win+V global) para gravar, solte para transcrever
- **Atalho global Win+V** — funciona de qualquer lugar da tela, com suporte a socket Unix para integração com compositor Wayland

### Alarmes
- **Múltiplos alarmes** — adicione, ative/desative e exclua alarmes pelo menu
- **Toque personalizado** — cada modelo de pet tem seu próprio ringtone (MP3)
- **Animação de dança** — o pet dança enquanto o alarme toca

### Sistema
- **Ferramentas com permissões** — ative/desative individualmente: ler arquivos, listar diretórios, executar comandos, escrever arquivos, abrir URLs, capturar tela, capturar áudio
- **Janela transparente** — fundo translúcido com bordas arredondadas, sempre no topo
- **Balão adaptável** — o balão de fala se posiciona automaticamente à esquerda ou direita dependendo da posição da janela na tela
- **Animação suave** — 8 FPS com suporte a GIFs animados e sprite sheets PNG

## 🚀 Requisitos

- Python 3.10+
- GTK 3.0 + Cairo + Pango
- `requests` (para APIs de IA)
- (Opcional) [Ollama](https://ollama.ai) para modelos locais
- (Opcional) Chave da [Groq](https://console.groq.com) ou [Gemini](https://aistudio.google.com)

### Dependências do sistema

```bash
# Ubuntu/Debian
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 libpulse0

# Fedora
sudo dnf install python3-gobject gtk3 cairo-gobject pulseaudio-libs

# Arch
sudo pacman -S python-gobject gtk3 pulseaudio
```

```bash
pip install requests
```

### Para o atalho global Win+V (opcional)

```bash
# Instala o pynput para captura global de teclas
pip install --user --break-system-packages pynput

# No Wayland (niri, Hyprland, etc.), adicione o usuário ao grupo input
sudo usermod -aG input $USER
# (requer logout/login)
```

## 🏃 Rodar

```bash
./run.sh
```

Ou diretamente:

```bash
python3 desktop_pet/main.py
```

## 🧠 Configuração

Clique com o botão direito no pet para abrir o menu de contexto.

### Provedores de IA

| Provedor | Chave? | Notas |
|----------|--------|-------|
| **Groq** (recomendado) | Sim | Rápido, gratuito; modelo: `llama-3.3-70b-versatile` |
| **Gemini** | Sim | Google; suporte a imagens; fallback entre modelos |
| **HuggingFace** | Não | Gratuito; modelos: Zephyr 7B, DialoGPT |
| **Ollama** | Local | Modelos locais: Qwen, DeepSeek, Llama; auto-inicia o servidor |
| **Frases prontas** | Não | Sem IA — respostas scriptadas; útil para teste |

### Modelos Ollama sugeridos

```bash
ollama pull qwen2.5:7b
ollama pull deepseek-r1:7b
ollama pull llama3.2:3b
```

### Permissões de ferramentas

Cada ferramenta tem uma permissão individual no menu **Inteligência → Permissões**:

| Ferramenta | Descrição |
|------------|-----------|
| `read_file` | Ler arquivos do sistema (máx. 2000 caracteres) |
| `list_files` | Listar diretórios (máx. 60 itens) |
| `run_command` | Executar comandos bash (com timeout de 30s; bloqueia comandos destrutivos) |
| `write_file` | Escrever conteúdo em arquivos |
| `open_url` | Abrir URLs via `xdg-open` |
| `screenshot` | Capturar tela |
| `listen` | Capturar áudio do desktop |

### Atalhos do teclado

| Tecla | Modo | Descrição |
|-------|------|-----------|
| `V` (configurável) | App em foco | Pressionar pra Falar (hold) |
| `Win+V` | Global | Pressionar pra Falar de qualquer lugar |
| Botão do microfone no chat | Chat aberto | Gravar áudio (hold/toggle) |

### Atalho global no niri

Adicione ao seu `cfg/keybinds.kdl`:

```
Mod+V   hotkey-overlay-title="Push to Talk" { spawn-sh "bash ~/.local/bin/mate-helper-ptt toggle"; }
```

## 📁 Estrutura do projeto

```
mate-helper/
├── run.sh                          # Script para iniciar o app
├── README.md
├── desktop_pet/
│   ├── main.py                     # Ponto de entrada
│   ├── app.py                      # Janela principal, menu, timers, STT
│   ├── chat.py                     # Janela de chat, execução de ferramentas
│   ├── ai.py                       # Integração com provedores de IA
│   ├── config.py                   # Gerenciamento de configuração persistente
│   ├── tools.py                    # Ferramentas de sistema (screenshot, arquivos, áudio, comandos)
│   ├── character.py                # Motor de sprites/animação
│   ├── log.py                      # Utilitário de logging
│   └── models/
│       ├── __init__.py             # Proxy de carregamento lazy dos modelos
│       ├── kasane_teto/            # Modelo: Kasane Teto (UTAUloid)
│       │   ├── model.py            # Identidade, prompts, configurações
│       │   ├── phrases.py          # Frases de fallback em PT-BR
│       │   ├── font.ttf            # Fonte personalizada
│       │   ├── ringtone.mp3        # Toque de alarme
│       │   └── sprites/            # Sprites PNG (9 arquivos)
│       └── white_guy/              # Modelo: Computador (PC)
│           ├── model.py
│           ├── phrases.py
│           ├── font.ttf
│           ├── ringtone.mp3
│           └── sprites/            # Sprites GIF (10 arquivos)
```

## 🎨 Como criar um modelo de pet

Criar um novo personagem é simples. Basta criar uma nova pasta em `desktop_pet/models/` seguindo a estrutura abaixo.

### Estrutura mínima

```
desktop_pet/models/meu_personagem/
├── __init__.py             # Pode estar vazio
├── model.py                # Obrigatório: identidade e configurações
├── phrases.py              # Obrigatório: frases de fallback
├── sprites/                # Obrigatório: imagens do personagem
│   ├── Default.png         # Sprite padrão (quieto)
│   └── DefaultSpeaking.png # Sprite falando
└── font.ttf                # Opcional: fonte personalizada
```

### 1. `model.py` — Identidade e configurações

```python
import os

MODEL_DIR = os.path.dirname(__file__)

# Identidade
MODEL_ID = "meu_personagem"
PET_NAME = "Meu Personagem"          # Nome completo
PET_SHORT_NAME = "MeuP"              # Nome curto (exibido no chat)

# Sprites
SPRITES_DIR = os.path.join(MODEL_DIR, "sprites")
SPRITE_NAMES = {
    "Normal": "Default",
    "Feliz": "Happy",
    "Triste": "Sad",
    "Raiva": "Angry",
    "Danca": "Dancing",
}

# Áudio
RINGTONE_PATH = os.path.join(MODEL_DIR, "ringtone.mp3")  # Opcional: pode ser None

# Fonte (opcional — usa a padrão se não existir)
FONT_NAME = "Pixelify Sans"
FONT_SIZE = 13

# Prompt de sistema — define a personalidade do personagem
SYSTEM_PROMPT = """Você é {PET_NAME}, um mascote de desktop amigável.
- Responda em português brasileiro
- Seja breve (1-2 frases)
- Use emoticons às vezes
- NUNCA diga que é uma IA"""

# Prompts de acessibilidade (leitura de tela e áudio)
ACCESSIBILITY_SCREEN_PROMPT = "Descreva o que você vê nesta captura de tela em português, com detalhes interessantes."
ACCESSIBILITY_AUDIO_PROMPT = "Comente sobre o que foi falado neste áudio de forma natural."

# Tarefas de acessibilidade
from . import phrases as _phrases

ACCESSIBILITY_TASKS = {
    "screen": [
        {"mode": "aleatorio", "min": 15, "max": 60, "prompt": ACCESSIBILITY_SCREEN_PROMPT},
    ],
    "audio": [
        {"mode": "aleatorio", "min": 10, "max": 30, "prompt": ACCESSIBILITY_AUDIO_PROMPT},
    ],
}
```

### 2. `phrases.py` — Frases de fallback

Cada modelo precisa de um `phrases.py` com duas funções e listas de frases nomeadas.

```python
import random

# Contexto para continuidade da conversa
_context = {"last_category": None, "history": []}

# Listas de frases (use quantas quiser em cada categoria)
GREETING = ["Olá! Como você está?", "Oieee!"]
HOW_ARE_YOU = ["Como você está?", "Tudo bem?"]
RETURN_GOOD = ["Que bom!", "Feliz em saber!"]
RETURN_BAD = ["Ah, que pena...", "Melhoras!"]
THANKS = ["De nada!", "Por nada!"]
BYE = ["Tchau!", "Até logo!"]

# ... (outras categorias: name, what_can_you_do, affection, jokes, etc.)

ALARM_PHRASES = ["Hora do alarme!", "Acordaaa!"]
THINKING_PREFIXES = ["Hmm...", "Deixa eu ver..."]
CONTINUATIONS = ["Continue...", "E então?"]

# Mapeamento de palavras-chave para categorias
CATEGORY_KEYWORDS = {
    "como_esta": ["como você está", "tudo bem", "como vai"],
    "nome": ["qual seu nome", "quem é você", "como se chama"],
    "tchau": ["tchau", "até logo", "ate mais", "adeus"],
    # ... adicione quantas categorias quiser
}

def pick(category, default=""):
    """Pega uma frase aleatória de uma categoria."""
    lst = globals().get(category, [])
    return random.choice(lst) if lst else default

def update_context(history):
    """Atualiza o contexto interno com o histórico da conversa."""
    _context["history"] = history

def get_fallback(message, history):
    """Retorna uma resposta baseada em palavras-chave quando não há IA."""
    msg = message.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in msg for kw in keywords):
            _context["last_category"] = category
            return pick(category)
    return pick("unknown", "Não entendi...")
```

### 3. Sprites

As imagens devem seguir a convenção de nomes:

| Arquivo | Descrição |
|---------|-----------|
| `Default.png` | Parado (sem falar) |
| `DefaultSpeaking.png` | Falando |
| `Happy.png` | Feliz |
| `HappySpeaking.png` | Feliz falando |
| `Sad.png` | Triste |
| `SadSpeaking.png` | Triste falando |
| `Angry.png` | Bravo |
| `AngrySpeaking.png` | Bravo falando |
| `Dancing.png` | Dançando (animado ou sprite único) |

**Formatos aceitos:**
- **PNG** — imagens estáticas ou sprite sheets (vários frames lado a lado). O sistema detecta automaticamente a largura de cada frame pela coluna de alpha zero.
- **GIF** — GIFs animados com delays por frame preservados.

> **Dica:** Você não precisa de todos os sprites. Se faltar algum, o sistema usa o `Default` como fallback.

### 4. font.ttf (opcional)

Coloque uma fonte `.ttf` na pasta do modelo. Se não existir, o sistema usa a fonte padrão do sistema.

### 5. ringtone.mp3 (opcional)

Coloque um arquivo MP3 para o toque do alarme. Se não existir, o alarme não toca áudio (mas ainda funciona visualmente).

### 6. `__init__.py`

Pode ser um arquivo vazio. É necessário apenas para o Python reconhecer a pasta como pacote.

### Finalizando

Depois de criar a pasta com os arquivos acima:

1. Reinicie o app
2. Clique com o botão direito → **Modelo do pet** → selecione seu modelo
3. Pronto! O app recarrega automaticamente com o novo personagem

## 🧱 Arquitetura

O app segue uma arquitetura modular:

| Camada | Arquivo | Responsabilidade |
|--------|---------|------------------|
| Entrada | `main.py` | Inicializa o GTK e cria a janela |
| Orquestração | `app.py` | Janela principal, eventos, timers, menu, STT |
| Conversa | `chat.py` | Chat UI, histórico, loop IA + ferramentas |
| IA | `ai.py` | Provedores: Groq, Gemini, HuggingFace, Ollama |
| Ferramentas | `tools.py` | Funções de sistema (screenshot, arquivos, comandos, áudio) |
| Personagem | `character.py` | Sprites, animação, moods |
| Config | `config.py` | Config JSON persistente em ~/.config/teto-pet/ |
| Modelos | `models/` | Pastas com identidade, sprites e frases de cada personagem |
| Log | `log.py` | Log simples com timestamp |

### Fluxo de conversa

```
Usuário (texto/voz) → ChatWindow._process_user_text()
  ├─ _run_tool() → match por palavras-chave → executa ferramenta → resposta
  └─ _call_ai_then_tool() → AI responde
       ├─ Se resposta contém "TOOL:" → executa ferramenta → realimenta AI
       └─ Se resposta normal → exibe no balão de fala + chat
```

### Sistema de tarefas automáticas

O app executa tarefas em background baseadas no modelo ativo:

```
TetoPet._start_all_timers()
  ├─ screen task: captura tela → AI descreve → mostra no balão
  ├─ audio task: captura áudio desktop → transcreve → AI comenta
  └─ speech task: fala aleatória do personagem
```

Cada tarefa pode ser configurada como **aleatória** (intervalo entre min-max) ou **exata** (intervalo fixo).

## 📜 Licença

MIT — @MCookinho
