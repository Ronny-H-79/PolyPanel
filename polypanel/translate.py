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
import time
import urllib.parse
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

CACHE_DIR = os.path.expanduser("~/.config/polypanel/cache/translations")
ENDPOINT = ("https://translate.googleapis.com/translate_a/single"
            "?client=gtx&sl=en&tl=de&dt=t&q=")
MAX_CHARS = 1200                     # Groesse eines Anfrage-Stuecks (Google-Limit ~2k)
TIMEOUT = 8.0

# Wenn Google mit 429 antwortet, ist die IP kurz gesperrt. Dann wird eine Zeit lang
# direkt der Ausweichdienst genutzt, statt weiter Anfragen zu verbrennen.
_GOOGLE_GESPERRT_BIS = 0.0
MYMEMORY = "https://api.mymemory.translated.net/get?langpair=en|de&q="
MYMEMORY_MAX = 450          # Zeichen je Anfrage (Dienstlimit)

DE_WOERTER = (" der ", " die ", " das ", " und ", " für ", " mit ", " nicht ", " ist ",
              " wird ", " kann ", " deine ", " dein ", " eine ", " einen ")
EN_WOERTER = (" the ", " and ", " with ", " you ", " for ", " this ", " that ", " your ",
              " from ", " will ", " can ")


def _schon_deutsch(text: str) -> bool:
    """Ist der Text wirklich schon deutsch?

    Fruehere Fassung (de >= 2 und de > en) hielt zweisprachige Beschreibungen -
    viele Workshop-Mods schreiben englisch UND deutsch - fuer deutsch und liess
    den englischen Teil stehen. Jetzt gilt ein Text erst als deutsch, wenn kein
    einziges englisches Signalwort vorkommt.
    """
    klein = " %s " % text.lower()
    de = sum(1 for w in DE_WOERTER if w in klein)
    en = sum(1 for w in EN_WOERTER if w in klein)
    return en == 0 and de >= 2


def _cache_pfad(text: str) -> str:
    # "v2": alte Eintraege stammen aus der Zeit, als Texte bei 400 Zeichen
    # abgeschnitten wurden - die duerfen nicht mehr greifen.
    return os.path.join(CACHE_DIR,
                        hashlib.sha1(("v3:" + text).encode("utf-8")).hexdigest() + ".txt")


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


def _stuecke(text: str) -> list[str]:
    """Text in Anfrage-Stuecke zerlegen - an Satzenden, sonst an Wortgrenzen.

    Vorher wurde hart bei 400 Zeichen abgeschnitten; der Rest blieb englisch.
    Jetzt wird der ganze Text uebersetzt, nur die Anfragen bleiben klein.
    """
    text = (text or "").strip()
    if not text:
        return []
    stuecke: list[str] = []
    rest = text
    while len(rest) > MAX_CHARS:
        fenster = rest[:MAX_CHARS]
        schnitt = max(fenster.rfind(". "), fenster.rfind("! "), fenster.rfind("? "),
                      fenster.rfind("\n"))
        if schnitt < MAX_CHARS // 2:            # kein Satzende gefunden: Wortgrenze nehmen
            schnitt = fenster.rfind(" ")
        if schnitt <= 0:
            schnitt = MAX_CHARS
        stuecke.append(rest[:schnitt + 1].strip())
        rest = rest[schnitt + 1:].strip()
    if rest:
        stuecke.append(rest)
    return stuecke


def _frage(text: str, versuche: int = 2) -> str:
    """Uebersetzung ueber Google; bei 429 Sperre merken und Ausweichdienst nehmen."""
    global _GOOGLE_GESPERRT_BIS
    if time.time() >= _GOOGLE_GESPERRT_BIS:
        url = ENDPOINT + urllib.parse.quote(text)
        for versuch in range(versuche):
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 PolyPanel"})
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    daten = json.loads(resp.read().decode("utf-8", "replace"))
                teile = [t[0] for t in (daten[0] or []) if t and t[0]]
                ergebnis = "".join(teile).strip()
                if ergebnis:
                    return ergebnis
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    _GOOGLE_GESPERRT_BIS = time.time() + 300
                    break
                time.sleep(0.4 + versuch)
            except Exception:                 # noqa: BLE001 - naechster Versuch
                time.sleep(0.4 + versuch)
    return _frage_ausweich(text)


def _frage_ausweich(text: str) -> str:
    """MyMemory als Ausweichdienst (kein Key, ~1000 Woerter/Tag)."""
    stuecke = _stuecke(text)
    if not stuecke:
        return ""
    teile = []
    for stueck in stuecke:
        weitere = [stueck[i:i + MYMEMORY_MAX] for i in range(0, len(stueck), MYMEMORY_MAX)]
        for teil in weitere:
            url = MYMEMORY + urllib.parse.quote(teil)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 PolyPanel"})
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    daten = json.loads(resp.read().decode("utf-8", "replace"))
                wert = ((daten.get("responseData") or {}).get("translatedText") or "").strip()
                if not wert or "MYMEMORY WARNING" in wert.upper():
                    return ""
                teile.append(wert)
            except Exception:                 # noqa: BLE001
                return ""
    return " ".join(teile).strip()


def _eins(text: str) -> str:
    if not text.strip():
        return text
    zwischengespeichert = _aus_cache(text)
    if zwischengespeichert:
        return zwischengespeichert
    if _schon_deutsch(text):
        return text
    stuecke = _stuecke(text)
    if not stuecke:
        return text
    ergebnisse = []
    unvollstaendig = False
    for stueck in stuecke:
        teil = _frage(stueck)
        if not teil:
            # Kein Ergebnis: Original behalten, aber NICHT cachen - sonst steht der
            # englische Text fuer immer im Cache (genau das war der Fehler).
            teil = stueck
            unvollstaendig = True
        ergebnisse.append(teil)
    ergebnis = " ".join(ergebnisse).strip()
    if not ergebnis or unvollstaendig or ergebnis == text.strip():
        return ergebnis or text
    _in_cache(text, ergebnis)
    return ergebnis


def _eins_en(text: str) -> str:
    """Deutsch -> Englisch (fuer Suchbegriffe in englischsprachigen Mod-Portalen)."""
    text = (text or "").strip()
    if not text:
        return text
    schluessel = "en:" + text
    zwischengespeichert = _aus_cache(schluessel)
    if zwischengespeichert:
        return zwischengespeichert
    url = ENDPOINT.replace("sl=en&tl=de", "sl=de&tl=en") + urllib.parse.quote(text[:MAX_CHARS])
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 PolyPanel"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            daten = json.loads(resp.read().decode("utf-8", "replace"))
        ergebnis = "".join(t[0] for t in (daten[0] or []) if t and t[0]).strip()
    except Exception:                     # noqa: BLE001
        return text
    if not ergebnis:
        return text
    _in_cache(schluessel, ergebnis)
    return ergebnis


# Kleines Fachglossar: Einzelworte uebersetzt der Dienst zu schlecht ("foerder" -> "promote").
GLOSSAR = {
    "förder": "conveyor", "förderband": "conveyor", "förderer": "conveyor",
    "lager": "storage", "container": "storage", "kiste": "container",
    "bergbau": "mining", "erz": "ore", "kohle": "coal", "öl": "oil", "wasser": "water",
    "strom": "power", "energie": "power", "generator": "generator", "reaktor": "reactor",
    "raffinerie": "refinery", "schmelze": "smelter", "fabrik": "factory", "maschine": "machine",
    "pumpe": "pump", "rohr": "pipe", "röhre": "pipe", "kabel": "wire", "bahn": "train",
    "zug": "train", "züge": "train", "bahnhof": "station", "fahrzeug": "vehicle",
    "aufzug": "lift", "verteiler": "splitter", "sortierer": "sorter", "schredder": "shredder",
    "blaupause": "blueprint", "blaupausen": "blueprints", "tür": "door", "tor": "gate",
    "wand": "wall", "fundament": "foundation", "treppe": "stairs", "licht": "light",
    "beleuchtung": "lighting", "sensor": "sensor", "schalter": "switch", "tank": "tank",
    "biomasse": "biomass", "brennstoff": "fuel", "batterie": "battery", "turm": "tower",
    "waffe": "weapon", "waffen": "weapons", "verteidigung": "defense", "mauer": "wall",
    "landwirtschaft": "farming", "farm": "farm", "pflanzen": "plants", "dünger": "fertilizer",
}


def query_english(query: str) -> str:
    """Deutschen Suchbegriff auf Englisch bringen, wenn er deutsch aussieht.

    Mod-Portale (ficsit.app, Nexus) sind englisch indexiert - "Foerderband" findet dort
    nichts, "conveyor" dagegen viele Treffer.
    """
    q = (query or "").strip()
    if not q:
        return q
    klein = q.lower()
    if klein in GLOSSAR:                      # Fachbegriff: Glossar ist zuverlaessiger
        return GLOSSAR[klein]
    if _schon_deutsch(" %s " % klein) or any(z in klein for z in ("ä", "ö", "ü", "ß")):
        uebersetzt = _eins_en(q)
        # Einzelwort-Uebersetzungen sind oft daneben ("foerder" -> "promote"): nur nehmen,
        # wenn das Ergebnis wie ein sinnvoller Begriff aussieht.
        if uebersetzt and uebersetzt.lower() != klein and " " not in q:
            return uebersetzt if len(uebersetzt) <= len(q) + 6 else klein
        return uebersetzt or q
    return q


def to_german(texts: list[str], workers: int = 4) -> list[str]:
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
