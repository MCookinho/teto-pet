#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk
from teto_pet.app import TetoPet


def main():
    app = TetoPet()
    Gtk.main()


if __name__ == "__main__":
    main()
