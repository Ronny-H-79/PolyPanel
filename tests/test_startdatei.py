"""Startdatei: mit AsaApi der Loader, mit Rueckfall der Server selbst."""
from __future__ import annotations

import os
import tempfile
import unittest

from polypanel.instance import Instance


class StartdateiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.win64 = os.path.join(self.tmp.name, "ShooterGame", "Binaries", "Win64", "ArkApi")
        os.makedirs(self.win64, exist_ok=True)
        for name in ("AsaApiLoader.exe",):
            open(os.path.join(self.win64, name), "w").close()
        self.inst = Instance(name="Probe", directory=self.tmp.name, game="ark")
        open(os.path.join(self.tmp.name, "ShooterGame", "Binaries", "Win64",
                          "ArkAscendedServer.exe"), "w").close()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_ohne_asaapi_server(self) -> None:
        self.assertEqual(os.path.basename(self.inst.exe), "ArkAscendedServer.exe")

    def test_mit_asaapi_loader(self) -> None:
        self.inst.asaapi = True
        self.assertEqual(os.path.basename(self.inst.exe), "AsaApiLoader.exe")

    def test_rueckfall_startet_server(self) -> None:
        self.inst.asaapi = True
        self.inst.asaapi_fallback = True
        self.assertEqual(os.path.basename(self.inst.exe), "ArkAscendedServer.exe")


if __name__ == "__main__":
    unittest.main()
