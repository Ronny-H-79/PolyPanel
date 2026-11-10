"""Reverse-Proxy-Unterstuetzung: nginx-Konfiguration erzeugen und einrichten.

PolyPanel selbst hoert nur auf 127.0.0.1. Fuer Zugriff aus dem Netz kommt nginx davor -
mit HTTPS, optionaler Basic-Auth und Zeiteinstellungen, die zu Snapshots/Backups passen.
"""
from __future__ import annotations

import os
import shutil
import subprocess

AVAILABLE = "/etc/nginx/sites-available"
ENABLED = "/etc/nginx/sites-enabled"
CERT_DIR = "/etc/letsencrypt/live"


def cert_paths(domain: str) -> tuple[str, str]:
    base = os.path.join(CERT_DIR, domain)
    return os.path.join(base, "fullchain.pem"), os.path.join(base, "privkey.pem")


def render(domain: str, port: int = 8790, auth_file: str = "", tls: bool = True) -> str:
    """nginx-Serverblock als Text."""
    fullchain, privkey = cert_paths(domain)
    auth = ""
    if auth_file:
        auth = ('        auth_basic "PolyPanel";\n'
                '        auth_basic_user_file %s;\n' % auth_file)

    if not tls:
        return """# PolyPanel - generiert von `PolyPanel proxy`
server {{
    listen 80;
    server_name {domain};

    client_max_body_size 32m;

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
        proxy_buffering off;
        access_log off;
{auth}    }}
}}
""".format(domain=domain, port=port, auth=auth)

    return """# PolyPanel - generiert von `PolyPanel proxy`
server {{
    listen 80;
    server_name {domain};

    location /.well-known/acme-challenge/ {{ root /var/www/html; }}
    location / {{ return 301 https://$host$request_uri; }}
}}

server {{
    listen 443 ssl;
    http2 on;
    server_name {domain};

    ssl_certificate     {fullchain};
    ssl_certificate_key {privkey};
    ssl_protocols       TLSv1.2 TLSv1.3;

    client_max_body_size 32m;

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
        proxy_buffering off;
        access_log off;
{auth}    }}
}}
""".format(domain=domain, port=port, auth=auth, fullchain=fullchain, privkey=privkey)


def nginx_bin() -> str:
    return shutil.which("nginx") or ""


def test_config(path: str) -> tuple[bool, str]:
    """nginx -t gegen die neue Datei (nur wenn nginx installiert ist)."""
    binary = nginx_bin()
    if not binary:
        return False, "nginx nicht gefunden"
    tmp = "/etc/nginx/nginx.conf"
    result = subprocess.run([binary, "-t"], capture_output=True, text=True)
    ok = result.returncode == 0
    return ok, (result.stderr or result.stdout).strip()


def install(domain: str, port: int = 8790, auth_file: str = "", tls: bool = True) -> dict:
    """Config schreiben, aktivieren, pruefen, nginx neu laden."""
    if os.geteuid() != 0:
        return {"ok": False, "error": "root noetig (sudo PolyPanel proxy --write …)"}
    if not nginx_bin():
        return {"ok": False, "error": "nginx ist nicht installiert"}
    if not os.path.isdir(AVAILABLE):
        return {"ok": False, "error": "%s fehlt" % AVAILABLE}

    target = os.path.join(AVAILABLE, "PolyPanel-%s.conf" % domain)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(render(domain, port, auth_file, tls))
    link = os.path.join(ENABLED, "PolyPanel-%s.conf" % domain)
    if not os.path.lexists(link):
        os.symlink(target, link)

    ok, msg = test_config(target)
    if not ok:
        os.remove(link)
        os.remove(target)
        return {"ok": False, "error": "nginx -t schlug fehl: %s" % msg}

    reload = subprocess.run(["systemctl", "reload", "nginx"], capture_output=True, text=True)
    if reload.returncode != 0:                      # z. B. Container ohne systemd
        reload = subprocess.run([nginx_bin(), "-s", "reload"], capture_output=True, text=True)
    return {"ok": reload.returncode == 0, "file": target,
            "reload": (reload.stderr or reload.stdout).strip() or "nginx neu geladen"}


def enable_tls(domain: str, email: str = "") -> dict:
    """Zertifikat per certbot holen (nginx-Modus)."""
    binary = shutil.which("certbot")
    if not binary:
        return {"ok": False, "error": "certbot nicht installiert (z. B. apt install certbot python3-certbot-nginx)"}
    cmd = [binary, "--nginx", "-d", domain, "--non-interactive", "--agree-tos",
           "--redirect", "--keep-until-expiring"]
    cmd += ["-m", email] if email else ["--register-unsafely-without-email"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return {"ok": res.returncode == 0, "out": (res.stdout or res.stderr).strip()[-400:]}
