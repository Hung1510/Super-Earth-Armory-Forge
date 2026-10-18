#!/usr/bin/env python3
"""
Randomize (full and Armor Only editions): the Presets tab has a Randomize button. It builds a whole random
loadout (random stacks, values and weight classes for every armor passive), applies it, and saves it as a
preset ("Random 1", ...). Ctrl+Z / Undo brings the old stacks back. The Passive Swap edition has no such button.

    python tests/test_randomize.py
"""
import glob
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import picker  # noqa: E402
from harness import FakeGame  # noqa: E402

F7 = 0x76
failed = []


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        failed.append(what)


def f32(v):
    return struct.unpack("<f", struct.pack("<f", v))[0]


def build(text="[settings]\nname = x\n[profile: Med-Kit]\n", **kw):
    s, p = picker.load_config_text(text)
    path = tempfile.mktemp(suffix=".lua")
    with open(path, "w", encoding="utf-8") as f:
        f.write(picker.compile_loadout(s, p, **kw))
    return path


def live_matches(g, text):
    _, profs = picker.load_config_text(text)
    for p in profs:
        _, rows, stats = picker.CATALOG[p["perk"]]
        over = {(m, t): f32(v) for m, t, v, _ in p["overrides"]}
        want = [(m, t, over.get((m, t), f32(v))) for m, t, v in rows]
        seen = set(want)
        for m, t, v, _ in p["rows"]:
            r = (m, t, f32(v))
            if r not in seen:
                seen.add(r)
                want.append(r)
        if [(m, t, v) for m, t, v, _ in g.rows(p["perk"])] != want:
            return False
    return True


ad = tempfile.mkdtemp()
g = FakeGame(build(), appdata=ad)
g.tick(420)
g.key(F7)
g.tick(120)
before = [g.rows(p) for p in (7, 2, 3)]
g.click("presets")
check("prandom" in g.regions(), "the Presets tab has a Randomize button")
g.click("prandom")
g.tick(5)
files = glob.glob(os.path.join(ad, "**", "my-presets.txt"), recursive=True)
text = open(files[0], encoding="utf-8").read() if files else ""
check("### preset: Random 1" in text, "Randomize saves the result as the preset 'Random 1'")
body = text.split("### preset: Random 1")[1].split("### end")[0]
s, profs = picker.load_config_text(body)
check({p["perk"] for p in profs} == set(picker.CATALOG), "it covers every armor passive (%d)" % len(profs))
check(body.count("=on") + body.count("= on") >= len(profs), "every armor has stacked passives (%d ticked)" % (body.count("=on") + body.count("= on")))
check(live_matches(g, body), "the game's rows equal what the loadout says (the random loadout is valid and applied)")
check([g.rows(p) for p in (7, 2, 3)] != before, "the stacks really changed")
g.click("prandom")
g.tick(5)
text2 = open(files[0], encoding="utf-8").read()
check("### preset: Random 2" in text2 and text2.count("### preset: Random") == 2, "a second press makes 'Random 2'")
g.click("tab:1")
g.click("undo")
g.tick(5)
check(live_matches(g, body), "Undo goes back to the first random loadout")

s_settings, _ = picker.load_config_text("[settings]\nname = x\n[profile: Med-Kit]\n")
sw = tempfile.mktemp(suffix=".lua")
with open(sw, "w", encoding="utf-8") as f:
    f.write(picker.compile_loadout(s_settings, [], blank=True, swap_only=True))
g2 = FakeGame(sw, appdata=tempfile.mkdtemp())
g2.tick(420)
g2.key(F7)
g2.tick(120)
g2.click("presets")
check("prandom" not in g2.regions() and "psave" in g2.regions(), "the Passive Swap edition has no Randomize button")

if failed:
    print("\n%d FAILED" % len(failed))
    sys.exit(1)
print("\nall randomize checks passed")
