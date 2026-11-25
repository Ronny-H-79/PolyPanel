## [0.70] - 2026-11-25

- Vor jedem Löschen kommt jetzt eine Rückfrage: Datei, Mod, Mod-Dateien, Snapshot, Backup und
  Whitelist-Eintrag. Die Texte stehen in beiden Sprachen, bisher waren sie fest auf Deutsch.

## [0.69] - 2026-11-24

- Dateien im Editor: lange Zeilen werden nicht mehr umbrochen, sondern seitlich gescrollt.

## [0.68] - 2026-11-24

- Fußzeile auch auf dem Dashboard. Version, Lizenz-Link, PayPal und Discord standen bisher nur auf
  der Instanzseite, weil die Vorlage den Platzhalter nicht kannte.

## [0.67] - 2026-11-24

- Tests statt „läuft bei mir". 27 Prüfungen mit der Standardbibliothek (`tests/`): Ini-Behandlung
  (doppelte Schlüssel, Kommentare, CRLF, Idempotenz), Mod-Reihenfolge und Anpinnen, Update-Entscheidung
  (kein Rückwärts-Angebot), Vollständigkeit der Routen und ein Rauchtest, der den Webserver in einem
  temporären Verzeichnis startet und Anmeldung, Kernrouten und Instanzverwaltung prüft.
- **GitHub Actions** (`.github/workflows/ci.yml`): bei jedem Push und Pull Request auf Python 3.10,
  3.12 und 3.13 - Stilprüfung, Textprüfung, Tests.
- **`ruff` sauber** mit Konfiguration in `pyproject.toml`; dabei gefundene echte Fehler behoben:
  doppelte Textschlüssel (der zweite Eintrag hat den ersten still überschrieben), unbenutzte
  Zuweisungen, fehlendes `raise … from`, mehrdeutige Variablennamen.
- Der POST-Handler ist zerlegt. Statt einer 559-Zeilen-Kette gibt es jetzt 22 Methoden je
  Fachthema (Mods, Dateien, Backups, Zeitplan …) und eine Route-Tabelle `_POST_ROUTES`. Verhalten
  unverändert: gegen die Vorgängerfassung wurden 31 Anfragen verglichen, keine Abweichung.
- `CONTRIBUTING.md` beschreibt Testlauf, Regeln für Änderungen und Fehlermeldungen.

## [0.66] - 2026-11-24

- Freie Lizenz: MIT. Das Projekt stand bisher unter „alle Rechte vorbehalten". Ab jetzt darf
  jeder es nutzen, ändern, weitergeben und auch kommerziell einsetzen - Bedingung ist nur, dass
  Copyright-Hinweis und Haftungsausschluss erhalten bleiben. `LICENSE` enthält den vollständigen
  Text, README und Dokumentation sind angepasst, die Fußzeile zeigt „MIT-Lizenz".

## [0.65] - 2026-11-24

- Handy-Regeln fehlten auf der Instanzseite. Der Instanz-Reiter hatte ein eigenes
  `<style>`-Element, in dem der Handy-Block nicht angehängt war - dort blieb die Dateiliste breit
  und die Kästchen klein. Die Regeln stehen jetzt auch dort am Ende.

## [0.64] - 2026-11-24

- Dateiliste auf dem Handy ohne Seitwärts-Scrollen. Jede Zeile ist jetzt ein kleiner Block:
  Dateiname oben links, Größe oben rechts, Datum unten links, die vier Aktions-Kästchen unten
  rechts. Statt die 520-px-Tabelle seitlich zu schieben, passt alles in die Bildschirmbreite.

## [0.63] - 2026-11-24

- Aktions-Kästchen auf dem Handy 36 × 36 px. Beim Aufräumen war die Vergrößerung für schmale
  Bildschirme verloren gegangen; die Felder bleiben jetzt auch mobil groß genug für den Daumen.

## [0.62] - 2026-11-24

- Streuklammer im Stylesheet. Nach dem Umbau der Handy-Regeln blieb eine überzählige `}` in
  den Basisstilen stehen; die Dateiliste verlor dadurch ihr `overflow-x` und schob die Seite auf
  543 px. Regel sitzt jetzt im Handy-Block, die Seite bleibt bei 375 px.

## [0.61] - 2026-11-24

- Dateiliste schob die Seite in die Breite. Die Tabelle mit 520 px Mindestbreite zwang die
  ganze Seite auf 556 px, obwohl der Bildschirm 390 px hat - man musste die Seite seitlich
  schieben. Abschnitte und Karten dürfen jetzt schrumpfen (`min-width:0`), die Tabelle scrollt
  nur in ihrem eigenen Kasten.

## [0.60] - 2026-11-24

- Server-Log auf dem Handy lesbar. Schrift von winzig auf 12 px, mehr Zeilenhöhe und ein
  höherer Logkasten (58 vh), damit man nicht zoomen muss. Statusabzeichen in der Kopfzeile sind
  etwas größer und besser zu treffen.

## [0.59] - 2026-11-24

- Kopfzeile auf dem Handy ist eine Zeile. CPU, RAM, Version, Changelog, Panel-Neustart und
  Sprachwahl stehen nebeneinander und lassen sich seitlich wischen, statt in vier Zeilen
  untereinander zu laufen. Der Kopf schrumpft dadurch von 227 auf rund 90 Pixel.

## [0.58] - 2026-11-24

- Handy-Regeln griffen nicht. Der Mobile-Block stand mitten im Stylesheet und wurde von
  späteren Basisregeln überschrieben - Eingabefelder blieben bei 14 px (und das iPhone zoomt beim
  Antippen hinein), die Kopfzeile blieb 248 px hoch. Die Regeln stehen jetzt als eigener Block am
  Ende des Stylesheets und gelten sicher.

## [0.57] - 2026-11-24

- Handy-Ansicht aufgeräumt. Unter 720 px Breite: einspaltiges Layout, Karten und Abschnitte
  in voller Breite, Kennzahlen 2×2 statt 4 nebeneinander, Einstellungen mit Beschriftung über dem
  Feld statt daneben, Tabs waagerecht scrollbar, Knöpfe mindestens 40 px hoch und Eingabefelder
  mit 16 px Schrift (verhindert das Hineinzoomen auf dem iPhone). Kopfzeile bricht um, statt
  über den Rand zu laufen.

## [0.56] - 2026-11-24

- Aktions-Symbole in der Dateiliste sind jetzt Kästchen. Statt nackter kleiner Symbole steht
  jede Aktion in einem eigenen Feld (30×30 px, auf dem Handy 34×34): Herunterladen grün umrandet,
  Löschen rot. Dadurch sind sie mit dem Finger sicher zu treffen.
- Die Dateiliste scrollt auf schmalen Bildschirmen waagerecht, statt Spalten zu quetschen.

## [0.55] - 2026-11-24

- Vollansicht lag im falschen Abschnitt. Das Overlay stand im Übersichts-Reiter (der beim
  Öffnen ausgeblendet ist) statt außerhalb der Tabs - dadurch blieb es unsichtbar, obwohl der
  Inhalt geladen wurde. Es hängt jetzt direkt hinter `<main>` und deckt die Seite unabhängig vom
  aktiven Reiter ab.

## [0.54] - 2026-11-24

- Dateien herunterladen. Jede Datei hat in der Liste einen eigenen Download-Pfeil (⬇) - ein
  echter Link, der Browser speichert die Datei direkt, ohne Umweg über den Editor. Endung und
  Name bleiben erhalten (`Content-Disposition`).
- Direkte Vollansicht. Das Symbol ⤢ öffnet die Datei im Vollbild über die ganze Seite: großer
  Editor, Speichern, Herunterladen, Schließen. `Esc` schließt sie wieder. Der kleine Vorschaukasten
  darunter bleibt für den schnellen Blick.

- Aktionsspalte in der Dateiliste. Herunterladen, Vollansicht, Umbenennen und Löschen stehen
  jetzt als eigene Symbole rechts in der Zeile statt zwischen Dateinamen und Größe.

## [0.53] - 2026-11-24

- Die Update-Anzeige bot einen Rückschritt an. Stand lokal schon eine neuere Version als auf
  GitHub (eigener Deploy vor dem Push), meldete das Panel „update 0.52 → 0.51“ - also ein
  Downgrade als Update. Jetzt gilt nur noch eine **höhere** GitHub-Version als Update; ist die
  eigene Fassung voraus, bleibt die Anzeige auf „aktuell“.
- Veralteter Cache hielt die alte Anzeige fest. Der 10-Minuten-Cache wurde auch dann
  ausgeliefert, wenn die darin vermerkte „neue“ Version älter war als die installierte. Solche
  Einträge werden jetzt verworfen und frisch geprüft.
- Die Build-Datei wird nicht mehr mitgeliefert. `.build` lag im Repo und wurde bei jedem
  Deploy mit einer uralten Fassung  überschrieben - dadurch meldete das Panel dauerhaft
  „neuer Build verfügbar“, obwohl Version und Commit schon stimmten. Die Datei entsteht jetzt nur
  noch beim Update bzw. Deploy.

## [0.52] - 2026-11-24

- Aktionsleiste der Instanzkarten. Statt sechs grauer Textknöpfe steht auf jeder Karte eine
  farbige Pille mit drei Gruppen - wie in einem Dateimanager: **rot** anhalten und löschen,
  **blau** Menü, Update, AsaApi, **grün** starten und neu starten. Die Symbole tragen den Text als
  Tooltip, gesperrte Aktionen bleiben sichtbar (blass) statt zu verschwinden, und ein kleiner Punkt
  am AsaApi-Symbol zeigt an, dass dort ein Update wartet.

## [0.51] - 2026-11-24

- Mods sortieren und anpinnen. Im Mods-Reiter lassen sich aktive Mods mit ▲/▼ oder per
  Drag & Drop umsortieren; ein Pin (📍) hält eine Mod dauerhaft oben (📌), etwa Stacking-Mods, die
  früh laden müssen. Die Reihenfolge ist die **Ladeliste**: sie wandert in `-mods=` der Startzeile
  und in `ActiveMods` der Game.ini. Reine Umsortierung schreibt nur diese eine Zeile - die Game.ini
  bleibt sonst Byte für Byte unangetastet.

- Die Game.ini wird nicht mehr neu geschrieben. `ark_write_ini()` hat die Datei über
  `configparser` komplett neu erzeugt; der Parser hält je Sektion nur einen Wert pro Schlüssel und
  wirft Wiederholungen weg. In einer echten ARK-Datei verschwanden so 795 `EngramEntryAutoUnlocks`,
  156 `ConfigOverrideItemMaxQuantity` und 99 `OverridePlayerLevelEngramPoints` (1.182 Zeilen und
  121 KB wurden zu 128 Zeilen und 18 KB), Werte wurden umgeschrieben (`true` → `True`,
  `DifficultyOffset=4` → `1.0`). Jetzt werden nur einzelne Zeilen gesetzt; alles andere bleibt erhalten.
- Das Server-Passwort bleibt stehen. `ark_write_ini()` hat `ServerPassword` bei jedem Start fest
  auf leer gesetzt; ein eingetragenes Beitrittspasswort war damit nach dem nächsten Start weg.
- Admin-Werte in der GameUserSettings.ini bleiben stehen. `ServerPVE`, `DifficultyOffset`,
  `ServerCrosshair` und `ShowMapPlayerLocation` werden nur noch eingetragen, wenn sie fehlen.
- INI-Sicherungen landen im Unterordner `backup/` neben den INIs statt als `.bak` daneben
  (je Datei die letzten 20 Fassungen). Der Serverordner sammelt keine Sicherungsdateien mehr.
- Zeilenenden bleiben erhalten. Gespeicherte INIs wurden mit LF statt CRLF geschrieben und
  schrumpften dabei um ein Byte je Zeile.
- Backups „vor Update“ werden als solche benannt statt unter „älter“ zu laufen.
## [0.50] - 2026-11-21

- Satisfactory: Spieler-Bereich war im Panel ausgeblendet. Eine alte CSS-Regel
  (`body[data-game="satisfactory"] #secPlayers{display:none}`) versteckte die Spielerliste
  vollstaendig - die Daten kamen an, waren aber nie zu sehen. Die Regel ist entfernt.
- Spielerliste: keine wirkungslosen Knoepfe mehr. Bei Spielern ohne ID (Satisfactory nennt
  nur Namen) wurden Kick/Ban/Whitelist/Item-Knoepfe mit leerem Wert angezeigt; sie erscheinen nur
  noch, wenn eine ID vorliegt.

## [0.49] - 2026-11-21

- Satisfactory: Spielernamen kommen jetzt aus dem Serverlog. Ab Spielversion 1.2 liefert
  `QueryServerState` keine `playerStates` mehr - die API meldet nur noch
  `numConnectedPlayers`. Das Panel liest die Namen deshalb aus dem Log des laufenden Servers
  (`LogNet: Join succeeded: <Name>`, beim Gehen `UNetConnection::Close ... Name: <Name>`) und
  beginnt erst an der Startmarke des letzten Serverlaufs, damit alte Sitzungen nicht mitzaehlen.
  Aeltere Serverversionen mit `playerStates` liefern weiterhin direkt aus der API.

## [0.48] - 2026-11-21

- Satisfactory: Spielerliste blieb leer, auch mit API-Token. Das Panel fragte die Spieler immer
  ueber `ListPlayers` ab - einen Befehl, den Satisfactory nicht kennt (die Abfrage endete im
  `insufficient_scope`-Fehler des API-Aufrufs und die Liste blieb leer). Jetzt hat der spieleigene
  Weg Vorrang: Satisfactory liefert die Spieler aus `QueryServerState`, alle anderen Spiele
  weiterhin ueber RCON/Telnet.

## [0.47] - 2026-11-21

- Satisfactory: API-Token im Panel eintragbar. Ohne Token antwortet der Server auf
  `QueryServerState` und `RunCommand` mit `insufficient_scope` - im Panel blieb die Spielerliste
  deshalb leer und Befehle liefen ins Leere. Das Feld gab es bisher gar nicht. Token im Spiel
  erzeugen (Server Manager -> Konsole -> `server.GenerateAPIToken`) und im Panel unter
  „API-Token" eintragen; er landet in der Instanz, nicht in einer Weltdatei.

## [0.46] - 2026-11-21

- Satisfactory: Server-Passwort laesst sich jetzt wirklich aendern und entfernen. Das Profil
  schrieb `ServerPassword` nur, wenn ein Wert gesetzt war - beim Leeren blieb der alte Wert in der
  `GameUserSettings.ini` stehen, der Server fragte weiter danach. Jetzt wird der Eintrag immer
  geschrieben (leer = kein Passwort).
- Einstellungen: geleerte Felder werden gesendet. Das Formular schickte nur nicht-leere Werte;
  dadurch liess sich kein Passwort entfernen (Meldung „keine Aenderungen"). Leere Werte gehen jetzt
  mit, wenn vorher etwas drinstand - unveraenderte leere Felder bleiben ausgespart.
- Einstellungen: Passwortfelder werden als Passwortfelder angezeigt (vorher Klartext-Textfeld
  mit sichtbarem Passwort).

## [0.45] - 2026-11-21

- Panel-Oberflaeche: Syntaxfehler in 0.44 behoben. Die Datei-Beschriftung fuer die neuen
  Live-Regeln brachte eine zusaetzliche Klammer in das Panel-JavaScript; das Panel blieb leer,
  weil keine Funktion definiert wurde. Jetzt korrekt verkettet, JavaScript geprueft (`node --check`).
- Panel-Quelltext: keine Python-Syntaxwarnungen mehr. Zwei JavaScript-Regexe (`\/` und `\d`)
  waren als einfache Zeichenkette notiert; sie stehen jetzt korrekt maskiert, die Ausgabe bleibt gleich.

## [0.44] - 2026-11-21

- 7 Days to Die: Blutmond und Spielregeln im Panel. Ab Version 2.0 des Spiels stehen
  Blutmond, Schwierigkeit, Loot, XP, Zombie-Tempo und aehnliche Regeln nicht mehr einzeln in der
  `serverconfig.xml` - FFP hat sie in den `SandboxCode` gepackt. Das Panel zeigt sie deshalb als
  eigene Gruppen „Blutmond" (Haeufigkeit, Gegnerzahl, Fenster, Warnung) und „Spielregeln (live)"
  (Schwierigkeit, XP, Loot, Luftabwurf, Tag-Nacht-Laenge, Todesstrafe, Zombie-Tempo, Block-Schaden,
  Quest-Limit). Die Werte gehen per `setgamepref` sofort an den laufenden Server; die Ist-Werte
  liest das Panel mit einem einzigen `getgamepref` (15 Sekunden zwischengespeichert).

- 7 Days to Die: gesetzte Live-Regeln ueberleben einen Neustart. Das Panel merkt sich die
  Werte in der Instanz und setzt sie nach jedem Serverstart automatisch erneut - einmal je
  Server-PID, damit haeufige Statusabfragen keinen zweiten Aufruf ausloesen.

## [0.43] - 2026-11-21

- Dateien: Fortschrittsbalken beim Hochladen. Ueber der Dateiliste laeuft ein Balken mit
  Prozentwert mit; die Statuszeile zeigt zusaetzlich Datei, Nummer und Prozent
  („lade 12/53 (42%): Mods/…/ModInfo.xml"). Der Upload laeuft ueber XMLHttpRequest, weil nur so
  der tatsaechliche Fortschritt der Leitung bekannt ist (`fetch` kann das nicht). Prozent bezieht
  sich auf die Gesamtgroesse aller Dateien im Stapel; beim Erfolg verschwindet der Balken nach
  2,5 Sekunden, bei Fehlern bleibt er mit der Fehlerzeile stehen.

## [0.42] - 2026-11-21

- Dateien: ganze Ordner hochladen. Neuer Knopf „Ordner hochladen" und Drag & Drop auf die
  Dateiliste: Ordner mit allen Unterordnern werden rekursiv uebertragen, die Struktur bleibt
  erhalten (`Mods/<Mod>/Config/...`). Bisher wanderten nur einzelne Dateien in den offenen Ordner,
  Unterordner musste man von Hand anlegen. Fortschritt („lade 12/53") und Fehlerzeile stehen
  im Dateien-Tab, Uploads laufen einzeln und ueberstehen damit die 2-GB-Grenze je Datei.

## [0.41] - 2026-11-21

- SFTP-Zugang blieb nach kurzer Zeit tot. Der Dienst hat alle 30 Sekunden alle Listener
  geschlossen und neu gebunden; das `wait_closed()` des asyncssh-Servers kann ohne bestehende
  Verbindung haengenbleiben. Danach war der Port (Standard 2225) dauerhaft geschlossen, obwohl die
  Unit weiterlief - Verbindungen wurden mit „Connection refused" abgewiesen. Der Dienst bindet
  jetzt einmal und laesst die Listener stehen; neu gebunden wird nur, wenn sich Port, Benutzer,
  Passwort oder Chroot einer Instanz aendern (Pruefung alle 10 Sekunden).

## [0.40] - 2026-11-21

- 7 Days to Die: Beitritts-Passwort ist jetzt ein eigenes Feld. `ServerPassword` hing an
  `rcon_password` (`ALIASES`, `write_config`, Kernfeld) - jedes Speichern des Server-Passworts
  überschrieb damit das RCON-Passwort und umgekehrt. Im Panel stand dauerhaft der zufällig erzeugte
  Hex-Wert, ein eingetragenes Passwort war nach dem nächsten Start wieder weg. Jetzt gilt
  `inst.server_password` (wie bei Empyrion/StarRupture), `rcon_password` bleibt unberührt.

## [0.24] - 2026-11-16

- Empyrion: alle Konfigurationsdateien im Reiter „Einstellungen" (80 Felder):
  `dedicated.yaml` vollständig (ServerConfig + GameConfig, inkl. Reserve-Playfields, LogFlags,
  KickPlayerWithPing, PlayerLoginParallelCount, EnableDLC, Seed, Notes), der Mehrspieler-Block aus
  `gameoptions.yaml` des Szenarios (49 Spielregeln: Verfall, Anti-Grief, Handel, Strukturen …) und
  die Adminliste aus `adminconfig.yaml` (SteamID64:Stufe - 3 GameMaster, 6 Moderator, 9 Admin).
  Die Adminliste wird beim ersten Speichern aus `adminconfig.example.yaml` angelegt.
- Der Einzelspieler-Block in `gameoptions.yaml` bleibt unangetastet.

## [0.23] - 2026-11-15

- Empyrion: alle Einstellungen im Panel. Der Reiter „Einstellungen" zeigt jetzt die
  Schlüssel aus `dedicated.yaml` (ServerConfig und GameConfig): Name, Port, Spielerzahl,
  Passwort, Beschreibung, Sichtbarkeit, Reserve-Playfields, Auto-Neustart, EAC, Bauklasse,
  Blueprints, Heartbeat, Start-Timeout, Telnet (an/Port/Passwort), Spielstand-Name, Modus,
  Szenario und Speicherordner. Werte werden direkt in der YAML gepflegt - Einrückung,
  Reihenfolge und Kommentare der Vorlage bleiben erhalten, auskommentierte Passwörter werden
  nicht als gesetzt angezeigt.

## [0.22] - 2026-11-15

- Empyrion startet jetzt wirklich. Drei Korrekturen am Profil: Startdatei ist
  `DedicatedServer/EmpyrionDedicated.exe` (im Wurzelordner liegen nur Batchdateien und der
  Launcher), Unity braucht `-nographics` **zusammen mit** `-batchmode` (einzeln: „requires
  -batchmode"), und `dedicated.yaml` wird nur innerhalb des `ServerConfig:`-Blocks gepflegt -
  Schlüssel auf oberster Ebene lehnt der Server mit „config file is updated to the current
  server version" ab und bricht ab.

## [0.21] - 2026-11-15

- Empyrion: Galactic Survival als Spielprofil. Dedicated Server über SteamCMD
  (App 530870, Windows-Binary unter Wine). Konfiguration in `dedicated.yaml`
  (`Srv_Name`, `Srv_Port`, `Srv_MaxPlayers`, `Srv_Password`) - Kommentare und Reihenfolge
  der Vorlage bleiben erhalten, unbekannte Schlüssel werden nicht angefasst. Start ohne
  Grafik über `EmpyrionDedicated_NoGraphics.exe`, Spielport UDP 30000. Kein RCON; kein
  Mod-Reiter (die Modverwaltung im Panel ist ARK-spezifisch).

## [0.20] - 2026-11-15

- Karte zeigt, was gerade läuft. Bisher stand bei einem laufenden Update nur "AUS".
  Jetzt erscheint eine Hinweiszeile (⏳ UPDATE LÄUFT, INSTALLATION LÄUFT, NEUSTART LÄUFT,
  WIRD GESTOPPT, WIRD GELÖSCHT, ASAPI WIRD EINGERICHTET). Quelle sind die laufenden
  Aktionen im Panel (Installation, SteamCMD-Update, Start/Stop/Restart/Löschen).

## [0.19] - 2026-11-15

- StarRupture ohne Mod-Reiter. Das Spiel kennt keine Mods; der Reiter „Mods" wird bei dieser
  Spielart ausgeblendet, statt eine leere Suche anzubieten.
- StarRupture-Installation scheiterte mit „Invalid platform". Der Schalter
  `+@sSteamCmdForcePlatformType windows` wurde nur für ARK gesetzt; StarRupture hat ebenfalls nur
  einen Windows-Server. Die Liste der Windows-Only-Spiele steht jetzt zentral in `installer.py`
  (`WINDOWS_ONLY_APPS`).

## [0.18] - 2026-11-15

- StarRupture als Spielprofil. Dedicated Server über SteamCMD (App-ID 3809400, Windows-Binary
  unter Wine). Angelegt wird die Instanz wie jede andere: Name, Port (UDP 7777), Spielerzahl. Die
  Startdatei wird gesucht (`StarRuptureServerEOS.exe`, `StarRuptureServer.exe` oder Pfad unter
  `Binaries/Win64`), die Konfiguration landet in `DSSettings.txt` neben der Startdatei
  (ServerName, Port, MaxPlayers, Passwort wenn gesetzt). Es gibt keinen Steuerkanal - Start, Stop,
  Update, Backups und Datei-Browser funktionieren, RCON/Spielerkonsole nicht; „Bereit" erkennt das
  Panel am belegten UDP-Port.

## [0.17] - 2026-11-14

- Kein zusätzliches Fenster mehr beim Anlegen und Installieren. Bisher öffnete das Panel für die
  neue Instanz ein eigenes Fenster mit der Einrichtung. Jetzt bleibt das Anlegen in der Übersicht
  (die neue Karte erscheint dort), und die Installation zeigt ihren Fortschritt im selben Tab.

## [0.16] - 2026-11-14

- AsaApi gehört bei ARK-Instanzen zur Installation. Nach dem SteamCMD-Lauf richtet das Panel
  AsaApi automatisch ein (komplettes Release inklusive `config.json` und der mitgelieferten DLLs) und
  startet die Instanz danach über `AsaApiLoader.exe`. Der Knopf **„API"** auf der Instanzkarte
  installiert oder aktualisiert die API jederzeit von Hand; er erscheint nur, wenn er etwas zu tun
  hat, und trägt bei einem neueren Release ein Badge mit der Version. Im Reiter „Mods" schaltet eine
  Checkbox die API samt Plugins wieder aus. Andere Spiele bleiben unberührt - dort taucht weder der
  Knopf noch die Checkbox auf.
- Firewall wird mitgemacht. Beim Start trägt das Panel Spiel- und Port der Instanz (UDP) in `ufw`
  ein, beim Löschen der Instanz werden die Regeln wieder entfernt. Ohne diese Freigaben läuft der
  Server, ist aber von aussen nicht erreichbar. Für `ufw` legt der Installer eine eng begrenzte
  `sudo`-Regel an (nur `/usr/sbin/ufw`); fehlt sie, startet der Server trotzdem und das Panel-Log
  nennt den Grund.
- **Mod-IDs direkt eintragen** (ARK). Im Reiter „Mods" gibt es ein Feld für die Mod-IDs (Komma,
  Semikolon oder Leerzeichen als Trenner). Es zeigt die aktive Liste und ersetzt sie beim Speichern.

- Metriken zählen alle Prozesse der Instanz. Bisher wurden nur die Starter-PID und ihre direkten
  Kinder gemessen; unter Wine/Proton und mit API-Loader hängt der eigentliche Serverprozess aber nicht
  daran, sodass CPU und RAM als 0 erschienen. Jetzt werden alle Prozesse der Instanz über ihre
  Kommandozeile gefunden und summiert.
- SessionName und MaxPlayers bleiben erhalten (ARK): Werte, die in der `GameUserSettings.ini`
  geändert werden, wandern zurück in die Instanz statt beim nächsten Start überschrieben zu werden.
- Die Sektion in der `Game.ini` wird unabhängig von der Schreibweise erkannt, damit keine zweite
  `ActiveMods`-Zeile entsteht.

- Start über `AsaApiLoader.exe` brach mit „LoaderFailed, Reason: UnknownLoaderResult" ab, wenn im
  Win64-Ordner die `config.json` des API-Releases fehlte.
- Eine doppelte `ActiveMods`-Zeile konnte dafür sorgen, dass eingetragene Mods beim Start
  stillschweigend ignoriert wurden.

## [0.15] - 2026-11-14

- Datei-Browser im Panel. Der Reiter „Dateien" der Instanzseite zeigt den Instanzordner im
  Browser: Ordner öffnen, Dateien hochladen (mehrere gleichzeitig), herunterladen, umbenennen,
  löschen und neue Ordner anlegen. Alles bleibt im Instanzordner - Pfade mit `..` werden abgewiesen
  (`Pfad liegt ausserhalb der Instanz`), Downloads laufen als Stream auch bei großen Dateien.
  Dateien lesen und ändern: Klick auf den Namen öffnet den Inhalt im Browser (Text bis 2 MB,
  Binärdateien werden abgewiesen), „Speichern" schreibt zurück und legt vorher eine `.bak`-Sicherung an.
- SFTP-Zugang pro Instanz. Auf der Instanzkarte läßt sich SFTP ein- und ausschalten; der
  Zugang ist auf den Instanzordner beschränkt (Chroot), Benutzer und Passwort werden je Instanz
  erzeugt, der Port kommt aus `sftp_base_port + laufender Nummer` (Standard 2225). „Neues Passwort"
  legt sofort ein neues an und kopiert es in die Zwischenablage.
- Der SFTP-Dienst läuft als eigener systemd-Dienst `polypanel-sftp` (Benutzer- oder Systemdienst,
  je nachdem wie das Panel installiert ist) und liest die Ports/Passwörter alle 30 Sekunden neu ein.
  Er hängt nicht am Laufzeitzustand der Instanz: Dateien hochladen geht auch bei gestopptem Server.

- Token bleibt gleich. Der Web-Token wird nur beim allerersten Start erzeugt und danach immer aus
  `~/.config/polypanel/token` gelesen - Neustart, Update und Selbst-Update ändern ihn nicht. Alte Links
  funktionieren also weiter; ein neuer Token entsteht erst, wenn die Datei gelöscht wird.
- Instanz-JSON kennt `sftp_enabled`, `sftp_user`, `sftp_password`, `sftp_port`; die Adresse
  `sftp://benutzer@host:port` steht auf der Karte, FileZilla-kompatibel (SFTP, kein FTP).

### Voraussetzung
- `asyncssh` (z. B. `apt install python3-asyncssh`). Fehlt es, läuft das Panel unverändert weiter,
  nur der SFTP-Dienst meldet im Panel-Log, was fehlt.

## [0.14] - 2026-11-13

- Karte und RCON stehen jetzt auf jeder Instanzkarte. Die Zeile zeigte den Kartennamen nur bei
  ASA-Instanzen - bei ARK: Survival Evolved, Satisfactory, 7D2D und Space Engineers fehlten Karte und
  RCON-Port. Jetzt gilt für alle: `<Karte> · <Spiel> · Port <n> · RCON <n>`, leere Angaben fallen weg.

## [0.13] - 2026-11-13

- Download-Geschwindigkeit im Installationsfenster. Neben Schritt und Prozent steht jetzt die
  aktuelle Rate in MB/s - berechnet aus den Byte-Zahlen der steamcmd-Zeilen und geglättet, damit
  die Anzeige nicht springt.

## [0.12] - 2026-11-13

- Instanzen starten nach der Installation nicht mehr von selbst. Der Supervisor wurde direkt
  nach der Installation aktiviert; weil ein frisch installierter Server noch nie lief, deutete er
  „Prozess weg" als Absturz und fuhr den Server sofort hoch. Jetzt wird die Instanz vor dem
  Dienststart als „gestoppt" markiert (`runner.mark_stopped`) - Start nur noch über „Start" im
  Panel. Der Marker verschwindet beim Start, die Absturz-Erkennung arbeitet danach wie gewohnt;
  auch nach einem Systemstart bleibt eine nie gestartete Instanz aus.

## [0.11] - 2026-11-13

### Überblick
Grobe Zusammenfassung dessen, was in den Panels steckt.

- Zwei Panels, ein Unterbau: AscendedPanel für ARK: Survival Ascended, PolyPanel für ASA, ASE,
  Satisfactory, 7 Days to Die und Space Engineers. Bedienung im Browser, Dienst auf dem Server.
- **Dashboard:** Instanzkarten mit Status, Karte, Ports, Build, CPU/RAM, Spielern und Laufzeit;
  Start, Restart, Update, Stop und Löschen direkt auf der Karte, Knöpfe sperren sich nach Zustand
  (läuft Stop, ist nur noch Menü frei usw.).
- **Instanzseite:** Live-Log, Konfigurationseditor mit Sicherung und Prüfung (INI-Werte als Formular
  oder roh), Mod-Verwaltung mit CurseForge-Suche/Update-Prüfung, Backups, Snapshots, Zeitplan und
  RCON-Konsole mit Ein-Klick-Befehlen.
- **Spieler:** Liste mit Kick, Ban, Whitelist und Gegenstände verteilen - Katalog mit Suche und
  Mengenfenster; die nötige Spieler-ID (ARKID) wird aus den `.arkprofile`-Dateien gelesen, weil
  ARK per RCON nur die EOS-ID liefert.
- **Sperren:** eigenes Fenster „Gesperrte Spieler" mit Entbannen je Zeile und ehrlichem Hinweis,
  warum ARK seine Ban-Liste nicht über RCON herausgibt.
- **Betrieb:** Absturz-Erkennung mit automatischem Neustart, Discord-Benachrichtigungen,
  Sprache Deutsch/Englisch jederzeit umschaltbar, mehrere Instanzen in einem Prozess.
- **Fehlermeldungen:** Knopf im Panel, Meldung geht an den Betreiber (Webhook, nur auf der Konsole
  setzbar) - mit Version, Instanz, System und Logauszug, Passwörter entfernt.

- Space Engineers startet nicht mehr im Experimental-Modus. SE prüft beim Start Prozessorkerne,
  Takt und RAM (`ProcessorCount >= 3`, `CPUFrequency >= 3.2 GHz`, mindestens 6 GB RAM) und erzwingt
  sonst Experimental - Gäste werden dann abgewiesen, bis sie Experimental in ihren Spieloptionen
  einschalten. Den Takt liest SE per WMI, das unter Wine aus `/proc/cpuinfo` gespeist wird, und VMs
  melden dort z. B. 2095 MHz. PolyPanel baut beim Start jetzt einen kleinen LD_PRELOAD-Shim
  (`~/.local/share/polypanel/se-cpufix/fakecpu.so`), der Wine 3.6 GHz meldet; im Serverlog steht
  danach `Experimental mode: No`. Voraussetzung ist ein C-Compiler (`build-essential`/`gcc`) -
  fehlt er, bleibt alles wie bisher und das Startlog sagt es.
- Hinweis-Popup zum Experimental-Modus entfernt. Seit der Server die Hardwareprüfung besteht, war
  das Fenster „Server läuft im Experimental-Modus" (plus die Warnleiste im Einstellungsreiter) nur noch
  im Weg - es legte sich über die ganze Seite und schluckte Klicks. Beides ist raus, samt
  `/api/experimental` und den zugehörigen Sprachschlüsseln; am Feld `ExperimentalMode` steht weiter
  „wirksam: AN/aus" aus dem Serverlog, falls SE doch einmal selbst umschaltet.
- „Installieren" öffnet wieder den Fortschritt. Lag der zuletzt gemerkte Reiter auf
  „Einstellungen", verdeckte er das Installationsfenster - der Klick wirkte, als lande man in den
  Einstellungen, während im Hintergrund korrekt installiert wurde. Während einer laufenden
  Installation schaltet die Instanzseite jetzt selbst auf „Übersicht" mit Balken und Log.
- Frische Installation startet jetzt wirklich ohne Experimental. Die Vorlage lieferte
  `PhysicsIterations 1` und `BlockLimitsEnabled NONE`, neue Instanzen zusätzlich `MaxPlayers 20` -
  drei Abweichungen vom Vanilla-Satz, wegen denen SE von sich aus auf Experimental schaltet
  (`Experimental mode reason: MaxPlayers, PhysicsIterations, BlockLimitsEnabled`). Vorlage und
  Instanz-Vorgabe sind jetzt Vanilla: Physics 8, Block-Limits GLOBALLY, 16 Spieler; dass mehr als
  16 Spieler Experimental erzwingt, steht als Hinweis am Feld.
- Löschen blockiert die Oberfläche nicht mehr. Stoppen (SE speichert bis zu 90 s) und das
  Entfernen mehrerer GB laufen jetzt als Hintergrund-Job; die Karte zeigt „Server wird gestoppt …",
  dann „Serverdateien werden gelöscht …" und am Ende die freigegebene Größe. Jeder Löschvorgang steht
  außerdem mit Zeitstempel und freigegebenen MB im `panel.log`.
- Wine wird im Installer ohne Rückfrage installiert - wie Xvfb und `gcc`. Die Frage „Wine
  installieren?" wurde erfahrungsgemäß mit „nein" beantwortet, danach startete kein Windows-Spiel.
