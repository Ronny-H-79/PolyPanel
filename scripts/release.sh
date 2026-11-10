#!/usr/bin/env bash
# noah2games release: Version setzen, committen, taggen, pushen.
#
#   ./scripts/release.sh 0.2.9            Version + Tag + Push
#   ./scripts/release.sh 0.2.9 --release  zusaetzlich GitHub-Release anlegen (braucht gh)
#
# Der Tag zeigt auf den Commit, der die Version einfuehrt - so bleibt jede
# Aenderung einem Stand zuordenbar.
set -euo pipefail

VERSION="${1:?Version angeben, z.B. 0.2.9}"
DO_RELEASE="${2:-}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Format: MAJOR.MINOR.PATCH (z.B. 0.2.9)" >&2
  exit 1
fi

if [ -n "$(git status --porcelain)" ] && [ "${FORCE:-0}" != "1" ]; then
  echo "Arbeitsverzeichnis ist nicht sauber - bitte erst committen (oder FORCE=1)." >&2
  git status --short >&2
  exit 1
fi

python3 - "$VERSION" <<'PY'
import re, sys
path = "noah2games/__init__.py"
version = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    text = fh.read()
text = re.sub(r'__version__ = "[^"]*"', '__version__ = "%s"' % version, text)
with open(path, "w", encoding="utf-8") as fh:
    fh.write(text)
print("Version gesetzt:", version)
PY

git add noah2games/__init__.py
git commit -q -m "release: $VERSION"
git tag -a "v$VERSION" -m "noah2games $VERSION"
git push origin main
git push origin "v$VERSION"
echo "Tag v$VERSION gepusht"

if [ "$DO_RELEASE" = "--release" ]; then
  if command -v gh >/dev/null 2>&1; then
    gh release create "v$VERSION" --title "noah2games $VERSION" --generate-notes
    echo "GitHub-Release angelegt"
  else
    echo "gh ist nicht installiert - Release bitte im Browser anlegen:"
    echo "  https://github.com/Ronny-H-79/Noah2Games/releases/new?tag=v$VERSION"
  fi
fi
