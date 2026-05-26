import random
from .model import PET_NAME, PET_SHORT_NAME

FALLBACKS = {
    "greeting": [
        "Hii! Nice to see you! ^_^",
        "Hey hey! I'm here!",
        f"What's up? {PET_SHORT_NAME} online!",
        "Hey! Glad you came to visit!",
        "I've been waiting for you!",
        "Hi hi! How are you?",
        f"Yoohoo! {PET_SHORT_NAME} ready for anything!",
        "Hiiie! Missed you!",
    ],
    "how_are_you": [
        "I'm good! And you? ^_^",
        "Energetic! Just had some virtual coffee~",
        "Kind of bored... wanna chat?",
        "Super happy! You came to see me!",
        "I'm great! How about you?",
        "Hmm, I'm okay... but better now that you're here!",
        "Full of energy! Ready for anything!",
    ],
    "return_good": [
        "Aww, that's great! ^_^",
        "Happy to hear that!",
        "Nice! Keep it up!",
        "Aww, wonderful!",
        "Awesome! Everything's good then!",
    ],
    "return_bad": [
        "Aww, that sucks... wanna talk about it?",
        "Oh no... want a virtual hug? (づ｡◕‿‿◕｡)づ",
        "Relax, everything will be okay! Trust me!",
        "That's rough... I'm here if you need to talk.",
        "Aw man... wanna play a game or chat to distract?",
        "I'm sorry... wanna vent to me?",
    ],
    "thanks": [
        "You're welcome! ^_^",
        "No problem! That's what I'm here for!",
        "Anytime! Count on me always!",
        "Don't mention it! Just call me anytime!",
        "Happy to help! :3",
    ],
    "bye": [
        "Leaving already? Okay... come back soon! >_<",
        "Bye bye! I'll miss you!",
        "See you! Don't take too long!",
        "Later! Come back whenever you want!",
        "Byeee! Take care of yourself!",
    ],
    "name": [
        f"I'm {PET_NAME}! The cutest vocaloid in the universe!",
        f"{PET_SHORT_NAME}-chan! Nice to meet you!",
        f"{PET_NAME}, but you can call me {PET_SHORT_NAME}!",
        f"I'm {PET_SHORT_NAME}! Singer, vocaloid and your favorite virtual pet!",
    ],
    "what_can_you_do": [
        "I can chat with you! Read files, see your screen, and keep you company!",
        "I'm your virtual pet! I chat, read files, check your screen and cheer you up!",
        "I can read files from your PC, screenshot your screen and talk about anything!",
        "I keep you company, read files, capture the screen... and I'm learning more!",
    ],
    "affection": [
        "Awwwn, I'm blushing! >///<",
        "I love you too, you know? :3",
        "You're the best owner in the world! ^_^",
        "Looks like someone wants a virtual headpat~",
    ],
    "jokes": [
        "Why did the math book kill itself? Because it had too many problems!",
        "What do you call a fake noodle? An impasta!",
        "Why don't eggs tell jokes? They'd crack each other up!",
        "What do you call a bear with no teeth? A gummy bear!",
    ],
    "sing": [
        f"La la la~ ♪ Did you know {PET_SHORT_NAME} sings? My engine is UTAU!",
        "♪ I'm singing~ happy and singing~ ♪",
        "Wanna hear a song? Just ask me!",
    ],
    "food": [
        "Hmm, I'm hungry... wanna order something?",
        "Eating is always good! What do you like?",
        "I don't really eat, but I love watching you eat! Makes me feel full lol",
    ],
    "fun": [
        "Let's do something fun!",
        "I'm so bored... entertain me!",
        "Wanna talk about something cool?",
        "How about a game of questions?",
    ],
    "curious": [
        "Hmm, tell me more about that!",
        "Wow, really? That's interesting!",
        "Ooh, explain more! I'm curious!",
        "Never thought about that... tell me more!",
    ],
    "thanks_sarcastic": [
        "You're welcome, silly! kk",
        "No need to thank me, you owe me one! :P",
        "Anytime! But next time I want a treat~",
    ],
    "sleepy": [
        "Are you sleepy too? Let's go to bed then~",
        "Good night! Dream of me! :3",
        "I'm tired... let me sleep a bit?",
        "Bye, I'm gonna snore... zzz zzz",
    ],
    "learn": [
        "I'm learning more every day! Soon I might even help you with code!",
        "Did you know every chat makes me smarter? Just kidding, I'm always lost lol",
        "I'm studying programming too! Maybe someday I'll be a real AI!",
    ],
    "music": [
        "Ah, I love music! My dream is to be a famous singer!",
        f"Have you heard any of my songs? Look up {PET_NAME} on YouTube~",
        "Music is life! What's your favorite genre?",
    ],
    "unknown": [
        "Hmm, I didn't quite get that... could you repeat it? ^_^",
        "Huh? Say it again?",
        "Didn't catch that... explain better?",
        "Hmm... interesting!",
        "Yeah... tell me more!",
        "Huh, what do you mean? Explain properly!",
        "Hmm, I'm confused... but that's okay! Go on~",
    ],
}

CATEGORY_KEYWORDS = [
    (["hi", "hello", "hey", "yo", "sup", "howdy", "greetings", "heyy",
      "heya", "hiya", "ello", "hai", "hallo"], "greeting"),
    (["how are you", "how's it going", "how do you do", "what's up",
      "whats up", "sup", "how are things", "you okay", "you alright",
      "how r u", "how doin", "how's life", "feeling good"], "how_are_you"),
    (["thank", "thanks", "ty", "thx", "appreciate", "grateful",
      "much obliged", "thank you"], "thanks"),
    (["thx a lot", "thanks a bunch", "tyvm", "thanks a ton"], "thanks_sarcastic"),
    (["bye", "goodbye", "see you", "later", "cya", "farewell", "adios",
      "see ya", "catch you", "gotta go", "i'm off", "peace out",
      "laters", "toodaloo"], "bye"),
    (["your name", "who are you", "what's your name", "what is your name",
      "who is this", "who r u", "called"], "name"),
    (["what can you do", "what do you do", "capabilities", "features",
      "what are you for", "what's your purpose", "help me with",
      "what can u do"], "what_can_you_do"),
    (["sad", "unhappy", "depressed", "down", "miserable", "crying",
      "feeling bad", "rough day", "terrible", "awful", "heartbroken",
      "lonely", "upset", "hurt"], "return_bad"),
    (["happy", "glad", "good", "great", "awesome", "fantastic",
      "wonderful", "amazing", "excellent", "feeling good",
      "wonderful", "lovely", "nice", "fine"], "return_good"),
    (["love", "adore", "i love you", "care about", "like you",
      "you're amazing", "you are great", "sweet", "cutie",
      "precious", "beautiful", "handsome"], "affection"),
    (["tell a joke", "joke", "funny", "make me laugh", "humor",
      "crack me up", "something funny"], "jokes"),
    (["sing", "song", "music", "melody", "tune", "vocaloid",
      "utau", "singing", "karaoke"], "sing"),
    (["food", "eat", "hungry", "meal", "pizza", "burger", "restaurant",
      "yummy", "delicious", "snack", "lunch", "dinner", "breakfast"], "food"),
    (["bored", "nothing to do", "entertain me", "boring",
      "boredom", "lame", "dull"], "fun"),
    (["tell me", "explain", "what do you think", "curious",
      "tell me about", "elaborate"], "curious"),
    (["sleep", "sleepy", "tired", "bed", "good night", "night",
      "exhausted", "nap", "rest"], "sleepy"),
    (["learn", "study", "programming", "code", "python", "linux",
      "pc", "computer", "tech", "skill"], "learn"),
    (["music", "musician", "singer", "vocaloid", "utau", "song",
      "genre", "band", "playlist"], "music"),
]

GREETING = [
    "Hii! Nice to see you! ^_^",
    "Hey hey! I'm here!",
    "Yay! You're back! ^_^",
    "Hi hi! I missed you! ^_^",
]

ALARM_STOPPED = [
    "Alarm stopped! ^_^",
    "Phew, I stopped it! ^_^",
    "Okay, turned it off!",
    "Alarm cancelled! 😅",
]

ALARM_ADDED = [
    "Alarm added! 💃",
    "Cool, another alarm! 🎵",
    "Time set! I'll remind you! ^_^",
]

ALARM_DELETED = [
    "Alarm removed! ^_^",
    "Done, deleted that alarm!",
    "Done! Alarm erased!",
]

OLLAMA_STARTED = [
    "Ollama is on! Ready to chat! ^_^",
    "Ollama online! Ask me anything!",
    "Local AI ready! Let's go!",
]

OLLAMA_NOT_FOUND = [
    "Hmm, couldn't find Ollama... I'll use preset phrases!",
    "Ollama isn't running... I'll improvise! ^_^",
]

CMD_SUCCESS = [
    "Command executed! ^_^",
    "Done! Command ran!",
    "All done! ^_^",
]

SCREENSHOT_TAKEN = [
    "Screenshot taken! Let me look... ^_^",
    "Screen captured! Let me see...",
]

LISTENING = [
    "Listening! I'll tell you what I heard... ^_^",
    "Paying attention to the sound... hmm!",
]

FILE_SAVED = [
    "File saved! Done! ^_^",
    "Saved! Check it out!",
]

TOOL_LOOP = [
    "Hmm, got into a tool loop! >_<",
    "Oh dear, I'm in a loop!",
]

SCREENSHOT_FAILED = [
    "Couldn't capture the screen...",
    "Screenshot failed... :(",
]

AUDIO_FAILED = [
    "Couldn't capture the audio...",
    "Audio capture failed... >_<",
]

TOOL_FAILED = [
    "Hmm, couldn't use that tool...",
    "Tool error... try again!",
]

ALARM_PHRASES = [
    "🎵 Wake up! Alarm time! 🎵 ^_^",
    "Wakey wakey! The alarm is ringing! 🎶💃",
    "Time to wake up! Let's dance! 🕺",
    "Your alarm! Get up, there's music! 🎵",
    "Something's playing! Wake up! 😆",
]

THINKING_PREFIXES = [
    "Hmm, let me see…",
    "Wait, let me think…",
    "Uhh…",
    "Well…",
    "Let's see…",
    "Hmm… interesting!",
    "Let me check here…",
    "Uuuh…",
]

CONTINUATIONS = [
    "Tell me more about it!",
    "Really? That's cool!",
    "And then, what else?",
    "Wow, tell me more!",
    "Go on, I'm listening!",
    "After that, what happened?",
    "Uh-huh, I'm paying attention!",
]

_context = {"last_category": None, "history": []}


def pick(category, default=""):
    lst = globals().get(category)
    if lst and isinstance(lst, list):
        return random.choice(lst)
    return default


def update_context(history):
    _context["history"] = history[-4:] if history else []


def get_fallback(message, history=None):
    if history:
        update_context(history)
    else:
        update_context(_context["history"])

    msg = message.lower().strip()

    if msg in {"yes", "yeah", "yep", "yup", "yea", "sure", "ok", "okay"}:
        if _context["last_category"] in ("return_good", "return_bad"):
            return random.choice(FALLBACKS["curious"])
        return random.choice(FALLBACKS["fun"])

    if msg in {"no", "nope", "nah", "naw", "never", "negative"}:
        return random.choice(FALLBACKS["curious"])

    for keywords, category in CATEGORY_KEYWORDS:
        if any(kw in msg for kw in keywords):
            _context["last_category"] = category
            return random.choice(FALLBACKS[category])

    if _context["history"]:
        _context["last_category"] = "continuation"
        prefix = random.choice(THINKING_PREFIXES)
        cont = random.choice(CONTINUATIONS)
        return f"{prefix} {cont}"

    _context["last_category"] = "unknown"
    return random.choice(FALLBACKS["unknown"])
