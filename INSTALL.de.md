# PolyPanel installieren

Ein Installer für den eigenen Multigame-Servermanager
(ARK: Survival Ascended, ARK: Survival Evolved, Satisfactory, 7 Days to Die, Space Engineers).
Alles läuft lokal, Python-Standardbibliothek plus SteamCMD und Wine.

## Voraussetzungen

| Was | Warum | Prüfen |
|---|---|---|
| Linux (x86_64) | getestet auf CachyOS/Arch | `uname -m` |
| Python ≥ 3.10 | Programm läuft damit | `python3 -V` |
| Wine ≥ 8 | führt die Windows-Serverdateien aus | `wine --version` |
| ~30 GB Platz pro Instanz | 12,4 GB Download + Sicherungen | `df -h ~` |
| ~4 GB RAM leer ohne Mods, 11–12 GB mit Mods/Welt/Spielern (nach oben offen) | ARK braucht das | `free -g` |

Fehlt Wine:

```bash
sudo pacman -S wine           # Arch / CachyOS
sudo apt install wine         # Debian / Ubuntu
```

SteamCMD wird beim ersten Installieren automatisch nach `~/steamcmd` geladen — kein root nötig.
Die nötigen 32-Bit-Bibliotheken richtet der Installer selbst ein (lib32gcc, libc6:i386 bzw. die
Pakete der Distribution); ohne sie bricht SteamCMD mit „Exit 127“ ab.

## Sprache

Der Installer fragt zuerst:

```
Sprache / Language:  [1] Deutsch  [2] English   [1]
```

Ohne Rueckfrage: `./install.sh --lang en` oder `NOAH_LANG=en ./install.sh`.
Gespeichert wird das in `~/.config/polypanel/settings.json`. Spaeter jederzeit umstellbar:

- `polypanel lang en` / `polypanel lang de`
- Weboberflaeche: Knopf oben rechts (`EN` / `DE`)

## Installation

Im eigenen Benutzerkonto installieren — **ohne sudo**:

```bash
git clone https://github.com/Ronny-H-79/PolyPanel.git polypanel
cd polypanel && ./install.sh
```

Alles landet unter `~/.local/share/polypanel`, Instanzen unter `~/polypanel-instances`, die Server laufen
unter deinem Benutzer. **Satisfactory startet nur so** — der Server verweigert den Start als root.

Wer `install.sh` als **root** startet, bekommt das automatisch: der Installer legt den Dienst-Benutzer
`polypanel` an und installiert dorthin (`/home/polypanel`), damit weder Panel noch Server als root laufen.
Ein anderer Benutzername geht mit `--user <name>`.

Genau dieser Aufruf, ohne Rückfragen:

```bash
git clone https://github.com/Ronny-H-79/PolyPanel.git polypanel && cd polypanel && ./install.sh --auto --lang de --web
```

Landet unter `/home/polypanel`, Web-Dienst als Benutzer `polypanel`, Port 8790.

Weitere Aufrufe:

```bash
git clone https://github.com/Ronny-H-79/PolyPanel.git polypanel   # oder Ordner kopieren
cd polypanel          # dieser Ordner enthaelt install.sh - NICHT PolyPanel/polypanel (das ist das Python-Paket)
./install.sh --check        # nur pruefen, was fehlt (aendert nichts)
./install.sh                # installieren, fragt bei fehlenden Paketen nach
./install.sh --auto         # fehlende Pakete ohne Rueckfrage installieren (sudo)
./install.sh --wizard       # installieren und danach den Assistenten starten
```

Fehlende Pakete (z. B. Wine) erkennt der Installer über `pacman`, `apt`, `dnf` oder `zypper` und
installiert sie auf Wunsch per `sudo` nach. Ohne Rueckfrage laesst sich das mit `--auto` erzwingen.

Der Installer prüft Python und Wine, kopiert die Programmdateien, legt den Befehl `polypanel` an
und richtet `~/.config/polypanel` ein. Er braucht **keine** root-Rechte.

## Web-Dienst (optional)

Der Installer fragt: „Web-Oberflaeche automatisch starten (systemd-Dienst)?" Mit `j` legt er als
**root** einen Systemdienst `/etc/systemd/system/polypanel-web.service` an (`WantedBy=multi-user.target`,
startet beim Booten) — als normaler Benutzer stattdessen `~/.config/systemd/user/polypanel-web.service`
(`systemctl --user enable --now`).
Ohne Zustimmung startet man die Oberflaeche bei Bedarf mit `polypanel web`.

## Zugriff von woanders

Standardsmaessig nur `127.0.0.1`. Von einem anderen Rechner per SSH-Tunnel:
`ssh -N -L 8790:127.0.0.1:8790 nutzer@server`, dann `http://127.0.0.1:8790/?token=…` oeffnen.
Im LAN/VPN: `polypanel web --host 0.0.0.0`. Aus dem Internet per nginx mit HTTPS:
`sudo polypanel proxy --domain PolyPanel.example.de --write --cert` (schreibt die Config, prueft mit `nginx -t`,
laedt nginx neu und holt das Zertifikat). Ohne nginx geht auch HTTPS direkt:
`polypanel web --tls-cert cert.pem --tls-key key.pem`. Details im README.

## Sicherheit (kurz)

Die Oberflaeche ist eine Administrationskonsole: **wer den Token hat, kann alles steuern** - Server
starten, stoppen, loeschen, Mods eintragen, Konsolenbefehle absetzen. Deshalb:

- Client-Installation (Modus `[1]`) und Server mit Domain (Modus `[2]`): polypanel bleibt auf `127.0.0.1`,
  der Zugang laeuft ueber SSH-Tunnel bzw. nginx mit HTTPS. Nur Modus `[3]` bindet direkt nach aussen.
- **Nicht unverschluesselt ins Internet stellen.** Bei `--host 0.0.0.0` ohne TLS wandert der Token im
  Klartext ueber jede Zwischenstation. Fuer oeffentlichen Zugriff HTTPS per `polypanel proxy` oder TLS direkt.
- Der Installer warnt bei Modus `[3]` (IP und Port) und fragt vorher nach.

Ausfuehrlich, inklusive was polypanel selbst absichert: `docs/zugriff.md`, Abschnitt „Sicherheit".

## Der Token

Nach der Installation zeigt `polypanel url` die Adresse mit Token an, z. B.
`http://127.0.0.1:8790/?token=…`. Der Schlüssel liegt in `~/.config/polypanel/token` (Rechte 0600) und
schuetzt die Oberflaeche davor, dass eine beliebige Webseite in deinem Browser Befehle an
`127.0.0.1` schickt (ohne Token: `HTTP 401`). Details im README, Abschnitt „Der Token".
Token zuruecksetzen: Datei loeschen, beim naechsten Start entsteht ein neuer.

## Einrichten

**Normaler Weg — im Browser:**

```bash
polypanel web
```

Ausgegebene Adresse mit Token öffnen, Instanz-Namen eintragen, Spiel (bei ARK die Karte) wählen,
**Anlegen** drücken, dann **Installieren** auf der neuen Karte. Damit werden die Serverdateien
geladen (~20 GB bei ARK Evolved) und der Dienst automatisch eingerichtet.

**Optional, nur Konsole — der Assistent:**

```bash
polypanel wizard
```

Das laeuft im **Terminal auf dem Server** — per SSH (`ssh nutzer@server`) oder direkt an der Konsole.
Der Assistent stellt Fragen, braucht also eine interaktive Sitzung. Nötig ist er nicht: dieselben
Schritte gibt es in der Web-Oberfläche (Name, Spiel, Karte, **Anlegen**, **Installieren**).

Der Assistent fragt Name, Map, Port und Session-Name, legt die Instanz an und bietet an,
die Serverdateien zu laden (~12,4 GB, 10–30 Minuten) und einen systemd-Dienst einzurichten.

Ohne Rueckfragen, z. B. fuer Skripte:

```bash
polypanel init --name test --dir ~/arkserver-test --map Ragnarok_WP --port 7790 --rcon-port 27025
polypanel update      # Serverdateien laden, danach polypanel start
```

## Benutzen

```bash
polypanel web                    # Weboberfläche starten
polypanel url                    # fertige Adresse inklusive Token anzeigen
polypanel status                 # Prozess, RCON, letzte Logzeile
polypanel start --wait 240
polypanel stop                   # SaveWorld → DoExit → SIGTERM
polypanel update --check         # ist ein Steam-Build verfügbar?
polypanel supervise --all        # Auto-Restart, geplante Neustarts, Backups
```

Die Web-Oberfläche zeigt ein Dashboard mit allen Instanzen (Status, CPU, RAM, Spieler),
pro Instanz Start/Stop/Update, Klick-Befehle für RCON, Spielerverwaltung, Whitelist/Bans,
Mod-Verwaltung mit Bildern, Einstellungen als Formular, Backups, Snapshots und Zeitplan.

## Autostart

```bash
systemctl --user daemon-reload
systemctl --user enable --now polypanel-<name>
loginctl enable-linger $USER      # läuft auch ohne angemeldete Sitzung
```

**Token vergessen oder Adresse verloren?**

```bash
polypanel token          # Web-Token mit Dateipfad und Adresse
polypanel token --quiet  # nur der Token (für Skripte)
polypanel url            # fertige Adresse inklusive Token
```

Der Token liegt zusätzlich in `~/.config/polypanel/token` (Rechte `600`).

## Deinstallieren

```bash
cd ~/polypanel          # in den Klon des Repos wechseln
./install.sh --uninstall
```

Entfernt Programm und Launcher. **Bleiben:** Instanzen (`~/arkserver-*`), Einstellungen
(`~/.config/polypanel`), Backups (`~/polypanel-backups`), Snapshots (`~/polypanel-snapshots`).

**SteamCMD** (`~/steamcmd`, `~/.steam`, `~/Steam`) wird von `--uninstall` ebenfalls entfernt.

### Alles entfernen (auch Instanzen und Welten)

```bash
cd ~/polypanel          # in den Klon des Repos wechseln
./install.sh --uninstall
rm -rf ~/polypanel-instances ~/.config/polypanel ~/polypanel-backups ~/polypanel-snapshots
rm -rf ~/.wine ~/.polypanel-wine-se # Wine-Prefixe (Standard und Space Engineers)
rm -f /etc/systemd/system/polypanel-*.service
systemctl daemon-reload
```

Was wo liegt: Programm `~/.local/share/polypanel` und `~/.local/bin/polypanel`, Einstellungen und
Token `~/.config/polypanel`, Instanzen mit Welten `~/polypanel-instances/<name>`, SteamCMD `~/steamcmd`,
`~/.steam` und `~/Steam`.

## Wo was liegt

| Pfad | Inhalt |
|---|---|
| `~/.local/share/polypanel` | Programm |
| `~/.local/bin/polypanel` | Launcher |
| `~/.config/polypanel/<name>.json` | Instanz-Konfiguration |
| `~/.config/polypanel/token` | Web-Token (0600) |
| `~/polypanel-instances/<name>` | Serverdateien der Instanz |
| `~/polypanel-backups/<name>` | Welt-Backups (tar.gz) |
| `~/polypanel-snapshots/<name>` | vollständige Instanz-Snapshots (Rollback nach Update) |

---

© 2026 Ronny H. · Kostenlos nutzbar, alle Rechte beim Autor — [Lizenz](LICENSE)
