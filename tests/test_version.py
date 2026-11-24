"""Update-Entscheidung: niemals ein Rueckschritt anbieten."""
from __future__ import annotations

import unittest

from polypanel.selfupdate import _tuple, entscheide


class VersionTest(unittest.TestCase):
    def test_sortierung_nach_zahlen(self) -> None:
        self.assertLess(_tuple("0.9"), _tuple("0.10"))
        self.assertEqual(_tuple("0.30"), (0, 30, 0))

    def test_github_neuer(self) -> None:
        update, available, ahead = entscheide("0.30", "0.31", "neu123", "alt456")
        self.assertTrue(update)
        self.assertEqual(available, "0.31")
        self.assertFalse(ahead)

    def test_installiert_neuer_kein_downgrade(self) -> None:
        update, available, ahead = entscheide("0.31", "0.30", "abc", "abc")
        self.assertFalse(update)
        self.assertEqual(available, "0.31")
        self.assertTrue(ahead)

    def test_gleiche_version_anderer_commit(self) -> None:
        update, _, ahead = entscheide("0.30", "0.30", "bbb", "aaa")
        self.assertTrue(update)
        self.assertFalse(ahead)

    def test_gleiche_version_gleicher_commit(self) -> None:
        update, _, _ = entscheide("0.30", "0.30", "aaa", "aaa")
        self.assertFalse(update)

    def test_ohne_gegenstelle(self) -> None:
        update, available, ahead = entscheide("0.30", "", "", "")
        self.assertFalse(update)
        self.assertEqual(available, "")
        self.assertFalse(ahead)


if __name__ == "__main__":
    unittest.main()
