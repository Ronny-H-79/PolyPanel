"""Rauchtest: der Webserver startet, schuetzt sich und beantwortet die Kernrouten."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request


def freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class WebTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.port = freier_port()
        umgebung = dict(os.environ)
        umgebung["POLYPANEL_CONFIG"] = cls.tmp.name
        umgebung.pop("PYTHONPATH", None)
        cls.proc = subprocess.Popen(
            [sys.executable, "-m", "polypanel", "web", "--port", str(cls.port)],
            env=umgebung, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.token = ""
        pfad = os.path.join(cls.tmp.name, "token")
        for _ in range(120):
            time.sleep(0.1)
            if os.path.exists(pfad):
                with open(pfad, encoding="utf-8") as fh:
                    cls.token = fh.read().strip()
                break
        if not cls.token:
            cls.tearDownClass()
            raise unittest.SkipTest("Server ist nicht gestartet")

    @classmethod
    def tearDownClass(cls) -> None:
        proc = getattr(cls, "proc", None)
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        tmp = getattr(cls, "tmp", None)
        if tmp:
            tmp.cleanup()

    def hole(self, pfad: str, methode: str = "GET", daten: bytes | None = None) -> tuple[int, str]:
        url = "http://127.0.0.1:%d%s%s%s" % (self.port, pfad,
                                             "&" if "?" in pfad else "?", "token=" + self.token)
        req = urllib.request.Request(url, method=methode, data=daten)
        try:
            with urllib.request.urlopen(req, timeout=15) as antwort:
                return antwort.status, antwort.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", "replace")

    def test_ohne_token_gesperrt(self) -> None:
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/api/instances" % self.port, timeout=10)
            self.fail("ohne Token muss 401 kommen")
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 401)

    def test_startseite_kommt(self) -> None:
        status, text = self.hole("/")
        self.assertEqual(status, 200)
        self.assertIn("<html", text.lower())

    def test_instanzliste_ist_json(self) -> None:
        status, text = self.hole("/api/instances")
        self.assertEqual(status, 200)
        self.assertIsInstance(json.loads(text), list)

    def test_hostwerte(self) -> None:
        status, text = self.hole("/api/host")
        self.assertEqual(status, 200)
        self.assertIn("cpu", json.loads(text))

    def test_instanz_anlegen_und_finden(self) -> None:
        status, text = self.hole("/api/instances?name=Rauch&map=Ragnarok_WP&port=%d" % freier_port(),
                                 methode="POST", daten=b"")
        self.assertEqual(status, 200, text)
        self.assertIn("Rauch", text)
        status, text = self.hole("/api/config?name=Rauch&file=game")
        self.assertEqual(status, 200)
        self.assertIn("ActiveMods", text)

    def test_unbekannte_route(self) -> None:
        status, _ = self.hole("/api/gibtsnicht")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
