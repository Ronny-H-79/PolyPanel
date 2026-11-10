"""Start/Stop/Status einer ARK-Instanz unter Wine bzw. Proton."""
from __future__ import annotations

import os
import signal
import re
import shutil
import subprocess
import sys
import time

from .instance import Instance
from .rcon import RconClient, RconError

STEAMCMD = os.path.expanduser("~/steamcmd/steamcmd.sh")


class RunnerError(RuntimeError):
    pass


def _env(inst: Instance) -> dict[str, str]:
    env = dict(os.environ)
    if not inst.profile.needs_wine:
        # Native Spiele (Satisfactory, 7 Days to Die) brauchen keine Wine-Umgebung
        env.pop("WINEPREFIX", None)
        return env
    env.setdefault("WINEDEBUG", "-all")
    prefix = inst.wine_prefix or inst.profile.wine_prefix(inst)
    if prefix:
        env["WINEPREFIX"] = os.path.expanduser(prefix)
    if inst.profile.wine_overrides:
        env.setdefault("WINEDLLOVERRIDES", inst.profile.wine_overrides)
    else:
        env.pop("WINEDLLOVERRIDES", None)
    if getattr(inst, "headless", False) and not getattr(inst.profile, "needs_display", False):
        # Wine 11 verbindet sich sonst per libwayland (Default wayland-0) und oeffnet ein Fenster
        env.pop("DISPLAY", None)
        env.pop("WAYLAND_DISPLAY", None)
        runtime = os.path.join(inst.directory, ".runtime")
        os.makedirs(runtime, mode=0o700, exist_ok=True)
        env["XDG_RUNTIME_DIR"] = runtime
    return env


def read_pid(inst: Instance) -> int | None:
    try:
        with open(inst.pid_file) as fh:
            pid = int(fh.read().strip())
    except (OSError, ValueError):
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        return None
    return pid


def is_running(inst: Instance) -> bool:
    pid = read_pid(inst)
    if pid is not None:
        return True
    return bool(instance_pids(inst))      # von Hand gestartet: ueber cwd/exe erkennen



def maintenance_lock(inst: Instance) -> str:
    return os.path.join(inst.directory + ".maintenance")


class maintenance:
    """Kontextmanager: haelt den Supervisor fern, waehrend Dateien ersetzt werden."""

    def __init__(self, inst: Instance, reason: str = "Wartung"):
        self.inst = inst
        self.reason = reason

    def __enter__(self) -> "maintenance":
        try:
            with open(maintenance_lock(self.inst), "w") as fh:
                fh.write("%s %s\n" % (time.strftime("%F %T"), self.reason))
        except OSError:
            pass
        return self

    def __exit__(self, *_exc) -> None:
        try:
            os.unlink(maintenance_lock(self.inst))
        except OSError:
            pass


def console_socket(inst: Instance) -> str:
    return os.path.join(inst.directory, ".PolyPanel-console.sock")


def send_console(inst: Instance, cmd: str) -> str:
    """Befehl ueber den consoled-Socket an die stdin-Pipe des Servers schicken."""
    import socket as _socket
    if not is_running(inst):
        raise RunnerError("Server laeuft nicht")
    path = console_socket(inst)
    if not os.path.exists(path):
        raise RunnerError("kein Konsolen-Socket (Server ohne consoled gestartet?)")
    try:
        with _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM) as s:
            s.settimeout(8)
            s.connect(path)
            s.sendall(cmd.strip().encode())
            reply = s.recv(256).decode("utf-8", "replace")
    except OSError as exc:
        raise RunnerError("Konsolen-Socket: %s" % exc) from exc
    return "gesendet: %s (%s)" % (cmd.strip(), reply)


def tail_console(inst: Instance, lines: int = 60) -> list[str]:
    return tail(inst.console_log, lines)


def _ports_free(inst: Instance) -> list[int]:
    """Belegte Ports zurueckgeben - fremde Prozesse (z. B. AMP) blockieren den Start."""
    import socket as _socket
    busy = []
    for port, kind in ((inst.port, _socket.SOCK_DGRAM), (inst.query_port, _socket.SOCK_DGRAM),
                       (inst.rcon_port, _socket.SOCK_STREAM)):
        sock = _socket.socket(_socket.AF_INET, kind)
        try:
            sock.bind(("0.0.0.0", port))
        except OSError:
            busy.append(port)
        finally:
            sock.close()
    return busy


def start(inst: Instance, wait: int = 0) -> int:
    if is_running(inst):
        raise RunnerError("laeuft bereits (PID %s)" % read_pid(inst))
    busy = _ports_free(inst)
    if busy:
        raise RunnerError(
            "Port %s ist schon belegt - vermutlich von einer anderen Instanz oder einem anderen "
            "Serverprogramm. Ports in den Einstellungen aendern (Spiel, Query, RCON)."
            % ", ".join(str(p) for p in busy))
    if not os.path.exists(inst.exe):
        raise RunnerError("Server nicht installiert: %s fehlt" % inst.exe)
    if not inst.profile.runtime_ready(inst):
        raise RunnerError("Laufzeit fehlt - .NET/Wine-Prefix einrichten "
                          "(Profil %s, post_install)" % inst.profile.key)
    inst.write_ini()
    try:
        os.makedirs(inst.cluster_path, exist_ok=True)
    except OSError:
        pass
    clear_stopped(inst)

    # consoled starten: er haelt die stdin-Pipe und startet die Server-exe.
    # In einer eigenen systemd-Scope, damit Wine-Prozesse nicht in der Prozessgruppe
    # des Web-Dienstes haengen und dessen Neustart blockieren.
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    argv = [sys.executable, "-m", "PolyPanel.consoled", inst.name]
    launcher = list(argv)
    scope_unit = "PolyPanel-%s.scope" % re.sub(r"[^A-Za-z0-9_.-]", "-", inst.name)
    if os.environ.get("NOAH_NO_SCOPE") != "1" and shutil.which("systemd-run"):
        launcher = ["systemd-run", "--scope", "--collect", "--quiet",
                    "--unit", scope_unit] + argv
        if os.geteuid() != 0:
            # als normaler Benutzer laeuft die Scope ueber den User-Manager (loginctl enable-linger)
            launcher.insert(1, "--user")
            runtime = "/run/user/%d" % os.getuid()
            if os.path.isdir(runtime):
                os.environ.setdefault("XDG_RUNTIME_DIR", runtime)
                os.environ.setdefault("DBUS_SESSION_BUS_ADDRESS", "unix:path=%s/bus" % runtime)

    def _spawn(cmd: list[str]) -> None:
        subprocess.Popen(cmd, cwd=base, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)

    _spawn(launcher)
    deadline = time.time() + 45
    fell_back = False
    while time.time() < deadline:
        if is_running(inst):
            break
        # Scope-Start gescheitert (kein systemd, kein Bus)? Dann ohne Scope versuchen
        if not fell_back and launcher is not argv and time.time() > (deadline - 36):
            _spawn(argv)
            fell_back = True
        time.sleep(0.5)
    else:
        raise RunnerError("Server nicht gestartet - siehe %s" % inst.console_log)
    pid = read_pid(inst)
    if wait and pid:
        deadline = time.time() + wait
        while time.time() < deadline:
            if not is_running(inst):
                raise RunnerError("Prozess beendet - siehe %s" % inst.console_log)
            if server_ready(inst):
                return pid
            time.sleep(5)
    return pid or 0


def stop_marker(inst: Instance) -> str:
    return os.path.join(inst.directory + ".stopped")


def mark_stopped(inst: Instance) -> None:
    try:
        with open(stop_marker(inst), "w") as fh:
            fh.write(time.strftime("%F %T"))
    except OSError:
        pass


def clear_stopped(inst: Instance) -> None:
    try:
        os.remove(stop_marker(inst))
    except OSError:
        pass


def was_stopped(inst: Instance) -> bool:
    return os.path.exists(stop_marker(inst))


def instance_pids(inst: Instance) -> list[int]:
    """Prozesse dieser Instanz - ueber Arbeitsverzeichnis und Programmdatei.

    Zuverlaessiger als die Kommandozeile: ein Server laeuft immer mit cwd im
    Instanzordner (ARK/7D2D dort, SE in DedicatedServer64 darunter). Damit werden
    auch Server erkannt, die von Hand gestartet wurden (keine PID-Datei).
    """
    base = os.path.realpath(inst.directory)
    own = os.getpid()
    pids: list[int] = []
    try:
        entries = os.listdir("/proc")
    except OSError:
        return pids
    for entry in entries:
        if not entry.isdigit():
            continue
        pid = int(entry)
        if pid == own:
            continue
        treffer = False
        for link in ("cwd", "exe"):
            try:
                ziel = os.readlink("/proc/%d/%s" % (pid, link))
            except OSError:
                continue
            if ziel and os.path.realpath(ziel).startswith(base):
                treffer = True
                break
        if not treffer:
            continue
        # eigene Werkzeuge (python -c, grep, tail) nie als Server zaehlen
        try:
            with open("/proc/%d/cmdline" % pid, "rb") as fh:
                raw = fh.read().replace(b"\0", b" ").decode("utf-8", "replace")
        except OSError:
            continue
        if any(x in raw for x in ("PolyPanel -m", "python -c", "pgrep", "grep ", "tail -")):
            continue
        pids.append(pid)
    return pids


def stop(inst: Instance, timeout: int = 45) -> str:
    """Beendet die Instanz und meldet, was passiert ist.

    Reihenfolge: SaveWorld -> DoExit -> warten, bis wirklich kein Prozess der
    Instanz mehr laeuft -> SIGTERM an die Gruppe -> SIGKILL auf die Reste.
    """
    started = time.time()
    pid = read_pid(inst)
    leftovers = instance_pids(inst)
    if pid is None and not leftovers:
        mark_stopped(inst)          # gewollt aus: Supervisor soll nicht neu starten
        return "lief nicht"
    steps: list[str] = []
    mark_stopped(inst)

    # 1. Sauber ueber den Steuerkanal des Spiels (ARK: SaveWorld+DoExit,
    #    7D2D: save, Satisfactory: API-Shutdown)
    try:
        steps.extend(inst.profile.graceful_stop(inst))
    except Exception as exc:                       # noqa: BLE001 - Stop darf nie scheitern
        steps.append("Steuerkanal nicht erreichbar (%s)" % exc.__class__.__name__)

    # 2. Warten, bis die Prozesse der Instanz wirklich weg sind
    # Steuerkanal hat reagiert -> laengere Frist zum Speichern (SE braucht bei grossen Welten Zeit)
    rcon_ok = any(s.startswith(("SaveWorld ok", "save ", "save:", "stop", "Shutdown ")) for s in steps)
    grace = timeout if rcon_ok else min(15, timeout)
    deadline = time.time() + grace
    while time.time() < deadline:
        if not instance_pids(inst):
            _cleanup(inst)
            steps.append("beendet nach %.0f s" % (time.time() - started))
            return ", ".join(steps)
        time.sleep(1)

    # 3. SIGTERM an die Prozessgruppe, dann an die Reste
    targets = instance_pids(inst)
    if pid is not None:
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except OSError:
            pass
    for target in targets:
        try:
            os.kill(target, signal.SIGTERM)
        except OSError:
            pass
    if targets or pid is not None:
        steps.append("SIGTERM")

    for _ in range(15):
        time.sleep(1)
        if not instance_pids(inst):
            _cleanup(inst)
            steps.append("beendet nach %.0f s" % (time.time() - started))
            return ", ".join(steps)

    # 4. SIGKILL auf alles, was uebrig ist
    for target in instance_pids(inst):
        try:
            os.kill(target, signal.SIGKILL)
        except OSError:
            pass
    if pid is not None:
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except OSError:
            pass
    steps.append("SIGKILL nach %.0f s" % (time.time() - started))
    _cleanup(inst)
    return ", ".join(steps)


def _cleanup(inst: Instance) -> None:
    try:
        os.unlink(inst.pid_file)
    except OSError:
        pass


def tail(path: str, lines: int = 20) -> list[str]:
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - 65536))
            data = fh.read().decode("utf-8", "replace")
    except OSError:
        return []
    return [ln.rstrip("\r") for ln in data.splitlines()[-lines:]]


def server_ready(inst: Instance) -> bool:
    """Bereitschaft je Spiel (ARK: Logmarker, andere: Port/API)."""
    try:
        return bool(inst.profile.ready(inst))
    except Exception:                       # noqa: BLE001 - Statusabfrage darf nicht werfen
        return False


def ark_server_ready(inst: Instance) -> bool:
    """Bereit = Marker nach dem letzten 'Log file open' und kein 'Log file closed' danach."""
    lines = tail(inst.log_path, 3000)
    start = -1
    for idx in range(len(lines) - 1, -1, -1):
        if "Log file open" in lines[idx]:
            start = idx
            break
    if start < 0:
        return False
    for line in lines[start + 1:]:
        if "Log file closed" in line:
            return False
        if "has successfully started" in line:
            return True
    return False


def last_log_line(inst: Instance) -> str:
    lines = tail(inst.log_path, 1)
    return lines[-1] if lines else ""


def status(inst: Instance) -> dict[str, object]:
    pid = read_pid(inst)
    if pid is None:
        _gefunden = instance_pids(inst)
        pid = _gefunden[0] if _gefunden else None
    info: dict[str, object] = {
        "name": inst.name,
        "pid": pid,
        "running": pid is not None,
        "ready": server_ready(inst) if pid else False,
        "last_log": last_log_line(inst)[:160],
    }
    if pid and not getattr(inst.profile, "has_control", True):
        info["players"] = []
        info["rcon"] = "kein Steuerkanal (Spiel ohne RCON/API)"
    elif pid:
        try:
            eigene = inst.profile.players(inst)
            if eigene is not None:
                info["players"] = eigene
                info["rcon"] = "ok"
            else:
                with inst.control(timeout=12) as rc:
                    out = rc.command("ListPlayers", timeout=12)
                    info["players"] = [l for l in out.splitlines() if l.strip()]
                    info["rcon"] = "ok"
        except Exception as exc:                 # noqa: BLE001 - Status darf nie 500en
            info["rcon"] = "fehler: %s" % exc.__class__.__name__
    return info


UPDATE_STATE: dict[str, object] = {"name": "", "running": False, "started": 0.0}


def update_log_path(inst: Instance) -> str:
    return os.path.join(inst.directory, ".update.log")


def update(inst: Instance, validate: bool = True) -> int:
    """SteamCMD-Update. Die Ausgabe landet in .update.log, damit die Oberflaeche mitlesen kann."""
    if is_running(inst):
        raise RunnerError("Server laeuft - vor dem Update stoppen")
    inst.write_ini()        # Konfiguration vor dem Update sichern (SteamCMD ueberschreibt sie ggf.)
    argv = [STEAMCMD, "+force_install_dir", inst.directory, "+login", "anonymous",
            "+app_update", inst.profile.server_app_id]
    if validate:
        argv.append("validate")
    argv.append("+quit")
    log = update_log_path(inst)
    UPDATE_STATE.update({"name": inst.name, "running": True, "started": time.time()})
    try:
        with open(log, "w", encoding="utf-8", errors="replace") as fh:
            fh.write("steamcmd %s\n" % " ".join(argv[3:]))
            fh.flush()
            proc = subprocess.Popen(argv, cwd=os.path.expanduser("~/steamcmd"),
                                    stdout=fh, stderr=subprocess.STDOUT)
            return proc.wait()
    finally:
        UPDATE_STATE["running"] = False


# ------------------------------------------------------------------ Updates
def installed_build(inst: Instance) -> str | None:
    """BuildID der installierten Serverdateien (Steam schreibt sie in die ACF)."""
    import re as _re
    path = os.path.join(inst.directory, "steamapps", "appmanifest_%s.acf" % inst.profile.server_app_id)
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            txt = fh.read()
    except OSError:
        return None
    m = _re.search(r'"buildid"\s+"(\d+)"', txt)
    return m.group(1) if m else None


def remote_build(timeout: int = 180, app_id: str = "2430930") -> str | None:
    """Aktueller BuildID des public-Zweigs laut Steam (App-ID je Spiel)."""
    import re as _re
    try:
        res = subprocess.run(
            [STEAMCMD, "+login", "anonymous", "+app_info_print", app_id, "+quit"],
            capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    m = _re.search(r'"buildid"\s+"(\d+)"', res.stdout)
    return m.group(1) if m else None


def check_update(inst: Instance) -> dict[str, object]:
    got = installed_build(inst)
    want = remote_build(app_id=inst.profile.server_app_id)
    return {
        "installed": got,
        "available": want,
        "up_to_date": (got is not None and got == want) if want else None,
        "running": is_running(inst),
    }


def update_installed(inst: Instance, restart_after: bool = True,
                     validate_update: bool = True) -> dict[str, object]:
    """Sauber updaten: stoppen, Backup, SteamCMD, wieder starten - unter Wartungssperre."""
    with maintenance(inst, "Update"):
        steps: list[str] = []
        was_running = is_running(inst)
        if was_running:
            steps.append("stop: " + stop(inst, timeout=90))
            time.sleep(3)
        # Daten vor dem Update sichern (Welt + Configs)
        try:
            from . import backups as _bk
            info = _bk.create(inst, label="vor-update")
            steps.append("Backup vor Update: %s (%.1f MB)" % (info["file"], info["size_mb"]))
        except Exception as exc:  # noqa: BLE001 - Update nicht blockieren
            steps.append("Backup vor Update fehlgeschlagen: %s" % exc)

        rc = update(inst, validate=validate_update)
        steps.append("steamcmd exit %d" % rc)
        if rc != 0:
            return {"ok": False, "steps": steps, "restart": False}
        started = False
        if restart_after:
            try:
                pid = start(inst, wait=300)
                started = True
                steps.append("start: PID %s" % pid)
            except RunnerError as exc:
                steps.append("start fehlgeschlagen: %s" % exc)
        return {"ok": rc == 0 and started, "steps": steps, "restart": started}
