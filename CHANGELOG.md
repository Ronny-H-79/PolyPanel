## [0.41] — 2026-11-21

### Behoben

- **SFTP-Zugang blieb nach kurzer Zeit tot.** Der Dienst hat alle 30 Sekunden alle Listener
  geschlossen und neu gebunden; das `wait_closed()` des asyncssh-Servers kann ohne bestehende
  Verbindung haengenbleiben. Danach war der Port (Standard 2225) dauerhaft geschlossen, obwohl die
  Unit weiterlief — Verbindungen wurden mit „Connection refused" abgewiesen. Der Dienst bindet
  jetzt einmal und laesst die Listener stehen; neu gebunden wird nur, wenn sich Port, Benutzer,
  Passwort oder Chroot einer Instanz aendern (Pruefung alle 10 Sekunden).

## [0.40] — 2026-11-21

### Behoben

- **7 Days to Die: Beitritts-Passwort ist jetzt ein eigenes Feld.** `ServerPassword` hing an
  `rcon_password` (`ALIASES`, `write_config`, Kernfeld) — jedes Speichern des Server-Passworts
  überschrieb damit das RCON-Passwort und umgekehrt. Im Panel stand dauerhaft der zufällig erzeugte
  Hex-Wert, ein eingetragenes Passwort war nach dem nächsten Start wieder weg. Jetzt gilt
  `inst.server_password` (wie bei Empyrion/StarRupture), `rcon_password` bleibt unberührt.

## [0.24] — 2026-11-16

### Neu
- **Empyrion: alle Konfigurationsdateien im Reiter „Einstellungen"** (80 Felder):
  `dedicated.yaml` vollständig (ServerConfig + GameConfig, inkl. Reserve-Playfields, LogFlags,
  KickPlayerWithPing, PlayerLoginParallelCount, EnableDLC, Seed, Notes), der Mehrspieler-Block aus
  `gameoptions.yaml` des Szenarios (49 Spielregeln: Verfall, Anti-Grief, Handel, Strukturen …) und
  die Adminliste aus `adminconfig.yaml` (SteamID64:Stufe — 3 GameMaster, 6 Moderator, 9 Admin).
  Die Adminliste wird beim ersten Speichern aus `adminconfig.example.yaml` angelegt.
- Der Einzelspieler-Block in `gameoptions.yaml` bleibt unangetastet.

## [0.23] — 2026-11-15

### Neu
- **Empyrion: alle Einstellungen im Panel.** Der Reiter „Einstellungen" zeigt jetzt die
  Schlüssel aus `dedicated.yaml` (ServerConfig und GameConfig): Name, Port, Spielerzahl,
  Passwort, Beschreibung, Sichtbarkeit, Reserve-Playfields, Auto-Neustart, EAC, Bauklasse,
  Blueprints, Heartbeat, Start-Timeout, Telnet (an/Port/Passwort), Spielstand-Name, Modus,
  Szenario und Speicherordner. Werte werden direkt in der YAML gepflegt — Einrückung,
  Reihenfolge und Kommentare der Vorlage bleiben erhalten, auskommentierte Passwörter werden
  nicht als gesetzt angezeigt.

## [0.22] — 2026-11-15

### Behoben
- **Empyrion startet jetzt wirklich.** Drei Korrekturen am Profil: Startdatei ist
  `DedicatedServer/EmpyrionDedicated.exe` (im Wurzelordner liegen nur Batchdateien und der
  Launcher), Unity braucht `-nographics` **zusammen mit** `-batchmode` (einzeln: „requires
  -batchmode"), und `dedicated.yaml` wird nur innerhalb des `ServerConfig:`-Blocks gepflegt —
  Schlüssel auf oberster Ebene lehnt der Server mit „config file is updated to the current
  server version" ab und bricht ab.

## [0.21] — 2026-11-15

### Neu
- **Empyrion: Galactic Survival als Spielprofil.** Dedicated Server über SteamCMD
  (App 530870, Windows-Binary unter Wine). Konfiguration in `dedicated.yaml`
  (`Srv_Name`, `Srv_Port`, `Srv_MaxPlayers`, `Srv_Password`) — Kommentare und Reihenfolge
  der Vorlage bleiben erhalten, unbekannte Schlüssel werden nicht angefasst. Start ohne
  Grafik über `EmpyrionDedicated_NoGraphics.exe`, Spielport UDP 30000. Kein RCON; kein
  Mod-Reiter (die Modverwaltung im Panel ist ARK-spezifisch).

## [0.20] — 2026-11-15

### Neu
- **Karte zeigt, was gerade läuft.** Bisher stand bei einem laufenden Update nur "AUS".
  Jetzt erscheint eine Hinweiszeile (⏳ UPDATE LÄUFT, INSTALLATION LÄUFT, NEUSTART LÄUFT,
  WIRD GESTOPPT, WIRD GELÖSCHT, ASAPI WIRD EINGERICHTET). Quelle sind die laufenden
  Aktionen im Panel (Installation, SteamCMD-Update, Start/Stop/Restart/Löschen).

## [0.19] — 2026-11-15

### Behoben
- **StarRupture ohne Mod-Reiter.** Das Spiel kennt keine Mods; der Reiter „Mods" wird bei dieser
  Spielart ausgeblendet, statt eine leere Suche anzubieten.
- **StarRupture-Installation scheiterte mit „Invalid platform".** Der Schalter
  `+@sSteamCmdForcePlatformType windows` wurde nur für ARK gesetzt; StarRupture hat ebenfalls nur
  einen Windows-Server. Die Liste der Windows-Only-Spiele steht jetzt zentral in `installer.py`
  (`WINDOWS_ONLY_APPS`).

## [0.18] — 2026-11-15

### Neu
- **StarRupture als Spielprofil.** Dedicated Server über SteamCMD (App-ID 3809400, Windows-Binary
  unter Wine). Angelegt wird die Instanz wie jede andere: Name, Port (UDP 7777), Spielerzahl. Die
  Startdatei wird gesucht (`StarRuptureServerEOS.exe`, `StarRuptureServer.exe` oder Pfad unter
  `Binaries/Win64`), die Konfiguration landet in `DSSettings.txt` neben der Startdatei
  (ServerName, Port, MaxPlayers, Passwort wenn gesetzt). Es gibt keinen Steuerkanal — Start, Stop,
  Update, Backups und Datei-Browser funktionieren, RCON/Spielerkonsole nicht; „Bereit" erkennt das
  Panel am belegten UDP-Port.

## [0.17] — 2026-11-14

### Geändert
- **Kein zusätzliches Fenster mehr beim Anlegen und Installieren.** Bisher öffnete das Panel für die
  neue Instanz ein eigenes Fenster mit der Einrichtung. Jetzt bleibt das Anlegen in der Übersicht
  (die neue Karte erscheint dort), und die Installation zeigt ihren Fortschritt im selben Tab.

## [0.16] — 2026-11-14

### Neu
- **AsaApi gehört bei ARK-Instanzen zur Installation.** Nach dem SteamCMD-Lauf richtet das Panel
  AsaApi automatisch ein (komplettes Release inklusive `config.json` und der mitgelieferten DLLs) und
  startet die Instanz danach über `AsaApiLoader.exe`. Der Knopf **„API"** auf der Instanzkarte
  installiert oder aktualisiert die API jederzeit von Hand; er erscheint nur, wenn er etwas zu tun
  hat, und trägt bei einem neueren Release ein Badge mit der Version. Im Reiter „Mods" schaltet eine
  Checkbox die API samt Plugins wieder aus. Andere Spiele bleiben unberührt — dort taucht weder der
  Knopf noch die Checkbox auf.
- **Firewall wird mitgemacht.** Beim Start trägt das Panel Spiel- und Port der Instanz (UDP) in `ufw`
  ein, beim Löschen der Instanz werden die Regeln wieder entfernt. Ohne diese Freigaben läuft der
  Server, ist aber von aussen nicht erreichbar. Für `ufw` legt der Installer eine eng begrenzte
  `sudo`-Regel an (nur `/usr/sbin/ufw`); fehlt sie, startet der Server trotzdem und das Panel-Log
  nennt den Grund.
- **Mod-IDs direkt eintragen** (ARK). Im Reiter „Mods" gibt es ein Feld für die Mod-IDs (Komma,
  Semikolon oder Leerzeichen als Trenner). Es zeigt die aktive Liste und ersetzt sie beim Speichern.

### Geändert
- **Metriken zählen alle Prozesse der Instanz.** Bisher wurden nur die Starter-PID und ihre direkten
  Kinder gemessen; unter Wine/Proton und mit API-Loader hängt der eigentliche Serverprozess aber nicht
  daran, sodass CPU und RAM als 0 erschienen. Jetzt werden alle Prozesse der Instanz über ihre
  Kommandozeile gefunden und summiert.
- **SessionName und MaxPlayers bleiben erhalten** (ARK): Werte, die in der `GameUserSettings.ini`
  geändert werden, wandern zurück in die Instanz statt beim nächsten Start überschrieben zu werden.
- Die Sektion in der `Game.ini` wird unabhängig von der Schreibweise erkannt, damit keine zweite
  `ActiveMods`-Zeile entsteht.

### Behoben
- Start über `AsaApiLoader.exe` brach mit „LoaderFailed, Reason: UnknownLoaderResult" ab, wenn im
  Win64-Ordner die `config.json` des API-Releases fehlte.
- Eine doppelte `ActiveMods`-Zeile konnte dafür sorgen, dass eingetragene Mods beim Start
  stillschweigend ignoriert wurden.

## [0.15] — 2026-11-14

### Neu
- **Datei-Browser im Panel.** Der Reiter „Dateien" der Instanzseite zeigt den Instanzordner im
  Browser: Ordner öffnen, Dateien hochladen (mehrere gleichzeitig), herunterladen, umbenennen,
  löschen und neue Ordner anlegen. Alles bleibt im Instanzordner — Pfade mit `..` werden abgewiesen
  (`Pfad liegt ausserhalb der Instanz`), Downloads laufen als Stream auch bei großen Dateien.
  **Dateien lesen und ändern:** Klick auf den Namen öffnet den Inhalt im Browser (Text bis 2 MB,
  Binärdateien werden abgewiesen), „Speichern" schreibt zurück und legt vorher eine `.bak`-Sicherung an.
- **SFTP-Zugang pro Instanz.** Auf der Instanzkarte läßt sich SFTP ein- und ausschalten; der
  Zugang ist auf den Instanzordner beschränkt (Chroot), Benutzer und Passwort werden je Instanz
  erzeugt, der Port kommt aus `sftp_base_port + laufender Nummer` (Standard 2225). „Neues Passwort"
  legt sofort ein neues an und kopiert es in die Zwischenablage.
- Der SFTP-Dienst läuft als eigener systemd-Dienst `polypanel-sftp` (Benutzer- oder Systemdienst,
  je nachdem wie das Panel installiert ist) und liest die Ports/Passwörter alle 30 Sekunden neu ein.
  Er hängt nicht am Laufzeitzustand der Instanz: Dateien hochladen geht auch bei gestopptem Server.

### Geändert
- **Token bleibt gleich.** Der Web-Token wird nur beim allerersten Start erzeugt und danach immer aus
  `~/.config/polypanel/token` gelesen — Neustart, Update und Selbst-Update ändern ihn nicht. Alte Links
  funktionieren also weiter; ein neuer Token entsteht erst, wenn die Datei gelöscht wird.
- Instanz-JSON kennt `sftp_enabled`, `sftp_user`, `sftp_password`, `sftp_port`; die Adresse
  `sftp://benutzer@host:port` steht auf der Karte, FileZilla-kompatibel (SFTP, kein FTP).

### Voraussetzung
- `asyncssh` (z. B. `apt install python3-asyncssh`). Fehlt es, läuft das Panel unverändert weiter,
  nur der SFTP-Dienst meldet im Panel-Log, was fehlt.

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