## [0.11] — 2026-11-13

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

### Behoben
- **Space Engineers startet nicht mehr im Experimental-Modus.** SE prüft beim Start Prozessorkerne,
  Takt und RAM (`ProcessorCount >= 3`, `CPUFrequency >= 3.2 GHz`, mindestens 6 GB RAM) und erzwingt
  sonst Experimental — Gäste werden dann abgewiesen, bis sie Experimental in ihren Spieloptionen
  einschalten. Den Takt liest SE per WMI, das unter Wine aus `/proc/cpuinfo` gespeist wird, und VMs
  melden dort z. B. 2095 MHz. PolyPanel baut beim Start jetzt einen kleinen LD_PRELOAD-Shim
  (`~/.local/share/polypanel/se-cpufix/fakecpu.so`), der Wine 3.6 GHz meldet; im Serverlog steht
  danach `Experimental mode: No`. Voraussetzung ist ein C-Compiler (`build-essential`/`gcc`) —
  fehlt er, bleibt alles wie bisher und das Startlog sagt es.