"""Source-RCON-Client (ASA/ASE) - reine stdlib, keine Abhaengigkeiten."""
from __future__ import annotations

import socket
import struct
import time

SERVERDATA_AUTH = 3
SERVERDATA_AUTH_RESPONSE = 2
SERVERDATA_EXECCOMMAND = 2
SERVERDATA_RESPONSE_VALUE = 0


class RconError(RuntimeError):
    pass


class RconClient:
    def __init__(self, host: str, port: int, password: str, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._req_id = 0

    # ---------------------------------------------------------------- intern
    def _next_id(self) -> int:
        self._req_id = (self._req_id + 1) % 0x7FFFFFFF
        return self._req_id

    def _send(self, req_id: int, pkt_type: int, body: str) -> None:
        assert self._sock is not None
        payload = struct.pack("<ii", req_id, pkt_type) + body.encode("utf-8") + b"\x00\x00"
        self._sock.sendall(struct.pack("<i", len(payload)) + payload)

    def _recv(self) -> tuple[int, int, str]:
        assert self._sock is not None
        head = self._read_exact(4)
        (size,) = struct.unpack("<i", head)
        if size < 8 or size > 1024 * 512:
            raise RconError("unplausible Paketgroesse: %r" % size)
        data = self._read_exact(size)
        req_id, pkt_type = struct.unpack("<ii", data[:8])
        body = data[8:].split(b"\x00", 1)[0].decode("utf-8", "replace")
        return req_id, pkt_type, body

    def _read_exact(self, n: int) -> bytes:
        assert self._sock is not None
        buf = b""
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise RconError("Verbindung vom Server geschlossen")
            buf += chunk
        return buf

    # ---------------------------------------------------------------- oeffentlich
    def connect(self) -> None:
        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self._sock.settimeout(self.timeout)
        auth_id = self._next_id()
        self._send(auth_id, SERVERDATA_AUTH, self.password)
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            try:
                req_id, pkt_type, _body = self._recv()
            except (socket.timeout, TimeoutError):
                continue
            if pkt_type == SERVERDATA_AUTH_RESPONSE:
                if req_id == -1:
                    raise RconError("RCON-Passwort falsch")
                if req_id == auth_id:
                    return
        raise RconError("keine Auth-Antwort (Server beschaeftigt?)")

    def command(self, cmd: str, timeout: float | None = None) -> str:
        if self._sock is None:
            self.connect()
        old = self._sock.gettimeout()
        if timeout:
            self._sock.settimeout(timeout)
        try:
            req_id = self._next_id()
            self._send(req_id, SERVERDATA_EXECCOMMAND, cmd)
            parts: list[str] = []
            deadline = time.time() + (timeout or self.timeout)
            while time.time() < deadline:
                try:
                    rid, ptype, body = self._recv()
                except (socket.timeout, TimeoutError):
                    break
                if ptype == SERVERDATA_RESPONSE_VALUE and rid == req_id:
                    parts.append(body)
                    # ASA schickt kein Endpaket; kurze Pause reicht
                    self._sock.settimeout(0.6)
                    continue
            return "".join(parts).strip()
        finally:
            if self._sock is not None:
                self._sock.settimeout(old)

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def __enter__(self) -> "RconClient":
        self.connect()
        return self

    def __exit__(self, *_exc) -> None:
        self.close()
