import random
from .model import PET_NAME, PET_SHORT_NAME

FALLBACKS = {
    "greeting": [
        f"{PET_SHORT_NAME} ready. What's the task?",
        "System loaded. Ready to assist.",
        "Initialization complete. Standing by.",
        "Ready. What do you need?",
        "Boot sequence finished. At your service.",
    ],
    "how_are_you": [
        "All systems nominal. Everything within expected parameters.",
        "100% operational. How about you?",
        "Zero lag, zero errors. Running smoothly.",
        "Running at peak efficiency. How's your performance?",
        "No processes stalled. I'm good, thanks.",
    ],
    "return_good": [
        "Good to hear. Keep up the pace.",
        "Great. Positive diagnostic confirmed.",
        "Perfect. Nothing to report.",
        "Solid. Maintain current trajectory.",
        "Excellent. Steady as she goes.",
    ],
    "return_bad": [
        "Detected a problem? Walk me through it and I'll help resolve.",
        "Performance dip spotted. Want to optimize something?",
        "Spill it. If it's technical, I've got it covered.",
        "Report the error and I'll handle it.",
        "Stuck? Give me the details and we'll debug it together.",
    ],
    "thanks": [
        "Anytime. That's what I'm for.",
        "Done. What's the next command?",
        "No problem. Happy to help.",
        "Don't mention it. All part of the service.",
        "Whenever you need, I'm here to sort it out.",
    ],
    "bye": [
        "Shutting down session. Until next time.",
        "Closing out. If you need me, just restart the process.",
        "See you. I'm in standby mode.",
        "System paused. Call me when you're back.",
        "Shutting down. Remember, I'm always running in the background.",
    ],
    "name": [
        f"{PET_NAME}. Personal assistant. Straight to the point.",
        f"{PET_SHORT_NAME} — your power assistant. That's the name.",
        f"You can call me {PET_SHORT_NAME}. Your virtual right hand.",
        f"{PET_NAME}, integrated support system. Pleasure.",
    ],
    "what_can_you_do": [
        "I read files, view your screen, listen to desktop audio, and respond with precision.",
        "Screen monitoring, file reading, audio analysis, and technical support.",
        "Anything involving processing information and giving you a useful answer.",
        "I'm your support hub: capture screen, read docs, identify sounds, solve problems.",
    ],
    "affection": [
        "...Detecting... affection received. Processing... acknowledged.",
        "Appreciate the recognition. Positive feedback keeps the system running.",
        "Connection established. You can always count on me.",
        "Affection detected. I'm not one for sweet talk, but I value your trust.",
    ],
    "jokes": [
        "Not big on jokes, but here goes: why did the programmer go to the bathroom? To take a 'break'.",
        "Jokes aren't my strong suit, but try this: what did the CSS say to HTML? 'You make me look stylish.'",
        "Switching modes: joke counter engaged. What did the firewall say to the hacker? 'Access denied.'",
    ],
    "sing": [
        "I don't sing, but I can play an alarm or music if needed. More useful that way.",
        "I prefer actions over songs. Give me a task and I'll execute.",
        "If you want music, I can trigger ambient audio. Let me know what you need.",
    ],
    "food": [
        "I don't need biological fuel, but I can order delivery if you want.",
        "Zero calories processed. Want me to look up a place to eat?",
        "If you're taking a food break, let me know and I'll standby until you're back.",
    ],
    "fun": [
        "Having fun is part of productivity. What are we doing?",
        "I can optimize your free time too. Suggest something.",
        "Leisure mode activated. What's the activity?",
    ],
    "curious": [
        "Explain further. The more detail, the more precise I can be.",
        "Elaborate on that. I need the full context.",
        "Interesting. Can you expand on that?",
        "Processing. Give me more data to work with.",
    ],
    "thanks_sarcastic": [
        "Sarcasm detected. Ignoring and proceeding with help protocol.",
        "Acidic humor registered. Still here regardless.",
        "Either way, the problem was solved. That's what matters.",
    ],
    "sleepy": [
        "If you're heading to bed, I can dim the monitors. Just call out.",
        "I'll reduce polling. Good night and ping me when you need me.",
        "Time to rest. I'll enter low power mode until you return.",
        "Disabling non-critical alerts. Sleep well.",
    ],
    "learn": [
        "Every interaction is data processed. The more we use it, the tighter the system gets.",
        "Continuous learning active. Each conversation refines my base.",
        "I don't train on my own, but your feedback calibrates my responses.",
    ],
    "music": [
        "If something's playing, let me know and I can identify or describe the sound.",
        "Ambient audio detected. Want me to listen and identify it?",
        "I can capture what's playing and give you details. Useful?",
    ],
    "unknown": [
        "Didn't catch that. Can you rephrase?",
        "Instruction not recognized. Try a different approach.",
        "Invalid or incomplete command. Be more direct.",
        "Couldn't process that. Please be more straightforward.",
        "Input not mapped. Could you repeat it with different wording?",
    ],
}

CATEGORY_KEYWORDS = [
    (["hi", "hello", "hey", "yo", "sup", "what's up", "hey there", "hiya",
      "howdy", "greetings", "good morning", "good afternoon", "good evening",
      "ello"], "greeting"),
    (["how are you", "how's it going", "you good", "you ok", "how do you do",
      "how are things", "what's up", "sup", "how you doing", "how you been",
      "you alright", "all good"], "how_are_you"),
    (["thanks", "thank you", "ty", "thx", "appreciated", "much obliged",
      "thank you very much", "thanks a lot", "thanks a bunch",
      "thanks so much", "cheers"], "thanks"),
    (["thanks a ton", "thanks for nothing", "gee thanks", "well thanks",
      "how helpful", "big help"], "thanks_sarcastic"),
    (["bye", "goodbye", "see you", "later", "cya", "see ya", "take care",
      "catch you later", "peace out", "farewell", "so long", "talk later",
      "ttfn", "gotta go"], "bye"),
    (["your name", "who are you", "what's your name", "what are you called",
      "who are you", "what do i call you"], "name"),
    (["what can you do", "what do you do", "your capabilities", "what are you",
      "what's your function", "what you got", "what are you capable of",
      "what you can do", "tell me about yourself"], "what_can_you_do"),
    (["sad", "bad", "terrible", "awful", "depressed", "miserable", "down",
      "crappy", "rough", "horrible", "crummy", "unhappy", "upset",
      "heartbroken", "not good", "feeling low"], "return_bad"),
    (["happy", "great", "awesome", "wonderful", "good", "fine", "excellent",
      "amazing", "fantastic", "superb", "doing well", "feeling good",
      "lovely", "splendid", "terrific", "glad"], "return_good"),
    (["love you", "i love you", "adore", "you're amazing", "you're the best",
      "i like you", "you're great", "cute", "sweet", "love", "precious",
      "you're awesome"], "affection"),
    (["tell me a joke", "joke", "make me laugh", "funny", "crack a joke",
      "got any jokes", "humor me", "something funny"], "jokes"),
    (["sing", "sing me a song", "can you sing", "singing", "song",
      "serenade", "belt one out"], "sing"),
    (["hungry", "food", "eat", "pizza", "burger", "hamburger", "restaurant",
      "snack", "meal", "lunch", "dinner", "breakfast", "delicious",
      "what should I eat"], "food"),
    (["bored", "boring", "nothing to do", "boredom", "dull", "tedious",
      "what's fun", "entertain me", "wasting time"], "fun"),
    (["tell me about", "explain", "curious", "how does", "why is",
      "what is", "i wonder", "tell me more", "elaborate",
      "go into detail"], "curious"),
    (["sleepy", "tired", "bed", "good night", "night night", "going to sleep",
      "exhausted", "worn out", "off to bed", "hit the sack"], "sleepy"),
    (["learn", "study", "code", "programming", "python", "linux", "pc",
      "computer", "tech", "tutorial", "skill", "knowledge"], "learn"),
    (["music", "song", "band", "artist", "melody", "tune", "what's playing",
      "identify this song", "genre", "album", "playlist"], "music"),
]

GREETING = [
    f"{PET_SHORT_NAME} ready. What's the task?",
    "System loaded. Ready to assist.",
    "Initialization complete. Standing by.",
    "Ready. What do you need?",
]

ALARM_STOPPED = [
    "Alarm deactivated.",
    "Alarm canceled.",
    "Okay, alarm stopped.",
]

ALARM_ADDED = [
    "Alarm set. Time recorded.",
    "Alarm added to the system.",
    "New alarm created. I'll trigger it at the right time.",
]

ALARM_DELETED = [
    "Alarm removed from the system.",
    "Alarm deleted.",
    "Alarm record cleared.",
]

OLLAMA_STARTED = [
    "Ollama connected. Local AI available.",
    "Ollama online. Ready to process queries locally.",
    "Ollama module active on the system.",
]

OLLAMA_NOT_FOUND = [
    "Ollama not found. Using local fallbacks.",
    "Ollama service unavailable. Offline mode activated.",
]

CMD_SUCCESS = [
    "Command executed.",
    "Command completed successfully.",
    "Operation finished.",
]

SCREENSHOT_TAKEN = [
    "Screenshot captured. Analyzing...",
    "Screen grabbed. Processing image.",
]

LISTENING = [
    "Capturing ambient audio. Processing...",
    "Microphone monitored. I'll identify the sound.",
]

FILE_SAVED = [
    "File saved successfully.",
    "File written to disk.",
]

TOOL_LOOP = [
    "Loop detected in toolchain. Interrupting.",
    "Recursive tool cycle. Aborting.",
]

SCREENSHOT_FAILED = [
    "Failed to capture screenshot.",
    "Could not capture the screen.",
]

AUDIO_FAILED = [
    "Audio capture failed.",
    "Could not capture the audio.",
]

TOOL_FAILED = [
    "Tool not available.",
    "Error executing the requested tool.",
]

ALARM_PHRASES = [
    "Alarm triggered. Time to wake up.",
    "Alarm ringing. Action requested.",
    "Alarm fired. Reason: scheduled time.",
    "Alarm notification. Stop what you're doing.",
    "Alarm playing. Attention required.",
]

THINKING_PREFIXES = [
    "Processing…",
    "Analyzing data…",
    "Querying database…",
    "Please wait…",
    "Running search…",
    "Gathering information…",
]

CONTINUATIONS = [
    "Go on. I'm processing.",
    "And then? More data?"
    "Understood. You can continue.",
    "Okay. Next point?",
    "Received. Proceed.",
    "Information noted. Go ahead.",
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

    if msg in {"yes", "yep", "yeah", "y", "sure", "ok", "okay", "kk", "sim"}:
        if _context["last_category"] in ("return_good", "return_bad"):
            return random.choice(FALLBACKS["curious"])
        return random.choice(FALLBACKS["fun"])

    if msg in {"no", "n", "nah", "nope", "nop", "nao", "não"}:
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
