# 🎀 Mate Helper

Um pet virtual de desktop com **Kasane Teto** que conversa, interage com seu sistema e comenta sobre sua tela.

![Teto](desktop_pet/models/kasane_teto/sprites/Happy.png)

## ✨ Funcionalidades

- **Pet na área de trabalho** — personagem animado com balão de fala
- **Chat com IA** — integração com Groq, Gemini, HuggingFace ou Ollama
- **Leitura de tela** — acessibilidade: a Teto descreve o que está na sua tela
- **Comandos de voz/texto** — abra sites, pastas, execute comandos
- **Perfil do usuário** — a IA te chama pelo nome
- **Balão lateral** — posição automática, esquerda ou direita
- **Modelos do pet** — suporte a múltiplos visuais

## 🚀 Requisitos

- Python 3.10+
- GTK 3.0 + Cairo + Pango
- `requests`
- (Opcional) [Ollama](https://ollama.ai) para modelos locais
- (Opcional) Chave da [Groq](https://console.groq.com) ou Gemini

### Instalação de dependências

```bash
# Ubuntu/Debian
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0

# Fedora
sudo dnf install python3-gobject gtk3 cairo-gobject

# Arch
sudo pacman -S python-gobject gtk3
```

```bash
pip install requests
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

Clique com o botão direito no pet para abrir o menu:

| Menu | Descrição |
|------|-----------|
| **Conversar** | Abre o chat com a Teto |
| **Aparência** | Sempre no topo, lado do balão, modelo do pet |
| **Acessibilidade** | Leitura automática da tela com intervalo configurável |
| **Inteligência** | Provedor de IA, chaves da API, permissões de ferramentas |
| **Ações** | Meu Perfil, Limpar Histórico |

### Provedores de IA

1. **Groq** (recomendado) — rápido, gratuito, precisa de chave
2. **Gemini** — Google, precisa de chave
3. **HuggingFace** — API gratuita
4. **Ollama** — local, modelos como Qwen, DeepSeek, Llama
5. **Frases prontas** — sem IA, só respostas scriptadas

## 🔧 Modelos Ollama sugeridos

```bash
ollama pull qwen2.5:7b
ollama pull deepseek-r1:7b
```

Ambos cabem em ~8GB VRAM e oferecem ótimo custo-benefício.

## 📁 Estrutura

```
mate-helper/
├── run.sh
├── desktop_pet/
│   ├── main.py
│   ├── app.py          # Janela principal e menu
│   ├── chat.py         # Chat e execução de ferramentas
│   ├── ai.py           # Provedores de IA
│   ├── config.py       # Configuração persistente
│   ├── tools.py        # Ferramentas (screenshot, comandos, etc.)
│   ├── phrases.py      # Frases de fallback
│   ├── character.py    # Animação do personagem
│   └── models/         # Sprites e configuração dos pets
│       └── kasane_teto/
│           ├── model.py
│           ├── font.ttf
│           └── sprites/
```

## 📜 Licença

MIT — @MCookinho
