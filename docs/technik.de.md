# Technik

Aufbau, Benutzung auf der Konsole, Stop-Reihenfolge und Hinweise für Entwickler.

[← zurück zum README](../README.de.md) · [English](technik.md)

## Benutzung

```bash
noah2games web               # Weboberfläche auf http://127.0.0.1:8790
noah2games url               # fertige Adresse inklusive Token
noah2games status            # Prozess, RCON, letzte Logzeile
noah2games start --wait 240
noah2games stop              # SaveWorld → DoExit → SIGTERM → SIGKILL
noah2games update --check    # ist ein neuer Steam-Build verfügbar?
noah2games supervise --all   # Auto-Restart, Zeitplan, Backups
```

## Aufbau

| Datei | Aufgabe |
|---|---|
| `noah2games/instance.py` | Instanz-Konfiguration (JSON), Pfade, INI-Schreiben, Startparameter |
| `noah2games/runner.py` | Start/Stop/Status/Update, RCON-Shutdown, Wartungssperre |
| `noah2games/consoled.py` | startet den Server am PTY, damit Wine kein Fenster öffnet |
| `noah2games/rcon.py` | eigener Source-RCON-Client |
| `noah2games/supervisor.py` | Health-Check, Auto-Restart, Zeitplan, Countdown |
| `noah2games/registry.py` | mehrere Instanzen, Portvergabe, Kennzahlen |
| `noah2games/mods.py` · `whitelist.py` · `config.py` · `backups.py` · `snapshots.py` | Fachmodule |
| `noah2games/webui.py` | Dashboard, Instanzseiten, JSON-API (stdlib `http.server`) |
| `noah2games/cli.py` | Kommandozeile inkl. `wizard` |

## Stop-Reihenfolge (bewusst so)

1. RCON `SaveWorld` — Spielstand sichern
2. RCON `DoExit` — reguläres Beenden
3. `SIGTERM` an die Prozessgruppe
4. `SIGKILL`

Ein `kill` ohne Schritt 1 kostet den Fortschritt seit dem letzten Autosave.

Hinweise für Mitentwickler: [entwicklung.md](entwicklung.md)
