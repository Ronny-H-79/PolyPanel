## [0.11] — 2026-11-13

### Changed
- **Reporting moved to the start page** (button in the header, only shown when a report webhook is
  configured) and is gone from the instance page.
- **It reports the panel, not the game:** the report carries the panel version, the system and the
  **panel logs** (service journal plus the instance's `.ascendedpanel-supervisor.log`, `.update.log`
  and `.install.log`). The game's server log is **not** attached. Passwords and tokens are still
  stripped before sending.
- Window wording follows: "What can't the panel do?" instead of "What happened?".

## [0.10] — 2026-11-13

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
