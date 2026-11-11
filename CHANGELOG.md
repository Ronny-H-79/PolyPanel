## [0.7.22] — 2026-11-11

### Neu
- **Fortschrittsbalken bei der Installation.** SteamCMD meldet während des Downloads
  `Update state (0x61) downloading, progress: 42.31`. Diese Zeile wird jetzt ausgewertet
  (`GET /api/install/progress`) und die Oberfläche zeigt darüber einen Balken mit Phase und Prozentwert
  — bei „preallocating"/„verifying" ohne Prozentwert steht die Phase als Text. Am Ende läuft der Balken
  auf 100 % und blendet sich aus. Das Installationsprotokoll zeigt statt 10 jetzt die letzten 40 Zeilen.
- Die erste Phase (Steam-API, Client-Konfiguration) hat keinen Prozentwert — der Balken erscheint
  erst, wenn der eigentliche Download beginnt.

### Geändert
- **Prüfskript für die Installer-Texte** (`tools/check_texts.py`): vergleicht jeden Aufruf
  `$(t SCHLUESSEL …)` mit den Platzhaltern im Text und meldet fehlende Argumente sowie unbekannte
  Schlüssel. Genau diese Klasse Fehler hatte die Abfrage ohne Paketnamen erzeugt.
- **Die Build-Anzeige verschwand bisher stillschweigend.** Wenn der Server noch nicht installiert war
  oder die Steam-Abfrage scheiterte (z. B. fehlende 32-Bit-Bibliotheken), wurde das Abzeichen einfach
  ausgeblendet — es sah aus, als würde die Update-Prüfung gar nicht laufen. Jetzt steht dort
  „UPDATE-STATUS UNBEKANNT" mit Begründung im Tooltip („noch nicht installiert" bzw. „Steam-Abfrage
  fehlgeschlagen"), und ein Klick fragt sofort neu an.
- **Update-Prüfung fragt nicht mehr jede Minute bei Steam nach.** Jede offene Browserseite rief alle
  60 Sekunden `/api/update` auf, und der Server startete dafür jedes Mal einen eigenen
  `steamcmd`-Prozess (`+app_info_print`, Timeout bis 180 s). Das Ergebnis wird jetzt **15 Minuten**
  zwischengespeichert, die Oberfläche fragt nur noch alle **5 Minuten** nach. Ein Klick auf die
  Build-Anzeige erzwingt eine frische Abfrage bei Steam.

### Behoben
- **Seite war nach dem Update tot.** Der eingefügte Fehlertext enthielt ein echtes Zeilenende im JavaScript-String; damit war der ganze `<script>`-Block ungültig (SyntaxError) und keine Schaltfläche reagierte mehr. Der Text ist jetzt korrekt maskiert (`\\n`), `node --check` über alle Vorlagen läuft fehlerfrei.
- **„Start" tat scheinbar nichts.** Die Oberfläche verschluckte jede Fehlermeldung
  (`catch(e){}`), also blieb bei belegtem Port, fehlenden Serverdateien oder einem Problem mit dem
  Supervisor einfach alles stumm. Jetzt erscheint ein Hinweis mit dem echten Text, z. B.
  „Port 7780 ist schon belegt …" oder „Server nicht installiert".
- **Bei „… fehlt. Jetzt installieren?" stand kein Paketname davor.** Der Aufruf übergab ein leeres
  Argument an die Textfunktion (`t missing_ask "" "$label"`), die Meldung liest aber `$2` — dadurch
  blieb der Name leer. Betraf jede fehlende Abhängigkeit (Wine, iproute2, 32-Bit-Bibliotheken).
  Jetzt steht dort z. B. „Wine fehlt. Jetzt installieren? [j/N]"; für die Bibliotheken gibt es einen
  eigenen Satz („32-Bit-Bibliotheken fuer SteamCMD fehlen. …"), damit die Grammatik stimmt.
- **Fehlender Text beim Sprachwechsel.** Die Oberfläche zeigte bei einem Fehler im Sprachwechsel
  `undefined` plus Fehlertext, weil der Schlüssel `msg.lang_failed` im Katalog fehlte. Jetzt steht
  dort „Sprache wechseln fehlgeschlagen:" bzw. „language switch failed:".
- **Selbst-Update tat nichts: „Panel wird nicht aktualisiert".** `apply()` suchte den Paketordner im
  GitHub-Archiv unter dem Repo-Namen (`AscendedPanel/`), installiert heißt er aber `ascendedpanel/`.
  Auf Linux sind das zwei verschiedene Ordner — das Update brach mit „Paketordner fehlt im Archiv"
  ab, während die Anzeige weiter „update verfügbar" meldete. Der Ordner wird jetzt ohne Rücksicht
  auf Groß-/Kleinschreibung gesucht, damit greift das Update wieder und die Kopfzeile zeigt danach
  die neue Version.
- **Beim Installieren blieb das Protokoll leer.** SteamCMD meldet den Download-Fortschritt mit
  Wagenrücklauf (`\r`) ohne Zeilenumbruch. Der Installer las zeilenweise und bekam deshalb erst nach
  dem kompletten Download eine Zeile — bei 10–15 GB sieht das aus wie „es passiert nichts".
  Jetzt wird blockweise gelesen, an `\r` und `\n` getrennt, ANSI-Farbcode entfernt und jede
  Fortschrittszeile sofort ins `.install.log` geschrieben (`flush` je Zeile). Auch das Laden von
  SteamCMD und der genaue Befehl stehen jetzt im Protokoll.
- **Update-Protokoll zeigt jetzt ebenfalls Zeilen statt einer Riesenzeile** — derselbe Weg wie bei
  der Installation.
- **SteamCMD scheiterte auf frischen Servern mit `Exit 127`.** Ursache waren fehlende
  32-Bit-Bibliotheken (`ld-linux.so.2`, `libstdc++.so.6` i386) — ein Anfaengerfehler, den das
  Programm selbst abfangen muss. Der Installer prueft die i386-Bibliotheken jetzt in `--check`,
  installiert sie mit `--auto` (apt: `dpkg --add-architecture i386` + `lib32gcc-s1`,
  `lib32stdc++6`, `libc6:i386`; dnf: `glibc.i686`; zypper: `glibc-32bit`;
  pacman: `lib32-glibc`) und nennt sonst den genauen Befehl, der von Hand noetig ist.

0.7.8] — 2026-11-10

### Behoben
- **`polypanel web` warf bei belegtem Port einen Traceback.** Wer den Web-Dienst schon laufen hatte,
  bekam `OSError: [Errno 98] Address already in use` samt Stacktrace. Jetzt erscheint eine klare
  Meldung mit drei Wegen — Dienst prüfen (`systemctl --user status polypanel-web`), anderer Port
  (`polypanel web --port <frei>`), oder nur die Adresse holen (`polypanel url`) — und Exit-Code 1.
- **Anleitung startete den Dienst doppelt.** Nach `install.sh` läuft der Dienst bereits; in der
  Installationsanleitung stand trotzdem noch `polypanel web`. Dort steht jetzt `polypanel url`,
  das nur die fertige Adresse mit Token ausgibt.
- **`xvfb` gehört jetzt zur Installation.** Fehlt der virtuelle Bildschirm, bricht der ARK-Ascended-Server unter Wine ab, bevor er ins Log schreibt — Startknopf ohne Wirkung, leeres Protokoll. Installer prüft `Xvfb` jetzt wie Wine, installiert es mit `--auto` (apt `xvfb`, dnf `xorg-x11-server-Xvfb`, pacman `xorg-server-xvfb`, zypper `xvfb`).
- **Server ließ sich nicht starten.** `runner.start()` rief den Supervisor als `-m AscendedPanel.consoled` auf, das Modul heißt aber `ascendedpanel.consoled` — auf Linux startet der Prozess damit gar nicht, es entsteht keine Console-Logdatei, und `stderr` ging zusätzlich nach `/dev/null`: kein Prozess, kein Log, keine Meldung. Der Aufruf ist korrigiert, und Startausgaben landen jetzt in `<instanz>/.start.log` statt im Nichts.
- **Installation brach mit `Failed to install app '2430930' (Missing configuration)` ab.** ARK Ascended hat keinen Linux-Server; SteamCMD lädt den Windows-Zweig nur mit `+@sSteamCmdForcePlatformType windows`. Der Schalter wird jetzt bei ASA automatisch mitgegeben — bei ASE, 7D2D, Satisfactory und Space Engineers bleibt die Kommandozeile unverändert. Gilt für Installation und Update.

## [0.7.7] — 2026-11-10

### Geändert
- **Zugriffsabfrage warnt jetzt vorab.** In der Frage steht bei `[3] direkt ueber IP und Port` nun
  „HTTP, nicht empfohlen". Die ausführliche Warnung samt Rückfrage (`Trotzdem so einrichten? [j/N]`)
  kommt wie bisher direkt nach der Wahl von `[3]`; wer `[1]` (SSH-Tunnel) nimmt, sieht sie bewusst
  nicht — dabei ist nichts aus dem Netz erreichbar.

## [0.7.6] — 2026-11-10

### Behoben
- **Installationsanleitung führte in die falsche Schreibweise.** `git clone … polypanel` legt den
  Ordner klein an, die Anleitung verlangte danach aber `cd PolyPanel`. Auf einem case-sensitiven
  Dateisystem bricht die Installation dort mit `No such file or directory` ab. Alle Befehle, die
  Fehlerbehebungstabelle und die Falle mit dem gleichnamigen Paketordner nennen jetzt
  `polypanel`; die doppelte `cd`-Zeile in `INSTALL.de.md` ist entfernt.

## [0.7.5] — 2026-11-10

### Geändert
- **Knopf „Englische Website" aus der Kopfzeile entfernt.** Er öffnete nur die englische README auf
  GitHub; der englische Text ist über die README im Repo erreichbar, der Platz im Kopf gehört den
  Statusanzeigen.

## [0.7.4] — 2026-11-10

### Geändert
- **Kopfzeilen-Knopf heißt jetzt „Englische Website" / „English website"** statt nur „English". Der
  Knopf öffnet die englische README auf GitHub — ohne das Wort war nicht erkennbar, was er tut.

## [0.7.3] — 2026-11-10

### Behoben
- **Englische Oberfläche zeigte deutsche Feldnamen.** `i18n.setting()` war vorhanden, wurde aber
  nirgends aufgerufen — die Einstellungen kamen immer mit den deutschen Labels aus den Profilen.
  Jetzt laufen alle Spiele durch `_uebersetzte_settings()`: Englisch nutzt die kuratierte Tabelle
  `SET_EN`, sonst den lesbar gemachten Schlüsselnamen (`EnableResearch` → „Enable research",
  `EnablePvPStructureDecay` → „Enable PvP structure decay"). Deutsch bleibt unverändert.
- Hinweis „Standard, noch nicht gesetzt" kommt aus dem Sprachkatalog (`setg.not_set`) statt fest
  deutsch im Profil zu stehen.

## [0.7.2] — 2026-11-10

### Geändert
- **Space-Engineers-Einstellungen sind schon vor der Installation vollständig.** Bisher zeigte der
  Reiter nur die sieben Kernfelder, weil die `SpaceEngineers-Dedicated.cfg` erst beim ersten Start
  entsteht. Jetzt liest `settings()` ersatzweise die mitgelieferte Vorlage und bietet zusätzlich alle
  bekannten Optionen an (247 Felder statt 7): gesetzte Werte kommen aus der Vorlage, der Rest steht
  leer mit dem Hinweis „Standard, noch nicht gesetzt".
- **Speichern funktioniert ohne Installation:** `apply_settings()` legt die Config aus der Vorlage an,
  trägt geänderte Werte ein und setzt Optionen, die in der Datei noch fehlen, passend ein (nur bekannte
  Schlüssel, Unbekanntes wird ignoriert).
- **Gruppierung nach Thema:** die acht Abschnitte aus `se_labels.py` (Limits, Bauen, Müll, Forschung,
  Begegnungen, Kampf, Netzwerk, Server) bestimmen jetzt den Reiter — vorher landeten 219 von 247
  Feldern unter „weitere", weil `_group_of()` nur wenige Schlüssel kannte.

## [0.7.1] — 2026-11-10

### Behoben
- **Space-Engineers-Instanz anlegen scheiterte mit „kein freier Port gefunden".** Das Profil hat keinen
  Steuerkanal (`default_control_port = 0`, kein RCON); `_free_port(0)` probierte 0/1, 10/11 … und lief
  an den privilegierten Ports < 1024 gegen die Wand. Jetzt wird bei einem Profil ohne Control-Port
  schlicht `0` eingetragen, und `_free_port()` gibt für `start <= 0` sofort `0` zurück.

## [0.7.0] — 2026-11-10

### Geändert
- **Das Projekt heißt jetzt PolyPanel.** Befehl `polypanel` (auch `python3 -m polypanel`), Dienst
  `polypanel-web.service`, Konfiguration unter `~/.config/polypanel`, Instanzen unter
  `~/polypanel-instances` bzw. `/mnt/Games/polypanel`, Backups/Snapshots unter
  `~/polypanel-backups` und `~/polypanel-snapshots`.
- **Bestehende Installationen migrieren automatisch:** liegt noch `~/.config/noah2games` bzw.
  `~/noah2games-instances` herum und das neue Verzeichnis fehlt, wird es beim ersten Start
  umbenannt (gleiche Partition) oder kopiert — Instanzen, Token und Einstellungen bleiben erhalten.

## [0.6.11] — 2026-11-10

### Geändert
- **Knopf „Dinos speichern" entfernt.** Er sendete exakt denselben Befehl wie „Welt speichern"
  (`SaveWorld`), ARK kennt keinen eigenen Save für Dinos. Der Hinweis an „Welt speichern" sagt jetzt,
  dass alle gezähmten Dinos mitgespeichert werden (wilde Dinos sind nicht Teil des Saves, sie werden
  beim Laden neu erzeugt).

## [0.6.10] — 2026-11-10

### Behoben
- **Nicht installierte Instanzen ließen sich nicht löschen.** Die Dashboard-Karte zeigte nur
  „Installieren" — wer eine Instanz anlegt und es sich anders überlegt, kam nicht mehr davon weg.
  Jetzt steht dort auch `Löschen`; die Rückfrage nach den Serverdateien entfällt, weil es keine gibt
  (der leere Instanzordner wird mit entfernt).
- **`delInst()` in noah prüfte `r.ok` auf einer Textantwort** (siehe 0.6.8er-Reihe) — nach dem
  Löschen lud die Karte nie neu. Jetzt `JSON.parse` mit Rückfall und Meldung mit freigegebenen GB/MB.

## [0.6.9] — 2026-11-10

### Neu
- **Deinstallieren direkt aus der Liste der installierten Mods.** Jede Zeile im Block
  „Installierte Mods" hat einen Knopf `Deinstallieren` (Rückfrage vorher, Freigabe in MB in der
  Meldung danach). `POST /api/mods/uninstall?id=<Schlüssel>` löscht ausschließlich Ordner innerhalb
  des Mod-Verzeichnisses dieser Instanz — `..`, absolute Pfade und fremde Unterordner werden
  abgelehnt (Schlüssel sind `Name` oder `GameFeatures/Name`).

## [0.6.8] — 2026-11-10

### Geändert
- **Der Mods-Reiter zeigt die installierten Mods jetzt immer ganz oben.** Neuer Block „Installierte
  Mods" über der Suche: Pfad, Anzahl, Aktualisieren-Knopf und die Liste mit Name und Größe. Gilt für
  alle Spiele (`GET /api/mods/installed`) — Satisfactory, 7D2D und Space Engineers über den
  Mod-Ordner, ARK-Spiele über ihre verwaltete Liste, die dafür sichtbar bleibt.
- **ASE hatte im Mods-Reiter gar keine Liste.** Die CSS-Regel, die für Nicht-ARK alles außer der
  Suchspalte ausblendet, traf auch `arkse` — die Mod-Liste war da, aber unsichtbar.

### Behoben
- `GET /api/mods/installed` liefert ein einheitliches Format (`name`, `size_mb`, `source`, `active`),
  damit die Oberfläche nicht je Spiel eine eigene Liste bauen muss.

## [0.6.7] — 2026-11-10

### Behoben
- **Mod-Installation für Satisfactory legte die Dateien flach in `Mods/` ab.** Die ficsit-Archive
  haben ihren Inhalt auf der Wurzel (`Binaries/`, `Content/`, `<Name>.uplugin`) — ein blankes
  `extractall(Mods/)` mischte zwei Mods in denselben Ordner, überschrieb `Content`/`Binaries`
  gegenseitig und SML fand überhaupt keine Mod (Symptom: „installiert“, aber im Spiel nichts da).
  Jetzt wird in **`Mods/<Ref>/`** bzw. für GameFeature-Mods in **`Mods/GameFeatures/<Ref>/`**
  entpackt (erkannt am `"GameFeature": true` im `.uplugin`), die alte Fassung wandert nach
  `<Instanz>/.mods-backup/<Ref>-<Zeitstempel>` (außerhalb von `Mods/`, sonst sieht SML zwei Mods
  mit derselben Referenz). Dazu `.smm`-Marker mit dem Versions-Hash, sha256-Prüfung des Downloads,
  Pfad-Prüfung beim Entpacken (Zip-Slip) und Entpacken in ein temporäres Verzeichnis mit
  anschließendem `move` — ein kaputter Download hinterlässt keinen halben Mod-Ordner.
- **Download der neuesten Version war Glückssache.** Die API liefert die Versionen nicht sortiert;
  die Abfrage `versions(filter:{limit:1})` nahm einfach die erste. Jetzt alle Versionen holen und
  nach `created_at` absteigend sortieren.
- **`ControlError` war in `games/satisfactory.py` nicht importiert.** Im Fehlerfall der
  ficsit-Abfrage kam statt der API-Meldung `NameError: name 'ControlError' is not defined` in der
  Oberfläche an.
- **Mods-Liste zeigte für Satisfactory nur einen Eintrag „GameFeatures“.** `_local_mods()` löst den
  SML-Unterordner jetzt auf und listet die einzelnen Mods mit ihrer Größe.
- **Suche sortiert nach Downloads statt nach dem internen `popularity`-Score.** Treffer mit dem
  Suchbegriff im Namen stehen zuerst (die ficsit-Suche matcht auch Beschreibungen, „train“ traf
  sonst „Follow Terrain“).

## [0.6.5] — 2026-11-10

### Behoben
- **Satisfactory-Modsuche lieferte beliebige Treffer.** Die ficsit.app-Abfrage hatte keine
  Sortierung — jetzt `order_by:popularity,order:desc` (GraphQL-Enum **ohne** Anführungszeichen,
  sonst lehnt die API die Abfrage mit „cannot represent non-enum value" ab). Treffer kommen damit
  nach Beliebtheit (Refined Power, Structural Solutions …).
- **Der Hinweistext im Mods-Reiter war für alle Spiele der Nexus/GitHub-Text.** Jetzt je Spiel:
  Steam-Workshop (ARK Evolved, Space Engineers), ficsit.app (Satisfactory), Nexus/GitHub (7D2D).
- **Deutsche Suchbegriffe in englischen Portalen.** `query_english()` übersetzt den Begriff
  (Fachglossar zuerst: „förder" → conveyor, „lager" → storage, „zug" → train; sonst den
  Übersetzungsdienst) — vorher fand „förder" nichts Brauchbares.

## [0.6.4] — 2026-11-10

### Neu
- **Mod-Suche für Space Engineers** — im Steam-Workshop (App 244850), echte Volltextsuche ohne Key,
  Treffer mit Abonnentenzahl und Beschreibung. „Installieren" trägt die Workshop-ID als `ModItem`
  in die `<Mods>`-Liste von `SpaceEngineers-Dedicated.cfg` ein (XML bleibt gültig, doppelte IDs
  werden abgefangen), der Server lädt sie beim Start.
- Eingetragene IDs stehen im Mods-Reiter; die Hinweistexte nennen jetzt allgemein den Steam-Workshop
  statt nur ARK Evolved.

### Geändert
- **Workshop-Suche liegt in `games/steam_workshop.py`** und wird von ARK Evolved *und* Space
  Engineers genutzt (vorher nur ASE, SE zeigte lediglich einen Link).

## [0.6.3] — 2026-11-10

### Geändert
- **Der Wizard steht nicht mehr im normalen Installationsablauf.** README und INSTALL nennen jetzt
  `noah2games web` als Weg (Instanz im Browser anlegen und installieren); der Konsolen-Assistent ist
  ein eigener, ausdrücklich optionaler Absatz („nur Konsole"). Die falsche Aussage „die
  Web-Oberfläche kann keine Instanz anlegen" ist raus — sie kann es seit dem Dashboard-Formular.
- Die Abschlusshinweise von `install.sh` nennen `noah2games web` als ersten Schritt und den Wizard
  als optional (neue Zeile, eigener Übersetzungsschlüssel).

## [0.6.2] — 2026-11-10

### Behoben
- **„Löschen mit Dateien" hat die Serverordner nie entfernt.** Das Sicherheitsnetz prüfte nur auf
  Namen, die mit `arkserver` beginnen — bei `~/noah2games-instances/<name>` und
  `/mnt/Games/noah2games/<name>` blieben 8–17 GB pro Instanz liegen, ohne Meldung. Jetzt gilt:
  Ordner muss in einem Instanzverzeichnis liegen und wie die Instanz heißen; dann wird gelöscht,
  die Größe vorher gemessen und als „X GB freigegeben" gemeldet. Alles andere wird mit klarem
  Hinweis abgelehnt statt still übersprungen.
- **Die Lösch-Rückmeldung im Dashboard war immer „Fehler"**, weil die Antwort als Text statt als
  JSON gelesen wurde. Jetzt erscheint die Meldung mit freigegebener Größe bzw. dem Hinweis, dass
  die Dateien liegen geblieben sind.
- Der Supervisor-Marker `<ordner>.stopped` wird beim Löschen mit entfernt.

## [0.6.1] — 2026-11-10

### Neu
- **Mod-Beschreibungen automatisch auf Deutsch.** In der deutschen Oberfläche werden die Treffer
  der Mod-Suche übersetzt (Steam-Workshop, CurseForge, Nexus/GitHub, ficsit.app) — inklusive der
  Vorschläge beim Tippen. Übersetzungen liegen unter `~/.config/noah2games/cache/translations`
  und werden wiederverwendet; schlägt die Übersetzung fehl, steht der Originaltext da.
  Erste Suche dadurch ~2,5 s, jede weitere ~0,4 s.
- Schon deutsche Texte werden erkannt und nicht erneut übersetzt.

## [0.6.0] — 2026-11-10

### Neu
- **Mod-Suche für ARK Evolved direkt im Steam-Workshop** — echte Volltextsuche (kein API-Key,
  kein Login), Treffer mit Abonnentenzahl, Beschreibung und Steam-Link. „Installieren“ trägt die
  Workshop-ID in die Mod-Liste ein (`ActiveMods` in der `GameUserSettings.ini`), der Server lädt
  sie beim nächsten Start selbst (`-automanagedmods`). Bereits eingetragene Mods sind markiert
  und der Knopf ist gesperrt.
- **Eingetragene Workshop-IDs im Mods-Reiter sichtbar** (Liste mit Hinweis „lädt beim nächsten
  Start“) — vorher war nur der Ordnerinhalt zu sehen, die IDs standen nur in der INI.
- Eigene Hinweistexte für ARK Evolved im Mods-Reiter (statt der Nexus/GitHub-Erklärung).

## [0.5.1] — 2026-11-10

### Neu
- **Alle ARK-Evolved-Einstellungen im Formular.** Statt der 51 Kernfelder zeigt der Reiter jetzt
  **262 Werte**: 156 aus `GameUserSettings.ini` (ServerSettings, SessionSettings, MOTD) und 100 aus
  `Game.ini` — inklusive Zucht-, Prägnungs-, PvP-, Turm-, Cryo-, Tribute- und Genesis-Optionen.
  Jede Eigenschaft hat eine deutsche Beschriftung und einen Hinweis.
- **Vollständige ASE-Vorlage mitgeliefert** (`games/arkse_template_gus.ini`, `..._game.ini`):
  Default-Werte der offiziellen ASE-Konfiguration, damit das Formular schon vor dem ersten Start
  vollständig ist. ASE ergänzt beim Start eigene Werte, die Oberfläche liest danach weiterhin alles
  aus den Dateien.
- **Schlüssel werden unabhängig von der Schreibweise erkannt** — ASE schreibt `serverPVE` und
  `globalVoiceChat` klein/gemischt, die Beschriftungen greifen trotzdem.

### Behoben
- **`ActiveMods` gehört in die `GameUserSettings.ini`** (Sektion `ServerSettings`), nicht in die
  `Game.ini` — dort hat ASE die Mod-Liste ignoriert.

## [0.5.0] — 2026-11-10

### Neu
- **ARK: Survival Evolved als fünftes Spiel** (`--game arkse`, Steam-App 376030). Anders als
  Ascended läuft ASE **nativ** unter Linux (`ShooterGame/Binaries/Linux/ShooterGameServer`),
  deshalb ohne Wine und ohne Prefix:
  - **Konfiguration**: `GameUserSettings.ini` und `Game.ini` unter
    `ShooterGame/Saved/Config/LinuxServer/` — Ports, Spieleserver-Name, Admin-Passwort und
    Workshop-Mods schreibt der Manager, die Karte steht in der Startzeile.
  - **Steuerung** über Source-RCON (`ServerAdminPassword`), inklusive Spielerliste, Kick/Ban,
    `SaveWorld` + `DoExit` beim Stop.
  - **Einstellungen**: alle Eigenschaften beider INI-Dateien als Formular, mit deutschen
    Beschriftungen und den bekannten Reitern (Server, Spiel & Tempo, PvP, Strukturen, Dinos,
    Transfer, Anzeige, MOTD, Game.ini).
  - **Mods**: Workshop-IDs im Feld „Mods", der Server lädt sie beim Start (`-automanagedmods`).
  - **Kartenauswahl** im Dashboard: The Island, Ragnarok, Scorched Earth, The Center, Aberration,
    Extinction, Valguero, Genesis, Crystal Isles, Genesis 2, Lost Island, Fjordur.
- **Kartenliste hängt jetzt am Spielprofil** — ARK ASA und ASE haben eigene Weltennamen, die
  Auswahl im Dashboard wird beim Wechsel des Spiels neu gefüllt (andere Spiele ohne Kartenauswahl).
- **Befehls-Knöpfe (Speichern, Broadcast, Dino-Wipe …)** gelten für ASE wie für ASA; Whitelist,
  Cluster-Reiter und INI-Roheditor bleiben ARK-Ascended-spezifisch.

## [0.4.3] — 2026-11-10

### Neu
- **Lizenz, Copyright, PayPal und Discord in der Oberfläche.** Jede Seite trägt unten einen Fuß
  mit `noah2games <Version> · © 2026 Ronny H. · alle Rechte vorbehalten` und drei Links:
  **Lizenz** (öffnet die neue Seite `/license` mit dem Lizenztext in der eingestellten Sprache),
  **PayPal** (Spendenlink) und **Discord-Community** (Ark-ASA-ASE-Hilfe). Oben rechts bleiben die
  beiden Marken-Icons.
- **Lizenzseite `/license`** (auch `/lizenz`): zeigt den Text aus `LICENSE` in Deutsch oder
  Englisch, je nach eingestellter Sprache, mit Rückweg zum Dashboard.

### Behoben
- **Der Installer kopiert die `LICENSE` jetzt mit** (bisher fehlte sie in `~/.local/share/noah2games`,
  damit auch der Copyright-Hinweis in der ausgelieferten Installation). README und INSTALL werden
  zusätzlich in beiden Sprachen mitkopiert.

## [0.4.2] — 2026-11-10

### Neu
- **Mod-Suche für alle Spiele.** Der Mods-Tab ist jetzt überall sichtbar:
  - **Satisfactory** — Suche und Installation direkt über ficsit.app (GraphQL), inkl. Download
    und Entpacken nach `FactoryGame/Mods`
  - **7 Days to Die** — Verweis auf die NexusMods-Suche (keine offizielle Such-API), Mods als
    Ordner nach `Mods/`
  - **Space Engineers** — Verweis auf den Steam Workshop; Workshop-IDs gehören in das
    Config-Feld „Mods", der Server lädt sie beim Start
- **Tabs deutlich sichtbarer**: gefüllte Fläche, kräftigere Schrift, aktiver Tab farbig hinterlegt.

## [0.4.1] — 2026-11-10

### Neu
- **Space Engineers als viertes Spiel** (App 298740). SteamCMD liefert nur die Windows-Variante,
  deshalb richtet noah2games beim ersten Installieren ein gemeinsames Wine-Prefix
  (`~/.noah2games-wine-se`) ein und installiert dort `dotnet48` und `vcrun2019` — einmalig für
  alle SE-Instanzen. Config-Vorlage (`SpaceEngineers-Dedicated.cfg`) wird mitgeliefert, über
  200 Optionen sind auf Deutsch beschriftet.
- **Optische Rückmeldung bei Start/Stop/Restart** im Dashboard: Banner mit Sekundenzähler,
  gesperrte Buttons, Abschlussmeldung („läuft" / „heruntergefahren").
- **Sauberes Herunterfahren** über die Serverkonsole (`save`, `stop`) statt sofortigem Signal.

### Behoben
- **Instanzliste konnte komplett leer bleiben**, wenn ein laufender Server keine PID-Datei hatte
  (KeyError bei fehlenden Messwerten).
- **Von Hand gestartete Server** werden jetzt über Arbeitsverzeichnis und Programmdatei erkannt —
  Status, Kennzahlen und Stop funktionieren auch dort.
- **7 Days to Die**: Logdatei wird gefunden (`output_log__*.txt`), `logs/` wird angelegt.
- **Satisfactory**: Statusabfrage brach an `ListPlayers` ab; Spieler kommen jetzt aus
  `QueryServerState`, fehlender API-Token wird nicht mehr als Fehler gewertet.
- **Space Engineers**: Status ohne RCON, Logdatei pro Start, `OnlineMode` muss groß geschrieben
  werden (sonst verwirft SE die ganze Config).
- **Web-UI**: neuer Hintergrund (wandernde Farbwolken), Glas-Optik, frischere Screenshots.

## [0.4.0] — 2026-11-10

### Neu
- **Spielprofile: Satisfactory und 7 Days to Die neben ARK.** Der Kern bleibt spielunabhängig,
  ein Profil liefert Startzeile, Konfigurationsdatei, Pfade und Steuerkanal:
  - `ark` — ARK: Survival Ascended (App 2430930, Source-RCON, Wine) wie bisher
  - `satisfactory` — Satisfactory Dedicated Server (App 1690800, `FactoryServer.sh`, Ports
    Spiel/Query/Beacon, Steuerung über die HTTPS-API `/api/v1` mit Bearer-Token)
  - `7d2d` — 7 Days to Die (App 294420, `startserver.sh`, `serverconfig.xml`, Steuerung über Telnet)
- Anlegen per `noah2games --name <name> init --game satisfactory|7d2d`, im Web-UI über den
  Parameter `game` an `/api/instances`.
- Neue Felder je Instanz: `beacon_port`, `api_token` (Satisfactory), `telnet_password` (7D2D).

### Geändert
- Wine wird nur noch für ARK verwendet; Satisfactory und 7D2D starten nativ.
- Instanzverzeichnis jetzt `~/noah2games-instances/<name>` (getrennt von noah).

## [0.3.70] — 2026-11-09

### Geändert
- **Stop ist deutlich schneller und meldet die Dauer.** Bisher wurde nur die PID des Starters
  beobachtet: der verschwindet zuerst, während `ArkAscendedServer.exe` und `wineserver` noch liefen —
  deshalb wartete noah2games die volle Kulanzzeit ab (bis 90 s) und ließ Reste stehen. Jetzt werden alle
  Prozesse der Instanz über die Kommandozeile gefunden, das Warten endet, sobald wirklich keiner mehr
  läuft, und die Meldung nennt die gebrauchte Zeit („beendet nach 6 s"). Notausstieg bleibt:
  SIGTERM an die Gruppe, danach SIGKILL auf die Reste.

## [0.3.68] — 2026-11-08

### Geändert
- **Die Backup-Box ist ganz entfernt.** Welt-Sicherungen laufen ausschließlich als Aufgabe im Zeitplan
  (Aktion „Backup"); Snapshots bleiben in ihrer Box. Über die Oberfläche lassen sich damit auch keine
  Backups mehr einzeln zurückholen — die Dateien unter `~/noah2games-backups` und die API bleiben bestehen.

## [0.3.67] — 2026-11-08

### Geändert
- **„Backup-Uhrzeiten" ist entfallen** — Backups laufen ausschließlich als Aufgabe im Zeitplan
  (Aktion „Backup"), damit es nicht zwei Stellen mit derselben Wirkung gibt. Die Backup-Box zeigt jetzt
  den Hinweis darauf und behält „Jetzt sichern" für eine sofortige Welt-Sicherung.

## [0.3.66] — 2026-11-08

### Behoben
- **Geleerte Uhrzeiten-Felder wurden ignoriert:** ein leer gelassenes Feld (Neustart, Backup, Snapshot)
  kam beim Server gar nicht an, weil leere Query-Werte wegfielen — die alten Zeiten blieben stehen und
  ließen sich so nicht abschalten. Jetzt werden leere Werte mitgesendet und leeren die Liste.

## [0.3.65] — 2026-11-08

### Geändert
- **Snapshots haben eigene Uhrzeiten** („Snapshot-Uhrzeiten" in der Snapshot-Box, kommagetrennt wie bei
  den Backups) statt einer Aktion im Zeitplan. Der Zeitplan bleibt für die übrigen Aktionen.
- „Auto-Snapshots behalten" bleibt unverändert und greift weiter für die automatischen Sicherungen.

## [0.3.64] — 2026-11-08

### Geändert
- **„Auto-Snapshots behalten" steht jetzt unter dem Knopf** statt darüber, und der Hinweis nennt die
  Platzrechnung (3 = ein Tag bei 3 pro Tag, 15 ≈ 180 GB).

## [0.3.63] — 2026-11-08

### Neu
- **Snapshots lassen sich jetzt ebenfalls per Zeitplan anlegen** (Aktion „Snapshot"), z. B. sonntags
  04:00. Damit die 12-GB-Kopien nicht auflaufen, bleiben nur die letzten drei Auto-Snapshots; die Zahl
  steht als „Auto-Snapshots behalten" bei der Snapshot-Box.
- Manuelle Snapshots werden dabei nie angefasst — aufgeräumt werden nur die mit dem Namen `auto_*`,
  sortiert nach Änderungszeit.
- **Zwei Snapshots in derselben Sekunde** hätten sich überschrieben (`FileExistsError`); der Name bekommt
  jetzt einen Zähler.

## [0.3.62] — 2026-11-08

### Geändert
- **Der Zeitplan nimmt die volle Breite ein**, die Backup-Box steht jetzt darunter. Damit haben die
  Aufgabenzeilen Platz für Aktion, Uhrzeit, Tage, Argument und Schalter in einer Zeile.
- „Backup-Uhrzeiten" bleibt in der Backup-Box (Backups sind keine Snapshots).

## [0.3.61] — 2026-11-08

### Geändert
- **„Backup-Uhrzeiten" steht jetzt bei den Snapshots** statt in der Backup-Box — dort, wo die Sicherungen
  hingehören. Der Hinweis nennt zusätzlich die neue Zeitplan-Aufgabe „Backup" als Alternative.

## [0.3.60] — 2026-11-08

### Behoben
- **Der Supervisor las den Zeitplan nur beim Start.** In der Oberfläche gespeicherte Aufgaben wurden erst
  nach einem Supervisor-Neustart ausgeführt. Er liest die Zeitplan-Felder jetzt bei jeder Runde neu,
  sobald sich die Instanzdatei geändert hat (Ports und Mods bleiben bewusst unberührt).
- **Das Selbst-Update startete den Supervisor nicht mit** — er lief weiter mit altem Code. Jetzt werden
  `noah2games-web` und `noah2games-supervise` neu gestartet, sofern sie laufen.

## [0.3.59] — 2026-11-08

### Behoben
- **Zeitplan-Aufgaben konnten dieselbe ID bekommen**, wenn sie in derselben Millisekunde angelegt wurden
  (z. B. beim Senden der ganzen Liste). Die ID ist jetzt zusätzlich durchnummeriert — sonst hätte der
  Supervisor zwei Aufgaben als „schon gelaufen" verwechselt.

## [0.3.58] — 2026-11-08

### Neu
- **Zeitplan mit Aufgaben** (Verwaltung → Zeitplan), ähnlich den Scheduled Tasks in AMP: je Aufgabe
  **Aktion, Uhrzeit, Wochentage** (leer = täglich) und ein Freitextfeld für Broadcast oder RCON-Befehl.
  Aktionen: Neustart, Start, Stop, Update + Neustart, Backup, Welt speichern, wilde Dinos löschen,
  Broadcast, freier RCON-Befehl.
- Neustart-Aufgaben nutzen die Vorwarnung (Countdown im Spiel), die übrigen laufen sofort; jede
  Ausführung geht an den Discord-Webhook, Fehler als Fehlermeldung.
- Die alten „Neustart-Uhrzeiten" bleiben als Rückfallebene erhalten.

## [0.3.57] — 2026-11-08

### Geändert
- **Der Hinweis nennt jetzt den Grund:** „Die CurseForge-API liefert höchstens 50 Treffer pro Abfrage —
  mehr lässt sich technisch nicht abrufen." An der Trefferzeile entsprechend
  „CurseForge-API: maximal 50 pro Abfrage".

## [0.3.56] — 2026-11-08

### Neu
- **Hinweis zur Trefferbegrenzung** unter dem Suchfeld: maximal 50 Treffer pro Suche, für mehr den
  Begriff eingrenzen. Steht zusätzlich an der Trefferzeile, sobald die Liste abgeschnitten ist
  („50 / 7.291 Treffer · mehr pro Suche nicht möglich").

## [0.3.55] — 2026-11-08

### Geändert
- **Mod-Suche holt 50 Treffer** statt 30 (mehr erlaubt die CurseForge-Suche pro Abfrage nicht).
  Für gezieltes Suchen reicht das; sonst den Begriff eingrenzen.

## [0.3.54] — 2026-11-08

### Geändert
- **Trefferzahl steht jetzt deutlich über der Mod-Liste** (12,5 px, Akzentfarbe statt 11 px gedämpft):
  „30 / 7.290 Treffer". Auch die Vorschlagsliste beim Tippen nennt ihre Anzahl.

## [0.3.53] — 2026-11-08

### Behoben
- **Zwischengespeicherte Suchergebnisse konnten die API-Suche verdecken.** Ein Ergebnis vom Notbehelf
  (wenige Treffer, ohne Key) wurde eine Stunde lang auch dann ausgeliefert, wenn inzwischen ein Key
  gesetzt war — die Suche zeigte weiter 8 statt 30 Treffer. Der Cache unterscheidet jetzt Key/ohne Key
  und die Trefferzahl; die Gesamtzahl wird mitgespeichert. Alte Cache-Dateien werden ignoriert.

## [0.3.52] — 2026-11-08

### Geändert
- **Mod-Suche zeigt bis zu 30 Treffer** statt 10, mit Trefferzahl darüber („30 / 1.412 Treffer",
  Gesamtzahl aus der CurseForge-Antwort). Die Liste ist scrollbar, statt die Seite zu verlängern.

## [0.3.51] — 2026-11-08

### Geändert
- **`console.curseforge.com` im Feld „CurseForge-API-Key" ist jetzt ein Link** (öffnet in neuem Tab),
  statt nur als Text dazustehen.

## [0.3.50] — 2026-11-08

### Geändert
- **Discord- und PayPal-Symbol größer und in den Markenfarben** (34 px Feld, 22 px Symbol; Discord
  #5865F2, PayPal #003087) statt einfarbig klein.

## [0.3.49] — 2026-11-08

### Neu
- **Discord und PayPal als Symbole oben rechts** — auf jeder Seite (Dashboard, Instanzseite, Mods,
  Verwaltung). Die Symbole sind eingebettet, es geht keine Anfrage an fremde Server, solange niemand
  klickt.

## [0.3.48] — 2026-11-08

### Neu
- **Reiter im Einstellungs-Formular:** die 90 bekannten INI-Werte sind in neun Gruppen sortiert —
  Server & Zugang, Spiel & Tempo, PvP & Regeln, Strukturen & Verfall, Dinos & Zucht, Transfer & Cluster,
  Anzeige, MOTD und Game.ini. Jeder Reiter nennt seine Anzahl; die Auswahl merkt sich der Browser.
- Gespeichert wird weiterhin alles auf einmal — die Felder der anderen Reiter bleiben erhalten.

## [0.3.47] — 2026-11-08

### Geändert
- **Der Knopf heißt „Menü" und führt direkt in die Instanz** — Beschriftung wie gewünscht, ohne
  Zwischenschritt oder Aufklappliste.

## [0.3.46] — 2026-11-08

### Geändert
- **Zurück zum direkten Weg:** „Öffnen" führt wieder ohne Zwischenschritt in die Instanz; Menü-Knopf und
  Dialog sind entfernt.

## [0.3.45] — 2026-11-08

### Geändert
- **Kein Dropdown mehr in der Karte:** ein einfacher Knopf **„Menü"** öffnet eine Auswahl mit Übersicht,
  Einstellungen, Mods und Verwaltung.

## [0.3.44] — 2026-11-08

### Geändert
- **Das Auswahlfeld in der Karte heißt „Menü …"** statt „Öffnen …" — es ist ja eine Auswahl, kein Knopf.

## [0.3.43] — 2026-11-08

### Geändert
- **Startseite neu geordnet:** „Neue Instanz" und „Hinweis" stehen jetzt oben, darunter die Instanzen —
  die Erzeugung bleibt damit immer an derselben Stelle und wandert nicht, wenn Instanzen dazukommen.
- **„Öffnen" ist ein Menü:** Übersicht, Einstellungen, Mods oder Verwaltung direkt anwählen; die
  Detailseite springt in den passenden Reiter.
- Karten- und Log-Größen wieder wie in 0.3.39 (Log nur bei laufenden Instanzen, 9,5 px, Karten ab 300 px).

## [0.3.39] — 2026-11-08

### Geändert
- **Laufende Instanzen nehmen im Dashboard zwei Spalten ein** (ab 900 px Fensterbreite). Sonst war die
  Karte so schmal, dass das Log unter die Kennzahlen rutschte statt daneben zu stehen.

## [0.3.38] — 2026-11-08

### Neu
- **Lebendes Server-Log in der Dashboard-Karte.** Rechts neben Status und Kennzahlen laufen die
  letzten Logzeilen mit (Aktualisierung alle 2,5 s), damit man ohne die Detailseite sieht, was der
  Server gerade tut. Bei schmalen Karten rutscht das Log unter die Kennzahlen.
- Die angezeigte Zeilenzahl folgt der Kartenhöhe; leere Ausgabe erscheint als „keine Ausgabe".

## [0.3.37] — 2026-11-08

### Geändert
- **CPU-Kachel zeigt jetzt den Anteil des Servers (0–100 %)** statt der Summe über alle Kerne.
  755 % auf 64 Kernen erscheint damit als „11,8 %"; der Verlaufsgraph endet ebenfalls bei 100 %.
  Die Kern-Aufschlüsselung („7,6 von 64 Kernen") steht im Tooltip, der Rohwert bleibt in der API
  unter `cpu` erhalten.

## [0.3.36] — 2026-11-08

### Behoben
- **CPU-Tooltip zeigte `undefined`/`NaN`**, wenn die Gegenstelle keine Kernzahl liefert (ältere
  Antwort im Browser-Cache). Ersatzwert ist jetzt die Kernzahl des Browsers, sonst 1.

## [0.3.35] — 2026-11-08

### Behoben
- **Selbst-Update startete den Benutzerdienst nicht neu.** Ohne angemeldete Sitzung (per `su`, `ssh`
  oder aus einem Skript) fehlten `XDG_RUNTIME_DIR` und `DBUS_SESSION_BUS_ADDRESS`, `systemctl --user`
  scheiterte und die Oberfläche lief weiter mit dem alten Code. Beide Variablen werden jetzt gesetzt,
  der Dienststart klappt damit auch aus einer Nicht-Login-Sitzung.

## [0.3.34] — 2026-11-08

### Behoben
- **Selbst-Update konnte die Installation zerstören.** `apply()` löschte das laufende Paketverzeichnis
  und kopierte erst danach das neue hinein — brach der Kopiervorgang ab (oder existierte das Ziel noch),
  blieb ein halbes Verzeichnis zurück und `noah2games` war nicht mehr startbar. Das neue Paket wird jetzt
  vollständig daneben aufgebaut und per `rename` getauscht; schlägt der Tausch fehl, wird der alte
  Stand zurückgerollt.
- **Sicherungen sammelten sich unbegrenzt.** Bei jedem Update entstand ein `noah2games.bak-<Zeitstempel>`.
  Es bleiben jetzt die letzten zwei.

## [0.3.33] — 2026-11-08

### Behoben
- **CPU-Graph schnitt alles über 100 % ab.** Die Sparkline im Dashboard war fest auf 100 % skaliert,
  ein ARK-Server mit 700 % Last erschien als flache Linie am oberen Rand. Sie skaliert jetzt auf den
  tatsächlichen Höchstwert (mindestens 100 %).
- **CPU-Zahl war erklärungsbedürftig.** Der Wert ist der Summenwert über alle Threads (wie `top`/`htop`),
  kann also deutlich über 100 % liegen. Die Kachel nennt im Tooltip jetzt Kerne und Anteil am Server,
  z. B. „7,5 von 64 Kernen ausgelastet (11,8 % des Servers)".

## [0.3.32] — 2026-11-08

### Behoben
- **`--user` ließ die Dateien root gehören**, wenn kein Web-Dienst eingerichtet wurde (`--no-web`) — der
  Benutzer konnte danach seine eigenen Configs nicht schreiben. Die Rechte werden jetzt direkt nach dem
  Kopieren gesetzt.

## [0.3.31] — 2026-11-08

### Behoben
- **`--user NAME` wurde nicht erkannt** („Unbekannte Option"): die Argumentschleife konnte mit `shift` kein
  zweites Wort lesen. Sie läuft jetzt als `while`-Schleife, damit funktionieren `--user noah2games` und
  `--user=noah2games` (ebenso `--lang de`).

## [0.3.30] — 2026-11-08

### Behoben
- **Selbst-Update konnte stillschweigend denselben Stand einspielen.** Das Archiv wurde über den Branch
  `main` geladen; codeload liefert dafür minutenlang eine zwischengespeicherte Fassung. Jetzt wird das
  Archiv **zum geprüften Commit** geladen (`/tar.gz/<sha>`) — was die Prüfung meldet, wird auch installiert.

## [0.3.29] — 2026-11-08

### Neu
- **`sudo ./install.sh --user noah2games`** — Installation unter einem eigenen Dienst-Benutzer. Der Installer legt
  den Benutzer samt Home an, kopiert nach `/home/noah2games/…`, setzt die Rechte, richtet die Oberfläche als
  **User-Dienst** ein und aktiviert `loginctl enable-linger`, damit sie ohne Login startet. Damit läuft
  kein Teil mehr als root (empfohlen für Server).

## [0.3.28] — 2026-11-08

### Behoben
- **Spielserver starb beim Neustart der Oberfläche, wenn noah2games als normaler Benutzer läuft.** Die eigene
  systemd-Scope wurde nur auf dem System-Bus versucht, was ohne root scheitert — der Start fiel still auf
  einen normalen Kindprozess zurück. Jetzt läuft sie als `systemd-run --user --scope` über den
  Benutzer-Manager (dafür einmalig `loginctl enable-linger <benutzer>`), damit der Server einen
  Web-Neustart überlebt.

## [0.3.27] — 2026-11-08

### Neu
- **Portprüfung vor dem Start.** Belegt ein fremdes Programm (z. B. ein AMP-Server) den Spiel-, Query-
  oder RCON-Port, bricht noah2games mit einer klaren Meldung ab, statt einen Server zu starten, der nicht
  erreichbar ist — und statt RCON-Anfragen versehentlich an den falschen Server zu schicken.

## [0.3.26] — 2026-11-08

### Behoben
- **Startzeile nach AMP-Vorbild.** Port, Query-Port, RCON und Passwort stehen jetzt ausschließlich in der
  Map-URL (`?listen?Port=…?QueryPort=…?RCONEnabled=True?RCONServerGameLogBuffer=600?RCONPort=…?ServerAdminPassword=…`),
  das Passwort als **letzte** Option — ASA liest sonst den Rest der Zeile mit hinein. Die getrennten
  `-port`/`-RCONPort`-Argumente sind entfallen.
- `-SessionName` wird nicht mehr als Argument übergeben (Leerzeichen im Namen zerlegten die Zeile);
  der Name kommt aus `[SessionSettings]` der INI.

## [0.3.25] — 2026-11-08

### Behoben
- **RCON blieb trotz `RCONEnabled=True` bei „Passwort falsch".** ASA übernimmt das Admin-Passwort nur aus
  der Kommandozeile; jetzt steht `?ServerAdminPassword=…` in der Map-URL (genau wie bei AMP). Hinweis:
  damit ist das Passwort wie bei jedem ARK-Server in `ps` sichtbar.

## [0.3.24] — 2026-11-08

### Behoben
- **RCON antwortete auf frisch angelegten Instanzen mit „Passwort falsch".** noah2games übergab nur
  `-RCONPort` und verließ sich beim Aktivieren auf die INI; ASA wertet das aber erst mit
  `?RCONEnabled=True` in der Map-URL aus (so macht es auch AMP). Die URL enthält jetzt
  `?listen?Port=…?RCONEnabled=True?RCONServerGameLogBuffer=600?RCONPort=…`. Das Passwort bleibt in der
  INI — es taucht damit nicht in der Prozessliste auf.

## [0.3.23] — 2026-11-08

### Geändert
- Beispiel für das Cluster-Verzeichnis im Hinweis: `/home/Noah2Games/arkcluster` statt `/home/benutzer/arkcluster`.

## [0.3.22] — 2026-11-08

### Geändert
- **Cluster-Felder zeigen ihre Vorgabewerte direkt im Feld** — Cluster-ID ist der Instanzname, Verzeichnis
  ist `<instanz>/clusters`. Man sieht also den Pfad, muss ihn nur überschreiben, wenn geteilt werden soll.
  Der Hinweis nennt zusätzlich ein Beispiel (`/home/benutzer/arkcluster`).

## [0.3.21] — 2026-11-08

### Neu
- **Cluster-Einstellungen.** Bisher steckten `-clusterid=noah2games` und ein Verzeichnis pro Instanz fest im Code —
  Karten konnten also nie etwas teilen. Jetzt gibt es im Reiter Einstellungen eine eigene Karte **Cluster**:
  Cluster-ID, gemeinsames Verzeichnis und die Option „Übertragungen ohne Filterprüfung"
  (`-NoTransferFromFiltering`). Ohne eigene Angabe bleibt es beim alten Verhalten.
- **53 weitere INI-Einstellungen** aus dem vollen ARK-Satz, u. a. Transfer-Sperren (Download/Upload von
  Spielern, Items, Dinos), Offline-Raid-Schutz, Tribe-Allianzen, Struktur-Verfall und -Aufheben,
  Dino-Verfall, gezähmte Dinos pro Spieler, Prägung, Treffer-Markierungen sowie Futter-/Torpor- und
  Ernteschaden-Multiplikatoren. Das Formular ist jetzt nach Datei **und** Abschnitt gruppiert.

## [0.3.20] — 2026-11-08

### Behoben
- **„leer" in der Whitelist-Liste** war noch fest deutsch; läuft jetzt über `i18n.py` (`empty`).

## [0.3.19] — 2026-11-08

### Behoben
- **Zwei weitere deutsche Texte in der englischen Oberfläche:** „kein Snapshot vorhanden" und die
  Meldung beim Speichern der Sprache kamen fest verdrahtet aus dem Code. Beide laufen jetzt über `i18n.py`.

## [0.3.18] — 2026-11-08

### Behoben
- **Mod-Status war fest auf Deutsch** („nicht heruntergeladen", „für alte Engine gebacken") und blieb
  auch in der englischen Oberfläche deutsch. Jetzt kommen Codes aus `mods.py` und die Übersetzung aus
  `i18n.py` — `not downloaded` / `built for an older engine`.

## [0.3.17] — 2026-11-08

### Neu
- **Englische Beschreibung:** eigener Knopf im Kopfbereich (neben „Changelog") öffnet
  `README.en.md` auf GitHub. Das README verlinkt jetzt oben zwischen Deutsch und English.

## [0.3.16] — 2026-11-08

### Behoben (wichtig)
- **Die Oberfläche war tot, sobald die Seite geladen war:** im Update-Fortschritt (0.3.13) stand ein
  Zeilenumbruch als echtes Zeichen im JavaScript, das war ein Syntaxfehler — damit war das ganze Skript
  ungültig. Folge: Reiter ließen sich nicht wechseln, Mod-Knöpfe, Einstellungen und alles andere
  reagierten nicht. Ersetzt durch `String.fromCharCode(10)`, JavaScript wird jetzt vor dem Push mit
  `node --check` geprüft.

## [0.3.15] — 2026-11-08

### Behoben
- **Der Spielserver hängt nicht mehr am Web-Dienst.** Bisher startete er als Kindprozess von
  `noah2games-web`; Wine-Prozesse blieben beim Stoppen in dessen Prozessgruppe zurück („Unit process …
  remains running after unit stopped") und blockierten jeden Neustart der Oberfläche. Jetzt läuft jede
  Instanz in einer eigenen transienten Unit (`noah2games-<name>.scope`, via `systemd-run --scope`), damit
  überlebt der Server einen Neustart der Oberfläche und umgekehrt. Ohne systemd fällt noah2games auf den
  bisherigen Start zurück (`NOAH_NO_SCOPE=1` erzwingt das).

## [0.3.14] — 2026-11-08

### Geändert
- **RAM-Hinweis im Dashboard war irreführend** („ca. 11,5 GB pro laufendem Server"). Der Wert hängt an
  Mods, Weltgröße und Spielerzahl: leer und ohne Mods sind es rund 4 GB, mit Mods und Welt 11–12 GB,
  nach oben offen. Text in Oberfläche und `INSTALL.md` entsprechend korrigiert.

## [0.3.13] — 2026-11-08

### Neu
- **Update-Fortschritt ist sichtbar.** Bisher ging die SteamCMD-Ausgabe an das Dienst-Protokoll, im
  Server-Log stand während des Updates nichts. Jetzt schreibt noah2games sie nach `.update.log` und die
  Oberfläche zeigt sie im Ausgabefeld, während das Update läuft (`/api/update/progress`, Abfrage alle 2 s).

## [0.3.12] — 2026-11-08

### Behoben
- **Der Changelog-Knopf zeigte den Stand der Erstinstallation.** Das Selbst-Update ersetzt nur das
  Paketverzeichnis, die `CHANGELOG*.md` daneben blieben liegen. Jetzt zieht das Update beide Dateien mit,
  und die Oberfläche holt den Text frisch, wenn die eigene Version darin fehlt.

## [0.3.11] — 2026-11-08

### Behoben
- **`noah2games url` zeigte auf einem Server `127.0.0.1`.** Bei Zugriffsart „IP" steht jetzt die Adresse,
  unter der die Oberfläche wirklich erreichbar ist (die lokale Adresse ermittelt noah2games selbst).

## [0.3.10] — 2026-11-08

### Behoben
- **Selbst-Update scheiterte stillschweigend.** Ein einzelner `504 Gateway Timeout` beim Archiv-Download
  beendete den Vorgang, die Oberfläche meldete trotzdem nichts — der Knopf wirkte wirkungslos. Jetzt:
  drei Versuche mit Pause und ein zweiter Weg über `codeload.github.com`, und die Oberfläche zeigt
  „Update fehlgeschlagen: …" statt Stille.
- Das Einspielen läuft synchron; der Neustart des Dienstes passiert eine Sekunde später, damit die
  Antwort noch ankommt.

## [0.3.9] — 2026-11-08

### Neu
- **Der Build-Badge ist ein Knopf.** Auf der Instanzseite stand bisher nur `AKTUELL 26515168` — das
  Update ließ sich nur von der Übersicht starten. Jetzt gilt: `UPDATE a→b` anklicken startet das Update
  (mit Rückfrage, Sicherung und Stop), `AKTUELL b` prüft beim Klick erneut. Tooltip erklärt beides,
  per Tastatur (Enter/Leertaste) genauso bedienbar.

## [0.3.8] — 2026-11-08

### Sicherheit
- **Token-Vergleich in konstanter Zeit** (`hmac.compare_digest`) statt `==`.
- **Sicherheits-Header** auf jeder Antwort: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer` (damit der Token nicht über die Herkunftsangabe abfließt) und eine
  restriktive `Content-Security-Policy`.
- **Mod-IDs werden geprüft** (nur Ziffern, max. 10 Stellen). Vorher landete der Wert ungefiltert in der
  Server-Kommandozeile (`-mods=…`).
- **Spieler-IDs** (Whitelist/Bans) nur als Steam64 (Ziffern) oder Hex-UniqueNetId — Zeilenumbrüche und
  Sonderzeichen werden abgelehnt, statt in die Textdatei zu wandern.

## [0.3.7] — 2026-11-08

### Geändert
- **Mod-Suche funktioniert ohne Instanz.** `/api/mods/search`, `/api/mods/suggest` und das Speichern des
  API-Keys hingen hinter der Instanz-Prüfung und antworteten ohne angelegte Instanz mit „keine Instanz".
- Der Mods-Reiter zeigt, womit gesucht wird: `CurseForge-API aktiv · Suche nach Titel und Beschreibung,
  sortiert nach Downloads` (grün, mit maskiertem Key) oder `Kein API-Key · nur genaue Mod-ID oder
  CurseForge-Link, keine Volltextsuche`.

## [0.3.6] — 2026-11-08

### Geändert
- Der Versionsknopf zeigt den Zustand im Text: `aktueller Stand` bzw. `neuer Stand`, nicht nur
  im Tooltip.

## [0.3.5] — 2026-11-08

### Geändert
- Meldet noah2games „gleiche Version, nur neuer Build", ist der Knopf nicht mehr klickbar — es gibt
  nichts zu holen. Änderungen, die ankommen sollen, bekommen einen Versionssprung.

## [0.3.4] — 2026-11-08

### Geändert
- Copyright nur noch unter dem Handle `ronny79privat` (statt Klarname).

## [0.3.3] — 2026-11-08

### Geändert
- Copyright-Hinweis im README und in der `LICENSE` (ronny79privat).
- „Für Entwickler" aus der Technik-Doku ausgelagert nach `docs/entwicklung.md` — für Anwender
  unwichtig, für Mitlesende weiterhin erreichbar.

## [0.3.2] — 2026-11-08

### Geändert
- README auf das Wesentliche gekürzt (111 statt 420 Zeilen). Funktionen, Zugriff, Betrieb und
  Technik stehen jetzt in `docs/funktionen.md`, `docs/zugriff.md`, `docs/betrieb.md` und
  `docs/technik.md`.

## [0.3.1] — 2026-11-08

### Geändert
- README neu sortiert: Installation und Deinstallation stehen oben, danach Zugriff von außen und
  der Token; Feature-Liste und Screenshots folgen weiter unten.

## [0.3.0] — 2026-11-08

### Hinzugefügt
- **Changelog-Knopf** im Kopf: öffnet die Änderungen als Popup, in der eingestellten Sprache
  (Deutsch/Englisch). Der Inhalt kommt aus der eigenen Installation, kein Netzzugriff nötig.
- Englische Fassung: `CHANGELOG.en.md`.

### Geändert
- Der Update-Dialog zeigt die Änderungen der neuen Version direkt an.
- Benachrichtigungen: Routine-Meldungen bleiben im Log, nur Ereignisse gehen an Discord.

## [0.2.9] — 2026-11-08

### Hinzugefügt
- **CHANGELOG.md** — was sich je Version geändert hat.
- Der Update-Dialog zeigt die Änderungen der neuen Version an, bevor man zustimmt.
- **`scripts/release.sh`**: Version setzen, committen, taggen, pushen (mit `--release` auch das
  GitHub-Release, sofern `gh` installiert ist).

## [0.2.8] — 2026-11-08

### Behoben
- Modsuche lieferte mit API-Key **null Treffer**: der Parameter `classId` schränkte die
  CurseForge-Abfrage auf eine Kategorie ein, die für ARK-ASA-Mods nichts liefert. Ohne
  Einschränkung kommen die erwarteten Ergebnisse.
- Leere Suchergebnisse werden nicht mehr eine Stunde zwischengespeichert.

## [0.2.7] — 2026-11-08

### Geändert
- Update-Prüfung wird **10 Minuten gecacht** — GitHub erlaubt ohne Token nur 60 Anfragen pro Stunde.
  `noah2games version` und `noah2games self-update` prüfen weiterhin frisch.

## [0.2.6] — 2026-11-08

### Hinzugefügt
- **„← Dashboard"** im Kopf der Instanzseite.

### Geändert
- Das Update-Badge der Instanz erscheint nur noch bei belastbarer Prüfung (vorher stand dort
  dauerhaft „UPDATE ?", solange die Serverdateien fehlten).
- `install.sh` startet einen laufenden `noah2games-web`-Dienst nach dem Kopieren neu, damit der neue
  Code sofort aktiv ist.

## [0.2.5] — 2026-11-08

### Geändert
- Update-Knopf im Badge-Stil statt als vollflächiger Block.

## [0.2.4] — 2026-11-08

### Geändert
- Update-Knopf ist beschriftet: `noah2games update: 0.2.3 → 0.2.4` statt nur Versionsnummern.

## [0.2.3] — 2026-11-08

### Behoben
- Selbst-Update holte das Quellarchiv über `codeload.github.com`, das nach einem Push noch den
  alten Stand ausliefert. Jetzt über die GitHub-API.

## [0.2.2] — 2026-11-08

### Behoben
- Versionsprüfung las `raw.githubusercontent.com` (bis zu 5 Minuten veraltet) — jetzt über die
  GitHub-API.

## [0.2.1] — 2026-11-08

### Behoben
- `/api/selfupdate` war nur mit vorhandener Instanz erreichbar.

## [0.2.0] — 2026-11-08

### Hinzugefügt
- **Selbst-Update**: Knopf im Kopf (`noah2games update: alt → neu`) und `noah2games self-update`.
- **Modsuche**: Mod-ID, CurseForge-Link oder Name; Vorschläge erscheinen beim Tippen, mit Bild,
  Downloads und einem Klick zum Übernehmen. Namen brauchen einen CurseForge-API-Key.
- **Mod-Updates im Blick**: installed-Datei vs. neueste Datei auf CurseForge, Kennzeichen „UPDATE".
- **Discord-Benachrichtigungen**: Absturz, Hänger, Update verfügbar, Backup-Fehler, geplanter
  Neustart — Routine bleibt im Log.
- **Hänger- und Absturzerkennung** im Supervisor; ein manueller Stop wird respektiert.
- **`noah2games proxy`**: richtet nginx mit HTTPS ein (Zertifikat per certbot, optional Basic Auth),
  prüft mit `nginx -t` und rollt bei Fehlern zurück.
- **HTTPS direkt** im Webserver (`--tls-cert` / `--tls-key`).
- **Instanz löschen** auf der Dashboard-Karte (Config ins `.trash`, Dateien nur auf Wunsch).
- **Update-Knopf** und **Löschen** direkt auf der Karte.
- **MOTD** als mehrzeiliges Formularfeld.
- **Zweisprachig** (Deutsch/Englisch): Sprachwahl im Installer, Knopf in der Oberfläche,
  `noah2games lang`.
- **Drei Zugriffswege** im Installer: client-seitig per SSH-Tunnel, öffentlich per Domain+HTTPS,
  direkt über IP und Port.
- Der **Supervisor-Dienst** wird nach der Installation einer Instanz automatisch eingerichtet
  (als root ein Systemdienst, der beim Booten startet).

### Geändert
- Instanzseite: Server-Log oben über die volle Breite und ziehbar (48 % Höhe, 150 Zeilen),
  Steuerknöpfe liegen auf der Dashboard-Karte.
- Server-Log springt beim Öffnen ans Ende; der aktive Reiter bleibt beim Neuladen erhalten.
- Kartenhintergrund deutlich sichtbar (Deckkraft 0.28 → 0.62).
- Einstellungen: mehrzeilige Felder (Textarea) möglich.
- `settings.json` wird mit `0600` geschrieben, weil sie den API-Key enthält.

## [0.1.0] — 2026-11-07

Erster öffentlicher Stand: Instanzen anlegen, Start/Stop/Restart/Update über SteamCMD, RCON-Konsole
mit Klick-Befehlen, Spielerverwaltung, Mod-Verwaltung, Config-Editor, Welt-Backups, Snapshots,
Whitelist/Bans, Zeitplan, Live-Metriken und Weboberfläche.
