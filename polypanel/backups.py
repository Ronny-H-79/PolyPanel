"""Backups: erstellen, auflisten, wiederherstellen, aufraeumen.

Gesichert wird ShooterGame/Saved (Welt, Spieler, Config) ohne Logs/Crashes.
"""
from __future__ import annotations

import os
import tarfile
import time

from .instance import Instance
from . import runner

BASE = os.path.expanduser("~/polypanel-backups")
SKIP_DIRS = {"Logs", "CrashReportClient", "Crashes"}


def _backup_dir(inst: Instance) -> str:
    path = os.path.join(BASE, inst.name)
    os.makedirs(path, exist_ok=True)
    return path


def _filter(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
    parts = info.name.split("/")
    if any(p in SKIP_DIRS for p in parts):
        return None
    if info.name.endswith(".log"):
        return None
    return info


def create(inst: Instance, label: str = "manuell") -> dict:
    """Welt + Config als tar.gz sichern; laufender Server wird vorher gespeichert.

    ARK schreibt beim Speichern Zwischendateien (*.arkrbf) und benennt sie um -
    deshalb werden Dateien einzeln und fehlertolerant gepackt, Temp-Dateien
    uebersprungen und nach dem SaveWorld kurz gewartet.
    """
    if runner.is_running(inst):
        try:
            from .rcon import RconClient
            with inst.control(timeout=10) as rc:
                rc.command("SaveWorld", timeout=25)
            time.sleep(3)
        except Exception:  # noqa: BLE001 - Backup trotzdem versuchen
            pass

    stamp = time.strftime("%Y%m%d-%H%M%S")
    tag = ("%s_" % label) if label else ""
    target = os.path.join(_backup_dir(inst), "%s_%s%s.tar.gz" % (inst.name, tag, stamp))
    src = os.path.join(inst.directory, "ShooterGame", "Saved")
    if not os.path.isdir(src):
        raise RuntimeError("ShooterGame/Saved fehlt - nichts zu sichern")

    packed = skipped = 0
    with tarfile.open(target, "w:gz") as tar:
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for name in files:
                if name.endswith((".log", ".arkrbf", ".tmp")):
                    continue
                path = os.path.join(root, name)
                arc = os.path.join("ShooterGame", "Saved", os.path.relpath(path, src))
                try:
                    tar.add(path, arcname=arc, recursive=False)
                    packed += 1
                except (OSError, tarfile.TarError):
                    skipped += 1
    size = os.path.getsize(target)
    return {"file": os.path.basename(target), "path": target,
            "size_mb": round(size / (1024 * 1024), 1), "created": stamp,
            "files": packed, "skipped": skipped}


def listing(inst: Instance) -> list[dict]:
    out = []
    folder = _backup_dir(inst)
    for name in sorted(os.listdir(folder), reverse=True):
        if not name.endswith(".tar.gz"):
            continue
        path = os.path.join(folder, name)
        try:
            st = os.stat(path)
        except OSError:
            continue
        kind = ("vor Restore" if "_vor-restore_" in name else
                "geplant" if "_auto_" in name else
                "manuell" if "_manuell_" in name else "aelter")
        out.append({"file": name, "path": path, "kind": kind,
                    "size_mb": round(st.st_size / (1024 * 1024), 1),
                    "mtime": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))})
    return out


def restore(inst: Instance, filename: str) -> str:
    """Backup einspielen: Server stoppen, entpacken, wieder starten."""
    path = os.path.join(_backup_dir(inst), os.path.basename(filename))
    if not os.path.exists(path):
        raise RuntimeError("Backup nicht gefunden: %s" % filename)
    with runner.maintenance(inst, "Restore"):
        was_running = runner.is_running(inst)
        steps = []
        if was_running:
            steps.append("stop: " + runner.stop(inst, timeout=90))
            time.sleep(3)

        # Sicherheitskopie des aktuellen Stands
        try:
            create(inst, label="vor-restore")
            steps.append("Sicherung des aktuellen Stands angelegt")
        except Exception as exc:  # noqa: BLE001
            steps.append("Sicherung fehlgeschlagen: %s" % exc)

        with tarfile.open(path, "r:gz") as tar:
            tar.extractall(inst.directory, filter="data")
        steps.append("entpackt: %s" % os.path.basename(path))

        if was_running:
            runner.start(inst)
            steps.append("start")
        return " | ".join(steps)


def delete(inst: Instance, filename: str) -> bool:
    path = os.path.join(_backup_dir(inst), os.path.basename(filename))
    try:
        os.unlink(path)
        return True
    except OSError:
        return False


def prune(inst: Instance, keep: int = 10) -> int:
    """Alte Backups nicht loeschen, sondern in .trash/ verschieben (nachvollziehbar)."""
    if keep is None or keep <= 0:
        return 0
    items = listing(inst)
    trash = os.path.join(_backup_dir(inst), ".trash")
    moved = 0
    for entry in items[keep:]:
        try:
            os.makedirs(trash, exist_ok=True)
            os.replace(entry["path"], os.path.join(trash, os.path.basename(entry["path"])))
            moved += 1
        except OSError:
            continue
    return moved
