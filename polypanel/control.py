"""Steuerkanaele fuer Spiele ohne Source-RCON - reine Standardbibliothek.

Der Kern ruft in allen Spielen `inst.control()` auf und bekommt ein Objekt mit
`command(text)` (+ Kontextmanager). Welche Leitung dahinter steckt, entscheidet
das Spielprofil:

* ARK ASA/ASE  -> Source-RCON (`PolyPanel.rcon.RconClient`)
* 7 Days to Die -> Telnet (`TelnetClient`)
* Satisfactory  -> HTTPS-API (`SatisfactoryApi`)
"""
from __future__ import annotations

import json
import re
import socket
import ssl
import time
import urllib.error
import urllib.request


class ControlError(RuntimeError):
    pass


# --------------------------------------------------------------------- Telnet
class TelnetClient:
    """Minimaler Telnet-Client fuer den 7-Days-to-Die-Dedicated-Server.

    Der Server schickt beim Verbinden einen Banner und fragt nach dem Passwort
    (Feld `TelnetPassword` in der serverconfig.xml). Danach nimmt er Befehle
    zeilenweise entgegen (`say`, `lp`, `save`, ...).
    """

    def __init__(self, host: str, port: int, password: str, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self._sock: socket.socket | None = None

    def _read_until(self, markers: tuple[str, ...], deadline: float) -> str:
        assert self._sock is not None
        buf = ""
        while time.time() < deadline:
            try:
                chunk = self._sock.recv(4096)
            except (socket.timeout, TimeoutError):
                break
            if not chunk:
                break
            buf += chunk.decode("utf-8", "replace")
            low = buf.lower()
            if any(m.lower() in low for m in markers):
                break
        return buf

    def connect(self) -> None:
        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self._sock.settimeout(1.0)
        banner = self._read_until(("password:", "logon successful"), time.time() + self.timeout)
        if "password:" in banner.lower():
            if not self.password:
                raise ControlError("Telnet-Passwort fehlt (TelnetPassword in der serverconfig.xml)")
            self._sock.sendall((self.password + "\r\n").encode())
            answer = self._read_until(("logon successful", "password incorrect"), time.time() + self.timeout)
            if "incorrect" in answer.lower() or "logon successful" not in answer.lower():
                raise ControlError("Telnet-Passwort falsch")

    def command(self, cmd: str, timeout: float | None = None) -> str:
        if self._sock is None:
            self.connect()
        assert self._sock is not None
        wait = timeout or self.timeout
        try:
            self._sock.sendall((cmd + "\r\n").encode())
        except OSError as exc:
            raise ControlError("Telnet-Senden fehlgeschlagen: %s" % exc) from exc
        # Antwort vollstaendig abholen: der Server schickt zuerst eine Log-Zeile, dann das
        # Ergebnis (bei `lp` z. B. alle Spieler plus "Total of N in the game"). Nach der ersten
        # Zeile abzubrechen liefert nur das Echo - deshalb lesen, bis 0,4 s lang nichts mehr kommt.
        ende = time.time() + wait
        buf = ""
        try:
            self._sock.settimeout(0.4)
        except OSError:
            pass
        while time.time() < ende:
            try:
                chunk = self._sock.recv(4096)
            except (socket.timeout, TimeoutError):
                if buf.strip():
                    break
                continue
            except OSError:
                break
            if not chunk:
                break
            buf += chunk.decode("utf-8", "replace")
        # Log-Zeilen des Servers gehoeren nicht zur Antwort
        zeilen = [z for z in buf.splitlines()
                  if " Executing command " not in z and " Telnet connection " not in z
                  and " Started thread " not in z and " Exited thread " not in z]
        return "\n".join(zeilen).strip()

    def close(self) -> None:
        if self._sock is not None:
            # sauber abmelden, sonst protokolliert 7D2D "socket has been shut down"
            try:
                self._sock.sendall(b"exit\r\n")
                self._sock.shutdown(1)          # SHUT_WR: dem Server das Ende mitteilen
            except OSError:
                pass
            try:
                self._sock.close()
            finally:
                self._sock = None

    def __enter__(self) -> "TelnetClient":
        self.connect()
        return self

    def __exit__(self, *_exc) -> None:
        self.close()


# ------------------------------------------------------------------- HTTPS-API
class SatisfactoryApi:
    """Satisfactory Dedicated Server API (v1), selbstsigniertes Zertifikat.

    Token steht als `ServerApiToken` in der ServerSettings.ini; ohne Token
    laesst der Server nur `HealthCheck`/`QueryServerState` zu.
    """

    def __init__(self, host: str, port: int, token: str = "", timeout: float = 10.0,
                 path: str = "/api/v1"):
        self.base = "https://%s:%d%s" % (host, port, path)
        self.token = token
        self.timeout = timeout

    def _post(self, function: str, data: dict | None = None) -> dict:
        body = json.dumps({"function": function, "data": data or {}}).encode()
        req = urllib.request.Request(self.base, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        if self.token:
            req.add_header("Authorization", "Bearer " + self.token)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as resp:
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            raise ControlError("API HTTP %s: %s" % (exc.code, exc.read()[:200])) from exc
        except (urllib.error.URLError, OSError) as exc:
            raise ControlError("API nicht erreichbar: %s" % exc) from exc
        try:
            payload = json.loads(raw)
        except ValueError:
            return {"raw": raw}
        if isinstance(payload, dict) and payload.get("errorCode"):
            raise ControlError("%s: %s" % (payload.get("errorCode"), payload.get("errorMessage")))
        return payload.get("data", payload)

    # ------------------------------------------------------------ oeffentlich
    def connect(self) -> None:
        """HealthCheck - wirft, wenn der Server nicht antwortet."""
        # neuere Server verlangen clientCustomData, sonst "missing_params"
        self._post("HealthCheck", {"clientCustomData": ""})

    def command(self, cmd: str, timeout: float | None = None) -> str:
        """Befehl ueber `RunCommand` (z. B. `server say Hallo`)."""
        old = self.timeout
        if timeout:
            self.timeout = timeout
        try:
            res = self._post("RunCommand", {"command": cmd})
        finally:
            self.timeout = old
        if isinstance(res, dict):
            return str(res.get("commandResult") or res.get("result") or json.dumps(res))
        return str(res)

    def state(self) -> dict:
        return self._post("QueryServerState") or {}

    def players(self) -> list[dict]:
        state = self.state()
        return ((state.get("serverGameState") or {}).get("playerList") or [])

    def shutdown(self, force: bool = False) -> str:
        return str(self._post("Shutdown", {"Force": bool(force)}))

    def close(self) -> None:
        return None

    def __enter__(self) -> "SatisfactoryApi":
        self.connect()
        return self

    def __exit__(self, *_exc) -> None:
        self.close()
