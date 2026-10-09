#!/usr/bin/env python3
"""
One-line codes for a recipe, a stratagem preset and a saved preset (Copy code / Paste code), and the
Presets tab's Compare view.

    python tests/test_codes_compare.py
"""
import base64
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


def b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)).decode()


def game(cfg="[settings]\nname = x\n[profile: Med-Kit]\n", swap=False, app=None):
    if swap:
        s, p = picker.load_config_text(cfg)[0], []
    else:
        s, p = picker.load_config_text(cfg)
    path = tempfile.mktemp(suffix=".lua")
    with open(path, "w", encoding="utf-8") as f:
        f.write(picker.compile_loadout(s, p, blank=True, swap_only=swap))
    g = FakeGame(path, appdata=app or tempfile.mkdtemp())
    g.tick(420)
    g.key(F7)
    g.tick(150)
    return g


def texts(g):
    return " | ".join(g.texts()).upper()


def forge(g, name):
    d = os.path.join(os.environ["LOCALAPPDATA"], "CowboyBingus", "Helldivers2", "ArmoryForge", name)
    return open(d, encoding="utf-8").read() if os.path.exists(d) else None


# ------------------------------------------------------------------ recipe codes
a = game()
a.click("tab:1")
a.click("sel:recipes")
a.click("rpick:1")
a.click("rcopy")
code = a.clipboard() or ""
check(code.startswith("AFR1:"), "Copy code on a recipe puts a one-line AFR1: code on the clipboard (%r)" % code[:20])
check("\n" not in code and " " not in code, "and it has no spaces or line breaks (safe in Discord)")
check(b64d(code[5:]).startswith("Medic Tank|Fortified|"), "it decodes to Name|Passive|Passive (%r)" % b64d(code[5:])[:50])

b = game(app=tempfile.mkdtemp())
b.click("tab:1")
b.clipboard("hey look at this %s thanks" % code)
b.click("sel:recipes")
b.click("paste")
rec = forge(b, "my-recipes.txt") or ""
check("Medic Tank 2 | Fortified | Unflinching | Extra Padding | Supplemental Adrenaline" in rec,
      "Paste code adds it as your own recipe (a built-in has that name, so it is 'Medic Tank 2') (%r)" % rec[-80:])
check("MEDIC TANK 2" in texts(b), "and it shows in the Recipes list")
b.clipboard("AFR1:!!!")
b.click("paste")
check("NO ARMORY FORGE CODE" in texts(b), "a broken code says so and adds nothing")
b.clipboard("just some words")
b.click("paste")
check("NO ARMORY FORGE CODE" in texts(b), "a clipboard that is no code says so")

# an own recipe round trip
a.click("tab:1")
a.click("sel:recipes")
a.click("rsave")
a.type_text("zz")
a.key(0x0D)
a.click("rcopy")
c2 = a.clipboard()
b.clipboard(c2)
b.click("paste")
check(len((forge(b, "my-recipes.txt") or "").strip().splitlines()) >= 3, "an own recipe goes through the same way")

# the Passive Swap edition has no recipes: the code is refused
s = game(cfg="[settings]\nname = x\n[profile: Med-Kit]\n", swap=True)
s.clipboard(code)
s.click("presets")
s.click("paste") if "paste" in s.regions() else None
check(forge(s, "my-recipes.txt") is None, "Passive Swap edition: a recipe code adds nothing")

# ------------------------------------------------------------------ preset codes and compare
g = game("[settings]\nname = x\n[profile: Med-Kit]\nFortified = on\n")
g.click("tab:1")
g.click("presets")
g.click("psave")
g.key(0x0D)
g.tick(5)
check("pcopy" in g.regions() and "pcmp" in g.regions(), "a saved preset has Copy code and Compare")
g.click("pcopy")
link = g.clipboard() or ""
check("#ini=" in link and "Med-Kit" in b64d(link.split("#ini=")[1]) or "[profile: 7]" in b64d(link.split("#ini=")[1]),
      "Copy code on a preset gives the web-builder link of that preset")

# change the stack, save a second preset
g.click("presets")        # close
g.click("tab:1")
g.tick(3)
regs = g.regions()
tick = [k for k in regs if k.startswith("tick:")]
check(len(tick) > 0, "the stack's passives can be ticked")
g.click(tick[0])
g.click("presets")
g.click("psave")
g.key(0x0D)
g.tick(5)
g.click("pcmp")
check("CLICK ANOTHER PRESET" in texts(g), "Compare asks for the second preset")
g.click("pre:user:1")
g.tick(5)
t = texts(g)
check("DONE COMPARING" in t.replace(" ", " ") or "pcmpend" in g.regions(), "comparing two presets shows the difference view")
check("ONLY IN MY PRESET" in t and "MED-KIT ARMOR | -" in t,
      "it lists what is only in one of them, under the armor it belongs to")
g.click("pcmpend")
g.click("pcmpnow")
check("pcmpend" in g.regions(), "Compare with my stack now works too")
g.click("pcmpend")
check("pload" in g.regions(), "Done comparing goes back to the preset")

# the web builder's built-in recipes (tools/picker.py RECIPES) are the panel's (tools/panel.lua PP.RECIPES)
import re  # noqa: E402
lua = open(os.path.join(HERE, "..", "tools", "panel.lua"), encoding="utf-8").read()
block = lua[lua.index("PP.RECIPES = {"):]
block = block[:block.index("\n}\n")]
panel_recipes = [(n, re.findall(r"'([^']+)'", ps))
                 for n, ps in re.findall(r"\{\s*'([^']+)',\s*\{([^}]*)\}", block)]
check(panel_recipes == [(n, list(ps)) for n, ps in picker.RECIPES] and len(panel_recipes) == 5,
      "the web builder's recipes are the panel's recipes")
names = {n.lower() for n, _, _ in picker.CATALOG.values()}
check(all(p.lower() in names for _, ps in picker.RECIPES for p in ps), "every recipe passive exists in the catalog")

if failed:
    print("\n%d FAILED" % len(failed))
    sys.exit(1)
print("\nall code and compare checks passed")
