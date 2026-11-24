"""Pfade und einmalige Uebernahme der alten ``noah2games``-Daten.

Beim Umbenennen auf PolyPanel bleiben Instanzen und Einstellungen erhalten: liegt noch
``~/.config/noah2games`` herum und ``~/.config/polypanel`` existiert nicht, wird das alte
Verzeichnis beim ersten Start umbenannt (gleiche Partition) bzw. kopiert. Dasselbe gilt
fuer die Instanzordner ``~/noah2games-instances`` -> ``~/polypanel-instances``.
"""
from __future__ import annotations

import os
import shutil

ALT_CONF = os.path.expanduser("~/.config/noah2games")
CONF_DIR = os.path.expanduser(os.environ.get("POLYPANEL_CONFIG", "~/.config/polypanel"))
TOKEN_PATH = os.path.join(CONF_DIR, "token")
# Fertige Adresse inklusive Token - praktisch, wenn die Konsole laengst gescrollt ist.
URL_PATH = os.path.join(CONF_DIR, "url")
SETTINGS_PATH = os.path.join(CONF_DIR, "settings.json")
CACHE_DIR = os.path.join(CONF_DIR, "cache")

ALT_INSTANCES = os.path.expanduser("~/noah2games-instances")
INSTANCES_DIR = os.path.expanduser(os.environ.get("POLYPANEL_INSTANCES", "~/polypanel-instances"))


def _uebernehmen(alt: str, neu: str) -> None:
    if os.path.isdir(neu) or not os.path.isdir(alt):
        return
    try:
        os.makedirs(os.path.dirname(neu), exist_ok=True)
        shutil.move(alt, neu)               # gleiche Partition: reines Umbenennen
    except OSError:
        try:
            shutil.copytree(alt, neu, dirs_exist_ok=True)
        except OSError:
            pass


def migriere() -> str:
    _uebernehmen(ALT_CONF, CONF_DIR)
    _uebernehmen(ALT_INSTANCES, INSTANCES_DIR)
    return CONF_DIR


migriere()
