## [0.12] — 2026-11-13

### Neu
- **Eigenes Panel-Log** (`~/.config/ascendedpanel/panel.log`, ab 1 MB gedreht). Die Meldung konnte
  das System-Journal nicht lesen, weil der Dienst unter root läuft — darum schreibt das Panel seine
  Ereignisse jetzt selbst mit: jede Aktion (Start, Stop, Restart, Update) und jeder Fehler im
  Web-Dienst landet dort.
- Fehlermeldungen enthalten damit wirklich **Panel-Logs**: eigene Logdatei, dazu
  `.ascendedpanel-supervisor.log`, `.update.log` und `.install.log` der Instanz; das Spiel-Log
  bleibt draußen. Leere Journal-Antworten (`-- No entries --`) werden herausgefiltert.

## [0.11] — 2026-11-13

### Geändert
- **Fehler melden sitzt jetzt auf der Startseite** (Knopf in der Kopfzeile, erscheint nur, wenn ein
  Melde-Webhook hinterlegt ist) und ist aus der Instanzseite verschwunden.
- **Gemeldet wird das Panel, nicht das Spiel:** Die Meldung enthält Panel-Version, System und die
  **Panel-Logs** (Journal des Dienstes, dazu `.ascendedpanel-supervisor.log`, `.update.log` und
  `.install.log` der betroffenen Instanz). Das Server-Log des Spiels wird **nicht** mitgeschickt.
  Passwörter und Token werden weiterhin vor dem Senden entfernt.
- Wortlaut im Fenster entsprechend: „Was kann das Panel nicht?" statt „Was ist passiert?".

## [0.10] — 2026-11-13

### Überblick
Grobe Zusammenfassung dessen, was in den Panels steckt.

- **Zwei Panels, ein Unterbau:** AscendedPanel für ARK: Survival Ascended, PolyPanel für ASA, ASE,
  Satisfactory, 7 Days to Die und Space Engineers. Bedienung im Browser, Dienst auf dem Server.
- **Dashboard:** Instanzkarten mit Status, Karte, Ports, Build, CPU/RAM, Spielern und Laufzeit;
  Start, Restart, Update, Stop und Löschen direkt auf der Karte, Knöpfe sperren sich nach Zustand
  (läuft Stop, ist nur noch Menü frei usw.).
- **Instanzseite:** Live-Log, Konfigurationseditor mit Sicherung und Prüfung (INI-Werte als Formular
  oder roh), Mod-Verwaltung mit CurseForge-Suche/Update-Prüfung, Backups, Snapshots, Zeitplan und
  RCON-Konsole mit Ein-Klick-Befehlen.
- **Spieler:** Liste mit Kick, Ban, Whitelist und Gegenstände verteilen — Katalog mit Suche und
  Mengenfenster; die nötige Spieler-ID (ARKID) wird aus den `.arkprofile`-Dateien gelesen, weil
  ARK per RCON nur die EOS-ID liefert.
- **Sperren:** eigenes Fenster „Gesperrte Spieler" mit Entbannen je Zeile und ehrlichem Hinweis,
  warum ARK seine Ban-Liste nicht über RCON herausgibt.
- **Betrieb:** Absturz-Erkennung mit automatischem Neustart, Discord-Benachrichtigungen,
  Sprache Deutsch/Englisch jederzeit umschaltbar, mehrere Instanzen in einem Prozess.
- **Fehlermeldungen:** Knopf im Panel, Meldung geht an den Betreiber (Webhook, nur auf der Konsole
  setzbar) — mit Version, Instanz, System und Logauszug, Passwörter entfernt.
