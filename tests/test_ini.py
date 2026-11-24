"""Prueft die Ini-Behandlung: eigene Zeilen, Doppel-Schluessel, CRLF, ActiveMods."""
from __future__ import annotations

import os
import tempfile
import unittest

from polypanel.instance import Instance, _update_key

GAME_INI = (
    "[/script/shootergame.shootergamemode]\r\n"
    "; eigene Notiz bleibt stehen\r\n"
    "EngramEntryAutoUnlocks=(EngramClassName=\"EngramEntry_Torch_C\",bAutoUnlock=True)\r\n"
    "EngramEntryAutoUnlocks=(EngramClassName=\"EngramEntry_Campfire_C\",bAutoUnlock=True)\r\n"
    "ConfigOverrideItemMaxQuantity=(ItemClassString=\"PrimalItemResource_Stone_C\",Quantity=(MaxItemQuantity=500,bIgnoreMultiplier=True))\r\n"
    "ConfigOverrideItemMaxQuantity=(ItemClassString=\"PrimalItemResource_Wood_C\",Quantity=(MaxItemQuantity=500,bIgnoreMultiplier=True))\r\n"
    "ActiveMods=1376189\r\n"
    "\r\n"
    "[/script/shootergame.shootergameusersettings]\r\n"
    "ServerPVE=True\r\n"
    "DifficultyOffset=4\r\n"
    "CustomAdminSetting=42\r\n"
)


class IniTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.pfad = os.path.join(self.tmp.name, "Game.ini")
        with open(self.pfad, "wb") as fh:
            fh.write(GAME_INI.encode())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _lies(self) -> bytes:
        with open(self.pfad, "rb") as fh:
            return fh.read()

    def test_doppelte_schluessel_bleiben(self) -> None:
        _update_key(self.pfad, "/script/shootergame.shootergamemode", "ActiveMods", "1,2,3")
        text = self._lies().decode()
        self.assertEqual(text.count("EngramEntryAutoUnlocks="), 2)
        self.assertEqual(text.count("ConfigOverrideItemMaxQuantity="), 2)

    def test_eigene_zeilen_bleiben(self) -> None:
        _update_key(self.pfad, "/script/shootergame.shootergamemode", "ActiveMods", "1")
        text = self._lies().decode()
        self.assertIn("; eigene Notiz bleibt stehen", text)
        self.assertIn("CustomAdminSetting=42", text)
        self.assertIn("ServerPVE=True", text)

    def test_wert_wird_ersetzt_nicht_gedoppelt(self) -> None:
        _update_key(self.pfad, "/script/shootergame.shootergamemode", "ActiveMods", "11,22")
        text = self._lies().decode()
        self.assertEqual(text.count("ActiveMods="), 1)
        self.assertIn("ActiveMods=11,22", text)

    def test_crlf_bleibt(self) -> None:
        _update_key(self.pfad, "/script/shootergame.shootergamemode", "ActiveMods", "5")
        roh = self._lies()
        self.assertEqual(roh.count(b"\n"), roh.count(b"\r\n"), "CRLF muss erhalten bleiben")

    def test_zweiter_lauf_ist_idempotent(self) -> None:
        _update_key(self.pfad, "/script/shootergame.shootergamemode", "ActiveMods", "7,8")
        erst = self._lies()
        _update_key(self.pfad, "/script/shootergame.shootergamemode", "ActiveMods", "7,8")
        self.assertEqual(erst, self._lies())


class WriteIniTest(unittest.TestCase):
    def test_instanz_schreibt_ports_und_mods(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inst = Instance(name="Probe", directory=tmp, game="ark", port=7801, rcon_port=27030,
                            mods=[931877, 912815])
            inst.ark_write_ini()
            with open(inst.gus_ini, encoding="utf-8") as fh:
                gus = fh.read()
            self.assertIn("Port=7801", gus)
            self.assertIn("RCONPort=27030", gus)
            with open(inst.game_ini, encoding="utf-8") as fh:
                game = fh.read()
            self.assertIn("ActiveMods=931877,912815", game)
            # zweiter Lauf aendert nichts
            inst.ark_write_ini()
            with open(inst.game_ini, encoding="utf-8") as fh:
                self.assertIn("ActiveMods=931877,912815", fh.read())


if __name__ == "__main__":
    unittest.main()
