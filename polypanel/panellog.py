"""Eigenes Panel-Log.

Das System-Journal kann der Panel-Benutzer nicht lesen (dort steht der Dienst unter
root). Damit Fehlermeldungen trotzdem Panel-Logs enthalten, schreibt das Panel seine
wichtigsten Ereignisse zusaetzlich in ``~/.config/<panel>/panel.log`` (wird bei 1 MB
weiter gedreht nach ``panel.log.1``).
"""
from __future__ import annotations

import os
import time

from .paths import CONF_DIR

PATH = os.path.join(CONF_DIR, "panel.log")
MAX_BYTES = 1_000_000


def write(text: str) -> None:
    """Zeile ins Panel-Log schreiben - Fehler hier duerfen nie stoeren."""
    zeile = " ".join(str(text).split())
    if not zeile:
        return
    try:
        os.makedirs(CONF_DIR, exist_ok=True)
        if os.path.exists(PATH) and os.path.getsize(PATH) > MAX_BYTES:
            os.replace(PATH, PATH + ".1")
        with open(PATH, "a", encoding="utf-8") as fh:
            fh.write("%s  %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), zeile))
    except OSError:
        pass


def tail(zeilen: int = 40) -> str:
    """Letzte Zeilen des Panel-Logs."""
    try:
        with open(PATH, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            groesse = fh.tell()
            fh.seek(max(0, groesse - 32_000))
            roh = fh.read().decode("utf-8", "replace")
    except OSError:
        return ""
    return "\n".join(roh.splitlines()[-zeilen:])
