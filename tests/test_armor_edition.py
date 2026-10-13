#!/usr/bin/env python3
"""
Armor Only edition: the full edition without the stratagem presets.

    python tests/test_armor_edition.py

1. No Stratagems tab, no On/Off switch on the Keys tab, and the stratagem key (F10) does nothing.
2. The rest of the full edition is still there: stacking and values on an armor tab.
3. The release zip: its own README, no scripts, the same mod id as the full edition (install one).
"""
import json
import os
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import picker  # noqa: E402
from harness import FakeGame  # noqa: E402

F7, F10 = 0x76, 0x79
failed = []


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        failed.append(what)


settings, _ = picker.load_config_text("[settings]\nname = %s\n[profile: Med-Kit]\n" % picker.TITLE)
lua_path = tempfile.mktemp(suffix=".lua")
with open(lua_path, "w", encoding="utf-8") as f:
    f.write(picker.compile_loadout(settings, [], blank=True, no_strat=True))

g = FakeGame(lua_path, appdata=tempfile.mkdtemp())
g.tick(420)
g.key(F7)
g.tick(120)
check("strat" not in g.regions(), "no Stratagems tab")
g.click("settings")
g.tick(10)
check("stratfeat:on" not in g.regions() and "stratfeat:off" not in g.regions(), "no stratagem On / Off on the Keys tab")
check("skey" not in " ".join(str(r) for r in g.regions()), "no stratagem key picker")
g.key(F10)
g.tick(30)
check("strat" not in g.regions(), "the stratagem key does nothing")
g.click("add")
g.tick(10)
check(any(str(r).startswith("addpick:") for r in g.regions()), "the full edition's + Armor picker is still there")

zip_path = tempfile.mktemp(suffix=".zip")
args = type("A", (), {"edition": "armor", "zip": zip_path, "presets": os.path.join(ROOT, "presets")})()
check(picker.cmd_release(args) == 0, "the Armor Only zip builds")
z = zipfile.ZipFile(zip_path)
names = z.namelist()
m = json.loads(z.read("manifest.json"))
check("Armor Only" in m["Name"] and picker.VERSION in m["Name"], "its name says Armor Only and the version")
check(not any(n.endswith((".py", ".lua")) for n in names), "no scripts in the zip")
check("README.txt" in names and b"stratagem" in z.read("README.txt").lower(), "it has its own README")
full = tempfile.mktemp(suffix=".zip")
picker.cmd_release(type("A", (), {"edition": "full", "zip": full, "presets": os.path.join(ROOT, "presets")})())
check(json.loads(zipfile.ZipFile(full).read("manifest.json"))["Guid"] == m["Guid"], "same mod id as the full edition (install one)")
if failed:
    print("\n%d FAILED" % len(failed))
    sys.exit(1)
print("\nall Armor Only checks passed")
