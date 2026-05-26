"""
Logging utility for Mate Helper.

Provides a single log() function that timestamp-prints to stderr,
used throughout the application for debug and error messages.
"""

import sys
from datetime import datetime


def log(msg, *args):
    """Print a timestamped message to stderr, with optional %-formatting."""
    ts = datetime.now().strftime("%H:%M:%S")
    if args:
        msg = msg % args
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)
