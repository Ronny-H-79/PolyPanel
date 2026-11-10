"""Supervisor: Health-Check, Auto-Restart, geplante Neustarts."""
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime

from .instance import Instance
from . import notify as notify_mod
from . import runner


def _port_open(port: int, udp: bool = True) -> bool:
    flag = "-ulpn" if udp else "-tlpn"
    try:
        out = subprocess.run(
            ["ss", flag], capture_output=True, text=True, timeout=10
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return (":%d " % port) in out or (":%d\n" % port) in out


def _log_size(inst: Instance) -> int:
    try:
        return os.path.getsize(inst.log_path)
    except OSError:
        return 0


def _state_path(inst: Instance) -> str:
    return os.path.join(inst.directory, ".noah2games-supervisor.json")


def _load_state(inst: Instance) -> dict:
    try:
        with open(_state_path(inst), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _save_state(inst: Instance, state: dict) -> None:
    with open(_state_path(inst), "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)


def notify(inst: Instance, text: str) -> None:
    """Lokales Log + Discord (falls Webhook gesetzt)."""
    line = "%s  %s" % (time.strftime("%F %T"), text)
    print(line, flush=True)
    try:
        with open(os.path.join(inst.directory, ".noah2games-supervisor.log"), "a") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def notify_event(inst: Instance, title: str, text: str, kind: str = "info", fields=None) -> None:
    line = "%s  %s" % (time.strftime("%F %T"), text)
    print(line, flush=True)
    try:
        with open(os.path.join(inst.directory, ".noah2games-supervisor.log"), "a") as fh:
            fh.write(line + "\n")
    except OSError:
        pass
    notify_mod.send(inst, title, text, kind, fields)


class Supervisor:
    def __init__(self, inst: Instance, interval: int = 30):
        self.inst = inst
        self.interval = interval
        self.state = _load_state(inst)
        self._schedule_mtime = 0.0
        self.state.setdefault("restarts", [])
        self.state.setdefault("last_size", 0)
        self.state.setdefault("last_scheduled", "")

    # ------------------------------------------------------------------ Checks
    def _record_restart(self, reason: str) -> None:
        now = time.time()
        restarts = [t for t in self.state["restarts"] if now - t < 3600]
        restarts.append(now)
        self.state["restarts"] = restarts
        _save_state(self.inst, self.state)
        notify(self.inst, "Neustart #%d in der letzten Stunde: %s" % (len(restarts), reason))

    def _too_many_restarts(self) -> bool:
        now = time.time()
        recent = [t for t in self.state["restarts"] if now - t < 3600]
        return len(recent) >= self.inst.max_restarts_per_hour

    def health(self) -> dict[str, object]:
        pid = runner.read_pid(self.inst)
        alive = pid is not None
        port = _port_open(self.inst.port, udp=True)
        size = _log_size(self.inst)
        grew = size > self.state.get("last_size", 0)
        self.state["last_size"] = size
        return {
            "alive": alive,
            "pid": pid,
            "port": port,
            "ready": runner.server_ready(self.inst) if alive else False,
            "log_grew": grew,
            "log_size": size,
        }

    def _due(self, times: list[str], key: str) -> str | None:
        """True, wenn eine Uhrzeit aus times jetzt erreicht ist und heute noch nicht lief."""
        now = datetime.now().strftime("%H:%M")
        if now in times:
            stamp = datetime.now().strftime("%Y-%m-%d ") + now
            if self.state.get(key) != stamp:
                self.state[key] = stamp
                _save_state(self.inst, self.state)
                return now
        return None

    def scheduled_due(self) -> str | None:
        return self._due(self.inst.restart_times, "last_scheduled")

    def backup_due(self) -> str | None:
        return self._due(self.inst.backup_times, "last_backup")

    def snapshot_due(self) -> str | None:
        return self._due(self.inst.snapshot_times, "last_snapshot")

    TASK_ACTIONS = ("restart", "start", "stop", "update", "backup",
                    "saveworld", "dinowipe", "broadcast", "rcon")

    def tasks_due(self) -> list[dict]:
        """Faellige Aufgaben: Uhrzeit passt, Wochentag passt, heute noch nicht gelaufen."""
        now = datetime.now()
        hhmm = now.strftime("%H:%M")
        dow = now.isoweekday()
        stamp = now.strftime("%Y-%m-%d %H:%M")
        due = []
        for task in self.inst.tasks or []:
            if not isinstance(task, dict) or not task.get("on", True):
                continue
            if (task.get("time") or "").strip() != hhmm:
                continue
            days = [int(d) for d in (task.get("days") or []) if str(d).isdigit()]
            if days and dow not in days:
                continue
            key = "task_%s" % (task.get("id") or task.get("time"))
            if self.state.get(key) == stamp:
                continue
            self.state[key] = stamp
            _save_state(self.inst, self.state)
            due.append(task)
        return due

    def _rcon(self, command: str) -> str:
        from .rcon import RconClient
        with self.inst.control(timeout=10) as rc:
            return rc.command(command, timeout=15)

    def run_task(self, task: dict) -> str:
        """Eine Zeitplan-Aufgabe ausfuehren; Rueckgabe ist die Meldung fuers Log."""
        action = (task.get("action") or "").strip()
        arg = (task.get("arg") or "").strip()
        if action == "backup":
            self._do_backup()
            return "Backup erstellt"
        if action == "start":
            if runner.is_running(self.inst):
                return "laeuft bereits"
            pid = runner.start(self.inst)
            return "gestartet (PID %d)" % pid
        if action == "stop":
            runner.mark_stopped(self.inst)
            return runner.stop(self.inst, timeout=90)
        if action == "update":
            runner.update_installed(self.inst, restart_after=True)
            return "Update + Neustart angestossen"
        if action == "saveworld":
            return self._rcon("SaveWorld") or "Welt gespeichert"
        if action == "dinowipe":
            return self._rcon("DestroyWildDinos") or "wilde Dinos entfernt"
        if action == "broadcast":
            self._rcon("Broadcast %s" % arg)
            return "Broadcast: %s" % arg
        if action == "rcon":
            return self._rcon(arg) or "RCON-Befehl abgesetzt"
        return "unbekannte Aktion: %s" % action

    def _broadcast(self, text: str) -> None:
        try:
            from .rcon import RconClient
            with self.inst.control(timeout=10) as rc:
                rc.command("Broadcast %s" % text, timeout=12)
            notify(self.inst, "Broadcast: %s" % text)
        except Exception as exc:  # noqa: BLE001
            notify(self.inst, "Broadcast fehlgeschlagen: %s" % exc.__class__.__name__)

    def _do_snapshot(self) -> str:
        """Auto-Snapshot anlegen und nur die letzten `snapshot_keep` behalten (jeder ~12 GB)."""
        from . import snapshots as snap
        info = snap.create(self.inst, label="auto")
        keep = max(1, int(getattr(self.inst, "snapshot_keep", 3) or 3))
        removed = 0
        try:
            # nur eigene Auto-Snapshots aufraeumen - manuelle bleiben unangetastet
            items = [s for s in snap.listing(self.inst)
                     if str(s.get("name", "")).startswith("auto_")]
        except Exception:  # noqa: BLE001
            items = []
        # nach echter Aenderungszeit sortieren (Namen koennen nach dem Aufraeumen wiederverwendet werden)
        items.sort(key=lambda s: os.path.getmtime(s["path"]) if s.get("path") else 0, reverse=True)
        for old in items[keep:]:
            try:
                if snap.delete(self.inst, old["name"]):
                    removed += 1
            except Exception:  # noqa: BLE001
                pass
        notify_event(self.inst, "Snapshot erstellt",
                     "%s (%.1f GB)%s" % (info["name"], info["size_gb"],
                                         (", %d alte entfernt" % removed) if removed else ""),
                     "info", {"Instanz": self.inst.name})
        return "Snapshot %s (%.1f GB)%s" % (info["name"], info["size_gb"],
                                            (", %d alte entfernt" % removed) if removed else "")

    def _do_backup(self) -> None:
        from . import backups
        try:
            info = backups.create(self.inst, label="auto")
            removed = backups.prune(self.inst, keep=self.inst.backups_keep)
            notify(self.inst, "Backup erstellt: %s (%.1f MB)%s"
                   % (info["file"], info["size_mb"], (", %d alte entfernt" % removed) if removed else ""))
        except Exception as exc:  # noqa: BLE001
            notify(self.inst, "Backup fehlgeschlagen: %s" % exc)
            notify_event(self.inst, "Backup fehlgeschlagen", str(exc)[:500], "backup",
                         {"Instanz": self.inst.name})

    # ------------------------------------------------------------------ Aktionen
    def restart(self, reason: str) -> None:
        if self._too_many_restarts():
            notify(self.inst, "Restart-Limit erreicht (%d/h) - kein weiterer Versuch: %s"
                   % (self.inst.max_restarts_per_hour, reason))
            return
        self._record_restart(reason)
        notify(self.inst, "stop (%s)" % reason)
        result = runner.stop(self.inst, timeout=90)
        notify(self.inst, "stop: %s" % result)
        time.sleep(3)
        try:
            pid = runner.start(self.inst)
            notify(self.inst, "start: PID %d" % pid)
        except runner.RunnerError as exc:
            notify(self.inst, "start fehlgeschlagen: %s" % exc)

    def _reload_schedule(self) -> None:
        """Zeitplan-Einstellungen neu lesen - die UI schreibt sie in die Instanzdatei.

        Ohne das laedt der Supervisor nur beim Start und ignorierte neue Aufgaben bis zum Neustart.
        Bewusst nur die Zeitplan-Felder: Ports/Mods mitten im Betrieb zu wechseln waere gefaehrlich.
        """
        from . import registry
        path = registry.conf_path(self.inst.name)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return
        if mtime == self._schedule_mtime:
            return
        self._schedule_mtime = mtime
        fresh = registry.load(self.inst.name)
        if fresh is None:
            return
        self.inst.tasks = fresh.tasks
        self.inst.restart_times = fresh.restart_times
        self.inst.backup_times = fresh.backup_times
        self.inst.snapshot_times = fresh.snapshot_times
        self.inst.snapshot_keep = fresh.snapshot_keep
        self.inst.warn_minutes = fresh.warn_minutes
        self.inst.backups_keep = fresh.backups_keep

    def tick(self) -> None:
        if os.path.exists(runner.maintenance_lock(self.inst)):
            return          # laufende Wartung (Restore/Update) nicht stoeren

        self._reload_schedule()

        # Zeitplan (Aufgabenliste)
        for task in self.tasks_due():
            action = (task.get("action") or "").strip()
            label = task.get("label") or action
            if action == "restart":
                wait = max(0, int(self.inst.warn_minutes)) * 60
                self.state["restart_at"] = time.time() + wait
                self.state["warned5"] = self.state["warned1"] = False
                _save_state(self.inst, self.state)
                if wait:
                    self._broadcast("Server restartet in %d Minuten" % self.inst.warn_minutes)
                    self.state["warned5"] = True
                else:
                    self.state.pop("restart_at", None)
                    self.restart("Zeitplan %s" % label)
                    notify_event(self.inst, "Neustart ausgefuehrt",
                                 "Zeitplan-Aufgabe %s ist durch." % label, "info")
            else:
                try:
                    result = self.run_task(task)
                    notify_event(self.inst, "Zeitplan: %s" % label, str(result)[:500], "info",
                                 {"Instanz": self.inst.name})
                except Exception as exc:  # noqa: BLE001
                    notify_event(self.inst, "Zeitplan fehlgeschlagen: %s" % label,
                                 "%s: %s" % (exc.__class__.__name__, exc), "error",
                                 {"Instanz": self.inst.name})

        # geplanter Snapshot (eigene Uhrzeiten, unabhaengig vom Zeitplan)
        sd = self.snapshot_due()
        if sd:
            try:
                self._do_snapshot()
            except Exception as exc:  # noqa: BLE001
                notify_event(self.inst, "Snapshot fehlgeschlagen", str(exc)[:500], "error",
                             {"Instanz": self.inst.name})

        # geplanter Neustart: Countdown ankuendigen, dann ausfuehren
        due = self.scheduled_due()
        if due:
            wait = max(0, int(self.inst.warn_minutes)) * 60
            self.state["restart_at"] = time.time() + wait
            self.state["warned5"] = self.state["warned1"] = False
            _save_state(self.inst, self.state)
            if wait:
                self._broadcast("Server restartet in %d Minuten" % self.inst.warn_minutes)
            self.state["warned5"] = True
            if not wait:
                self.state.pop("restart_at", None)
                self.restart("geplant %s" % due)
                notify_event(self.inst, "Neustart ausgefuehrt",
                             "Geplanter Neustart %s ist durch." % due, "info")
            return

        rat = self.state.get("restart_at")
        if rat:
            left = rat - time.time()
            if left <= 60 and not self.state.get("warned1"):
                self.state["warned1"] = True
                _save_state(self.inst, self.state)
                self._broadcast("Server restartet in 1 Minute")
            if left <= 0:
                self.state.pop("restart_at", None)
                _save_state(self.inst, self.state)
                self.restart("geplant (Countdown)")
                notify_event(self.inst, "Neustart ausgefuehrt",
                             "Geplanter Neustart ist durch.", "info")
            return

        # Update-Pruefung alle 6 Stunden
        self._maybe_update_notice()

        h = self.health()
        if not h["alive"]:
            if runner.was_stopped(self.inst):
                if not self.state.get("stop_notified"):
                    self.state["stop_notified"] = True
                    _save_state(self.inst, self.state)
                    notify_event(self.inst, "Server gestoppt", "Manuell gestoppt - der Supervisor laesst ihn aus.", "info")
                return
            tail = runner.tail(self.inst.log_path, 12)
            notify_event(self.inst, "Server abgestuerzt",
                         "Der Prozess ist ohne Abschied verschwunden. Neustart laeuft.",
                         "crash", {"Letzte Logzeilen": "\n".join(x[-90:] for x in tail[-4:])})
            self.restart("Prozess weg (Absturz)")
            return
        if self.state.get("stop_notified"):
            self.state["stop_notified"] = False
            _save_state(self.inst, self.state)
        if not h["port"]:
            # Prozess lebt, aber Spielport zu -> Startup-Haenger oder abgestuerzt
            streak = int(self.state.get("no_port_ticks", 0)) + 1
            self.state["no_port_ticks"] = streak
            _save_state(self.inst, self.state)
            waited = streak * self.interval
            if waited >= self.inst.hang_seconds:
                self.state["no_port_ticks"] = 0
                notify_event(self.inst, "Server haengt",
                             "Port %d ist seit %ds zu, obwohl der Prozess laeuft. Neustart."
                             % (self.inst.port, waited), "hang",
                             {"Instanz": self.inst.name, "Log": str(self.state.get("log_size", 0))})
                self.restart("Port %d seit %ds zu" % (self.inst.port, waited))
            return
        if self.state.get("no_port_ticks"):
            self.state["no_port_ticks"] = 0
            _save_state(self.inst, self.state)

    def _maybe_update_notice(self) -> None:
        """Alle 6 Stunden pruefen, ob ein neuer Server-Build bereitsteht."""
        now = time.time()
        last = float(self.state.get("update_checked", 0) or 0)
        if now - last < 6 * 3600:
            return
        self.state["update_checked"] = now
        _save_state(self.inst, self.state)
        try:
            info = runner.check_update(self.inst)
        except Exception:  # noqa: BLE001 - Steam darf den Tick nicht kippen
            return
        if not info.get("available") or info.get("up_to_date"):
            return
        if str(info.get("available")) == str(self.state.get("update_notified")):
            return
        self.state["update_notified"] = str(info.get("available"))
        _save_state(self.inst, self.state)
        notify_event(self.inst, "Server-Update verfuegbar",
                     "Ein neuer ARK-Build liegt bei Steam bereit.",
                     "update", {"Installiert": info.get("installed", "?"),
                                "Verfuegbar": info.get("available", "?")})

    def run(self) -> None:
        notify(self.inst, "Supervisor startet (%s, Intervall %ds, geplante Neustarts: %s)"
               % (self.inst.name, self.interval, ", ".join(self.inst.restart_times) or "keine"))
        while True:
            try:
                self.tick()
            except Exception as exc:  # noqa: BLE001 - Supervisor darf nie sterben
                notify(self.inst, "Tick-Fehler: %s: %s" % (exc.__class__.__name__, exc))
            time.sleep(self.interval)
