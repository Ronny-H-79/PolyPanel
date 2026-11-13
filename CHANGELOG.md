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
