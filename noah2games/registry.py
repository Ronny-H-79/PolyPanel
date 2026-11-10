"""Instanz-Registry: mehrere Server unter ~/.config/noah2games/<name>.json."""
from __future__ import annotations

import json
import os
import secrets
import socket

from . import games
from .instance import Instance

CONF_DIR = os.path.expanduser("~/.config/noah2games")

MAPS = [
    ("Ragnarok_WP", "Ragnarok"),
    ("TheIsland_WP", "The Island"),
    ("ScorchedEarth_WP", "Scorched Earth"),
    ("Aberration_WP", "Aberration"),
    ("Extinction_WP", "Extinction"),
    ("TheCenter_WP", "The Center"),
    ("Astraeos_WP", "Astraeos"),
    ("Valguero_WP", "Valguero"),
    ("LostColony_WP", "Lost Colony"),
    ("Genesis_WP", "Genesis"),
]


def conf_path(name: str) -> str:
    return os.path.join(CONF_DIR, "%s.json" % name)


def names() -> list[str]:
    """Namen aller Instanzen - settings.json und fremde Dateien werden uebersprungen."""
    try:
        files = [f for f in os.listdir(CONF_DIR) if f.endswith(".json")]
    except OSError:
        return []
    out: list[str] = []
    for f in files:
        if f == "settings.json":
            continue
        try:
            with open(os.path.join(CONF_DIR, f), encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and "directory" in data:
            out.append(f[:-5])
    return sorted(out)


def load(name: str) -> Instance | None:
    path = conf_path(name)
    if not os.path.exists(path):
        return None
    return Instance.load(path)


def forget(name: str, delete_files: bool = False) -> dict:
    """Instanz entfernen: Config ins .trash legen, Dateien nur auf Wunsch loeschen."""
    import shutil
    import time as _time
    inst = load(name)
    if not inst:
        return {"ok": False, "error": "Instanz nicht gefunden"}
    trash = os.path.join(CONF_DIR, ".trash")
    os.makedirs(trash, exist_ok=True)
    stamp = _time.strftime("%Y%m%d-%H%M%S")
    moved = os.path.join(trash, "%s_%s.json" % (name, stamp))
    shutil.move(conf_path(name), moved)
    removed_dir = ""
    if delete_files:
        directory = inst.directory.rstrip("/")
        # Sicherheitsnetz: nur Verzeichnisse, die wie ein Serverordner aussehen
        if directory and os.path.isdir(directory) and os.path.basename(directory).startswith("arkserver"):
            shutil.rmtree(directory, ignore_errors=True)
            removed_dir = directory
    return {"ok": True, "config": moved, "removed_dir": removed_dir}


def save(inst: Instance) -> None:
    inst.save(conf_path(inst.name))


def _free_port(start: int, udp: bool = True) -> int:
    """Erstes freies Port-Paar ab start finden (Spiel-Port und Port+1)."""
    kind = socket.SOCK_DGRAM if udp else socket.SOCK_STREAM
    port = start
    while port < start + 400:
        ok = True
        for p in (port, port + 1):
            s = socket.socket(socket.AF_INET, kind)
            try:
                s.bind(("0.0.0.0", p))
            except OSError:
                ok = False
            finally:
                s.close()
            if not ok:
                break
        if ok:
            return port
        port += 10
    raise RuntimeError("kein freier Port gefunden")


def create(name: str, map_name: str = "", port: int | None = None,
           session_name: str = "", max_players: int = 20,
           game: str = games.DEFAULT_GAME) -> Instance:
    if not name or not name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Name nur mit Buchstaben, Zahlen, - und _")
    if load(name):
        raise ValueError("Instanz '%s' existiert bereits" % name)
    prof = games.get(game)
    game_port = port or _free_port(prof.default_game_port)
    ctrl_port = _free_port(prof.default_control_port, udp=False)
    inst = Instance(
        name=name,
        directory=os.path.expanduser("~/noah2games-instances/%s" % name),
        game=prof.key,
        map=map_name or ("Ragnarok_WP" if prof.key == "ark" else ""),
        session_name=session_name or prof.label,
        port=game_port,
        query_port=game_port + 1,
        rcon_port=ctrl_port,
        rcon_password=secrets.token_hex(8),
        max_players=max_players,
    )
    inst.save(conf_path(name))
    return inst


def installed(inst: Instance) -> bool:
    return os.path.exists(inst.exe)


def build_id(inst: Instance) -> str | None:
    path = os.path.join(inst.directory, "steamapps",
                                "appmanifest_%s.acf" % inst.profile.server_app_id)
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"buildid"' in line:
                    return line.split('"')[3]
    except OSError:
        return None
    return None


def size_gb(inst: Instance) -> float:
    total = 0
    for root, _dirs, files in os.walk(inst.directory):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return round(total / (1024 ** 3), 1)


def info(inst: Instance) -> dict:
    from . import runner
    from . import metrics
    running = runner.is_running(inst)
    data = metrics.sample(inst) if running else {"cpu": 0.0, "ram_gb": 0.0, "ram_mb": 0,
                                                 "ram_peak_gb": 0.0, "uptime": 0, "players": 0,
                                                 "player_names": [],
                                                 "cpu_hist": [], "ram_hist": []}
    return {
        "name": inst.name,
        "game": inst.game,
        "game_label": inst.profile.label,
        "map": inst.map,
        "session": inst.session_name,
        "port": inst.port,
        "rcon_port": inst.rcon_port,
        "directory": inst.directory,
        "installed": installed(inst),
        "runtime_ready": inst.profile.runtime_ready(inst),
        "build": build_id(inst),
        "size_gb": size_gb(inst) if installed(inst) else 0.0,
        "running": running,
        "ready": runner.server_ready(inst) if running else False,
        "map_image": ("/static/maps/%s.jpg" % inst.map
                      if inst.game == "ark" and os.path.exists(
                          os.path.expanduser("~/.config/noah2games/static/maps/%s.jpg" % inst.map))
                      else ""),
        "cpu": data.get("cpu", 0.0),                        # Summe ueber alle Kerne, wie top
        "cpu_pct": round(data["cpu"] / (metrics.CORES or 1), 1),   # Anteil des Servers
        "cores": metrics.CORES,
        "cpu_hist_pct": [round(v / (metrics.CORES or 1), 1) for v in data.get("cpu_hist", [])],
        "ram_gb": data.get("ram_gb", 0.0),
        "ram_mb": data.get("ram_mb", 0),
        "ram_peak_gb": data.get("ram_peak_gb", 0.0),
        "uptime": data.get("uptime", 0),
        "players": data.get("players", 0),
        "player_names": data.get("player_names", []),
        "cpu_hist": data.get("cpu_hist", []),
        "ram_hist": data.get("ram_hist", []),
    }
