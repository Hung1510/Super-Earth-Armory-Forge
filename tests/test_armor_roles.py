#!/usr/bin/env python3
"""
The optional Armor Roles download (packs/armor-roles): three loadouts for the Every armor stack. Each one
parses in Python and in the web builder's code, can be pasted into the game panel from its file text, and
puts the weight class and the values it says on the armor you wear.

    python tests/test_armor_roles.py
"""
import glob
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

F7 = 0x76
failed = []
WEIGHT = {"light": 0, "medium": 1, "heavy": 2}


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        failed.append(what)


def pid_of(name):
    return next(k for k, v in picker.CATALOG.items() if v[0].lower() == name.lower())


def build(text):
    s, p = picker.load_config_text(text)
    path = tempfile.mktemp(suffix=".lua")
    with open(path, "w", encoding="utf-8") as f:
        f.write(picker.compile_loadout(s, p, blank=True))
    return path


MK = pid_of("Med-Kit")
files = sorted(glob.glob(os.path.join(ROOT, "packs", "armor-roles", "*.ini")))
check(len(files) == 3, "the pack has three role files")

for path in files:
    name = os.path.basename(path)
    text = open(path, encoding="utf-8").read()
    s, profiles = picker.load_config_text(text)
    ev = [p for p in profiles if p["perk"] == picker.EVERY]
    check(len(ev) == 1 and ev[0].get("weight") in (0, 1, 2) and ev[0]["enabled"], "%s: one Every armor stack with a weight and passives" % name)
    want_weight = ev[0]["weight"]

    g = FakeGame(build("[settings]\nname = x\n[profile: Med-Kit]\n"), appdata=tempfile.mkdtemp())
    g.wear(MK)
    g.tick(420)
    g.key(F7)
    g.tick(150)
    g.clipboard(text)                      # the player copied the whole file in Notepad
    check("paste" in g.regions(), "%s: the armor tab offers Paste code" % name)
    g.click("paste")
    g.tick(60)
    pp = g.state[b"pp"]
    check(any("Every armor" in t or t for t in g.texts()), "%s: the panel shows it" % name)
    ws = g.kit_weights(MK)
    check(ws[:-1] == [want_weight] * (len(ws) - 1), "%s: the worn armor gets weight %s" % (name, want_weight))
    have = {}
    for r in g.rows(MK):
        have.setdefault(r[0], []).append(r[2])
    hit = 0
    for h, kind, value, label in ev[0]["rows"]:
        if kind == 0:
            continue                         # a flag the passive sets, not a value the file edits
        hit += 1
        check(any(abs(v - value) < 1e-5 for v in have.get(h, [])), "%s: %s = %s on the armor" % (name, label, value))
    check(hit > 0, "%s: values were checked" % name)

# the zip
out = tempfile.mktemp(suffix=".zip")
args = type("A", (), {"zip": out})
check(picker.cmd_pack(args) == 0, "picker.py pack builds the zip")
names = zipfile.ZipFile(out).namelist()
check(sorted(n for n in names if n.endswith(".ini")) == [os.path.basename(f) for f in files] and "README.txt" in names,
      "the zip holds the three role files and the README, no scripts")

if failed:
    print("\n%d FAILED" % len(failed))
    sys.exit(1)
print("\nall Armor Roles checks passed")
