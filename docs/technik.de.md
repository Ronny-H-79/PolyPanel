# Technik

Aufbau, Benutzung auf der Konsole, Stop-Reihenfolge und Hinweise für Entwickler.

[← zurück zum README](../README.de.md) · [English](technik.md)

## Benutzung

```bash
polypanel web               # Weboberfläche auf http://127.0.0.1:8790
polypanel url               # fertige Adresse inklusive Token
polypanel status            # Prozess, RCON, letzte Logzeile
polypanel start --wait 240
polypanel stop              # SaveWorld → DoExit → SIGTERM → SIGKILL
polypanel update --check    # ist ein neuer Steam-Build verfügbar?
polypanel supervise --all   # Auto-Restart, Zeitplan, Backups
```

## Aufbau

| Datei | Aufgabe |
|---|---|
| `PolyPanel/instance.py` | Instanz-Konfiguration (JSON), Pfade, INI-Schreiben, Startparameter |
| `PolyPanel/runner.py` | Start/Stop/Status/Update, RCON-Shutdown, Wartungssperre |
| `PolyPanel/consoled.py` | startet den Server am PTY, damit Wine kein Fenster öffnet |
| `PolyPanel/rcon.py` | eigener Source-RCON-Client |
| `PolyPanel/supervisor.py` | Health-Check, Auto-Restart, Zeitplan, Countdown |
| `PolyPanel/registry.py` | mehrere Instanzen, Portvergabe, Kennzahlen |
| `PolyPanel/mods.py` · `whitelist.py` · `config.py` · `backups.py` · `snapshots.py` | Fachmodule |
| `PolyPanel/webui.py` | Dashboard, Instanzseiten, JSON-API (stdlib `http.server`) |
| `PolyPanel/cli.py` | Kommandozeile inkl. `wizard` |

## Stop-Reihenfolge (bewusst so)

1. RCON `SaveWorld` — Spielstand sichern
2. RCON `DoExit` — reguläres Beenden
3. `SIGTERM` an die Prozessgruppe
4. `SIGKILL`

Ein `kill` ohne Schritt 1 kostet den Fortschritt seit dem letzten Autosave.

Hinweise für Mitentwickler: [entwicklung.md](entwicklung.md)

---

© 2026 Ronny H. · Kostenlos nutzbar, alle Rechte beim Autor — [Lizenz](../LICENSE)
