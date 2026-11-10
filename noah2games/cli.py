"""CLI: python3 -m noah2games <befehl> [--name NAME]"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .instance import Instance
from . import games
from . import i18n
from . import runner
from .rcon import RconClient

CONF_DIR = os.path.expanduser("~/.config/noah2games")


def conf_path(name: str) -> str:
    return os.path.join(CONF_DIR, "%s.json" % name)


def load(name: str) -> Instance:
    path = conf_path(name)
    if not os.path.exists(path):
        sys.exit("keine Konfiguration: %s (erst 'init' ausfuehren)" % path)
    return Instance.load(path)


def cmd_init(args: argparse.Namespace) -> None:
    prof = games.get(args.game)
    inst = Instance(
        name=args.name,
        directory=os.path.abspath(os.path.join(args.dir, args.name)) if args.dir.endswith("noah2games-instances") else os.path.abspath(args.dir),
        game=prof.key,
        map=args.map or (prof.maps[0][0] if prof.maps else ""),
        session_name=args.session or "Gameserver %s" % args.name,
        port=args.port or prof.default_game_port,
        query_port=(args.port or prof.default_game_port) + 1,
        rcon_port=args.rcon_port or prof.default_control_port,
        rcon_password=args.rcon_password or os.urandom(8).hex(),
    )
    inst.save(conf_path(args.name))
    inst.write_ini()
    print("Konfiguration: %s" % conf_path(args.name))
    print("RCON-Passwort: %s" % inst.rcon_password)
    print("Verzeichnis  : %s" % inst.directory)


def cmd_start(args: argparse.Namespace) -> None:
    inst = load(args.name)
    pid = runner.start(inst, wait=args.wait)
    print("gestartet, PID %d" % pid)
    if args.wait:
        print("Server bereit" if runner.server_ready(inst) else "noch nicht bereit")


def cmd_stop(args: argparse.Namespace) -> None:
    print(runner.stop(load(args.name), timeout=args.timeout))


def cmd_status(args: argparse.Namespace) -> None:
    info = runner.status(load(args.name))
    if args.json:
        print(json.dumps(info, indent=2, ensure_ascii=False))
        return
    from .i18n import t
    print("%-8s: %s" % (t("cli.status_instance"), info["name"]))
    print("%-8s: %s" % (t("cli.status_process"),
                        "PID %s" % info["pid"] if info["running"] else t("cli.off")))
    print("%-8s: %s" % (t("cli.status_ready"), t("cli.yes") if info["ready"] else t("cli.no")))
    if "rcon" in info:
        print("%-8s: %s" % (t("cli.status_rcon"), info["rcon"]))
    for line in info.get("players", []):  # type: ignore[union-attr]
        print("  %s" % line)
    print("%-8s: %s" % (t("cli.status_log"), info["last_log"]))


def cmd_logs(args: argparse.Namespace) -> None:
    inst = load(args.name)
    for line in runner.tail(inst.log_path, args.lines):
        print(line)


def cmd_rcon(args: argparse.Namespace) -> None:
    inst = load(args.name)
    with inst.control(timeout=15) as rc:
        print(rc.command(" ".join(args.command), timeout=20))


def cmd_update(args: argparse.Namespace) -> None:
    inst = load(args.name)
    if args.check:
        info = runner.check_update(inst)
        print("installiert : %s" % info["installed"])
        print("verfuegbar  : %s" % info["available"])
        print("aktuell     : %s" % ("ja" if info["up_to_date"] else "NEIN - Update verfuegbar"))
        sys.exit(0 if info["up_to_date"] else 3)
    result = runner.update_installed(
        inst, restart_after=not args.no_restart, validate_update=not args.no_validate
    )
    for step in result["steps"]:  # type: ignore[union-attr]
        print(step)
    sys.exit(0 if result["ok"] else 1)


def cmd_supervise(args: argparse.Namespace) -> None:
    import threading
    import time as _time

    from . import registry
    from .supervisor import Supervisor
    from .i18n import t

    if getattr(args, "all", False):
        names = registry.names()
        if not names:
            sys.exit("keine Instanzen konfiguriert")
        print("Supervisor fuer %d Instanzen: %s" % (len(names), ", ".join(names)), flush=True)
        for name in names:
            obj = registry.load(name)
            if obj:
                threading.Thread(target=Supervisor(obj, interval=args.interval).run,
                                 daemon=True).start()
        try:
            while True:
                _time.sleep(3600)
        except KeyboardInterrupt:
            return
    from .supervisor import Supervisor as _S
    inst = load(args.name)
    if args.restart_times is not None:
        inst.restart_times = [t.strip() for t in args.restart_times.split(",") if t.strip()]
        inst.save(conf_path(args.name))
    Supervisor(inst, interval=args.interval).run()


def cmd_lang(args: argparse.Namespace) -> None:
    """Sprache anzeigen oder setzen (de/en)."""
    from .i18n import lang, set_lang, t
    if not args.value:
        print(t("cli.lang_now", l=lang()))
        return
    try:
        print(t("cli.lang_set", l=set_lang(args.value)))
    except ValueError:
        sys.exit(t("cli.lang_bad"))


def cmd_url(args: argparse.Namespace) -> None:
    """Fertige Web-Adresse inklusive Token ausgeben."""
    from .i18n import t
    from .webui import TOKEN_PATH, token

    host = args.host
    try:
        from . import i18n as _i18n
        if _i18n.get("access", "") == "ip" and host in ("127.0.0.1", "localhost"):
            # direkter Zugriff: die IP zeigen, unter der der Server erreichbar ist
            import socket as _socket
            sock = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
            try:
                sock.connect(("1.1.1.1", 80))
                host = sock.getsockname()[0]
            finally:
                sock.close()
    except Exception:  # noqa: BLE001
        pass
    print("http://%s:%d/?token=%s" % (host, args.port, token()))
    dom = ""
    try:
        from . import i18n as _i18n
        dom = _i18n.domain()
    except Exception:  # noqa: BLE001
        dom = ""
    if dom:
        print("https://%s/?token=%s" % (dom, token()))
    if args.quiet:
        return
    print(t("cli.token_file", path=TOKEN_PATH), file=sys.stderr)
    import socket as _sock
    ip = ""
    try:
        _s = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
        _s.connect(("1.1.1.1", 80))
        ip = _s.getsockname()[0]
        _s.close()
    except OSError:
        ip = _sock.gethostname()
    print(t("cli.token_remote", host=ip), file=sys.stderr)


def cmd_open(args: argparse.Namespace) -> None:
    """Web-Adresse mit Token im Standardbrowser oeffnen."""
    import webbrowser
    from .webui import token
    url = "http://%s:%d/?token=%s" % (args.host, args.port, token())
    print(url)
    webbrowser.open(url)


def _lan_ip() -> str:
    """Erste LAN-Adresse des Rechners (ohne Docker-Bruecken)."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("1.1.1.1", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return ""


def cmd_proxy(args: argparse.Namespace) -> None:
    """nginx-Konfiguration fuer HTTPS erzeugen (und optional einrichten)."""
    from . import proxy
    from .i18n import t

    from . import i18n
    domain = args.domain or i18n.domain()
    if not domain:
        sys.exit(t("cli.domain_none"))
    auth_file = args.auth_file or ""
    text = proxy.render(domain, args.port, auth_file, tls=not args.no_tls)

    if not args.write:
        print(text)                                    # Konfiguration -> stdout (umleitbar)
        print(t("cli.proxy_next_steps", domain=domain, port=args.port), file=sys.stderr)
        return

    result = proxy.install(domain, args.port, auth_file, tls=not args.no_tls)
    if not result.get("ok"):
        sys.exit(t("cli.proxy_failed", err=result.get("error", "")))
    print(t("cli.proxy_written", file=result["file"]))
    if not args.no_tls and args.cert:
        got = proxy.enable_tls(domain, args.email or "")
        print(t("cli.proxy_cert_ok") if got.get("ok") else t("cli.proxy_cert_fail", out=got.get("out", "")))


def cmd_web(args: argparse.Namespace) -> None:
    from .i18n import t
    from .webui import serve, token
    cert = getattr(args, "tls_cert", "") or ""
    key = getattr(args, "tls_key", "") or ""
    local_only = args.host in ("127.0.0.1", "localhost")
    print("Token: %s" % token())
    if local_only:
        print("  %s http://127.0.0.1:%d/?token=%s" % (t("cli.url"), args.port, token()))
        print("  %s" % t("cli.tunnel_hint", port=args.port))
    else:
        ip = _lan_ip()
        print("  ! %s" % t("cli.exposed_warning", port=args.port))
        print("  %s http://127.0.0.1:%d/?token=%s" % (t("cli.url"), args.port, token()))
        if ip:
            print("  %s http://%s:%d/?token=%s" % (t("cli.url"), ip, args.port, token()))
    serve(host=args.host, port=args.port, cert=cert, key=key)


def cmd_version(args: argparse.Namespace) -> None:
    """Installierte Version und Stand auf GitHub anzeigen."""
    from . import selfupdate
    info = selfupdate.check(force=True)
    print("noah2games %s" % info.get("installed", "?"))
    if not info.get("ok"):
        print("  Pruefung fehlgeschlagen: %s" % info.get("error", ""))
        return
    if info.get("update"):
        from .selfupdate import _tuple
        newer = bool(info.get("available")) and _tuple(info["available"]) > _tuple(info["installed"])
        if newer:
            print("  verfuegbar: %s (GitHub %s)" % (info.get("available"), info.get("commit", "")))
        else:
            print("  neuer Stand verfuegbar (%s, installiert %s)"
                  % (info.get("commit", ""), info.get("local_commit", "") or "unbekannt"))
        print("  einspielen mit: noah2games self-update")
    else:
        print("  aktuell")


def cmd_self_update(args: argparse.Namespace) -> None:
    """noah2games selbst aktualisieren (Paket von GitHub ersetzen, Dienst neu starten)."""
    from . import selfupdate
    # ohne Cache pruefen: wer "self-update" tippt, will den echten Stand
    info = selfupdate.check(force=True)
    if not args.force and info.get("ok") and not info.get("update"):
        print("noah2games %s ist aktuell" % info.get("installed", "?"))
        return
    print("lade %s (installiert: %s)" % (info.get("available", "?"), info.get("installed", "?")))
    result = selfupdate.apply()
    if not result.get("ok"):
        sys.exit("Update fehlgeschlagen: %s" % result.get("error", ""))
    if result.get("from") == result.get("to"):
        print("aktualisiert: %s (neuer Stand, Commit %s)" % (result.get("to"), selfupdate.remote_commit()))
    else:
        print("aktualisiert: %s -> %s" % (result.get("from"), result.get("to")))
    print("Sicherung des alten Stands: %s" % result.get("backup"))
    restarted = selfupdate.restart_service()
    print("Dienst neu gestartet (%s)" % restarted.get("scope") if restarted.get("ok")
          else "Dienst nicht neu gestartet - bitte noah2games-web neu starten")


def cmd_install_unit(args: argparse.Namespace) -> None:
    """Supervisor-Dienst anlegen (Systemdienst als root, sonst User-Dienst)."""
    from . import units
    inst = load(args.name)
    result = units.install(inst)
    if not result.get("ok"):
        sys.exit("Dienst fehlgeschlagen: %s" % (result.get("error") or result.get("message")))
    print("Dienst eingerichtet: %s (%s)"
          % (result["path"], "Systemdienst" if result["system"] else "Benutzerdienst"))
    print("  systemctl %sstatus noah2games-%s" % ("" if result["system"] else "--user ", inst.name))


def cmd_wizard(args: argparse.Namespace) -> None:
    """Einrichtungsassistent: Instanz anlegen, Server holen, Dienst einrichten."""
    import shutil as _shutil

    from . import installer, registry
    from .i18n import t

    print("%s\n%s" % (t("wiz.intro"), "-" * 40))
    if not _shutil.which("wine"):
        print(t("wiz.wine_missing"))
        print("  Arch/CachyOS: sudo pacman -S wine   Debian/Ubuntu: sudo apt install wine")
    py_ok = sys.version_info >= (3, 10)
    print("Python %d.%d %s" % (sys.version_info.major, sys.version_info.minor,
                               "ok" if py_ok else "- zu alt, bitte 3.10+"))
    if not py_ok:
        sys.exit(1)

    name = args.name or input("Instanz-Name (nur intern) " + t("wiz.name", d="ark1") + " ").strip() or "ark1"
    if registry.load(name):
        sys.exit("Instanz '%s' existiert bereits" % name)

    print("\n" + t("wiz.maps"))
    for idx, (mid, label) in enumerate(registry.MAPS, 1):
        print("  %2d) %s" % (idx, label))
    choice = input(t("wiz.map", d=1) + " ").strip() or "1"
    try:
        map_id = registry.MAPS[int(choice) - 1][0]
    except (ValueError, IndexError):
        map_id = registry.MAPS[0][0]

    port_raw = input(t("wiz.port") + " ").strip()
    port = int(port_raw) if port_raw.isdigit() else None
    if port is not None and not (1024 <= port <= 65535):
        print("  " + t("wiz.port_bad", p=port))
        port = None
    session = input(t("wiz.session", d="Gameserver %s" % name) + " ").strip() or "Gameserver %s" % name

    inst = registry.create(name, map_id, port, session)
    inst.write_ini()
    print("\n" + t("wiz.created", n=name))
    print("  Verzeichnis: %s" % inst.directory)
    print("  Port: %d (Query %d) · RCON %d" % (inst.port, inst.query_port, inst.rcon_port))
    print("  RCON-Passwort: %s" % inst.rcon_password)

    if args.install or (input("\n" + t("wiz.download_q") + " ")
                        .strip().lower() in ("j", "y", "ja", "yes")):
        print(t("wiz.downloading"))
        result = installer.install_server(inst, log=lambda line: None)
        print(t("wiz.done", r=("ok" if result["ok"] else "failed"), l=result["log"]))

    if input(t("wiz.service_q") + " ").strip().lower() in ("j", "y", "ja", "ja", "yes"):
        unit = os.path.expanduser("~/.config/systemd/user")
        os.makedirs(unit, exist_ok=True)
        path = os.path.join(unit, "noah2games-%s.service" % name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("[Unit]\nDescription=noah2games (%s)\nAfter=network-online.target\n\n"
                     "[Service]\nType=simple\nWorkingDirectory=%s\n"
                     "ExecStart=%s -m noah2games supervise --all\nRestart=always\nRestartSec=15\n\n"
                     "[Install]\nWantedBy=default.target\n"
                     % (name, os.path.dirname(os.path.dirname(os.path.abspath(__file__))), sys.executable))
        print("Unit: %s" % path)
        print("  systemctl --user daemon-reload && systemctl --user enable --now noah2games-%s" % name)

    from .webui import token as _token
    print("\n" + t("wiz.web"))
    print("  noah2games web")
    print("  http://127.0.0.1:8790/?token=%s" % _token())


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="noah2games", description="noah2games - Multigame-Server-Manager (ARK Ascended/Evolved, Satisfactory, 7 Days to Die, Space Engineers)")
    p.add_argument("--name", default=None, help="Instanzname (default: test)")
    sub = p.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--name", default=argparse.SUPPRESS, help="Instanzname")

    pi = sub.add_parser("init", parents=[common], help="Konfiguration anlegen")
    pi.add_argument("--game", default="ark", choices=games.keys(),
                    help="Spielprofil der Instanz")
    pi.add_argument("--dir", default=os.path.expanduser("~/noah2games-instances"))
    pi.add_argument("--map", default="")
    pi.add_argument("--session", default="")
    pi.add_argument("--port", type=int, default=0)
    pi.add_argument("--rcon-port", type=int, default=0)
    pi.add_argument("--rcon-password", default="")
    pi.set_defaults(func=cmd_init)

    ps = sub.add_parser("start", parents=[common], help="Server starten")
    ps.add_argument("--wait", type=int, default=0, help="Sekunden auf Bereitschaft warten")
    ps.set_defaults(func=cmd_start)

    pt = sub.add_parser("stop", parents=[common], help="sauber beenden")
    pt.add_argument("--timeout", type=int, default=90)
    pt.set_defaults(func=cmd_stop)

    sub.add_parser("restart", parents=[common], help="stop + start").set_defaults(func=None)

    pst = sub.add_parser("status", parents=[common], help="Status anzeigen")
    pst.add_argument("--json", action="store_true")
    pst.set_defaults(func=cmd_status)

    pl = sub.add_parser("logs", parents=[common], help="Log-Ende anzeigen")
    pl.add_argument("-n", "--lines", type=int, default=25)
    pl.set_defaults(func=cmd_logs)

    pr = sub.add_parser("rcon", parents=[common], help="RCON-Befehl")
    pr.add_argument("command", nargs=argparse.REMAINDER)
    pr.set_defaults(func=cmd_rcon)

    pu = sub.add_parser("update", parents=[common], help="SteamCMD-Update")
    pu.add_argument("--no-validate", action="store_true")
    pu.add_argument("--check", action="store_true", help="nur pruefen, nichts installieren")
    pu.add_argument("--no-restart", action="store_true", help="nach dem Update nicht starten")
    pu.set_defaults(func=cmd_update)

    pv = sub.add_parser("supervise", parents=[common], help="Supervisor im Vordergrund")
    pv.add_argument("--interval", type=int, default=30)
    pv.add_argument("--restart-times", default=None, help="z.B. 05:00,17:00")
    pv.add_argument("--all", action="store_true", help="alle Instanzen ueberwachen")
    pv.set_defaults(func=cmd_supervise)

    pun = sub.add_parser("install-unit", parents=[common], help="systemd-User-Unit schreiben")
    pun.set_defaults(func=cmd_install_unit)

    pwz = sub.add_parser("wizard", parents=[common], help="Einrichtung mit Nachfragen")
    pwz.add_argument("--install", action="store_true", help="Serverdateien ohne Rueckfrage laden")
    pwz.set_defaults(func=cmd_wizard)

    po = sub.add_parser("open", parents=[common], help="Web-Oberflaeche im Browser oeffnen")
    po.add_argument("--host", default="127.0.0.1")
    po.add_argument("--port", type=int, default=8790)
    po.set_defaults(func=cmd_open)

    pv = sub.add_parser("version", parents=[common], help="Version und Update-Status anzeigen")
    pv.set_defaults(func=cmd_version)

    psu = sub.add_parser("self-update", parents=[common], help="noah2games selbst aktualisieren")
    psu.add_argument("--force", action="store_true", help="auch ohne neuere Version neu laden")
    psu.set_defaults(func=cmd_self_update)

    pl2 = sub.add_parser("lang", parents=[common], help="Sprache anzeigen/setzen (de|en)")
    pl2.add_argument("value", nargs="?", default=None)
    pl2.set_defaults(func=cmd_lang)

    pu2 = sub.add_parser("url", parents=[common], help="Web-Adresse mit Token anzeigen")
    pu2.add_argument("--quiet", action="store_true", help="nur die Adresse (fuer Skripte)")
    pu2.add_argument("--host", default="127.0.0.1")
    pu2.add_argument("--port", type=int, default=8790)
    pu2.set_defaults(func=cmd_url)

    pp = sub.add_parser("proxy", parents=[common],
                        help="nginx-Konfiguration fuer HTTPS erzeugen/einrichten")
    pp.add_argument("--domain", default="")
    pp.add_argument("--port", type=int, default=8790)
    pp.add_argument("--auth-file", default="", help="Pfad zur htpasswd-Datei (optional)")
    pp.add_argument("--no-tls", action="store_true", help="nur HTTP (z. B. hinter anderem Proxy)")
    pp.add_argument("--write", action="store_true", help="nach /etc/nginx schreiben und laden (root)")
    pp.add_argument("--cert", action="store_true", help="Zertifikat per certbot holen")
    pp.add_argument("--email", default="")
    pp.set_defaults(func=cmd_proxy)

    pw = sub.add_parser("web", parents=[common], help="Web-UI starten")
    pw.add_argument("--host", default="127.0.0.1")
    pw.add_argument("--port", type=int, default=8790)
    pw.add_argument("--tls-cert", dest="tls_cert", default="")
    pw.add_argument("--tls-key", dest="tls_key", default="")
    pw.set_defaults(func=cmd_web)

    args = p.parse_args(argv)
    if args.cmd != "wizard":
        args.name = getattr(args, "name", None) or "test"
    if args.cmd == "restart":
        inst = load(args.name)
        print("stop:", runner.stop(inst, timeout=90))
        print("start: PID %d" % runner.start(inst))
        return
    args.func(args)


if __name__ == "__main__":
    main()
