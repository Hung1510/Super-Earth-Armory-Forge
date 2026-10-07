#!/usr/bin/env python3
"""
6.5: `booster = ...` in loadout.ini (full edition only, off unless set).

    python tests/test_booster_slot.py

The game's loadout reads helmet, cape, armor, booster. With the setting, the booster number is
written next to the copies of the loadout that hold the armor being worn; nothing else is
touched. Tested against the fake game (the real slot is still to be confirmed in game).
"""
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import picker  # noqa: E402
from harness import LOADOUT_BASE, FakeGame  # noqa: E402

failed = []


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        failed.append(what)


MK = next(k for k, v in picker.CATALOG.items() if v[0] == "Med-Kit")
HEAD = "[settings]\nname = x\n"


def build(swap=False):
    s, p = picker.load_config_text(HEAD + "[profile: Med-Kit]\nFortified = on\n")
    path = tempfile.mktemp(suffix=".lua")
    with open(path, "w", encoding="utf-8") as f:
        f.write(picker.compile_loadout(s, p, **({"swap_only": True} if swap else {})))
    return path


def game(ini_text, swap=False):
    app = tempfile.mkdtemp()
    ini = os.path.join(app, "CowboyBingus", "Helldivers2", "ArmoryForge", "loadout.ini")
    os.makedirs(os.path.dirname(ini), exist_ok=True)
    with open(ini, "w", encoding="utf-8", newline="") as f:
        f.write(ini_text)
    g = FakeGame(build(swap), retire=True, appdata=app)
    g.mem[LOADOUT_BASE][0x400:0x420] = b"\0" * 32
    g.wear(MK, 0x100)
    struct.pack_into("<I", g.mem[LOADOUT_BASE], 0x10C, 1)            # the game says Vitality
    # a look-alike that holds another armor (not the one worn): must stay as it is
    other = g.kit_ids[next(k for k in g.kit_ids if isinstance(k, int) and k != MK)]
    struct.pack_into("<IIII", g.mem[LOADOUT_BASE], 0x200, g.kit_ids["helmet"], g.kit_ids["cape"], other, 1)
    g.tick(900)
    return g, ini


def word(g, off):
    return struct.unpack_from("<I", g.mem[LOADOUT_BASE], off)[0]


g, ini = game(HEAD + "booster = Stamina\n[profile: Med-Kit]\nFortified = on\n")
check(word(g, 0x10C) == 2, "booster = Stamina: the word after helmet, cape, armor says Stamina (2)")
check(word(g, 0x20C) == 1, "... a copy holding another armor is left alone")
check(word(g, 0x100) == g.kit_ids["helmet"] and word(g, 0x108) == g.kit_ids[MK], "... and the ids next to it are untouched")

g, _ = game(HEAD + "booster = muscle enhancement\n[profile: Med-Kit]\nFortified = on\n")
check(word(g, 0x10C) == 3, "names are loose: 'muscle enhancement' is 3")
g, _ = game(HEAD + "booster = 4\n[profile: Med-Kit]\nFortified = on\n")
check(word(g, 0x10C) == 4, "a number works too")
g, _ = game(HEAD + "booster = none\n[profile: Med-Kit]\nFortified = on\n")
check(word(g, 0x10C) == 0, "none = no booster (0)")

g, _ = game(HEAD + "[profile: Med-Kit]\nFortified = on\n")
check(word(g, 0x10C) == 1, "no setting: the game's own booster is left alone")
g, _ = game(HEAD + "booster = off\n[profile: Med-Kit]\nFortified = on\n")
check(word(g, 0x10C) == 1, "booster = off: left alone")
g, _ = game(HEAD + "booster = Banana\n[profile: Med-Kit]\nFortified = on\n")
check(word(g, 0x10C) == 1, "an unknown name changes nothing")

# a word that is not a booster number (> 21) is never overwritten
g, ini = game(HEAD + "booster = Stamina\n[profile: Med-Kit]\nFortified = on\n")
struct.pack_into("<I", g.mem[LOADOUT_BASE], 0x10C, 0xDEADBEEF)
g.tick(300)
check(word(g, 0x10C) == 0xDEADBEEF, "a word above 21 is not a booster number: left alone")

# armor changed: follows the new armor; setting written back after a change by the game
g, ini = game(HEAD + "booster = UAV Recon\n[profile: Med-Kit]\nFortified = on\n")
struct.pack_into("<I", g.mem[LOADOUT_BASE], 0x10C, 6)                # the game resets it
g.tick(300)
check(word(g, 0x10C) == 4, "the game resetting the word: written back within a few seconds")

# saved with the loadout, and not in the Passive Swap edition
g, ini = game(HEAD + "booster = Stamina\n[profile: Med-Kit]\nFortified = on\n")
g.key(0x76)
g.tick(120)
g.click("sel:9")
g.click("inc:1")
g.key(0x76)
g.tick(120)
saved = open(ini, encoding="utf-8").read()
check("booster = Stamina" in saved, "a save from the panel keeps the setting in loadout.ini")
gs, _ = game(HEAD + "booster = Stamina\n", swap=True)
check(word(gs, 0x10C) == 1, "Passive Swap edition: the setting is ignored")

if failed:
    print("\n%d FAILED" % len(failed))
    sys.exit(1)
print("\nall booster-slot checks passed")
