"""Instanz-Registry: mehrere Server unter ~/.config/polypanel/<name>.json."""
from __future__ import annotations

import json
import os
import secrets
import socket

from . import games
from .instance import Instance

from .paths import CONF_DIR

MAPS = list(games.get("ark").maps)     # ASA-Karten (aeltere Aufrufer nutzen diese Liste)


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
    freed_gb = 0.0
    hinweis = ""
    if delete_files:
        directory = inst.directory.rstrip("/")
        grund = _delete_refusal(inst, directory)
        if grund:
            hinweis = grund
        else:
            freed_gb = _dir_gb(directory)
            shutil.rmtree(directory, ignore_errors=True)
            if not os.path.exists(directory):
                removed_dir = directory
                marker = directory + ".stopped"       # Rest des Supervisor-Markers
                if os.path.exists(marker):
                    try:
                        os.remove(marker)
                    except OSError:
                        pass
            else:
                hinweis = "Ordner konnte nicht vollstaendig geloescht werden: %s" % directory
    return {"ok": True, "config": moved, "removed_dir": removed_dir,
            "freed_gb": round(freed_gb, 2), "freed_mb": round(freed_gb * 1024),
            "hint": hinweis}


# Nur innerhalb dieser Verzeichnisse werden Serverdateien geloescht
INSTANCE_ROOTS = (os.path.expanduser("~/polypanel-instances"),
                  "/mnt/Games/polypanel")


def _delete_refusal(inst: Instance, directory: str) -> str:
    """Leerer String = loeschen erlaubt; sonst der Grund (Sicherheitsnetz)."""
    if not directory or not os.path.isdir(directory):
        return "Ordner existiert nicht: %s" % directory
    real = os.path.realpath(directory)
    if real in ("/", os.path.expanduser("~"), os.path.expanduser("~/PolyPanel")):
        return "Ordner sieht nicht wie eine Instanz aus: %s" % real
    in_root = any(real.startswith(os.path.realpath(root) + os.sep) for root in INSTANCE_ROOTS)
    if not in_root:
        return ("Ordner liegt ausserhalb der Instanzverzeichnisse - bitte von Hand löschen: %s"
                % real)
    if os.path.basename(real) != inst.name:
        return ("Ordner heisst nicht wie die Instanz (%s) - bitte von Hand löschen: %s"
                % (inst.name, real))
    return ""


def _dir_gb(directory: str) -> float:
    total = 0
    for root, _dirs, files in os.walk(directory):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total / (1024 ** 3)


def save(inst: Instance) -> None:
    inst.save(conf_path(inst.name))


def _free_port(start: int, udp: bool = True) -> int:
    """Erstes freies Port-Paar ab start finden (Spiel-Port und Port+1)."""
    if start <= 0:
        return 0
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
           session_name: str = "", max_players: int | None = None,
           game: str = games.DEFAULT_GAME) -> Instance:
    if not name or not name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Name nur mit Buchstaben, Zahlen, - und _")
    if load(name):
        raise ValueError("Instanz '%s' existiert bereits" % name)
    prof = games.get(game)
    game_port = port or _free_port(prof.default_game_port)
    # Spiele ohne Steuerkanal (Space Engineers, kein RCON) haben keinen Control-Port - 0 bleibt 0.
    # Vorher lief _free_port(0) in die Schleife 0/1, 10/11, ... und scheiterte an den
    # privilegierten Ports < 1024 ("kein freier Port gefunden").
    ctrl_port = _free_port(prof.default_control_port, udp=False) if prof.default_control_port else 0
    inst = Instance(
        name=name,
        directory=os.path.expanduser("~/polypanel-instances/%s" % name),
        game=prof.key,
        map=map_name or (prof.maps[0][0] if prof.maps else ""),
        session_name=session_name or prof.label,
        port=game_port,
        query_port=game_port + 1,
        rcon_port=ctrl_port,
        rcon_password=secrets.token_hex(8),
        max_players=max_players if max_players is not None else prof.default_max_players,
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
                          os.path.expanduser("~/.config/polypanel/static/maps/%s.jpg" % inst.map))
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
