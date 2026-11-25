## [0.71] - 2026-11-25

- New switch under Mods: start the server without AsaApi when the loader does not match after an
  ARK update. The server stays reachable; quests, starter kit and kill counting are missing in game.
  Switch it back once the loader works again.

## [0.70] - 2026-11-25

- Every delete now asks first: file, mod, mod files, snapshot, backup and whitelist entry. The texts
  exist in both languages; they used to be hard-coded German.

## [0.69] - 2026-11-24

- File editor: long lines are no longer wrapped but scroll sideways.

## [0.68] - 2026-11-24

- Footer on the dashboard too. Version, licence link, PayPal and Discord only appeared on the
  instance page, the template did not know the placeholder.

## [0.67] - 2026-11-24

- Tests instead of "works on my machine". 27 checks using the standard library (`tests/`): ini
  handling (duplicate keys, comments, CRLF, idempotence), mod order and pinning, update decision
  (never offer a downgrade), route-table completeness, and a smoke test that starts the web server
  in a temporary directory and exercises login, core routes and instance management.
- **GitHub Actions** (`.github/workflows/ci.yml`): on every push and pull request, Python 3.10, 3.12
  and 3.13 - style check, text check, tests.
- **`ruff` clean** with configuration in `pyproject.toml`; real bugs it found are fixed: duplicated
  translation keys (the second entry silently overrode the first), unused assignments, missing
  `raise … from`, ambiguous variable names.
- The POST handler is split up. Instead of one 559-line chain there are now 22 methods per topic
  (mods, files, backups, schedule …) and a `_POST_ROUTES` table. Behaviour unchanged: 31 requests
  were compared against the previous version, no difference.
- `CONTRIBUTING.md` covers the test run, change rules and bug reports.

## [0.66] - 2026-11-24

- Free licence: MIT. The project was "all rights reserved" until now. From here on anyone may
  use, modify, redistribute and also sell it - the only condition is that the copyright notice and
  the warranty disclaimer stay. `LICENSE` holds the full text, README and docs are updated, the
  footer shows "MIT licence".

## [0.65] - 2026-11-24

- The mobile rules were missing on the instance page. The instance template had its own
  `<style>` element without the mobile block, so the file list stayed wide and the boxes small
  there. The rules are now appended there too.

## [0.64] - 2026-11-24

- File list on phones without sideways scrolling. Each row is a small block now: filename top
  left, size top right, date bottom left, the four action boxes bottom right. Instead of panning a
  520 px table, everything fits the screen width.

## [0.63] - 2026-11-24

- Action boxes are 36 × 36 px on phones. The mobile enlargement got lost while tidying up; the
  fields are large enough for a thumb again.

## [0.62] - 2026-11-24

- Stray brace in the stylesheet. Reworking the mobile rules left an extra `}` in the base
  styles; the file list lost its `overflow-x` and pushed the page to 543 px. The rule now sits in
  the mobile block and the page stays at 375 px.

## [0.61] - 2026-11-24

- The file list pushed the page wider. The 520 px minimum table width forced the whole page to
  556 px on a 390 px screen, so you had to pan sideways. Sections and cards may shrink now
  (`min-width:0`); the table scrolls inside its own box only.

## [0.60] - 2026-11-24

- Readable server log on phones. Font raised to 12 px with more line height and a taller log
  box (58 vh) so you don't have to zoom. The status badges in the header are slightly larger and
  easier to hit.

## [0.59] - 2026-11-24

- The header is a single row on phones. CPU, RAM, version, changelog, panel restart and the
  language switch sit side by side and scroll horizontally instead of stacking into four rows.
  That shrinks the header from 227 to roughly 90 pixels.

## [0.58] - 2026-11-24

- The mobile rules did not apply. The mobile block sat in the middle of the stylesheet and was
  overridden by later base rules - inputs stayed at 14 px (which makes iOS zoom in on tap) and the
  header stayed 248 px tall. The rules are now a separate block at the end of the stylesheet and
  apply reliably.

## [0.57] - 2026-11-24

- Mobile layout tidied up. Below 720 px: single column, cards and sections full width, stats in
  a 2×2 grid instead of four across, settings with the label above the field, tabs scroll
  horizontally, buttons at least 40 px tall and inputs at 16 px (so iOS does not zoom in). The
  header wraps instead of running over the edge.

## [0.56] - 2026-11-24

- The action icons in the file list are boxes now. Instead of bare little glyphs each action
  sits in its own field (30×30 px, 34×34 on phones): download outlined in green, delete in red.
  That makes them easy to hit with a finger.
- The file list scrolls horizontally on narrow screens instead of squeezing columns.

## [0.55] - 2026-11-24

- The full view sat in the wrong section. The overlay lived inside the overview tab (hidden on
  open) instead of outside the tabs, so it stayed invisible although the content loaded. It now
  sits right after `<main>` and covers the page regardless of the active tab.

## [0.54] - 2026-11-24

- Download files. Each file in the list gets its own download arrow (⬇) - a real link, so the
  browser saves it straight away instead of routing it through the editor. Name and extension are
  preserved (`Content-Disposition`).
- Direct full view. The ⤢ icon opens the file full-screen: a large editor with save, download
  and close. `Esc` closes it again. The small preview box below stays for a quick look.

- Action column in the file list. Download, full view, rename and delete now sit as their own
  icons at the right of each row instead of between filename and size.

## [0.53] - 2026-11-24

- The update badge offered a downgrade. When the local build was already newer than GitHub
  (own deploy before the push), the panel reported “update 0.52 → 0.51” - a downgrade as an
  update. Only a **higher** GitHub version counts as an update now; if the local build is ahead,
  the badge stays on “up to date”.
- A stale cache pinned the old reading. The 10-minute cache was served even when the “newer”
  version it recorded was older than the installed one. Such entries are dropped and re-checked.
- The build file is no longer shipped. `.build` was tracked in the repo and overwritten with a
  stale version  on every deploy, so the panel kept reporting “new build available” even
  though version and commit already matched. The file is now only written on update or deploy.

## [0.52] - 2026-11-24

- Action bar on the instance cards. Instead of six grey text buttons each card now carries a
  coloured pill with three groups - like a file manager: **red** stop and delete, **blue** menu,
  update, AsaApi, **green** start and restart. The icons keep the text as a tooltip, disabled
  actions stay visible (faded) instead of disappearing, and a small dot on the AsaApi icon marks a
  pending update.

## [0.51] - 2026-11-24

- Sort and pin mods. In the mods tab, active mods can be reordered with ▲/▼ or by drag & drop;
  a pin (📍) keeps a mod at the top for good (📌) - stacking mods, for instance, which have to load
  early. The order is the **load order**: it goes into `-mods=` on the command line and into
  `ActiveMods` in Game.ini. A pure reorder rewrites that single line only - the rest of Game.ini
  stays untouched byte for byte.

- Game.ini is no longer rewritten. `ark_write_ini()` used to regenerate the file through
  `configparser`, which keeps only one value per key and section and drops duplicates. In a real
  ARK file this removed 795 `EngramEntryAutoUnlocks`, 156 `ConfigOverrideItemMaxQuantity` and 99
  `OverridePlayerLevelEngramPoints` entries (1,182 lines and 121 KB became 128 lines and 18 KB), and
  values were normalised (`true` → `True`, `DifficultyOffset=4` → `1.0`). Now only individual lines
  are touched; everything else is preserved.
- The server password survives. `ark_write_ini()` forced `ServerPassword` to empty on every
  start, so a configured join password was gone after the next restart.
- Admin values in GameUserSettings.ini survive. `ServerPVE`, `DifficultyOffset`,
  `ServerCrosshair` and `ShowMapPlayerLocation` are only written when the key is missing.
- INI backups go into the `backup/` subfolder next to the INIs instead of a `.bak` file beside
  them (last 20 versions per file). The server folder no longer collects backup files.
- Line endings are preserved. Saved INIs were written with LF instead of CRLF, shrinking them by
  one byte per line.
- “Before update” backups are labelled as such instead of showing up as “older”.
## [0.50] - 2026-11-21

- Satisfactory: player section was hidden in the panel. An old CSS rule
  (`body[data-game="satisfactory"] #secPlayers{display:none}`) hid the player list entirely - the
  data arrived but was never visible. The rule is gone.
- Player list: no more dead buttons. For players without an ID (Satisfactory reports names
  only) the kick/ban/whitelist/item buttons were rendered with an empty value; they now appear
  only when an ID exists.

## [0.49] - 2026-11-21

- Satisfactory: player names now come from the server log. Since game version 1.2,
  `QueryServerState` no longer returns `playerStates` - the API only reports
  `numConnectedPlayers`. The panel therefore reads names from the running server's log
  (`LogNet: Join succeeded: <Name>`, on leaving `UNetConnection::Close ... Name: <Name>`) and
  starts at the boot marker of the latest run so old sessions are not counted. Older server
  versions exposing `playerStates` still use the API directly.

## [0.48] - 2026-11-21

- Satisfactory: player list stayed empty even with an API token. The panel always asked for
  players via `ListPlayers`, a command Satisfactory does not have (the call ended in the API's
  `insufficient_scope` error and the list stayed empty). The game-specific path now takes
  precedence: Satisfactory reads players from `QueryServerState`, every other game still uses
  RCON/Telnet.

## [0.47] - 2026-11-21

- Satisfactory: API token can be entered in the panel. Without a token the server answers
  `QueryServerState` and `RunCommand` with `insufficient_scope`, which left the player list empty
  and commands without effect. The field did not exist. Create the token in game (Server Manager
  -> Console -> `server.GenerateAPIToken`) and paste it into "API-Token"; it is stored in the
  instance.

## [0.46] - 2026-11-21

- Satisfactory: the server password can now really be changed and removed. The profile only
  wrote `ServerPassword` when a value was set - clearing it left the old value in
  `GameUserSettings.ini` and the server kept asking for it. The entry is now always written
  (empty = no password).
- Settings: cleared fields are submitted. The form only sent non-empty values, so a password
  could never be removed (message "no changes"). Empty values are now sent when the field had a
  value before; untouched empty fields are still skipped.
- Settings: password fields render as password inputs (previously a plain text field showing
  the password).

## [0.45] - 2026-11-21

- Panel UI: syntax error from 0.44 fixed. The file caption for the new live rules added an
  extra parenthesis to the panel JavaScript; the panel rendered empty because no function was
  defined. Now chained correctly and checked with `node --check`.
- Panel source: no more Python syntax warnings. Two JavaScript regexes (`\/` and `\d`)
  sat in plain strings; they are masked correctly now, the emitted code is unchanged.

## [0.44] - 2026-11-21

- 7 Days to Die: blood moon and game rules in the panel. Since game version 2.0, blood moon,
  difficulty, loot, XP, zombie speed and similar rules are no longer individual properties in
  `serverconfig.xml` - FFP packed them into `SandboxCode`. The panel therefore shows two extra
  groups, "Blood Moon" (frequency, enemy count, range, warning) and "Game rules (live)"
  (difficulty, XP, loot, airdrop, day/night length, death penalty, zombie speed, block damage,
  quest limit). Values are pushed to the running server with `setgamepref`; current values are read
  with a single `getgamepref` (cached for 15 seconds).

- 7 Days to Die: live rules survive a restart. The panel stores the values in the instance and
  re-applies them after every server start - once per server PID, so frequent status polls do not
  trigger a second run.

## [0.43] - 2026-11-21

- Files: upload progress bar. A bar above the file list tracks the percentage; the status line
  also names the file, index and percent ("uploading 12/53 (42%): Mods/…/ModInfo.xml"). Uploads now
  use XMLHttpRequest, since only that exposes real transfer progress (`fetch` cannot). The
  percentage covers the total size of the whole batch; on success the bar disappears after 2.5
  seconds, on errors it stays next to the error line.

## [0.42] - 2026-11-21

- Files: upload whole folders. New "Upload folder" button plus drag & drop onto the file list:
  folders including all subfolders are transferred recursively and keep their structure
  (`Mods/<Mod>/Config/...`). Previously only single files could be dropped into the open folder and
  subfolders had to be created by hand. Progress ("uploading 12/53") and errors show up in the Files
  tab; uploads run one by one, so the 2 GB per-file limit still applies.

## [0.41] - 2026-11-21

- The SFTP port died a few seconds after start. The service closed and rebuilt every listener
  every 30 seconds; asyncssh's `wait_closed()` can hang when no connection ever existed. After that
  the port (2225 by default) stayed closed while the unit kept running, so clients got
  "Connection refused". The service now binds once and keeps the listeners; it only rebinds when
  port, user, password or chroot of an instance change (checked every 10 seconds).

## [0.40] - 2026-11-21

- 7 Days to Die: the join password is a field of its own now. `ServerPassword` was tied to
  `rcon_password` (`ALIASES`, `write_config`, core field), so saving the server password overwrote
  the RCON password and vice versa. The panel kept showing the randomly generated hex value, and a
  password that was entered was gone after the next start. It now uses `inst.server_password` (as
  Empyrion/StarRupture do) and leaves `rcon_password` untouched.

## [0.24] - 2026-11-16

- Empyrion: all config files in the "Settings" tab (80 fields): `dedicated.yaml` in full
  (ServerConfig + GameConfig, incl. reserve playfields, LogFlags, KickPlayerWithPing,
  PlayerLoginParallelCount, EnableDLC, Seed, Notes), the multiplayer block of the scenario's
  `gameoptions.yaml` (49 gameplay rules) and the admin list from `adminconfig.yaml`
  (SteamID64:level). The singleplayer block is never touched.

## [0.23] - 2026-11-15

- Empyrion: every setting in the panel. The "Settings" tab now exposes the keys from
  `dedicated.yaml` (ServerConfig and GameConfig): name, port, players, password, description,
  visibility, reserve playfields, auto restart, EAC, size class, blueprints, heartbeat, start
  timeout, telnet (on/port/password), save name, mode, scenario and save directory. Values are
  edited in place - indentation, order and comments of the template are preserved, commented-out
  passwords are not shown as set.

## [0.22] - 2026-11-15

- Empyrion now actually starts. Three profile fixes: the start file is
  `DedicatedServer/EmpyrionDedicated.exe` (the root only holds batch files and the launcher),
  Unity needs `-nographics` **together with** `-batchmode`, and `dedicated.yaml` is only edited
  inside the `ServerConfig:` block - top-level keys are rejected with "config file is updated to
  the current server version".

## [0.21] - 2026-11-15

- Empyrion: Galactic Survival game profile. Dedicated server via SteamCMD
  (app 530870, Windows binary under Wine). Configuration in `dedicated.yaml`
  (`Srv_Name`, `Srv_Port`, `Srv_MaxPlayers`, `Srv_Password`) - comments and key order of the
  template are preserved, unknown keys stay untouched. Started without graphics via
  `EmpyrionDedicated_NoGraphics.exe`, game port UDP 30000. No RCON, no mods tab.

## [0.20] - 2026-11-15

- The card shows what is happening. Previously an update in progress showed only
  "STOPPED". Now a hint line appears (⏳ UPDATING, INSTALLING, RESTARTING, STOPPING,
  DELETING, SETTING UP ASAPI), sourced from the panel's running actions.

## [0.19] - 2026-11-15

- StarRupture without a mods tab. The game has no mods; the "Mods" tab is hidden for this game
  type instead of offering an empty search.
- StarRupture installation failed with "Invalid platform". The
  `+@sSteamCmdForcePlatformType windows` switch was only set for ARK; StarRupture also ships a
  Windows-only server. The list of Windows-only games now lives in `installer.py`
  (`WINDOWS_ONLY_APPS`).

## [0.18] - 2026-11-15

- StarRupture game profile. Dedicated server via SteamCMD (app ID 3809400, Windows binary under
  Wine). Instances are created like any other: name, port (UDP 7777), player count. The start file is
  located automatically (`StarRuptureServerEOS.exe`, `StarRuptureServer.exe` or a path under
  `Binaries/Win64`), configuration is written to `DSSettings.txt` next to it (ServerName, Port,
  MaxPlayers, password if set). There is no control channel - start, stop, update, backups and the
  file browser work, RCON/console and player list do not; "ready" is detected by the bound UDP port.

## [0.17] - 2026-11-14

- No extra window when creating or installing. The panel used to open a separate window with the
  setup page for the new instance. Creating now stays on the overview (the new card appears there),
  and the installation shows its progress in the same tab.

## [0.16] - 2026-11-14

- AsaApi is part of the installation for ARK instances. After the SteamCMD run the panel sets up
  AsaApi automatically (the complete release including `config.json` and the bundled DLLs) and starts
  the instance through `AsaApiLoader.exe` from then on. The **"API"** button on the instance card
  installs or updates the API by hand at any time; it only appears when there is something to do and
  shows a version badge for a newer release. A checkbox in the "Mods" tab turns the API and its
  plugins off again. Other games are unaffected - neither the button nor the checkbox appears there.
- Firewall comes along. On start the panel adds the instance's game port (UDP) to `ufw`, and
  removes those rules when the instance is deleted. Without them the server runs but cannot be
  reached from outside. For `ufw` the installer creates a tightly scoped `sudo` rule (only
  `/usr/sbin/ufw`); if it is missing, the server still starts and the panel log names the reason.
- **Paste mod IDs directly** (ARK). The "Mods" tab has a field for mod IDs (comma, semicolon or space
  as separator). It shows the active list and replaces it on save.

- Metrics count every process of the instance. Previously only the starter PID and its direct
  children were measured; under Wine/Proton and with the API loader the actual server process is not
  attached to them, so CPU and RAM showed up as 0. All processes of the instance are now found via
  their command line and summed up.
- SessionName and MaxPlayers survive (ARK): values changed in `GameUserSettings.ini` are carried
  back into the instance instead of being overwritten on the next start.
- The section in `Game.ini` is recognised regardless of its capitalisation, so no second `ActiveMods`
  line is created.

- Starting through `AsaApiLoader.exe` aborted with "LoaderFailed, Reason: UnknownLoaderResult" when
  the API release's `config.json` was missing in the Win64 directory.
- A duplicate `ActiveMods` line could make the server silently ignore configured mods on start.

## [0.15] - 2026-11-14

- File browser inside the panel. The "Files" tab of an instance shows its directory in the
  browser: open folders, upload files (several at once), download, rename, delete and create new
  folders. Everything stays inside the instance directory - paths with `..` are rejected and
  downloads are streamed. Read and edit files: clicking a name opens the content in the browser
  (text up to 2 MB, binary files rejected), "Save" writes it back and keeps a `.bak` copy first.
- Per-instance SFTP access. Each instance card can switch SFTP on and off; access is confined to
  the instance directory (chroot), user and password are generated per instance, and the port comes
  from `sftp_base_port + running number` (default 2225). "New password" immediately creates one and
  copies it to the clipboard.
- The SFTP service runs as its own systemd unit `polypanel-sftp` (user or system service, following
  how the panel itself is installed) and re-reads ports/passwords every 30 seconds. It is independent
  of the instance runtime state: uploading works while the server is stopped.

- Token stays the same. The web token is generated on the very first start only and is read from
  `~/.config/polypanel/token` afterwards - restarts, updates and self-updates do not change it, so old
  links keep working. A new token is only created when that file is deleted.
- The instance JSON gained `sftp_enabled`, `sftp_user`, `sftp_password`, `sftp_port`; the address
  `sftp://user@host:port` is shown on the card and works with FileZilla (SFTP, not FTP).

### Requirement
- `asyncssh` (e.g. `apt install python3-asyncssh`). Without it the panel keeps working unchanged and
  only the SFTP service reports the missing module in the panel log.

## [0.14] - 2026-11-13

- Map and RCON now appear on every instance card. The card line only showed the map name for ASA
  instances - ARK: Survival Evolved, Satisfactory, 7D2D and Space Engineers dropped map and RCON port.
  Now for all: `<map> · <game> · Port <n> · RCON <n>`, empty parts are left out.

## [0.13] - 2026-11-13

### New
- Download speed in the install window. Alongside step and percentage the current rate in MB/s is
  shown - computed from the byte counters in the steamcmd lines and smoothed so the number does not
  jump around.

## [0.12] - 2026-11-13

- Instances no longer start by themselves after installation. The supervisor was enabled right
  after the install; as a freshly installed server never ran, it read "process gone" as a crash and
  started it immediately. The instance is now marked as "stopped" (`runner.mark_stopped`) before the
  service starts - starting only happens via "Start" in the panel. The marker is cleared on start, so
  crash detection works as before, and an instance that was never started also stays off after a
  system boot.

## [0.11] - 2026-11-13

### Overview
Rough summary of what the panels contain.

- Two panels, one base: AscendedPanel for ARK: Survival Ascended, PolyPanel for ASA, ASE,
  Satisfactory, 7 Days to Die and Space Engineers. Browser UI, service on the server.
- **Dashboard:** instance cards with status, map, ports, build, CPU/RAM, players and uptime; start,
  restart, update, stop and delete right on the card, buttons locked by state (while stopping only
  the menu stays available, and so on).
- Instance page: live log, config editor with backup and validation (INI values as a form or
  raw), mod management with CurseForge search and update check, backups, snapshots, schedule and an
  RCON console with one-click commands.
- **Players:** list with kick, ban, whitelist and giving items - catalogue with search and a
  quantity window; the required player id (ARKID) is read from the `.arkprofile` files because ARK
  only exposes the EOS id over RCON.
- **Bans:** its own "banned players" window with per-row unban and an honest note on why ARK does
  not hand out its ban list over RCON.
- **Operation:** crash detection with automatic restart, Discord notifications, German/English
  switchable at any time, several instances in one process.
- Bug reports: button in the panel, report goes to the operator (webhook, console-only) with
  version, instance, system and log excerpt, passwords stripped.

- Space Engineers no longer starts in Experimental mode. At startup SE checks CPU cores, clock
  and RAM (`ProcessorCount >= 3`, `CPUFrequency >= 3.2 GHz`, at least 6 GB RAM) and otherwise forces
  Experimental - players are rejected until they enable Experimental in their game options. SE reads
  the clock via WMI, which Wine feeds from `/proc/cpuinfo`, and VMs report e.g. 2095 MHz there.
  PolyPanel now builds a small LD_PRELOAD shim at start time
  (`~/.local/share/polypanel/se-cpufix/fakecpu.so`) that reports 3.6 GHz to Wine; the server log then
  shows `Experimental mode: No`. Requires a C compiler (`build-essential`/`gcc`) - if it is missing,
  nothing changes and the start log says so.
- Experimental-mode popup removed. Now that the server passes the hardware check, the "server is
  running in experimental mode" window (and the warning bar in the settings tab) only got in the way -
  it covered the whole page and swallowed clicks. Both are gone, together with `/api/experimental` and
  the related language keys; the `ExperimentalMode` field still shows "effective: on/off" from the
  server log in case SE flips it by itself.
- "Install" shows the progress again. If the remembered tab was "Settings", it covered the install
  panel - the click looked like it landed in the settings while the install ran correctly in the
  background. During a running install the instance page now switches to "Overview" by itself, with
  progress bar and log.
- A fresh install now really starts without Experimental. The template shipped
  `PhysicsIterations 1` and `BlockLimitsEnabled NONE`, and new instances added `MaxPlayers 20` - three
  deviations from the vanilla set, which is exactly why SE forces Experimental on its own
  (`Experimental mode reason: MaxPlayers, PhysicsIterations, BlockLimitsEnabled`). Template and
  instance default are now vanilla: physics 8, block limits GLOBALLY, 16 players; that more than 16
  players forces Experimental is stated as a hint on the field.
- Deleting no longer blocks the UI. Stopping (SE saves for up to 90 s) and removing several GB now
  run as a background job; the card shows "stopping the server …", then "deleting server files …" and
  finally the freed size. Every delete is also logged with timestamp and freed MB in `panel.log`.
- Wine is installed without asking: like Xvfb and `gcc`. The "install Wine?" question was answered
  with "no" in practice, and afterwards no Windows game started.
