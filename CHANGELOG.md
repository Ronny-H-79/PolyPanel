## [0.14] — 2026-11-13

### Behoben
- **Karte und RCON stehen jetzt auf jeder Instanzkarte.** Die Zeile zeigte den Kartennamen nur bei
  ASA-Instanzen — bei ARK: Survival Evolved, Satisfactory, 7D2D und Space Engineers fehlten Karte und
  RCON-Port. Jetzt gilt für alle: `<Karte> · <Spiel> · Port <n> · RCON <n>`, leere Angaben fallen weg.

## [0.13] — 2026-11-13

### Neu
- **Download-Geschwindigkeit im Installationsfenster.** Neben Schritt und Prozent steht jetzt die
  aktuelle Rate in MB/s — berechnet aus den Byte-Zahlen der steamcmd-Zeilen und geglättet, damit
  die Anzeige nicht springt.

## [0.12] — 2026-11-13

### Behoben
- **Instanzen starten nach der Installation nicht mehr von selbst.** Der Supervisor wurde direkt
  nach der Installation aktiviert; weil ein frisch installierter Server noch nie lief, deutete er
  „Prozess weg" als Absturz und fuhr den Server sofort hoch. Jetzt wird die Instanz vor dem
  Dienststart als „gestoppt" markiert (`runner.mark_stopped`) — Start nur noch über „Start" im
  Panel. Der Marker verschwindet beim Start, die Absturz-Erkennung arbeitet danach wie gewohnt;
  auch nach einem Systemstart bleibt eine nie gestartete Instanz aus.

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
- **Hinweis-Popup zum Experimental-Modus entfernt.** Seit der Server die Hardwareprüfung besteht, war
  das Fenster „Server läuft im Experimental-Modus" (plus die Warnleiste im Einstellungsreiter) nur noch
  im Weg — es legte sich über die ganze Seite und schluckte Klicks. Beides ist raus, samt
  `/api/experimental` und den zugehörigen Sprachschlüsseln; am Feld `ExperimentalMode` steht weiter
  „wirksam: AN/aus" aus dem Serverlog, falls SE doch einmal selbst umschaltet.
- **„Installieren" öffnet wieder den Fortschritt.** Lag der zuletzt gemerkte Reiter auf
  „Einstellungen", verdeckte er das Installationsfenster — der Klick wirkte, als lande man in den
  Einstellungen, während im Hintergrund korrekt installiert wurde. Während einer laufenden
  Installation schaltet die Instanzseite jetzt selbst auf „Übersicht" mit Balken und Log.
- **Frische Installation startet jetzt wirklich ohne Experimental.** Die Vorlage lieferte
  `PhysicsIterations 1` und `BlockLimitsEnabled NONE`, neue Instanzen zusätzlich `MaxPlayers 20` —
  drei Abweichungen vom Vanilla-Satz, wegen denen SE von sich aus auf Experimental schaltet
  (`Experimental mode reason: MaxPlayers, PhysicsIterations, BlockLimitsEnabled`). Vorlage und
  Instanz-Vorgabe sind jetzt Vanilla: Physics 8, Block-Limits GLOBALLY, 16 Spieler; dass mehr als
  16 Spieler Experimental erzwingt, steht als Hinweis am Feld.
- **Löschen blockiert die Oberfläche nicht mehr.** Stoppen (SE speichert bis zu 90 s) und das
  Entfernen mehrerer GB laufen jetzt als Hintergrund-Job; die Karte zeigt „Server wird gestoppt …",
  dann „Serverdateien werden gelöscht …" und am Ende die freigegebene Größe. Jeder Löschvorgang steht
  außerdem mit Zeitstempel und freigegebenen MB im `panel.log`.
- **Wine wird im Installer ohne Rückfrage installiert** — wie Xvfb und `gcc`. Die Frage „Wine
  installieren?" wurde erfahrungsgemäß mit „nein" beantwortet, danach startete kein Windows-Spiel.
