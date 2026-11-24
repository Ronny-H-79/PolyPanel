"""Dateien einer Instanz: Liste, Download, Upload, Ordner, Umbenennen, Loeschen.

Alle Pfade sind relativ zum Instanzordner. `_ziel()` loest sie auf und weist alles ab, was
aus dem Ordner herausfuehrt (auch ueber `..`, Symlinks werden ueber realpath geprueft).
"""
from __future__ import annotations

import os
import shutil


class PfadFehler(ValueError):
    """Pfad zeigt aus dem Instanzordner heraus."""


def basis(inst) -> str:
    return os.path.realpath(os.path.abspath(inst.directory))


def _ziel(inst, rel: str) -> str:
    wurzel = basis(inst)
    sauber = (rel or "").replace("\\", "/").strip("/")
    ziel = os.path.realpath(os.path.join(wurzel, sauber))
    if ziel != wurzel and not ziel.startswith(wurzel + os.sep):
        raise PfadFehler("Pfad liegt ausserhalb der Instanz")
    return ziel


def relativ(inst, absolt: str) -> str:
    return os.path.relpath(absolt, basis(inst)).replace(os.sep, "/")


def liste(inst, rel: str = "") -> dict:
    ordner = _ziel(inst, rel)
    if not os.path.isdir(ordner):
        raise FileNotFoundError("Ordner gibt es nicht: %s" % rel)
    eintraege = []
    with os.scandir(ordner) as it:
        for e in it:
            try:
                st = e.stat(follow_symlinks=False)
            except OSError:
                continue
            eintraege.append({
                "name": e.name,
                "pfad": (rel.strip("/") + "/" + e.name).strip("/"),
                "ordner": e.is_dir(follow_symlinks=False),
                "link": e.is_symlink(),
                "groesse": 0 if e.is_dir(follow_symlinks=False) else st.st_size,
                "zeit": int(st.st_mtime),
            })
    eintraege.sort(key=lambda x: (not x["ordner"], x["name"].lower()))
    eltern = "/".join(rel.strip("/").split("/")[:-1]) if rel.strip("/") else ""
    return {"pfad": rel.strip("/"), "eltern": eltern, "eintraege": eintraege}


def lesen(inst, rel: str) -> str:
    ziel = _ziel(inst, rel)
    if not os.path.isfile(ziel):
        raise FileNotFoundError("Datei gibt es nicht: %s" % rel)
    return ziel


def schreiben(inst, rel: str, daten: bytes) -> str:
    ziel = _ziel(inst, rel)
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    with open(ziel, "wb") as fh:
        fh.write(daten)
    return relativ(inst, ziel)


def ordner(inst, rel: str) -> str:
    ziel = _ziel(inst, rel)
    os.makedirs(ziel, exist_ok=True)
    return relativ(inst, ziel)


def loeschen(inst, rel: str) -> str:
    ziel = _ziel(inst, rel)
    if ziel == basis(inst):
        raise PfadFehler("Der Instanzordner selbst bleibt")
    if os.path.isdir(ziel) and not os.path.islink(ziel):
        shutil.rmtree(ziel)
    else:
        os.remove(ziel)
    return rel


def umbenennen(inst, rel: str, neu: str) -> str:
    ziel = _ziel(inst, rel)
    neu_sauber = (neu or "").replace("\\", "/").strip("/")
    if not neu_sauber or "/" in neu_sauber:
        raise PfadFehler("Neuer Name darf keinen Pfad enthalten")
    ziel_neu = _ziel(inst, os.path.join(os.path.dirname(rel.strip("/")), neu_sauber))
    if os.path.exists(ziel_neu):
        raise FileExistsError("Name ist schon vergeben: %s" % neu_sauber)
    os.replace(ziel, ziel_neu)
    return relativ(inst, ziel_neu)
