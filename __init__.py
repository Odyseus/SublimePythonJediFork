#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import sys

# Add dependencies on package initialization.
sys.path.append(os.path.join(os.path.dirname(__file__), "dependencies"))

from python_utils.sublime_text_utils import events

# NOTE: Import last.
from .st_plugins import SublimePythonJediForkToggleLoggingLevelCommand    # noqa
from .st_plugins.completion import *                                      # noqa


def plugin_loaded():
    """On plugin loaded callback.
    """
    events.broadcast("plugin_loaded")


def plugin_unloaded():
    """On plugin unloaded.
    """
    events.broadcast("plugin_unloaded")


if __name__ == "__main__":
    pass
