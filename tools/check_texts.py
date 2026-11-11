#!/usr/bin/env python3
"""Prueft die Textausgaben in install.sh.

Aufruf:  python3 tools/check_texts.py [install.sh]

Prueft zwei Dinge:
1. Jeder Aufruf ``$(t SCHLUESSEL ...)`` liefert so viele Argumente, wie der Text
   Platzhalter ($2, $3 ...) verwendet - ein fehlendes Argument erzeugt sonst
   Meldungen wie "  fehlt. Jetzt installieren?" ohne Paketnamen.
2. Jeder benutzte Schluessel ist definiert (de und en).

Rueckgabewert 1, wenn etwas fehlt - damit in einem Release-Lauf pruefbar.
"""
import re
import sys
import os


import re


def definitionen(txt):
    start = txt.index("t() {")
    ende = txt.index("\n}\n", start)
    block = txt[start:ende]
    defs = {}
    for m in re.finditer(r"^\s{4}(?:en|de):([a-z0-9_]+)\)\s*(.*)$", block, flags=re.M):
        key, body = m.group(1), m.group(2)
        platzhalter = {int(x) for x in re.findall(r"\$(\d)", body)}
        defs[key] = defs.get(key, set()) | platzhalter
    return defs


def aufrufe(txt):
    """Alle $(t KEY ...) Aufrufe mit ihren Argumenten (verschachtelungssicher)."""
    ergebnis = []
    for m in re.finditer(r"\$\(t ([a-z0-9_]+)", txt):
        key = m.group(1)
        i = m.end()
        tiefe, in_quote, args, aktuell = 1, None, 0, False
        while i < len(txt):
            ch = txt[i]
            if in_quote:
                if ch == in_quote:
                    in_quote = None
                i += 1
                continue
            if ch in "\"'":
                in_quote = ch
                if not aktuell:
                    aktuell = True
                    args += 1
                i += 1
                continue
            if ch in "($" and ch == "$" and txt[i:i + 2] == "$(":
                if not aktuell:
                    aktuell = True
                    args += 1
                tiefe += 1
                i += 1
                continue
            if ch == "(":
                tiefe += 1
            elif ch == ")":
                tiefe -= 1
                if tiefe == 0:
                    break
            elif ch.isspace():
                aktuell = False
            elif not aktuell:
                aktuell = True
                args += 1
            i += 1
        ergebnis.append((txt[:m.start()].count("\n") + 1, key, args))
    return ergebnis


def main() -> int:
    pfad = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "install.sh")
    txt = open(pfad, encoding="utf-8").read()
    defs = definitionen(txt)
    alle = aufrufe(txt)
    fehler = []
    for zeile, key, args in alle:
        if key not in defs:
            fehler.append("Zeile %d: Schluessel '%s' nicht definiert" % (zeile, key))
            continue
        noetig = max(defs[key]) - 1 if defs[key] else 0
        if args < noetig:
            fehler.append("Zeile %d: t %s ... hat %d Argument(e), Text braucht %d"
                          % (zeile, key, args, noetig))
    print("%s: %d Schluessel, %d Aufrufe, %d Fehler" % (os.path.basename(pfad), len(defs), len(alle), len(fehler)))
    for f in fehler:
        print("  ! " + f)
    return 1 if fehler else 0


if __name__ == "__main__":
    raise SystemExit(main())
