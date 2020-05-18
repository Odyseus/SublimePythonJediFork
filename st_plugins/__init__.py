#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os

root_folder = os.path.realpath(os.path.abspath(os.path.join(
    os.path.normpath(os.path.join(os.path.dirname(__file__), os.pardir)))))

import sublime_plugin

from python_utils import log_system
from python_utils.sublime_text_utils import events
from python_utils.sublime_text_utils import logger as logger_utils
from python_utils.sublime_text_utils import settings as settings_utils


plugin_name = "SublimePythonJediFork"
_log_file = log_system.generate_log_path(storage_dir=os.path.join(root_folder, "tmp", "logs"),
                                         prefix="LOG")
logger = logger_utils.SublimeLogger(logger_name=plugin_name, log_file=_log_file)
settings = settings_utils.Settings(name_space=plugin_name, logger=logger)


def set_logging_level():
    try:
        logger.set_logging_level(logging_level=settings.get("logging_level", "ERROR"))
    except Exception as err:
        print(err)


@events.on("plugin_loaded")
def on_plugin_loaded():
    """On plugin loaded.
    """
    settings.load()
    set_logging_level()


@events.on("plugin_unloaded")
def on_plugin_unloaded():
    settings.unobserve()
    events.off(on_settings_changed)


@events.on("settings_changed")
def on_settings_changed(settings, **kwargs):
    if settings.has_changed("logging_level"):
        set_logging_level()


def is_desired_scope(view):
    if view and len(view.sel()) > 0:
        return len(view.sel()) > 0 and bool(
            view.score_selector(view.sel()[0].a,
                                settings.get("commands_scope", "source.python - string - comment"))
        )
    else:
        return False


def is_repl(view):
    """Check if a view is a REPL."""
    return view.settings().get("repl", False)


def unique(items, pred=lambda x: x):
    stack = set()

    for i in items:
        calculated = pred(i)
        if calculated in stack:
            continue
        stack.add(calculated)
        yield i


class SublimePythonJediForkToggleLoggingLevelCommand(settings_utils.SettingsToggleList,
                                                     sublime_plugin.WindowCommand):
    _ody_key = "logging_level"
    _ody_settings = settings
    _ody_description = "Logging level - %s"
    _ody_values_list = ["ERROR", "INFO", "DEBUG"]


if __name__ == "__main__":
    pass
