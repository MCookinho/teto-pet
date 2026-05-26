import sys
from datetime import datetime


def log(msg, *args):
    ts = datetime.now().strftime("%H:%M:%S")
    if args:
        msg = msg % args
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)
