## [0.43] — 2026-11-21

### Added

- **Files: upload progress bar.** A bar above the file list tracks the percentage; the status line
  also names the file, index and percent ("uploading 12/53 (42%): Mods/…/ModInfo.xml"). Uploads now
  use XMLHttpRequest, since only that exposes real transfer progress (`fetch` cannot). The
  percentage covers the total size of the whole batch; on success the bar disappears after 2.5
  seconds, on errors it stays next to the error line.

## [0.42] — 2026-11-21

### Added

- **Files: upload whole folders.** New "Upload folder" button plus drag & drop onto the file list:
  folders including all subfolders are transferred recursively and keep their structure
  (`Mods/<Mod>/Config/...`). Previously only single files could be dropped into the open folder and
  subfolders had to be created by hand. Progress ("uploading 12/53") and errors show up in the Files
  tab; uploads run one by one, so the 2 GB per-file limit still applies.

## [0.41] — 2026-11-21

### Fixed

- **The SFTP port died a few seconds after start.** The service closed and rebuilt every listener
  every 30 seconds; asyncssh's `wait_closed()` can hang when no connection ever existed. After that
  the port (2225 by default) stayed closed while the unit kept running, so clients got
  "Connection refused". The service now binds once and keeps the listeners; it only rebinds when
  port, user, password or chroot of an instance change (checked every 10 seconds).

## [0.40] — 2026-11-21

### Fixed

- **7 Days to Die: the join password is a field of its own now.** `ServerPassword` was tied to
  `rcon_password` (`ALIASES`, `write_config`, core field), so saving the server password overwrote
  the RCON password and vice versa. The panel kept showing the randomly generated hex value, and a
  password that was entered was gone after the next start. It now uses `inst.server_password` (as
  Empyrion/StarRupture do) and leaves `rcon_password` untouched.

## [0.24] — 2026-11-16

### Added
- **Empyrion: all config files in the "Settings" tab** (80 fields): `dedicated.yaml` in full
  (ServerConfig + GameConfig, incl. reserve playfields, LogFlags, KickPlayerWithPing,
  PlayerLoginParallelCount, EnableDLC, Seed, Notes), the multiplayer block of the scenario's
  `gameoptions.yaml` (49 gameplay rules) and the admin list from `adminconfig.yaml`
  (SteamID64:level). The singleplayer block is never touched.

## [0.23] — 2026-11-15

### Added
- **Empyrion: every setting in the panel.** The "Settings" tab now exposes the keys from
  `dedicated.yaml` (ServerConfig and GameConfig): name, port, players, password, description,
  visibility, reserve playfields, auto restart, EAC, size class, blueprints, heartbeat, start
  timeout, telnet (on/port/password), save name, mode, scenario and save directory. Values are
  edited in place — indentation, order and comments of the template are preserved, commented-out
  passwords are not shown as set.

## [0.22] — 2026-11-15

### Fixed
- **Empyrion now actually starts.** Three profile fixes: the start file is
  `DedicatedServer/EmpyrionDedicated.exe` (the root only holds batch files and the launcher),
  Unity needs `-nographics` **together with** `-batchmode`, and `dedicated.yaml` is only edited
  inside the `ServerConfig:` block — top-level keys are rejected with "config file is updated to
  the current server version".

## [0.21] — 2026-11-15

### Added
- **Empyrion: Galactic Survival game profile.** Dedicated server via SteamCMD
  (app 530870, Windows binary under Wine). Configuration in `dedicated.yaml`
  (`Srv_Name`, `Srv_Port`, `Srv_MaxPlayers`, `Srv_Password`) — comments and key order of the
  template are preserved, unknown keys stay untouched. Started without graphics via
  `EmpyrionDedicated_NoGraphics.exe`, game port UDP 30000. No RCON, no mods tab.

## [0.20] — 2026-11-15

### Added
- **The card shows what is happening.** Previously an update in progress showed only
  "STOPPED". Now a hint line appears (⏳ UPDATING, INSTALLING, RESTARTING, STOPPING,
  DELETING, SETTING UP ASAPI), sourced from the panel's running actions.

## [0.19] — 2026-11-15

### Fixed
- **StarRupture without a mods tab.** The game has no mods; the "Mods" tab is hidden for this game
  type instead of offering an empty search.
- **StarRupture installation failed with "Invalid platform".** The
  `+@sSteamCmdForcePlatformType windows` switch was only set for ARK; StarRupture also ships a
  Windows-only server. The list of Windows-only games now lives in `installer.py`
  (`WINDOWS_ONLY_APPS`).

## [0.18] — 2026-11-15

### Added
- **StarRupture game profile.** Dedicated server via SteamCMD (app ID 3809400, Windows binary under
  Wine). Instances are created like any other: name, port (UDP 7777), player count. The start file is
  located automatically (`StarRuptureServerEOS.exe`, `StarRuptureServer.exe` or a path under
  `Binaries/Win64`), configuration is written to `DSSettings.txt` next to it (ServerName, Port,
  MaxPlayers, password if set). There is no control channel — start, stop, update, backups and the
  file browser work, RCON/console and player list do not; "ready" is detected by the bound UDP port.

## [0.17] — 2026-11-14

### Changed
- **No extra window when creating or installing.** The panel used to open a separate window with the
  setup page for the new instance. Creating now stays on the overview (the new card appears there),
  and the installation shows its progress in the same tab.

## [0.16] — 2026-11-14

### Added
- **AsaApi is part of the installation for ARK instances.** After the SteamCMD run the panel sets up
  AsaApi automatically (the complete release including `config.json` and the bundled DLLs) and starts
  the instance through `AsaApiLoader.exe` from then on. The **"API"** button on the instance card
  installs or updates the API by hand at any time; it only appears when there is something to do and
  shows a version badge for a newer release. A checkbox in the "Mods" tab turns the API and its
  plugins off again. Other games are unaffected — neither the button nor the checkbox appears there.
- **Firewall comes along.** On start the panel adds the instance's game port (UDP) to `ufw`, and
  removes those rules when the instance is deleted. Without them the server runs but cannot be
  reached from outside. For `ufw` the installer creates a tightly scoped `sudo` rule (only
  `/usr/sbin/ufw`); if it is missing, the server still starts and the panel log names the reason.
- **Paste mod IDs directly** (ARK). The "Mods" tab has a field for mod IDs (comma, semicolon or space
  as separator). It shows the active list and replaces it on save.

### Changed
- **Metrics count every process of the instance.** Previously only the starter PID and its direct
  children were measured; under Wine/Proton and with the API loader the actual server process is not
  attached to them, so CPU and RAM showed up as 0. All processes of the instance are now found via
  their command line and summed up.
- **SessionName and MaxPlayers survive** (ARK): values changed in `GameUserSettings.ini` are carried
  back into the instance instead of being overwritten on the next start.
- The section in `Game.ini` is recognised regardless of its capitalisation, so no second `ActiveMods`
  line is created.

### Fixed
- Starting through `AsaApiLoader.exe` aborted with "LoaderFailed, Reason: UnknownLoaderResult" when
  the API release's `config.json` was missing in the Win64 directory.
- A duplicate `ActiveMods` line could make the server silently ignore configured mods on start.

## [0.15] — 2026-11-14

### Added
- **File browser inside the panel.** The "Files" tab of an instance shows its directory in the
  browser: open folders, upload files (several at once), download, rename, delete and create new
  folders. Everything stays inside the instance directory — paths with `..` are rejected and
  downloads are streamed. **Read and edit files:** clicking a name opens the content in the browser
  (text up to 2 MB, binary files rejected), "Save" writes it back and keeps a `.bak` copy first.
- **Per-instance SFTP access.** Each instance card can switch SFTP on and off; access is confined to
  the instance directory (chroot), user and password are generated per instance, and the port comes
  from `sftp_base_port + running number` (default 2225). "New password" immediately creates one and
  copies it to the clipboard.
- The SFTP service runs as its own systemd unit `polypanel-sftp` (user or system service, following
  how the panel itself is installed) and re-reads ports/passwords every 30 seconds. It is independent
  of the instance runtime state: uploading works while the server is stopped.

### Changed
- **Token stays the same.** The web token is generated on the very first start only and is read from
  `~/.config/polypanel/token` afterwards — restarts, updates and self-updates do not change it, so old
  links keep working. A new token is only created when that file is deleted.
- The instance JSON gained `sftp_enabled`, `sftp_user`, `sftp_password`, `sftp_port`; the address
  `sftp://user@host:port` is shown on the card and works with FileZilla (SFTP, not FTP).

### Requirement
- `asyncssh` (e.g. `apt install python3-asyncssh`). Without it the panel keeps working unchanged and
  only the SFTP service reports the missing module in the panel log.

## [0.14] — 2026-11-13

### Fixed
- **Map and RCON now appear on every instance card.** The card line only showed the map name for ASA
  instances — ARK: Survival Evolved, Satisfactory, 7D2D and Space Engineers dropped map and RCON port.
  Now for all: `<map> · <game> · Port <n> · RCON <n>`, empty parts are left out.

## [0.13] — 2026-11-13

### New
- **Download speed in the install window.** Alongside step and percentage the current rate in MB/s is
  shown — computed from the byte counters in the steamcmd lines and smoothed so the number does not
  jump around.

## [0.12] — 2026-11-13

### Fixed
- **Instances no longer start by themselves after installation.** The supervisor was enabled right
  after the install; as a freshly installed server never ran, it read "process gone" as a crash and
  started it immediately. The instance is now marked as "stopped" (`runner.mark_stopped`) before the
  service starts — starting only happens via "Start" in the panel. The marker is cleared on start, so
  crash detection works as before, and an instance that was never started also stays off after a
  system boot.

## [0.11] — 2026-11-13


### Overview
Rough summary of what the panels contain.

- **Two panels, one base:** AscendedPanel for ARK: Survival Ascended, PolyPanel for ASA, ASE,
  Satisfactory, 7 Days to Die and Space Engineers. Browser UI, service on the server.
- **Dashboard:** instance cards with status, map, ports, build, CPU/RAM, players and uptime; start,
  restart, update, stop and delete right on the card, buttons locked by state (while stopping only
  the menu stays available, and so on).
- **Instance page:** live log, config editor with backup and validation (INI values as a form or
  raw), mod management with CurseForge search and update check, backups, snapshots, schedule and an
  RCON console with one-click commands.
- **Players:** list with kick, ban, whitelist and giving items — catalogue with search and a
  quantity window; the required player id (ARKID) is read from the `.arkprofile` files because ARK
  only exposes the EOS id over RCON.
- **Bans:** its own "banned players" window with per-row unban and an honest note on why ARK does
  not hand out its ban list over RCON.
- **Operation:** crash detection with automatic restart, Discord notifications, German/English
  switchable at any time, several instances in one process.
- **Bug reports:** button in the panel, report goes to the operator (webhook, console-only) with
  version, instance, system and log excerpt, passwords stripped.

### Fixed
- **Space Engineers no longer starts in Experimental mode.** At startup SE checks CPU cores, clock
  and RAM (`ProcessorCount >= 3`, `CPUFrequency >= 3.2 GHz`, at least 6 GB RAM) and otherwise forces
  Experimental — players are rejected until they enable Experimental in their game options. SE reads
  the clock via WMI, which Wine feeds from `/proc/cpuinfo`, and VMs report e.g. 2095 MHz there.
  PolyPanel now builds a small LD_PRELOAD shim at start time
  (`~/.local/share/polypanel/se-cpufix/fakecpu.so`) that reports 3.6 GHz to Wine; the server log then
  shows `Experimental mode: No`. Requires a C compiler (`build-essential`/`gcc`) — if it is missing,
  nothing changes and the start log says so.
- **Experimental-mode popup removed.** Now that the server passes the hardware check, the "server is
  running in experimental mode" window (and the warning bar in the settings tab) only got in the way —
  it covered the whole page and swallowed clicks. Both are gone, together with `/api/experimental` and
  the related language keys; the `ExperimentalMode` field still shows "effective: on/off" from the
  server log in case SE flips it by itself.
- **"Install" shows the progress again.** If the remembered tab was "Settings", it covered the install
  panel — the click looked like it landed in the settings while the install ran correctly in the
  background. During a running install the instance page now switches to "Overview" by itself, with
  progress bar and log.
- **A fresh install now really starts without Experimental.** The template shipped
  `PhysicsIterations 1` and `BlockLimitsEnabled NONE`, and new instances added `MaxPlayers 20` — three
  deviations from the vanilla set, which is exactly why SE forces Experimental on its own
  (`Experimental mode reason: MaxPlayers, PhysicsIterations, BlockLimitsEnabled`). Template and
  instance default are now vanilla: physics 8, block limits GLOBALLY, 16 players; that more than 16
  players forces Experimental is stated as a hint on the field.
- **Deleting no longer blocks the UI.** Stopping (SE saves for up to 90 s) and removing several GB now
  run as a background job; the card shows "stopping the server …", then "deleting server files …" and
  finally the freed size. Every delete is also logged with timestamp and freed MB in `panel.log`.
- **Wine is installed without asking** — like Xvfb and `gcc`. The "install Wine?" question was answered
  with "no" in practice, and afterwards no Windows game started.