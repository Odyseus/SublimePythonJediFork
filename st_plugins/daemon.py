#!/usr/bin/python3
# -*- coding: utf-8 -*-
from concurrent.futures import ThreadPoolExecutor

from collections import defaultdict
from functools import partial
from functools import wraps

import jedi

from jedi.api import environment

import sublime


from . import logger
from . import settings
from .facade import JediFacade
from python_utils.sublime_text_utils import events
from python_utils.sublime_text_utils import queue
from python_utils.sublime_text_utils import utils

DAEMONS = defaultdict(dict)  # per window
REQUESTORS = defaultdict(dict)  # per window
_plugin_id = "SublimePythonJedi-{}"


@events.on("settings_changed")
def on_settings_changed(settings, **kwargs):
    if any((settings.has_changed("python_virtualenv"),
            settings.has_changed("python_interpreter"),
            settings.has_changed("python_package_paths"))):
        DAEMONS.clear()
        REQUESTORS.clear()


def _prepare_request_data(view, location):
    if location is None:
        location = view.sel()[0].begin()
    current_line, current_column = view.rowcol(location)

    filename = view.file_name() or ""
    source = view.substr(sublime.Region(0, view.size()))
    return filename, source, current_line, current_column


def _get_daemon(view):
    window_id = view.window().id()
    if window_id not in DAEMONS:
        DAEMONS[window_id] = Daemon(view, settings=settings)
    return DAEMONS[window_id]


def _get_requestor(view):
    window_id = view.window().id()
    if window_id not in REQUESTORS:
        REQUESTORS[window_id] = ThreadPoolExecutor(max_workers=1)
    return REQUESTORS[window_id]


def ask_daemon_sync(view, ask_type, ask_kwargs, location=None):
    """Jedi sync request shortcut.

    Parameters
    ----------
    view : sublime.View
        A Sublime Text view.
    ask_type : str
        Description
    ask_kwargs : dict
        Description
    location : int, int, None, optional
        Description

    Returns
    -------
    TYPE
        Description
    """
    daemon = _get_daemon(view)
    return daemon.request(
        ask_type,
        ask_kwargs or {},
        *_prepare_request_data(view, location))


def ask_daemon(view, callback, ask_type, ask_kwargs=None, location=None):
    """Jedi async request shortcut.

    Parameters
    ----------
    view : sublime.View
        A Sublime Text view.
    callback : TYPE
        Description
    ask_type : str
        Description
    ask_kwargs : dict, None, optional
        Description
    location : int, int, None, optional
        Description
    """
    window_id = view.window().id()

    def _async_summon():
        answer = ask_daemon_sync(view, ask_type, ask_kwargs, location)
        run_in_active_view(window_id)(callback)(answer)

    if callback:
        queue.debounce(
            partial(sublime.set_timeout_async, _async_summon, 0),
            delay=settings.get("completion_timeout", 10),
            key=_plugin_id.format("debounce")
        )
        # sublime.set_timeout_async(_async_summon, 0)


def run_in_active_view(window_id):
    """Run function in active ST active view for binded window.

    sublime.View instance would be passed as first parameter to function.

    Parameters
    ----------
    window_id : TYPE
        Description

    Returns
    -------
    TYPE
        Description
    """
    def _decorator(func):
        @wraps(func)
        def _wrapper(*args, **kwargs):
            for window in sublime.windows():
                if window.id() == window_id:
                    return func(window.active_view(), *args, **kwargs)

            logger.info(
                "Unable to find a window where function must be called."
            )
        return _wrapper
    return _decorator


class Daemon():
    """Jedi Requester.

    Attributes
    ----------
    complete_funcargs : TYPE
        Description
    env : TYPE
        Description
    sys_path : TYPE
        Description
    """

    def __init__(self, view, settings):
        """Prepare to call daemon.

        :type settings: dict

        Parameters
        ----------
        settings : TYPE
            Description
        """
        view_context = utils.get_view_context(view)
        python_virtualenv = settings.get("python_virtualenv").get(sublime.platform(), "")
        python_interpreter = settings.get("python_interpreter").get(sublime.platform(), "")

        if python_virtualenv:
            logger.debug("Jedi Environment: {0}".format(python_virtualenv))
            self.env = environment.create_environment(
                utils.substitute_variables(view_context, python_virtualenv),
                safe=False
            )
        elif python_interpreter:
            logger.debug("Jedi Environment: {0}".format(python_interpreter))
            self.env = environment.create_environment(
                utils.substitute_variables(view_context, python_interpreter),
                safe=False
            )
        else:
            self.env = jedi.get_default_environment()

        self.sys_path = self.env.get_sys_path()
        # prepare the extra packages if any
        extra_packages = settings.get("python_package_paths").get(sublime.platform(), [])

        if extra_packages:
            logger.debug("Jedi Extra Packages: {0}".format(extra_packages))
            self.sys_path = utils.substitute_variables(
                view_context, extra_packages) + self.sys_path

    def request(
            self,
            request_type,
            request_kwargs,
            filename,
            source,
            line,
            column):
        """Send request to daemon process.

        Parameters
        ----------
        request_type : TYPE
            Description
        request_kwargs : TYPE
            Description
        filename : TYPE
            Description
        source : TYPE
            Description
        line : TYPE
            Description
        column : TYPE
            Description

        Returns
        -------
        TYPE
            Description
        """
        logger.info("Sending request to daemon for '{0}'".format(request_type))
        logger.debug((request_type, request_kwargs, filename, line, column))

        facade = JediFacade(
            env=self.env,
            complete_funcargs=settings.get("auto_complete_function_params"),
            source=source,
            line=line + 1,
            column=column,
            filename=filename,
            sys_path=self.sys_path,
        )

        answer = facade.get(request_type, request_kwargs)
        logger.debug("Answer: {0}".format(answer))

        return answer


if __name__ == "__main__":
    pass
