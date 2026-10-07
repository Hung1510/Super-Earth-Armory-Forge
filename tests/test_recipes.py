#!/usr/bin/env python3
"""
Recipes (full edition): named sets of armor passives, applied with one click.

    python tests/test_recipes.py

The RECIPES row in an armor tab opens a list: built-in recipes plus your own, saved to
ArmoryForge\\my-recipes.txt. Applying ticks passives in the stack (Undo works); loadout.ini
gets nothing new. The Passive Swap edition has no recipes.
"""
import os
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


def build(text, **kw):
    s, p = picker.load_config_text(text)
    path = tempfile.mktemp(suffix=".lua")
    with open(path, "w", encoding="utf-8") as f:
        f.write(picker.compile_loadout(s, p, **kw))
    return path


def ticked(g):
    """the names ticked in the saved loadout.ini of tab 1"""
    g.tick(120)
    ini = open(os.path.join(FDIR[0], "loadout.ini"), encoding="utf-8").read()
    return sorted(ln.split("=")[0].strip() for ln in ini.splitlines() if ln.rstrip().endswith("= on"))


FDIR = [None]
app = tempfile.mkdtemp()
fdir = os.path.join(app, "CowboyBingus", "Helldivers2", "ArmoryForge")
FDIR[0] = fdir
g = FakeGame(build("[settings]\nname = x\n[profile: Med-Kit]\nFortified = on\n"), appdata=app)
g.tick(420)
g.key(F7)
g.tick(120)
g.click("tab:1")
check("sel:recipes" in g.regions(), "the armor tab has a RECIPES row")
g.click("sel:recipes")
texts = " ".join(g.texts())
check("MEDIC TANK" in texts and "GHOST" in texts, "built-in recipes are listed")
check("rpick:1" in g.regions() and "rapply:add" in g.regions(), "pick and apply controls exist")

g.click("rapply:add")
now = ticked(g)
check({"Fortified", "Unflinching", "Extra Padding", "Supplemental Adrenaline"} <= set(now), "Add to stack ticks the recipe's passives (%s)" % now)
g.click("undo")
check(ticked(g) == ["Fortified"], "Undo takes the recipe back")

g.click("rpick:2")
g.click("rapply:only")
now = ticked(g)
check(now == ["Feet First", "Reduced Signature", "Scout"], "Only this replaces the ticks (%s)" % now)

# save the ticks as your own recipe, name it, reload it
g.click("rsave")
check(any(t.upper().startswith("MY RECIPE 1") for t in g.texts()), "a saved recipe appears, ready to rename")
for ch in "AB":
    g.key(ord(ch))
    g.tick(3)
g.key(0x0D)
g.tick(10)
saved = open(os.path.join(fdir, "my-recipes.txt"), encoding="utf-8").read()
check("| Scout" in saved and "| Feet First" in saved and "Feet First" in saved, "my-recipes.txt holds the recipe")
check(saved.splitlines()[1].lower().startswith("ab |"), "the recipe was renamed (%r)" % saved.splitlines()[1:2])
check("recipe" not in open(os.path.join(fdir, "loadout.ini"), encoding="utf-8").read().lower(), "loadout.ini is unchanged in format")

g.click("rpick:1")
g.click("rapply:only")
g.click("rpick:6")
g.click("rapply:add")
check(set(ticked(g)) >= {"Scout", "Fortified", "Unflinching"}, "your recipe applies like a built-in one")
g.click("rdel")
check(os.path.exists(os.path.join(fdir, "my-recipes.txt")) and "Scout" in open(os.path.join(fdir, "my-recipes.txt")).read(), "Delete asks first")
g.click("rdel")
check("Scout" not in open(os.path.join(fdir, "my-recipes.txt")).read(), "a second click deletes it")

# a fresh session reads the file
app2 = tempfile.mkdtemp()
fdir = os.path.join(app2, "CowboyBingus", "Helldivers2", "ArmoryForge")
FDIR[0] = fdir
os.makedirs(fdir)
open(os.path.join(fdir, "my-recipes.txt"), "w", encoding="utf-8").write("Pals | Scout | Concussive Padding, Reinforced\r\n")
g2 = FakeGame(build("[settings]\nname = x\n[profile: Med-Kit]\n"), appdata=app2)
g2.tick(420)
g2.key(F7)
g2.tick(120)
g2.click("tab:1")
g2.click("sel:recipes")
check("PALS" in " ".join(g2.texts()), "recipes load from my-recipes.txt next session")
g2.click("rpick:6")
g2.click("rapply:add")
check(ticked(g2) == ["Concussive Padding, Reinforced", "Scout"], "a passive name with a comma survives the file")

# Passive Swap edition: none
sw = FakeGame(build("[settings]\nname = x\n[profile: Med-Kit]\n", blank=True, swap_only=True), appdata=tempfile.mkdtemp())
sw.tick(420)
sw.key(F7)
sw.tick(120)
sw.click("tab:1")
check("sel:recipes" not in sw.regions(), "Passive Swap edition: no recipes row")

if failed:
    print("\n%d FAILED" % len(failed))
    sys.exit(1)
print("\nall recipe checks passed")
