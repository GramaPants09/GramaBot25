"""Agent tool package.

Importing this package registers every built-in tool by importing the handler
modules (each uses the ``@tool`` decorator from ``registry`` at import time).
Handler modules are added in Task 6.
"""
from . import registry  # noqa: F401

# Handler modules register their tools on import. Import failures of any single
# group should not prevent the others from loading.
for _mod in (
    "music_tools",
    "voice_tools",
    "aura_tools",
    "mod_tools",
    "openclaw_tools",
    "search_tools",
):
    try:
        __import__(f"{__name__}.{_mod}")
    except Exception as _e:  # pragma: no cover - handler modules arrive in Task 6
        import logging

        logging.getLogger(__name__).debug("tool module %s not loaded: %s", _mod, _e)
