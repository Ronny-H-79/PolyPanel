"""Kuratierte RCON-Befehle fuer die Klick-Buttons der Weboberflaeche.

Felder:
  id      Kurzname (API)
  label   Beschriftung im UI
  group   Gruppierung im UI
  cmd     Befehl; {name} wird aus den Argumenten ersetzt
  args    [(name, Frage, Vorgabe)] - leer = kein Dialog
  confirm True = Rueckfrage vor dem Senden
  danger  True = rot markieren
  note    kurze Erklaerung (Tooltip/Untertitel)
"""
from __future__ import annotations

COMMANDS: list[dict] = [
    # ---------------------------------------------------------------- Wartung
    {
        "id": "save", "label": "Welt speichern", "group": "Wartung",
        "cmd": "SaveWorld", "args": [], "confirm": False, "danger": False,
        "note": "sofortiger Save - vor jedem Neustart sinnvoll",
    },
    {
        "id": "save_all_dinos", "label": "Dinos speichern", "group": "Wartung",
        "cmd": "SaveWorld", "args": [], "confirm": False, "danger": False,
        "note": "Alias fuer SaveWorld (Dino-Zustand inklusive)",
    },
    # ---------------------------------------------------------- Kommunikation
    {
        "id": "broadcast", "label": "Broadcast", "group": "Kommunikation",
        "cmd": "Broadcast {text}",
        "args": [("text", "Nachricht an alle Spieler", "Server-Neustart in 5 Minuten")],
        "confirm": False, "danger": False,
        "note": "Meldung mittig auf dem Bildschirm aller Spieler",
    },
    {
        "id": "chat", "label": "Chat-Nachricht", "group": "Kommunikation",
        "cmd": "ServerChat {text}",
        "args": [("text", "Nachricht im Chat", "Willkommen auf dem Server")],
        "confirm": False, "danger": False,
        "note": "erscheint als Server-Nachricht im Chat",
    },
    {
        "id": "motd", "label": "MOTD zeigen", "group": "Kommunikation",
        "cmd": "ShowMessageOfTheDay", "args": [], "confirm": False, "danger": False,
        "note": "Message of the Day erneut anzeigen",
    },
    # ------------------------------------------------------------------ Welt
    {
        "id": "time", "label": "Tageszeit", "group": "Welt",
        "cmd": "SetTimeOfDay {time}",
        "args": [("time", "Uhrzeit (hh:mm)", "12:00")],
        "confirm": False, "danger": False,
        "note": "setzt die Spielzeit, z. B. 06:00 fuer Morgen",
    },
    {
        "id": "wipe_dinos", "label": "Wilde Dinos löschen", "group": "Welt",
        "cmd": "DestroyWildDinos", "args": [], "confirm": True, "danger": True,
        "note": "Dino-Wipe: alle wilden Dinos werden entfernt, gezähmte bleiben",
    },
    # ------------------------------------------------------------------ Info
    {
        "id": "players", "label": "Spielerliste", "group": "Info",
        "cmd": "ListPlayers", "args": [], "confirm": False, "danger": False,
        "note": "zeigt Online-Spieler mit SteamID",
    },
    {
        "id": "getchat", "label": "Chat abrufen", "group": "Info",
        "cmd": "GetChat", "args": [], "confirm": False, "danger": False,
        "note": "letzte Chatzeilen aus dem Serverpuffer",
    },
    {
        "id": "gameday", "label": "Spieltag", "group": "Info",
        "cmd": "GetGameDay", "args": [], "confirm": False, "danger": False,
        "note": "aktueller Spieltag seit Serverstart",
    },
]


def by_id(cmd_id: str) -> dict | None:
    for c in COMMANDS:
        if c["id"] == cmd_id:
            return c
    return None


def build(cmd_id: str, values: dict[str, str]) -> str | None:
    entry = by_id(cmd_id)
    if not entry:
        return None
    cmd = entry["cmd"]
    for name, _q, default in entry["args"]:  # type: ignore[misc]
        val = (values.get(name) or default or "").strip()
        cmd = cmd.replace("{%s}" % name, val)
    return cmd
