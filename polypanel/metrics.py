"""Live-Kennzahlen je Instanz: CPU, RAM, Laufzeit, Spieler (mit kleiner Historie)."""
from __future__ import annotations

import os
import time
from collections import deque

from .instance import Instance
from . import runner

HZ = os.sysconf("SC_CLK_TCK")
PAGE = os.sysconf("SC_PAGE_SIZE")
HISTORY: dict[str, dict[str, deque]] = {}
_PREV: dict[str, tuple[int, float]] = {}
_PLAYERS: dict[str, tuple[float, list[str]]] = {}
_HOST_PREV: list = [None]           # letzte Host-CPU-Messung (total, idle)
PLAYER_TTL = 15.0
CORES = os.cpu_count() or 1          # CPU-Werte sind Kern-Prozente (wie top)



def _boot_time() -> float:
    try:
        with open("/proc/stat") as fh:
            for line in fh:
                if line.startswith("btime"):
                    return float(line.split()[1])
    except OSError:
        pass
    return 0.0


def _proc(pid: int) -> dict | None:
    try:
        with open("/proc/%d/stat" % pid) as fh:
            parts = fh.read().split()
    except OSError:
        return None
    ticks = int(parts[13]) + int(parts[14])
    starttime = int(parts[21])
    rss_pages = int(parts[23])
    return {"ticks": ticks, "starttime": starttime, "rss_pages": rss_pages}


def _children_ticks(pid: int) -> int:
    """CPU-Ticks aller Kindprozesse (wineserver etc.), eine Ebene tief."""
    total = 0
    try:
        with open("/proc/%d/task/%d/children" % (pid, pid)) as fh:
            kids = fh.read().split()
    except OSError:
        return 0
    for kid in kids:
        try:
            with open("/proc/%s/stat" % kid) as fh:
                parts = fh.read().split()
            total += int(parts[13]) + int(parts[14])
        except (OSError, IndexError, ValueError):
            continue
    return total


def _instance_pids(inst: Instance) -> list[int]:
    """Alle Prozesse der Instanz (nicht nur PID + direkte Kinder).

    Wine/Proton- und Loader-Ketten haengen nicht am Starter: der eigentliche
    Serverprozess wird spaeter von PID 1 adoptiert. Deshalb ueber die Kommandozeile
    suchen; Windows-Pfade (Backslashes) werden vorher normalisiert.
    """
    path = os.path.normpath(inst.directory).replace("\\", "/").lower()
    if not path:
        return []
    pids: list[int] = []
    try:
        entries = os.listdir("/proc")
    except OSError:
        return []
    for entry in entries:
        if not entry.isdigit():
            continue
        try:
            with open("/proc/%s/cmdline" % entry, "rb") as fh:
                raw = fh.read().decode("utf-8", "replace").replace("\\", "/").lower()
        except OSError:
            continue
        if path in raw:
            pids.append(int(entry))
    return pids


def _child_pids(pid: int) -> list[int]:
    try:
        with open("/proc/%d/task/%d/children" % (pid, pid)) as fh:
            return [int(k) for k in fh.read().split()]
    except (OSError, ValueError):
        return []


def _peak_mb(pid: int) -> float:
    try:
        with open("/proc/%d/status" % pid) as fh:
            for line in fh:
                if line.startswith("VmHWM:"):
                    return int(line.split()[1]) / 1024
    except (OSError, ValueError, IndexError):
        pass
    return 0.0


def players_cached(inst: Instance) -> tuple[int, list[str]]:
    now = time.time()
    cached = _PLAYERS.get(inst.name)
    if cached and now - cached[0] < PLAYER_TTL:
        return len(cached[1]), cached[1]
    names: list[str] = []
    try:
        import re
        from .rcon import RconClient
        with inst.control(timeout=8) as rc:
            out = rc.command(getattr(inst.profile, "players_command", "ListPlayers"), timeout=10)
        from .playerparse import parse
        names = [p["name"] for p in parse(out)]
    except Exception:  # noqa: BLE001
        names = []
    _PLAYERS[inst.name] = (now, names)
    return len(names), names


_HIST: dict[int, dict[str, list]] = {}


def _hist(pid: int, cpu: float, ram_gb: float) -> tuple[list, list]:
    """Kurze Verlaufsreihe fuer die Sparklines (max. 60 Werte)."""
    h = _HIST.setdefault(pid, {"cpu": [], "ram": []})
    h["cpu"].append(cpu)
    h["ram"].append(ram_gb)
    del h["cpu"][:-60]
    del h["ram"][:-60]
    return list(h["cpu"]), list(h["ram"])


def sample(inst: Instance) -> dict:
    """Momentaufnahme; CPU braucht zwei Messungen, daher beim ersten Aufruf 0."""
    # Alle Prozesse der Instanz summieren, nicht nur die PID aus der Datei: Wine/Proton
    # und ein API-Loader laufen als eigene Prozesse, bei 7D2D steht in der PID-Datei nur
    # `/bin/sh startserver.sh` (2 MB) - sonst zeigt das Panel "RAM 0".
    pid_datei = runner.read_pid(inst)
    pids = set(_instance_pids(inst))
    pids.update(runner.instance_pids(inst))
    if pid_datei:
        pids.add(pid_datei)
        pids.update(_child_pids(pid_datei))
    out = {
        "cpu": 0.0, "ram_mb": 0, "ram_gb": 0.0, "ram_peak_gb": 0.0, "uptime": 0, "players": 0,
        "player_names": [],
    }
    infos = [info for info in (_proc(p) for p in pids) if info]
    if not infos:
        _PREV.pop(inst.name, None)
        out["cpu_hist"], out["ram_hist"] = [], []
        return out

    now = time.time()
    ticks = sum(info["ticks"] for info in infos)
    prev = _PREV.get(inst.name)
    if prev:
        d_ticks = ticks - prev[0]
        d_time = now - prev[1]
        if d_time > 0:
            out["cpu"] = round(max(0.0, d_ticks / HZ / d_time * 100.0), 1)
    _PREV[inst.name] = (ticks, now)

    peak_mb = sum(_peak_mb(p) for p in pids)
    out["ram_peak_gb"] = round(peak_mb / 1024, 2)

    ram_mb = sum(info["rss_pages"] for info in infos) * PAGE / (1024 * 1024)
    out["ram_mb"] = int(ram_mb)
    out["ram_gb"] = round(ram_mb / 1024, 2)
    start = min(info["starttime"] for info in infos)
    boot = _boot_time()
    out["uptime"] = int(now - (boot + start / HZ)) if boot else 0

    count, names = players_cached(inst)
    out["players"] = count
    out["player_names"] = names

    hist = HISTORY.setdefault(inst.name, {"cpu": deque(maxlen=60), "ram": deque(maxlen=60)})
    hist["cpu"].append(out["cpu"])
    hist["ram"].append(out["ram_gb"])
    out["cpu_hist"] = list(hist["cpu"])
    out["ram_hist"] = list(hist["ram"])
    return out


def host() -> dict:
    """Host-Auslastung: RAM aus /proc/meminfo, CPU aus /proc/stat (Delta)."""
    ram_total = ram_avail = 0
    try:
        with open("/proc/meminfo") as fh:
            vals = {}
            for line in fh:
                key, _, rest = line.partition(":")
                vals[key] = float(rest.split()[0])
            ram_total = vals.get("MemTotal", 0) / 1024 / 1024
            ram_avail = vals.get("MemAvailable", 0) / 1024 / 1024
    except (OSError, ValueError):
        pass

    cpu = 0.0
    try:
        with open("/proc/stat") as fh:
            parts = fh.readline().split()[1:]
        idle = float(parts[3]) + float(parts[4])
        total = sum(float(p) for p in parts)
        prev = _HOST_PREV[0]
        if prev:
            d_total = total - prev[0]
            d_idle = idle - prev[1]
            if d_total > 0:
                cpu = round((1 - d_idle / d_total) * 100.0, 1)
            _HOST_PREV[0] = (int(total), idle)
        else:
            _HOST_PREV[0] = (int(total), idle)
    except (OSError, IndexError, ValueError):
        pass

    return {
        "cpu": cpu,
        "ram_total_gb": round(ram_total, 1),
        "ram_used_gb": round(ram_total - ram_avail, 1),
        "ram_pct": round((ram_total - ram_avail) / ram_total * 100, 1) if ram_total else 0.0,
    }
