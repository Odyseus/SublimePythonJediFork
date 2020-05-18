#!/usr/bin/python3
# -*- coding: utf-8 -*-
import re

import sublime
import sublime_plugin

from . import is_desired_scope
from . import is_repl
from . import logger
from . import settings
from .daemon import ask_daemon

__all__ = [
    "SublimePythonJediForkCompletions",
    "SublimePythonJediForkParamsAutocompleteCommand"
]

_plugin_id = "SublimePythonJedi-{}"
_following_chars = {"\r", "\n", "\t", " ", ")", "]", ";", "}", "\x00"}
_plugin_only_completion = (sublime.INHIBIT_WORD_COMPLETIONS |
                           sublime.INHIBIT_EXPLICIT_COMPLETIONS)


class SublimePythonJediForkParamsAutocompleteCommand(sublime_plugin.TextCommand):
    """
    Function / Class constructor autocompletion command
    """

    def run(self, edit, characters="("):
        """
        Insert completion character, and complete function parameters
        if possible

        :param edit: sublime.Edit
        :param characters: str
        """
        self._insert_characters(edit, characters, ")")

        if self.view and len(self.view.sel()) and settings.get("auto_complete_function_params"):
            ask_daemon(
                self.view,
                self.show_template,
                "funcargs",
                location=self.view.sel()[0].end()
            )
            # queue_utils.debounce(
            #     partial(
            #         ask_daemon,
            #         self.view,
            #         self.show_template,
            #         "funcargs",
            #         location=self.view.sel()[0].end()),
            #     delay=settings.get("completion_timeout", 10),
            #     key=_plugin_id.format("funcargs")
            # )

    @property
    def auto_match_enabled(self):
        """ check if sublime closes parenthesis automaticly """
        return self.view.settings().get("auto_match_enabled", True)

    def _insert_characters(self, edit, open_pair, close_pair):
        """
        Insert autocomplete character with closed pair
        and update selection regions

        If sublime option `auto_match_enabled` turned on, next behavior have to be:

            when none selection

            `( => (<caret>)`
            `<caret>1 => ( => (<caret>1`

            when text selected

            `text => (text<caret>)`

        In other case:

            when none selection

            `( => (<caret>`

            when text selected

            `text => (<caret>`


        :param edit: sublime.Edit
        :param characters: str
        """
        regions = [a for a in self.view.sel()]
        self.view.sel().clear()

        for region in reversed(regions):
            next_char = self.view.substr(region.begin())
            # replace null byte to prevent error
            next_char = next_char.replace("\x00", "\n")
            logger.debug("Next characters: {0}".format(next_char))

            following_text = next_char not in _following_chars
            logger.debug("Following text: {0}".format(following_text))

            if self.auto_match_enabled:
                self.view.insert(edit, region.begin(), open_pair)
                position = region.end() + 1

                # IF selection is non-zero
                # OR after cursor no any text and selection size is zero
                # THEN insert closing pair
                if region.size() > 0 or not following_text and region.size() == 0:
                    self.view.insert(edit, region.end() + 1, close_pair)
                    position += (len(open_pair) - 1)
            else:
                self.view.replace(edit, region, open_pair)
                position = region.begin() + len(open_pair)

            self.view.sel().add(sublime.Region(position, position))

    def show_template(self, view, template):
        view.run_command("insert_snippet", {"contents": template})


class SublimePythonJediForkCompletions(sublime_plugin.ViewEventListener):
    """Sublime Text autocompletion integration."""

    _completions = []
    _previous_completions = []
    _last_location = None

    def __enabled(self):
        if sublime.active_window().active_view().id() != self.view.id():
            return False

        if is_repl(self.view) and not settings.get("enable_in_sublime_repl"):
            logger.debug("JEDI does not complete in SublimeREPL views.")
            return False

        if not is_desired_scope(self.view):
            logger.debug("JEDI completes only the following scopes:")
            logger.debug(settings.get("commands_scope", "source.python - string - comment"))
            return False

        return True

    def on_query_completions(self, prefix, locations):
        """Sublime autocomplete event handler.

        Get completions depends on current cursor position and return
        them as list of ("possible completion", "completion type")

        :param prefix: string for completions
        :type prefix: basestring
        :param locations: offset from beginning
        :type locations: int

        :return: list of tuple(str, str)
        """
        if not self.__enabled():
            return None

        logger.info("JEDI completions triggered.")

        if settings.get("only_complete_after_regex"):
            previous_char = self.view.substr(locations[0] - 1)
            if not re.match(settings.get("only_complete_after_regex"), previous_char):
                return None

        if self._last_location != locations[0]:
            self._last_location = locations[0]
            ask_daemon(
                self.view,
                self._receive_completions,
                "autocomplete",
                location=locations[0]
            )
            # queue_utils.debounce(
            #     partial(
            #         ask_daemon,
            #         self.view,
            #         self._receive_completions,
            #         "autocomplete",
            #         location=locations[0]),
            #     delay=settings.get("completion_timeout", 10),
            #     key=_plugin_id.format("autocomplete")
            # )
            return [], _plugin_only_completion

        if self._last_location == locations[0] and self._completions:
            self._last_location = None
            return self._completions

    def _receive_completions(self, view, completions):
        if not completions:
            return

        logger.debug("Completions: {0}".format(completions))

        self._previous_completions = self._completions
        self._completions = completions

        if (completions and (
                not view.is_auto_complete_visible() or
                not self._is_completions_subset())):
            only_jedi_completion = (
                settings.get("sublime_completions_visibility", "default")
                in ("default", "jedi")
            )
            view.run_command("hide_auto_complete")
            view.run_command("auto_complete", {
                "api_completions_only": only_jedi_completion,
                "disable_auto_insert": True,
                "next_completion_if_showing": False
            })

    def _is_completions_subset(self):
        completions = {completion for _, completion in self._completions}
        previous = {completion for _, completion in self._previous_completions}
        return completions.issubset(previous)


if __name__ == "__main__":
    pass
