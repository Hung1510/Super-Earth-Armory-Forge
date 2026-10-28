#!/usr/bin/env python3
"""
Release notes for a tag, from CHANGELOG.md (used by .github/workflows/release.yml).

    python tools/release_notes.py v5.4 > notes.md
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FOOTER = """
### Downloads
| File | Where it's for | What it does |
|---|---|---|
| `Super-Earth-Armory-Forge-v{v}.zip` | GitHub, AyakaMods | **Full edition:** stack any armor passives onto your armor and set every value, live in game (F7) |
| `Super-Earth-Armory-Forge-Armor-Only-v{v}.zip` | GitHub, AyakaMods | **Armor Only edition:** the full edition without the stratagem presets, so nothing of them is loaded or run |
| `Super-Earth-Armory-Forge-HellForge-v{v}.zip` | HellForge | **HellForge edition:** the full edition in the layout HellForge mods use; import this one in HellForge, not the plain zip |
| `Super-Earth-Armory-Forge-Offline-Editor-v{v}.zip` | GitHub, AyakaMods | **Offline Editor (optional):** a Windows window to edit and validate `loadout.ini` as text; needs Python 3.10+, not part of the mod |
| `Super-Earth-Armory-Forge-Offline-Editor-v{v}.exe` | GitHub | The same Offline Editor as one Windows program, built by GitHub from the source in this release (no Python needed) |

Install one edition with Arsenal (or any HD2 mod manager), or the HellForge zip in HellForge; all need **Bingus Shared Loader**. Start the game and press **F7**.
Single-player / private lobbies only.
"""


def notes(tag):
    version = tag.lstrip("vV")
    # a tag on the wrong commit (e.g. pushed from a clone that wasn't pulled) builds old code
    # under the new number: refuse it
    picker = open(os.path.join(ROOT, "tools", "picker.py"), encoding="utf-8").read()
    built = re.search(r'^VERSION = "([^"]+)"', picker, re.M).group(1)
    if built != version:
        sys.exit("tag %s is on a commit whose tools/picker.py says VERSION %s: pull, then tag the latest main" % (tag, built))
    text = open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    m = re.search(r"^## %s\b[^\n]*\n(.*?)(?=^## |\Z)" % re.escape(version), text, re.S | re.M)
    if not m:
        sys.exit("CHANGELOG.md has no '## %s' section" % version)
    body = m.group(1).strip()
    return "## What's new in %s\n\n%s\n%s" % (version, body, FOOTER.replace("{v}", version))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.stdout.write(notes(sys.argv[1]))
