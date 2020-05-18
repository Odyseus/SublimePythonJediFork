#!/usr/bin/python3
# -*- coding: utf-8 -*-
from itertools import chain
from operator import itemgetter

import jedi

from jedi.api.completion import Parameter

from . import logger
from . import settings
from . import unique


def format_completion(complete):
    """Returns a tuple of the string that would be visible in
    the completion dialogue and the completion word

    Parameters
    ----------
    complete : jedi.api_classes.Completion
        Description

    Returns
    -------
    tuple
        Description
    """
    return (complete.name + "\t" + complete.type, complete.name)


def get_function_parameters(call_signature, with_keywords=True):
    """Return list function parameters, prepared for sublime completion.

    Tuple contains parameter name and default value

    Parameters list excludes: self, *args and **kwargs parameters

    Parameters
    ----------
    call_signature : jedi.api.classes.CallSignature
        Description
    with_keywords : bool, optional
        Description

    Returns
    -------
    TYPE
        Description
    """
    if not call_signature:
        return []

    params = []
    for param in call_signature.params:
        logger.debug("Parameter: {0}".format((
            type(param._name),
            param._name.get_kind(),
            param._name.string_name,
            param.description,
        )))

        # print call sign looks like: "value, ..., sep, end, file, flush"
        # and all params after "..." are non required and not a keywords
        if not with_keywords and param.name == "...":
            break

        if (not param.name or
                param.name in ("self", "...") or
                param._name.get_kind() == Parameter.VAR_POSITIONAL or
                param._name.get_kind() == Parameter.VAR_KEYWORD):
            continue

        param_description = param.description.replace("param ", "")
        is_keyword = "=" in param_description

        if is_keyword and with_keywords:
            default_value = param_description.rsplit("=", 1)[1].lstrip()
            params.append((param.name, default_value))
        elif is_keyword and not with_keywords:
            continue
        else:
            params.append((param.name, None))

    return params


class JediFacade():
    """Facade to call Jedi API.


     Action       | Method
    ===============================
     autocomplete | get_autocomplete
    -------------------------------
     funcargs     | get_funcargs
    --------------------------------

    Attributes
    ----------
    auto_complete_function_params : TYPE
        Description
    script : TYPE
        Description
    """

    def __init__(
            self,
            env,
            complete_funcargs,
            source,
            line,
            column,
            filename="",
            encoding="utf-8",
            sys_path=None):
        filename = filename or None
        self.script = jedi.Script(
            source=source,
            line=line,
            column=column,
            path=filename,
            encoding=encoding,
            environment=env,
            sys_path=sys_path,
        )

    def get(self, _action, *args, **kwargs):
        """Action dispatcher.

        Parameters
        ----------
        _action : TYPE
            Description
        *args
            Description
        **kwargs
            Description

        Returns
        -------
        TYPE
            Description
        """
        try:
            return getattr(self, "get_" + _action)(*args, **kwargs)
        except Exception:
            logger.exception("`JediFacade.get_{0}` failed".format(_action))

    def get_funcargs(self, *args, **kwargs):
        """Complete callable object parameters with Jedi.

        Parameters
        ----------
        *args
            Description
        **kwargs
            Description

        Returns
        -------
        TYPE
            Description
        """
        complete_all = settings.get("auto_complete_function_params", "all") == "all"
        call_parameters = self._complete_call_assigments(
            with_keywords=complete_all,
            with_values=complete_all
        )
        return ", ".join(p[1] for p in call_parameters)

    def get_autocomplete(self, *args, **kwargs):
        """Jedi completion.

        Parameters
        ----------
        *args
            Description
        **kwargs
            Description

        Returns
        -------
        TYPE
            Description
        """
        completions = chain(
            self._complete_call_assigments(with_keywords=True,
                                           with_values=True),
            self._completion()
        )
        return list(unique(completions, itemgetter(0)))

    def _completion(self):
        """Regular completions.

        :rtype: list of (str, str)

        Yields
        ------
        TYPE
            Description
        """
        completions = self.script.completions(fuzzy=settings.get("fuzzy_jedi_completions", False))
        for complete in completions:
            yield format_completion(complete)

    def _complete_call_assigments(
            self,
            with_keywords=True,
            with_values=True):
        """Get function or class parameters and build Sublime Snippet string
        for completion

        :rtype: str

        Parameters
        ----------
        with_keywords : bool, optional
            Description
        with_values : bool, optional
            Description

        Yields
        ------
        TYPE
            Description
        """
        try:
            call_definition = self.script.call_signatures()[0]
        except IndexError:
            # probably not a function/class call
            return

        parameters = get_function_parameters(call_definition, with_keywords)
        for index, parameter in enumerate(parameters):
            name, value = parameter

            if value is not None and with_values:
                yield (name + "\tparam",
                       "%s=${%d:%s}" % (name, index + 1, value))
            else:
                yield (name + "\tparam",
                       "${%d:%s}" % (index + 1, name))


if __name__ == "__main__":
    pass
