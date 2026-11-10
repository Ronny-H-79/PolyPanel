"""Kurze englische Texte (Mod-Beschreibungen) automatisch nach Deutsch uebersetzen.

Warum nicht lokal per LLM: 24 Treffer pro Suche waeren mit einem 12B-Modell zu langsam.
Der Uebersetzungs-Endpunkt von Google braucht keinen Key; Ergebnisse liegen als Datei
im Cache, damit eine Wiederholung ohne Netz auskommt. Schlaegt etwas fehl, bleibt der
Originaltext stehen - die Suche darf nie an der Uebersetzung scheitern.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

CACHE_DIR = os.path.expanduser("~/.config/noah2games/cache/translations")
ENDPOINT = ("https://translate.googleapis.com/translate_a/single"
            "?client=gtx&sl=en&tl=de&dt=t&q=")
MAX_CHARS = 400                      # laengere Texte werden abgeschnitten
TIMEOUT = 8.0

DE_WOERTER = (" der ", " die ", " das ", " und ", " für ", " mit ", " nicht ", " ist ",
              " wird ", " kann ", " deine ", " dein ", " eine ", " einen ")
EN_WOERTER = (" the ", " and ", " with ", " you ", " for ", " this ", " that ", " your ",
              " from ", " will ", " can ")


def _schon_deutsch(text: str) -> bool:
    """Grobe Schaetzung: enthaelt der Text schon ueberwiegend deutsche Woerter?"""
    klein = " %s " % text.lower()
    de = sum(1 for w in DE_WOERTER if w in klein)
    en = sum(1 for w in EN_WOERTER if w in klein)
    return de >= 2 and de > en


def _cache_pfad(text: str) -> str:
    return os.path.join(CACHE_DIR, hashlib.sha1(text.encode("utf-8")).hexdigest() + ".txt")


def _aus_cache(text: str) -> str:
    try:
        with open(_cache_pfad(text), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def _in_cache(text: str, uebersetzt: str) -> None:
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(_cache_pfad(text), "w", encoding="utf-8") as fh:
            fh.write(uebersetzt)
    except OSError:
        pass


def _eins(text: str) -> str:
    if not text.strip():
        return text
    zwischengespeichert = _aus_cache(text)
    if zwischengespeichert:
        return zwischengespeichert
    if _schon_deutsch(text):
        return text
    kurz = text[:MAX_CHARS]
    url = ENDPOINT + urllib.parse.quote(kurz)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 noah2games"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            daten = json.loads(resp.read().decode("utf-8", "replace"))
        teile = [t[0] for t in (daten[0] or []) if t and t[0]]
        ergebnis = "".join(teile).strip()
    except Exception:                     # noqa: BLE001 - Originaltext behalten
        return text
    if not ergebnis:
        return text
    if len(text) > MAX_CHARS:             # Rest unuebersetzt anhaengen
        ergebnis += " …"
    _in_cache(text, ergebnis)
    return ergebnis


def to_german(texts: list[str], workers: int = 6) -> list[str]:
    """Liste uebersetzen; Reihenfolge bleibt, Fehler liefern den Originaltext."""
    if not texts:
        return []
    with ThreadPoolExecutor(max_workers=min(workers, max(1, len(texts)))) as pool:
        return list(pool.map(_eins, texts))


def translate_items(items: list[dict], field: str, limit: int = 12) -> list[dict]:
    """Das angegebene Feld der ersten `limit` Treffer uebersetzen (in place)."""
    if not items:
        return items
    kopf = items[:limit]
    texte = [str(it.get(field) or "") for it in kopf]
    if not any(t.strip() for t in texte):
        return items
    for it, neu in zip(kopf, to_german(texte)):
        if neu:
            it[field] = neu
    return items
