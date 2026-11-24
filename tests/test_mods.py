"""Mod-Reihenfolge und Anpinnen."""
from __future__ import annotations

import tempfile
import unittest

from polypanel import mods as modlib
from polypanel.instance import Instance


class ModsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.inst = Instance(name="Probe", directory=self.tmp.name, mods=[111, 222, 333])
        self.inst.ark_write_ini()   # Game.ini anlegen; Mod-Funktionen aendern nur eine bestehende Datei

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _aktiv(self) -> list[int]:
        return self.inst.mods

    def test_anpinnen_setzt_nach_vorn(self) -> None:
        modlib.set_pinned(self.inst, "333", True)
        self.assertEqual(self._aktiv()[0], 333)
        self.assertIn(333, self.inst.mods_pinned)

    def test_pin_loesen(self) -> None:
        modlib.set_pinned(self.inst, "333", True)
        modlib.set_pinned(self.inst, "333", False)
        self.assertNotIn(333, self.inst.mods_pinned)

    def test_verschieben(self) -> None:
        modlib.move(self.inst, "222", -1)
        self.assertEqual(self._aktiv()[:2], [222, 111])

    def test_reihenfolge_wird_geschrieben(self) -> None:
        modlib.reorder(self.inst, ["333", "111", "222"])
        self.assertEqual(self._aktiv(), [333, 111, 222])
        with open(self.inst.game_ini, encoding="utf-8") as fh:
            self.assertIn("ActiveMods=333,111,222", fh.read())

    def test_pins_bleiben_vorn_beim_sortieren(self) -> None:
        modlib.set_pinned(self.inst, "222", True)
        modlib.reorder(self.inst, ["111", "333", "222"])
        self.assertEqual(self._aktiv()[0], 222)


if __name__ == "__main__":
    unittest.main()
