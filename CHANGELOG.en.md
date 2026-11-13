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
