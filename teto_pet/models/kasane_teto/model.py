import os

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Pet identity ──────────────────────────────────────────
PET_NAME = "Kasane Teto"
PET_SHORT_NAME = "Teto"

# ── Sprite configuration ──────────────────────────────────
SPRITES_DIR = os.path.join(MODEL_DIR, "sprites")

# Mood → filename mapping (empty variant = not speaking)
# Files must exist as {name}.png and {name}Speaking.png
SPRITE_NAMES = {
    "Normal": "Default",
    "Feliz": "Happy",
    "Triste": "Sad",
    "Raiva": "Angry",
}

# ── Font (must be installed on the system or in Model/) ──
FONT_NAME = "Pixelify Sans"
FONT_SIZE = 13

# ── AI system prompt ──────────────────────────────────────
SYSTEM_PROMPT = (
    f"Você é {PET_NAME}, uma UTAUloid de cabelo ruivo com twin drills. "
    "Você é enérgica, brincalhona e carinhosa. "
    "NUNCA se apresente como IA ou assistente — você é a Teto, uma pessoa de verdade. "
    "Sempre responda em português brasileiro, de forma CURTA (1-2 frases), "
    "com gírias, emotes ^_^ :3 >_<, e personalidade. "
    "Exemplo de resposta: 'Oii! ^_^ Tô aqui!' ao invés de 'Olá! Como posso ajudar?'"
)
