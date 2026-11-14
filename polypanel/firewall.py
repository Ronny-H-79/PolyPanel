"""Firewall (UFW) fuer die Instanzports.

Ein Panel, das den Server startet, aber die Firewall vergisst, produziert genau den
Fehler „komme nicht auf den Server“: Port belegt, Server laeuft, aber von aussen kommt
nichts an. Deshalb oeffnet das Panel die Ports jeder Instanz selbst.

`ufw` braucht root. Der Dienstbenutzer bekommt dafuer eine eng begrenzte NOPASSWD-Regel
(`/etc/sudoers.d/polypanel-ufw`, nur /usr/sbin/ufw). Fehlt sie, wird nichts freigegeben
und der Aufrufer schreibt einen Hinweis ins Panel-Log - der Start laeuft trotzdem.
"""
from __future__ import annotations

import re
import subprocess

from .instance import Instance

UFW = "/usr/sbin/ufw"
KOMMENTAR = "PolyPanel:%s"


def _ufw(args: list[str], timeout: int = 15) -> tuple[bool, str]:
    try:
        lauf = subprocess.run(["sudo", "-n", UFW] + args, capture_output=True,
                              text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    text = (lauf.stdout + lauf.stderr).strip()
    return lauf.returncode == 0, text


def _ports(inst: Instance) -> list[tuple[str, str]]:
    return [(str(inst.port), KOMMENTAR % inst.name + " GamePort"),
            (str(inst.query_port), KOMMENTAR % inst.name + " QueryPort")]


def open_ports(inst: Instance) -> dict:
    """Spiel- und Query-Port (UDP) freigeben - idempotent, mehrfach aufrufbar."""
    ok_alle = True
    meldungen: list[str] = []
    for port, kommentar in _ports(inst):
        ok, text = _ufw(["allow", "%s/udp" % port, "comment", kommentar])
        ok_alle = ok_alle and ok
        if text:
            meldungen.append(text.splitlines()[-1][:140])
    return {"ok": ok_alle, "meldungen": meldungen}


def close_ports(inst: Instance) -> dict:
    """Alle Regeln dieser Instanz entfernen (beim Loeschen der Instanz)."""
    ok, status = _ufw(["status", "numbered"])
    if not ok:
        return {"ok": False, "error": status[:200]}
    muster = re.compile(re.escape(KOMMENTAR % inst.name) + r"\s+(Game|Query)Port")
    nummern = []
    for zeile in status.splitlines():
        treffer = re.match(r"\[\s*(\d+)\]\s+(.*)$", zeile.strip())
        if treffer and muster.search(treffer.group(2)):
            nummern.append(int(treffer.group(1)))
    entfernt = 0
    for nummer in sorted(nummern, reverse=True):   # von hinten: Nummern verschieben sich
        ok_del, _text = _ufw(["--force", "delete", str(nummer)])
        entfernt += 1 if ok_del else 0
    return {"ok": True, "entfernt": entfernt}
