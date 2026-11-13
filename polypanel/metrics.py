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
_PREV: dict[int, tuple[int, float]] = {}
_PLAYERS: dict[str, tuple[float, list[str]]] = {}
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
            out = rc.command("ListPlayers", timeout=10)
        names = [m.group(2).strip() for m in
                 (re.match(r"^\s*(\d+)\.\s*(.+?)\s*,\s*([0-9A-Za-z]{15,32})\s*$", ln) for ln in out.splitlines())
                 if m]
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
    # Immer den groessten Prozess der Instanz messen, nicht blind die PID aus der Datei:
    # bei 7D2D steht dort der Wrapper `/bin/sh startserver.sh` (2 MB), das Spiel selbst ist ein
    # Kindprozess mit mehreren GB. Sonst zeigt das Panel "RAM 0".
    kandidaten = set(runner.instance_pids(inst))
    pid_datei = runner.read_pid(inst)
    if pid_datei:
        kandidaten.add(pid_datei)
    pid, bester_rss = None, -1
    for kandidat in kandidaten:
        _info = _proc(kandidat)
        if _info and _info["rss_pages"] > bester_rss:
            pid, bester_rss = kandidat, _info["rss_pages"]
    out = {
        "cpu": 0.0, "ram_mb": 0, "ram_gb": 0.0, "ram_peak_gb": 0.0, "uptime": 0, "players": 0,
        "player_names": [],
    }
    if not pid:
        _PREV.pop(pid or 0, None)
        out["cpu_hist"], out["ram_hist"] = [], []
        return out

    info = _proc(pid)
    if not info:
        out["cpu_hist"], out["ram_hist"] = [], []
        return out

    now = time.time()
    ticks = info["ticks"] + _children_ticks(pid)
    prev = _PREV.get(pid)
    if prev:
        d_ticks = ticks - prev[0]
        d_time = now - prev[1]
        if d_time > 0:
            out["cpu"] = round(max(0.0, d_ticks / HZ / d_time * 100.0), 1)
    _PREV[pid] = (ticks, now)

    peak_mb = 0
    try:
        with open("/proc/%d/status" % pid) as fh:
            for line in fh:
                if line.startswith("VmHWM:"):
                    peak_mb = int(line.split()[1]) / 1024
                    break
    except OSError:
        pass
    out["ram_peak_gb"] = round(peak_mb / 1024, 2)

    ram_mb = info["rss_pages"] * PAGE / (1024 * 1024)
    out["ram_mb"] = int(ram_mb)
    out["ram_gb"] = round(ram_mb / 1024, 2)
    out["uptime"] = int(now - (_boot_time() + info["starttime"] / HZ)) if _boot_time() else 0

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
        prev = _PREV.get(-1)
        if prev:
            d_total = total - prev[0]
            d_idle = idle - prev[1]
            if d_total > 0:
                cpu = round((1 - d_idle / d_total) * 100.0, 1)
            _PREV[-1] = (int(total), idle)
        else:
            _PREV[-1] = (int(total), idle)
    except (OSError, IndexError, ValueError):
        pass

    return {
        "cpu": cpu,
        "ram_total_gb": round(ram_total, 1),
        "ram_used_gb": round(ram_total - ram_avail, 1),
        "ram_pct": round((ram_total - ram_avail) / ram_total * 100, 1) if ram_total else 0.0,
    }
