# Mitarbeiten

Fehler und Wünsche am besten als Issue, mit Logauszug und der Version aus dem Kopf der Oberfläche.

Vor einem Pull Request:

```bash
python3 -m unittest discover -s tests -t .
ruff check .
python3 tools/check_texts.py
```

Die Tests brauchen nur Python. Ruff holst du mit `pip install ruff`. Die CI läuft dieselben drei
Schritte auf Python 3.10, 3.12 und 3.13.

`Game.ini` und `GameUserSettings.ini` bitte zeilenweise ändern (`_update_key`). Ein Parser schreibt
die Datei neu und wirft dabei Kommentare und doppelte Schlüssel weg. Genau das hat im Betrieb schon
einmal eine eingerichtete Ini zerlegt.

Tokens und Passwörter gehören nicht ins Repo, sie liegen unter `~/.config/polypanel/token`.

Wer Texte anfasst, zieht den Eintrag in `CHANGELOG.md` und `CHANGELOG.en.md` nach.

Ein Thema pro Commit, Betreff kurz halten (`fix: ...`, `feat: ...`).
