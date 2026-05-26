"""
Entry point for Mate Helper (Teto Pet) desktop pet application.

Bootstraps the Python path, initialises GTK, and launches the main
application window via TetoPet.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk
from desktop_pet.app import TetoPet


def main():
    app = TetoPet()
    Gtk.main()


if __name__ == "__main__":
    main()
