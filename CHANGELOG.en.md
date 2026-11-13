## [0.7.37] — 2026-11-13

### Added
- **Item dialog with a list instead of free text.** The "Item" button opens a searchable list
  of known items (tools, weapons, ammo, consumables, resources, armour) plus a quantity field;
  full blueprint paths live in `polypanel/catalog.py`. A custom blueprint can still be entered.
  New endpoint `/api/catalog?q=`.
- **Unban dialog on the instance page.** The EOS id of a banned player can be entered above the
  player list - offline players cannot be clicked and ARK offers no ban list over RCON.

## [0.7.36] — 2026-11-13

### Changed
- **Removed unused log styles** (`.logwrap`, `.loghead`, `.cardlog`) - leftovers of the log
  window on the overview cards.

## [0.7.35] — 2026-11-13

### Changed
- **No log window on the overview page anymore.** With many instances the overview became
  cluttered and every card additionally polled log lines every 2.5 seconds. The log stays on
  the instance page; cards now show status, load and actions only.

## [0.7.34] — 2026-11-13

### Changed
- **Menu stays available at all times.** Even during stop, start, restart or update the menu
  button stays active - log, configuration and pages remain reachable, only the actions that
  make no sense right now are locked.

## [0.7.33] — 2026-11-13

### Added
- **Player window on the overview.** Clicking the player count opens a window listing every
  player of the instance: name, **EOS id** and the actions **Kick**, **Ban**, **Unban**.
  Ban asks for confirmation; the list reloads after each action.

## [0.7.32] — 2026-11-13

### Changed
- **Update stays available while the instance is stopped.** That is exactly when the server
  files get replaced - previously the button was locked in the stopped state.

## [0.7.31] — 2026-11-13

### Fixed
- **Player count stayed at 0 with players online.** `ListPlayers` line detection only accepted
  15-17 digit ids (SteamID). ARK: Survival Ascended returns the **32 character hex EOS id**, so no
  line matched and the player list stayed empty. Both formats are accepted now.

### Changed
- **Buttons lock according to state.** While a stop runs, every button is disabled. While start,
  restart or update runs (or the instance is still booting) **only Stop** stays enabled, to abort.
  The state comes from the server (`action` in `/api/instances`) and is set locally on click so
  double clicks cannot slip through.
- **"1 instances" instead of "1 instance".** The dashboard counter now uses the singular form when
  exactly one instance exists (new text key `dash.instance_single`).


## [0.7.29] — 2026-11-11

### Fixed
- **The admin password did not survive a restart/update.** The ARK profile's start line always got the
  RCON password while the admin password was written into `GameUserSettings.ini`. ARK reads the value
  from the start line and overwrites the INI on start. Start line, INI and RCON login now use the same
  source (`Instance.admin_pw`: admin password, otherwise RCON password). An admin password set in the
  config editor (form or raw INI) is copied into the instance config and therefore persists.
- **"Restart" behaved like "Stop" — the server never came back.** A restart was `stop(); sleep(3);
  start()` inside a thread without error handling: if the start failed (e.g. because Wine still held
  the ports), the server stayed down without any message. There is now `runner.restart()`: stop, wait
  until the ports are really free (leftover processes of the instance are terminated), then start with
  one retry; on failure the error names every step and the blocking port.
- **Failures of start/restart/update are visible** (in `<instance>/.start.log`, the supervisor log and
  as a Discord event, instead of vanishing inside the thread).
- Installing through the UI sent a 404 response after the success message.

## [0.7.28] — 2026-11-11

### Added
- **Progress bar while installing.** SteamCMD prints `Update state (0x61) downloading, progress: 42.31`;
  that line is now parsed (`GET /api/install/progress`) and the UI shows a bar with phase and
  percentage — phases without a percentage (preallocating, verifying) show as text. When done the bar
  runs to 100 % and hides itself. The install log now shows the last 40 lines instead of 10.
- The first phase (Steam API, client config) has no percentage, so the bar appears when the actual
  download starts.

### Changed
- **Checker for the installer texts** (`tools/check_texts.py`): compares every `$(t KEY …)` call with
  the placeholders used by the text and reports missing arguments and unknown keys — the exact class
  of bug that produced the prompt without a package name.
- **The build badge used to disappear silently.** If the server was not installed yet, or the Steam
  query failed (e.g. missing 32-bit libraries), the badge was simply hidden — it looked as if the
  update check never ran. It now reads "UPDATE STATUS UNKNOWN" with the reason in the tooltip
  ("not installed yet" or "Steam query failed"), and a click retries right away.
- **The update check no longer asks Steam every minute.** Every open browser tab called `/api/update`
  once a minute, and the server spawned a separate `steamcmd` process each time (`+app_info_print`,
  timeout up to 180 s). The result is now cached for **15 minutes** and the UI asks only every
  **5 minutes**; clicking the build badge forces a fresh query.

### Fixed
- **The page was dead after the update.** The inserted error text contained a real newline inside the JavaScript string, which broke the whole `<script>` block (SyntaxError) and left every button unresponsive. The text is escaped properly now (`\\n`) and `node --check` passes on all templates.
- **"Start" appeared to do nothing.** The UI swallowed every error (`catch(e){}`), so a busy port,
  missing server files or a supervisor problem stayed completely silent. It now shows the real
  message, e.g. "Port 7780 is already in use …" or "server not installed".
- **The "… is missing. Install now?" prompt had no package name.** The call passed an empty argument
  to the text function (`t missing_ask "" "$label"`) while the message prints `$2`, so the name was
  blank — for every missing dependency (Wine, iproute2, 32-bit libraries). It now reads
  "Wine fehlt. Jetzt installieren? [j/N]", and the libraries got their own sentence so the German
  grammar fits.
- **Missing text on language switch.** The UI showed `undefined` plus the error when switching the
  language failed, because `msg.lang_failed` was not in the catalog. It now reads
  "Sprache wechseln fehlgeschlagen:" / "language switch failed:".
- **Self-update did nothing ("panel does not update").** `apply()` looked for the package folder
  inside the GitHub archive under the repo name (`AscendedPanel/`), but it is installed as
  `ascendedpanel/`. On Linux those are two different folders, so the update aborted with "package
  folder missing from archive" while the badge kept offering the update. The folder is now matched
  case-insensitively, so the update applies and the header shows the new version afterwards.
- **The log stayed empty during installation.** SteamCMD reports download progress with a carriage
  return (`\r`) and no newline. The installer read line by line, so the first line only arrived after
  the whole download — with 10-15 GB that looks like "nothing is happening". Output is now read in
  blocks, split on `\r` and `\n`, stripped of ANSI colour codes and every progress line is written to
  `.install.log` immediately (flushed per line). The SteamCMD fetch and the exact command are logged
  as well.
- **The update log now shows real lines instead of one endless line** — same path as the install.
- **SteamCMD failed on fresh servers with `exit 127`.** The cause was missing 32-bit libraries
  (`ld-linux.so.2`, i386 `libstdc++.so.6`) - a beginner trap the program has to handle itself. The
  installer now checks for i386 libraries in `--check`, installs them with `--auto` (apt:
  `dpkg --add-architecture i386` plus `lib32gcc-s1`, `lib32stdc++6`, `libc6:i386`; dnf:
  `glibc.i686`; zypper: `glibc-32bit`; pacman: `lib32-glibc`) and otherwise prints the exact command
  needed by hand.

0.7.8] — 2026-11-10

### Fixed
- **`polypanel web` raised a traceback when the port was taken.** If the web service was already
  running you got `OSError: [Errno 98] Address already in use` plus a full stack trace. It now prints a
  clear message with three options — check the service (`systemctl --user status polypanel-web`), use another
  port (`polypanel web --port <free>`), or just print the address (`polypanel url`) — and exits 1.
- **Docs started the service twice.** After `install.sh` the service already runs, yet the install
  instructions still said `polypanel web`. They now say `polypanel url`, which only prints the ready
  address with the token.
- **`xvfb` is now part of the installation.** Without the virtual display the ARK Ascended server aborts under Wine before writing anything to its log — start button seemingly dead, empty log. The installer checks `Xvfb` like Wine and installs it with `--auto` (apt `xvfb`, dnf `xorg-x11-server-Xvfb`, pacman `xorg-server-xvfb`, zypper `xvfb`).
- **The server would not start.** `runner.start()` launched the supervisor as `-m AscendedPanel.consoled` while the module is `ascendedpanel.consoled` — on Linux that process never starts, no console log is created, and `stderr` also went to `/dev/null`: no process, no log, no message. The call is fixed and start output now lands in `<instance>/.start.log` instead of nowhere.
- **Install aborted with `Failed to install app '2430930' (Missing configuration)`.** ARK Ascended has no Linux server build; SteamCMD only fetches the Windows branch with `+@sSteamCmdForcePlatformType windows`. The switch is now passed automatically for ASA — ASE, 7D2D, Satisfactory and Space Engineers keep their command line unchanged. Applies to install and update.
- **Installs can be cancelled.** While downloading there is a button "cancel installation" above the log (`POST /api/install/cancel`); it kills the SteamCMD process group, notes it in the log and clears the progress. The partial download stays and is reused on the next attempt.
- **`Xvfb` is installed without asking.** The prompt for a "virtual display" sounded optional, yet the ARK Ascended server cannot start under Wine without it. The installer now pulls the package silently (also as root without `sudo`), `--check` only reports it. If the install fails the package name is shown.
- **SteamCMD now repairs itself.** A self-test (`steamcmd +quit`) runs before every install; if it fails or SteamCMD reports `Missing configuration`, the client is downloaded again and the attempt repeated **once** — no manual steps. That was needed for a reliable install on a fresh VPS.
- **`--uninstall` now removes SteamCMD as well** (`~/steamcmd`, `~/.steam`); previously the multi-GB
  client files stayed behind after the panel was gone.
- **Search field in the settings.** A search box above the tabs filters all groups at once by name or ini key (`NoTributeDownloads`), hides empty sections and restores the previously selected tab when cleared.
## [0.7.7] — 2026-11-10

### Changed
- **The access question now flags the risky option up front.** `[3] direct via IP and port` is labelled
  "HTTP, NOT recommended". The detailed warning and the `Really set it up this way? [j/N]` prompt still
  appear right after choosing `[3]`; picking `[1]` (SSH tunnel) deliberately shows none, because then
  nothing is exposed to the network.

## [0.7.6] — 2026-11-10

### Fixed
- **Install instructions used the wrong case.** `git clone … polypanel` creates a lowercase folder,
  but the docs then asked for `cd PolyPanel`. On a case-sensitive filesystem that aborts with
  `No such file or directory`. All commands, the troubleshooting table and the note about the
  same-named package folder now say `polypanel`; the duplicated `cd` line in `INSTALL.de.md` is gone.

## [0.6.5] — 2026-11-10

### Fixed
- **Satisfactory mod search returned arbitrary hits.** The ficsit.app query had no ordering — now
  `order_by:popularity,order:desc` (GraphQL enum **without** quotes, otherwise the API rejects it
  with "cannot represent non-enum value"). Hits now come sorted by popularity.
- **The hint text in the mods tab was the Nexus/GitHub text for every game.** Now per game: Steam
  Workshop (ARK Evolved, Space Engineers), ficsit.app (Satisfactory), Nexus/GitHub (7D2D).
- **German search terms in English portals.** `query_english()` translates the term (glossary first:
  "förder" → conveyor, "lager" → storage, "zug" → train; otherwise the translation service).

## [0.6.4] — 2026-11-10

### Added
- **Mod search for Space Engineers** — in the Steam Workshop (app 244850), real full-text search
  without a key, hits with subscriber count and description. "Install" writes the workshop ID as a
  `ModItem` into the `<Mods>` list of `SpaceEngineers-Dedicated.cfg` (XML stays valid, duplicate IDs
  are caught); the server downloads it on start.
- Entered IDs show up in the mods tab; the hint texts now name the Steam Workshop instead of only
  ARK Evolved.

### Changed
- **The workshop search lives in `games/steam_workshop.py`** and is used by ARK Evolved *and* Space
  Engineers (previously ASE only, SE just showed a link).

## [0.6.3] — 2026-11-10

### Changed
- **The wizard is no longer part of the normal install flow.** README and INSTALL now name
  `noah2games web` as the path (create and install the instance in the browser); the console wizard
  is its own, explicitly optional paragraph ("console only"). The wrong statement "the web interface
  cannot create an instance" is gone — it can, via the dashboard form.
- The closing hints of `install.sh` name `noah2games web` first and the wizard as optional
  (new line, own translation key).

## [0.6.2] — 2026-11-10

### Fixed
- **"Delete with files" never removed the server folders.** The safety check only accepted names
  starting with `arkserver` — for `~/noah2games-instances/<name>` and `/mnt/Games/noah2games/<name>`
  8–17 GB per instance stayed on disk, silently. Now the folder must sit inside an instance root and
  be named like the instance; its size is measured first and reported as "X GB freed". Everything
  else is refused with a clear hint instead of being skipped quietly.
- **The delete message in the dashboard always said "error"** because the response was read as text
  instead of JSON. It now reports the freed size, or that the files were left in place.
- The supervisor marker `<folder>.stopped` is removed together with the folder.

## [0.6.1] — 2026-11-10

### Added
- **Mod descriptions are translated to German automatically.** In the German UI the mod search hits
  (Steam Workshop, CurseForge, Nexus/GitHub, ficsit.app) are translated — including the suggestions
  while typing. Translations are cached in `~/.config/noah2games/cache/translations` and reused;
  if a translation fails the original text stays. First search ~2.5 s, every repeat ~0.4 s.
- Texts that are already German are detected and not translated again.

## [0.6.0] — 2026-11-10

### Added
- **Mod search for ARK Evolved straight in the Steam Workshop** — real full-text search (no API
  key, no login), hits with subscriber count, description and Steam link. "Install" writes the
  workshop ID into the mod list (`ActiveMods` in `GameUserSettings.ini`); the server downloads it
  on the next start (`-automanagedmods`). Mods already added are marked and the button is disabled.
- **Entered workshop IDs are visible** in the mods tab (list with "downloaded on next start") —
  previously only the folder content was shown, the IDs lived in the INI only.
- Own hint texts for ARK Evolved in the mods tab (instead of the Nexus/GitHub explanation).

## [0.5.1] — 2026-11-10

### Added
- **Every ARK Evolved setting in the form.** Instead of the 51 core fields the tab now shows
  **262 values**: 156 from `GameUserSettings.ini` (ServerSettings, SessionSettings, MOTD) and 100
  from `Game.ini` — including breeding, imprinting, PvP, turret, cryo, tribute and Genesis options.
  Every property has a German label and a hint.
- **Full ASE template shipped** (`games/arkse_template_gus.ini`, `..._game.ini`): default values of
  the official ASE configuration, so the form is complete before the first start. ASE adds its own
  values on start; the UI keeps reading everything from the files.
- **Keys are matched regardless of casing** — ASE writes `serverPVE` and `globalVoiceChat` in mixed
  case, the labels still apply.

### Fixed
- **`ActiveMods` belongs in `GameUserSettings.ini`** (section `ServerSettings`), not in `Game.ini` —
  ASE ignored the mod list there.

## [0.5.0] — 2026-11-10

### Added
- **ARK: Survival Evolved as the fifth game** (`--game arkse`, Steam app 376030). Unlike Ascended
  it runs **natively** on Linux (`ShooterGame/Binaries/Linux/ShooterGameServer`) — no Wine, no
  prefix:
  - **Configuration**: `GameUserSettings.ini` and `Game.ini` in
    `ShooterGame/Saved/Config/LinuxServer/` — ports, server name, admin password and workshop mods
    are written by the manager, the map goes into the launch line.
  - **Control** via Source RCON (`ServerAdminPassword`), including player list, kick/ban and
    `SaveWorld` + `DoExit` on stop.
  - **Settings**: every property of both INI files as a form, with German labels and the familiar
    tabs (server, gameplay, PvP, structures, dinos, transfer, display, MOTD, Game.ini).
  - **Mods**: workshop IDs in the "Mods" field, the server downloads them on start
    (`-automanagedmods`).
  - **Map list** in the dashboard: The Island, Ragnarok, Scorched Earth, The Center, Aberration,
    Extinction, Valguero, Genesis, Crystal Isles, Genesis 2, Lost Island, Fjordur.
- **The map list now belongs to the game profile** — ASA and ASE use different world names, so the
  dashboard refills the select when the game changes (other games have no map select).
- **Console command buttons (save, broadcast, dino wipe …)** work for ASE as for ASA; whitelist,
  cluster tab and the raw INI editor stay Ascended-specific.

## [0.4.3] — 2026-11-10

### Added
- **Licence, copyright, PayPal and Discord inside the UI.** Every page now carries a footer with
  `noah2games <version> · © 2026 Ronny H. · all rights reserved` and three links: **Licence**
  (opens the new `/license` page with the licence text in the active language), **PayPal**
  (donation link) and **Discord community** (Ark-ASA-ASE-Hilfe). The two brand icons stay in the
  top right corner.
- **`/license` page** (also `/lizenz`): shows the text from `LICENSE` in German or English,
  depending on the UI language, with a link back to the dashboard.

### Fixed
- **The installer now copies `LICENSE`** (it was missing from `~/.local/share/noah2games`, and with
  it the copyright notice in the installed copy). README and INSTALL are copied in both languages.

## [0.4.2] — 2026-11-10

### Added
- **Mod search for every game.** The mods tab is now visible everywhere:
  - **Satisfactory** — search and install straight from ficsit.app (GraphQL), including download
    and extraction into `FactoryGame/Mods`
  - **7 Days to Die** — links to the NexusMods search (no official search API), mods go into
    `Mods/` as folders
  - **Space Engineers** — links to the Steam Workshop; workshop IDs belong into the "Mods"
    config field and are downloaded by the server on start
- **Clearly visible tabs**: filled background, stronger type, active tab colour-filled.

## [0.4.1] — 2026-11-10

### Added
- **Space Engineers as fourth game** (app 298740). SteamCMD ships the Windows build only, so
  noah2games creates a shared Wine prefix (`~/.noah2games-wine-se`) on first install and adds
  `dotnet48` and `vcrun2019` there — once for all SE instances. A config template
  (`SpaceEngineers-Dedicated.cfg`) is included; 200+ options are labelled in German.
- **Visual feedback for start/stop/restart** in the dashboard: banner with a seconds counter,
  disabled buttons, final message ("running" / "stopped").
- **Graceful shutdown** through the server console (`save`, `stop`) instead of an immediate signal.

### Fixed
- **The instance list could stay empty** when a running server had no PID file (KeyError on
  missing metrics).
- **Hand-started servers** are detected via working directory and executable — status, metrics and
  stop now work for them too.
- **7 Days to Die**: log file is found (`output_log__*.txt`), `logs/` is created.
- **Satisfactory**: status query failed on `ListPlayers`; players now come from `QueryServerState`,
  a missing API token is no longer treated as an error.
- **Space Engineers**: status without RCON, per-run log file, `OnlineMode` must be uppercase
  (otherwise SE discards the whole config).
- **Web UI**: new background (drifting colour clouds), glass look, refreshed screenshots.

## [0.4.0] — 2026-11-10

### Added
- **Game profiles: Satisfactory and 7 Days to Die alongside ARK.** The core stays game-agnostic;
  a profile provides the launch line, config file, paths and control channel:
  - `ark` — ARK: Survival Ascended (app 2430930, Source RCON, Wine) as before
  - `satisfactory` — Satisfactory Dedicated Server (app 1690800, `FactoryServer.sh`, game/query/
    beacon ports, controlled via the HTTPS API `/api/v1` with a bearer token)
  - `7d2d` — 7 Days to Die (app 294420, `startserver.sh`, `serverconfig.xml`, controlled via Telnet)
- Create with `noah2games --name <name> init --game satisfactory|7d2d`, or via the `game`
  parameter of `/api/instances` in the web UI.
- New per-instance fields: `beacon_port`, `api_token` (Satisfactory), `telnet_password` (7D2D).

### Changed
- Wine is only used for ARK; Satisfactory and 7D2D run natively.
- Instance directory is now `~/noah2games-instances/<name>` (separate from noah).

## [0.3.70] — 2026-11-09

### Changed
- **Stopping is much faster and now reports the duration.** Previously only the launcher PID was
  watched: it disappears first while `ArkAscendedServer.exe` and `wineserver` are still running, so
  noah2games waited out the full grace period (up to 90 s) and left processes behind. Now every process of
  the instance is found via its command line, the wait ends as soon as none is left, and the message
  includes the time taken ("stopped after 6 s"). Fallback unchanged: SIGTERM to the group, then
  SIGKILL on the rest.

## [0.3.68] — 2026-11-08

### Changed
- **The backup box is gone entirely.** World backups run exclusively as a task in the schedule (action
  "Backup"); snapshots keep their own box. The UI no longer offers restoring single backups — the files
  under `~/noah2games-backups` and the API remain.

## [0.3.67] — 2026-11-08

### Changed
- **"Backup times" is gone** — backups run exclusively as a task in the schedule (action "Backup"), so the
  same effect no longer lives in two places. The backup box now points to that and keeps "Back up now"
  for an immediate world backup.

## [0.3.66] — 2026-11-08

### Fixed
- **Cleared time fields were ignored:** an empty field (restart, backup, snapshot) never reached the
  server because empty query values were dropped — the old times stayed and could not be switched off.
  Empty values are passed through now and clear the list.

## [0.3.65] — 2026-11-08

### Changed
- **Snapshots have their own time list** ("Snapshot times" in the snapshot box, comma separated like the
  backups) instead of being an action in the schedule. The schedule stays for the other actions.
- "Keep auto snapshots" is unchanged and still applies to the automatic snapshots.

## [0.3.64] — 2026-11-08

### Changed
- **"Keep auto snapshots" now sits below the button** instead of above it, and the hint states the disk
  math (3 = one day at 3 per day, 15 ≈ 180 GB).

## [0.3.63] — 2026-11-08

### Added
- **Snapshots can be created by the schedule too** (action "Snapshot"), e.g. Sundays 04:00. So the 12 GB
  copies do not pile up, only the last three auto snapshots are kept; the number is available as
  "Keep auto snapshots" next to the snapshot box.
- Manual snapshots are never touched — only `auto_*` ones are pruned, sorted by change time.
- **Two snapshots within the same second** would have collided (`FileExistsError`); the name now gets a
  counter.

## [0.3.62] — 2026-11-08

### Changed
- **The schedule now takes the full width**, the backup box sits below it. That gives the task rows room
  for action, time, weekdays, argument and switch on one line.
- "Backup times" stays in the backup box (backups are not snapshots).

## [0.3.61] — 2026-11-08

### Changed
- **"Backup times" now sits with the snapshots** instead of the backup box — where the safety copies
  belong. The note also points to the new schedule task "Backup" as an alternative.

## [0.3.60] — 2026-11-08

### Fixed
- **The supervisor only read the schedule at start-up.** Tasks saved in the UI only ran after a
  supervisor restart. It now reloads the schedule fields each round as soon as the instance file changes
  (ports and mods deliberately untouched).
- **Self-update did not restart the supervisor**, so it kept running old code. Now `noah2games-web` and
  `noah2games-supervise` are both restarted when they are active.

## [0.3.59] — 2026-11-08

### Fixed
- **Scheduled tasks could share the same ID** when created within the same millisecond (e.g. when the
  whole list was sent). The ID now carries an index — otherwise the supervisor would treat two tasks as
  "already done".

## [0.3.58] — 2026-11-08

### Added
- **Schedule with tasks** (Management → Schedule), similar to AMP's scheduled tasks: each task has an
  **action, time, weekdays** (empty = daily) and a free-text field for broadcast or RCON command.
  Actions: restart, start, stop, update + restart, backup, save world, destroy wild dinos, broadcast,
  free RCON command.
- Restart tasks use the warning countdown in game, the others run immediately; every run is reported to
  the Discord webhook, failures as errors.
- The old "restart times" stay as a fallback.

## [0.3.57] — 2026-11-08

### Changed
- **The note now states the reason:** "The CurseForge API returns at most 50 hits per request — more
  cannot be fetched." The hit line reads "CurseForge API: at most 50 per request".

## [0.3.56] — 2026-11-08

### Added
- **Note about the hit limit** below the search field: at most 50 hits per search, narrow the term for
  more. Also appended to the hit line as soon as the list is truncated
  ("50 / 7,291 hits · no more per search").

## [0.3.55] — 2026-11-08

### Changed
- **Mod search fetches 50 hits** instead of 30 (the CurseForge search API does not allow more per request).
  Enough for targeted searching; otherwise narrow the term.

## [0.3.54] — 2026-11-08

### Changed
- **The hit count is clearly visible above the mod list now** (12.5 px, accent colour instead of dim
  11 px): "30 / 7,290 hits". The suggestion list while typing names its count as well.

## [0.3.53] — 2026-11-08

### Fixed
- **Cached search results could hide the API results.** A fallback result (few hits, no key) was served
  for an hour even after a key had been set — the search kept showing 8 instead of 30 hits. The cache now
  separates keyed/unkeyed searches and the hit limit, and stores the total count.

## [0.3.52] — 2026-11-08

### Changed
- **Mod search lists up to 30 hits** instead of 10, with the hit count above it ("30 / 1,412 hits",
  total taken from the CurseForge response). The list scrolls instead of stretching the page.

## [0.3.51] — 2026-11-08

### Changed
- **`console.curseforge.com` in the "CurseForge API key" field is a link now** (opens in a new tab)
  instead of plain text.

## [0.3.50] — 2026-11-08

### Changed
- **Discord and PayPal icons are bigger and use the brand colours** (34 px box, 22 px glyph; Discord
  #5865F2, PayPal #003087) instead of small and monochrome.

## [0.3.49] — 2026-11-08

### Added
- **Discord and PayPal icons in the top right** — on every page (dashboard, instance page, mods,
  management). The icons are embedded, so no request goes to an external server unless someone clicks.

## [0.3.48] — 2026-11-08

### Added
- **Tabs in the settings form:** the 90 known INI values are sorted into nine groups — Server & access,
  Gameplay & rates, PvP & rules, Structures & decay, Dinos & breeding, Transfer & cluster, Display, MOTD
  and Game.ini. Each tab shows its count; the browser remembers the last choice.
- Saving still writes everything at once — fields on the other tabs are kept.

## [0.3.47] — 2026-11-08

### Changed
- **The button reads "Menu" and opens the instance directly** — label as requested, no intermediate step
  or dropdown.

## [0.3.46] — 2026-11-08

### Changed
- **Back to the direct route:** "Open" leads straight into the instance again; the menu button and dialog
  are gone.

## [0.3.45] — 2026-11-08

### Changed
- **No dropdown in the card any more:** a plain **"Menu"** button opens a choice of Overview, Settings,
  Mods and Management.

## [0.3.44] — 2026-11-08

### Changed
- **The selector in the card is labelled "Menu …"** instead of "Open …" — it is a choice, not a button.

## [0.3.43] — 2026-11-08

### Changed
- **Start page reordered:** "New instance" and "Note" sit on top now, the instances follow below — the
  creation form stays where it is even when instances are added.
- **"Open" is a menu:** pick Overview, Settings, Mods or Management; the detail page jumps to that tab.
- Card and log sizing back to 0.3.39 (log only for running instances, 9.5 px, cards from 300 px).

## [0.3.39] — 2026-11-08

### Changed
- **Running instances span two grid columns** on the dashboard (window width 900 px and up). Otherwise the
  card was too narrow and the log dropped below the metrics instead of sitting next to them.

## [0.3.38] — 2026-11-08

### Added
- **Live server log inside the dashboard card.** Next to status and metrics the last log lines scroll by
  (refresh every 2.5 s), so you can see what the server is doing without opening the detail page. On
  narrow cards the log moves below the metrics.
- The number of lines follows the card height; empty output shows as "no output".

## [0.3.37] — 2026-11-08

### Changed
- **The CPU tile now shows the server's share (0–100 %)** instead of the sum over all cores. 755 % on
  64 cores appears as "11.8 %"; the history graph ends at 100 % as well. The core breakdown ("7.6 of 64
  cores") moved to the tooltip, the raw value stays in the API as `cpu`.

## [0.3.36] — 2026-11-08

### Fixed
- **The CPU tooltip showed `undefined`/`NaN`** when the response carried no core count (older answer in
  the browser cache). The fallback is now the browser's core count, otherwise 1.

## [0.3.35] — 2026-11-08

### Fixed
- **Self-update did not restart the user service.** Without a login session (via `su`, `ssh` or from a
  script) `XDG_RUNTIME_DIR` and `DBUS_SESSION_BUS_ADDRESS` were missing, `systemctl --user` failed and
  the web interface kept running the old code. Both variables are set now, so the restart also works
  from a non-login session.

## [0.3.34] — 2026-11-08

### Fixed
- **Self-update could destroy the installation.** `apply()` deleted the live package directory and only
  then copied the new one in — if the copy aborted (or the target still existed), a half-written
  directory was left behind and `noah2games` would no longer start. The new package is now built completely
  next to the target and swapped in with `rename`; if the swap fails, the previous state is restored.
- **Backups accumulated without limit.** Every update created a `noah2games.bak-<timestamp>`. Now the last two
  are kept.

## [0.3.33] — 2026-11-08

### Fixed
- **The CPU graph clipped everything above 100 %.** The dashboard sparkline was pinned to 100 %, so an
  ARK server at 700 % load showed as a flat line at the top. It now scales to the observed maximum
  (at least 100 %).
- **The CPU figure needed an explanation.** It sums all threads (like `top`/`htop`) and can therefore
  exceed 100 %. The tile's tooltip now names cores and share of the server, e.g. "7.5 of 64 cores busy
  (11.8 % of the server)".

## [0.3.32] — 2026-11-08

### Fixed
- **`--user` left the files owned by root** when no web service was set up (`--no-web`), so the user could not
  write its own configs. Ownership is now fixed right after copying.

## [0.3.31] — 2026-11-08

### Fixed
- **`--user NAME` was not recognised** ("unknown option"): the argument loop could not read a second word with
  `shift`. It is a `while` loop now, so `--user noah2games` and `--user=noah2games` work (as does `--lang de`).

## [0.3.30] — 2026-11-08

### Fixed
- **Self-update could silently install the same state.** The archive was fetched via the `main` branch, which
  codeload serves from cache for minutes. It now downloads the archive **for the verified commit**
  (`/tar.gz/<sha>`), so what the check reports is what gets installed.

## [0.3.29] — 2026-11-08

### Added
- **`sudo ./install.sh --user noah2games`** — install under a dedicated service user. The installer creates the
  user and home, copies to `/home/noah2games/…`, fixes ownership, sets the UI up as a **user service** and enables
  `loginctl enable-linger` so it starts without a login. Nothing runs as root any more.

## [0.3.28] — 2026-11-08

### Fixed
- **The game server died when the UI restarted while noah2games runs as a normal user.** The dedicated systemd
  scope was only attempted on the system bus, which fails without root, so the start silently fell back to
  a plain child process. It now uses `systemd-run --user --scope` via the user manager (needs a one-time
  `loginctl enable-linger <user>`), so the server survives a UI restart.

## [0.3.27] — 2026-11-08

### Added
- **Port check before start.** If another program (e.g. an AMP server) holds the game, query or RCON port,
  noah2games stops with a clear message instead of starting a server nobody can reach — and instead of sending
  RCON requests to the wrong server.

## [0.3.26] — 2026-11-08

### Fixed
- **Launch line modelled on AMP.** Port, query port, RCON and password now live only in the map URL
  (`?listen?Port=…?QueryPort=…?RCONEnabled=True?RCONServerGameLogBuffer=600?RCONPort=…?ServerAdminPassword=…`),
  the password as the **last** option — otherwise ASA swallows the rest of the line. The separate
  `-port`/`-RCONPort` arguments are gone.
- `-SessionName` is no longer passed as an argument (spaces in the name split the line); the name comes from
  `[SessionSettings]` in the INI.

## [0.3.25] — 2026-11-08

### Fixed
- **RCON still said "wrong password" even with `RCONEnabled=True`.** ASA only takes the admin password from
  the command line; the map URL now carries `?ServerAdminPassword=…` (exactly like AMP). Note: as with any
  ARK server, the password is then visible in `ps`.

## [0.3.24] — 2026-11-08

### Fixed
- **RCON replied "wrong password" on freshly created instances.** noah2games passed only `-RCONPort` and relied on
  the INI to enable it; ASA only honours that with `?RCONEnabled=True` in the map URL (same as AMP). The URL
  now carries `?listen?Port=…?RCONEnabled=True?RCONServerGameLogBuffer=600?RCONPort=…`. The password stays in
  the INI, so it does not show up in the process list.

## [0.3.23] — 2026-11-08

### Changed
- Example cluster directory in the hint: `/home/Noah2Games/arkcluster` instead of `/home/user/arkcluster`.

## [0.3.22] — 2026-11-08

### Changed
- **Cluster fields show their defaults inside the input** — cluster ID is the instance name, directory is
  `<instance>/clusters`. You see the path and only overwrite it when maps should share. The hint also names
  an example (`/home/user/arkcluster`).

## [0.3.21] — 2026-11-08

### Added
- **Cluster settings.** `-clusterid=noah2games` and a per-instance directory used to be hardcoded, so maps could
  never share anything. The Settings tab now has a **Cluster** card: cluster ID, shared directory and the
  "transfers without filter check" option (`-NoTransferFromFiltering`). Without your own values the old
  behaviour stays.
- **53 more INI settings** from the full ARK set: transfer locks (download/upload of survivors, items,
  dinos), offline raid protection, tribe alliances, structure decay and pickup, dino decay, tamed dinos per
  player, imprinting, hit markers plus food/torpor and harvesting multipliers. The form is now grouped by
  file **and** section.

## [0.3.20] — 2026-11-08

### Fixed
- **"leer" in the whitelist list** was still hardcoded German; now translated via `i18n.py` (`empty`).

## [0.3.19] — 2026-11-08

### Fixed
- **Two more German strings in the English UI:** "kein Snapshot vorhanden" and the language-save error were
  hardcoded. Both now come from `i18n.py`.

## [0.3.18] — 2026-11-08

### Fixed
- **Mod status was hardcoded German** ("nicht heruntergeladen", "für alte Engine gebacken") and stayed
  German in the English UI. `mods.py` now returns codes and `i18n.py` supplies the text —
  `not downloaded` / `built for an older engine`.

## [0.3.17] — 2026-11-08

### Added
- **English description:** a button next to "Changelog" opens `README.en.md` on GitHub. The README now links
  between German and English at the top.

## [0.3.16] — 2026-11-08

### Fixed (important)
- **The UI was dead after page load:** the update progress code (0.3.13) contained a raw newline inside a
  JavaScript string — a syntax error that invalidated the whole script. Tabs stopped switching and mod
  buttons, settings and everything else stopped responding. Replaced with `String.fromCharCode(10)`;
  JavaScript is now checked with `node --check` before pushing.

## [0.3.15] — 2026-11-08

### Fixed
- **The game server no longer lives inside the web service.** It used to start as a child of `noah2games-web`;
  Wine processes stayed in that unit's cgroup on stop ("Unit process … remains running after unit
  stopped") and blocked every restart of the UI. Each instance now runs in its own transient unit
  (`noah2games-<name>.scope` via `systemd-run --scope`), so the server survives a UI restart and vice versa.
  Without systemd noah2games falls back to the previous start (`NOAH_NO_SCOPE=1` forces it).

## [0.3.14] — 2026-11-08

### Changed
- **The RAM note on the dashboard was misleading** ("about 11.5 GB per running server"). Usage depends on
  mods, world size and players: about 4 GB empty without mods, 11-12 GB with mods and a world, more above
  that. Adjusted in the UI and `INSTALL.md`.

## [0.3.13] — 2026-11-08

### Added
- **Update progress is visible.** SteamCMD output used to go to the service journal, so the server log
  showed nothing during an update. noah2games now writes it to `.update.log` and the UI streams it while the
  update runs (`/api/update/progress`, polled every 2 s).

## [0.3.12] — 2026-11-08

### Fixed
- **The changelog button showed the initial install.** Self-update replaced only the package directory, so
  the `CHANGELOG*.md` files next to it stayed stale. The update now carries both files along, and the UI
  re-fetches the text when its own version is missing.

## [0.3.11] — 2026-11-08

### Fixed
- **`noah2games url` printed `127.0.0.1` on a server.** With access mode "ip" it now shows the address the UI is
  actually reachable at.

## [0.3.10] — 2026-11-08

### Fixed
- **Self-update failed silently.** A single `504 Gateway Timeout` while downloading the archive aborted the
  run and the UI reported nothing, so the button looked dead. Now: three attempts with backoff and a
  second source (`codeload.github.com`), plus the UI shows "Update failed: …" instead of silence.
- The update runs synchronously; the service restart happens a second later so the response still arrives.

## [0.3.9] — 2026-11-08

### Added
- **The build badge is a button.** On the instance page it only read `UP TO DATE 26515168`; the update
  could only be started from the overview. Now `UPDATE a→b` starts the update on click (confirmation,
  backup, stop), `UP TO DATE b` re-checks. Tooltips explain both, keyboard (Enter/Space) works too.

## [0.3.8] — 2026-11-08

### Security
- **Constant-time token comparison** (`hmac.compare_digest`) instead of `==`.
- **Security headers** on every response: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer` (keeps the token out of the Referer header) and a restrictive CSP.
- **Mod IDs are validated** (digits only, max 10) — previously the value went unfiltered into the server
  command line (`-mods=…`).
- **Player IDs** (whitelist/bans) only as Steam64 or hex UniqueNetId; newlines and special characters are
  rejected instead of being written to the file.

## [0.3.7] — 2026-11-08

### Changed
- **Mod search works without an instance.** `/api/mods/search`, `/api/mods/suggest` and saving the API key
  sat behind the instance check and answered "keine Instanz" when no instance existed.
- The Mods tab shows which mode is active: `CurseForge API active · searches titles and descriptions,
  sorted by downloads` (green, with a masked key) or `No API key · only exact mod ID or CurseForge link`.

## [0.3.6] — 2026-11-08

### Changed
- The version button shows the state in its label: `up to date` or `new build`, not only in the tooltip.

## [0.3.5] — 2026-11-08

### Changed
- When noah2games reports "same version, new build only", the button is no longer clickable — there is
  nothing to fetch. Changes that should reach users get a version bump.

## [0.3.4] — 2026-11-08

### Changed
- Copyright uses the handle `ronny79privat` only (no real name).

## [0.3.3] — 2026-11-08

### Changed
- Copyright notice in README and `LICENSE` (ronny79privat).
- Developer notes moved out of the technical docs into `docs/entwicklung.md` — irrelevant for users,
  still reachable for contributors.

## [0.3.2] — 2026-11-08

### Changed
- README trimmed to the essentials (111 instead of 420 lines). Features, access, operation and
  internals moved to `docs/funktionen.md`, `docs/zugriff.md`, `docs/betrieb.md` and `docs/technik.md`.

## [0.3.1] — 2026-11-08

### Changed
- README reordered: installation and removal first, then remote access and the token; feature list
  and screenshots follow further down.

## [0.3.0] — 2026-11-08

### Added
- **Changelog button** in the header: opens the changes as a popup in the configured language
  (German/English). Content is read from the local installation, no network needed.
- English version: `CHANGELOG.en.md`.

### Changed
- The update dialog shows the changes of the new version directly.
- Notifications: routine messages stay in the log, only events go to Discord.

## [0.2.9] — 2026-11-08

### Added
- **CHANGELOG.md** — what changed in each version.
- The update dialog shows the changes of the new version before you confirm.
- **`scripts/release.sh`**: set version, commit, tag, push (with `--release` also the GitHub
  release, if `gh` is installed).

## [0.2.8] — 2026-11-08

### Fixed
- Mod search with an API key returned **zero results**: the `classId` parameter restricted the
  CurseForge query to a category that holds no ARK ASA mods. Without it the expected results come back.
- Empty search results are no longer cached for an hour.

## [0.2.7] — 2026-11-08

### Changed
- Update check is **cached for 10 minutes** — GitHub allows only 60 requests per hour without a token.
  `noah2games version` and `noah2games self-update` still check fresh.

## [0.2.6] — 2026-11-08

### Added
- **"← Dashboard"** in the header of the instance page.

### Changed
- The instance update badge only appears on a reliable check (it used to say "UPDATE ?" forever
  while the server files were missing).
- `install.sh` restarts a running `noah2games-web` service after copying, so the new code is active
  immediately.

## [0.2.5] — 2026-11-08

### Changed
- Update button in badge style instead of a solid block.

## [0.2.4] — 2026-11-08

### Changed
- Update button is labelled: `noah2games update: 0.2.3 → 0.2.4` instead of bare version numbers.

## [0.2.3] — 2026-11-08

### Fixed
- Self-update fetched the source archive from `codeload.github.com`, which still serves the old
  state after a push. Now it uses the GitHub API.

## [0.2.2] — 2026-11-08

### Fixed
- Version check read `raw.githubusercontent.com` (up to 5 minutes stale) — now via the GitHub API.

## [0.2.1] — 2026-11-08

### Fixed
- `/api/selfupdate` was only reachable when an instance existed.

## [0.2.0] — 2026-11-08

### Added
- **Self-update**: button in the header (`noah2games update: old → new`) and `noah2games self-update`.
- **Mod search**: mod ID, CurseForge link or name; suggestions appear while typing with image,
  downloads and one click to add. Names require a CurseForge API key.
- **Mod updates at a glance**: installed file vs. newest file on CurseForge, marked "UPDATE".
- **Discord notifications**: crash, hang, update available, backup failure, scheduled restart —
  routine messages stay in the log.
- **Hang and crash detection** in the supervisor; a manual stop is respected.
- **`noah2games proxy`**: sets up nginx with HTTPS (certificate via certbot, optional basic auth),
  verifies with `nginx -t` and rolls back on errors.
- **HTTPS directly** in the web server (`--tls-cert` / `--tls-key`).
- **Delete instance** on the dashboard card (config to `.trash`, files only on request).
- **Update button** and **delete** directly on the card.
- **MOTD** as a multi-line form field.
- **Bilingual** (German/English): language question in the installer, button in the UI,
  `noah2games lang`.
- **Three access modes** in the installer: client-side via SSH tunnel, public via domain+HTTPS,
  direct via IP and port.
- The **supervisor service** is created automatically after installing an instance (a system
  service as root, starting at boot).

### Changed
- Instance page: server log at the top across the full width and resizable (48 % height, 150 lines);
  control buttons live on the dashboard card.
- The log jumps to the end when opened; the active tab survives a reload.
- Map background clearly visible (opacity 0.28 → 0.62).
- Settings: multi-line fields (textarea) supported.
- `settings.json` is written with `0600` because it holds the API key.

## [0.1.0] — 2026-11-07

First public release: create instances, start/stop/restart/update via SteamCMD, RCON console with
click commands, player management, mod management, config editor, world backups, snapshots,
whitelist/bans, schedule, live metrics and a web interface.
