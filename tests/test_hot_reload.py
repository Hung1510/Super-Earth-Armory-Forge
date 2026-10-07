#!/usr/bin/env python3
"""
6.3: loadout.ini edited on disk while the game runs is picked up (cLoser: deleting stat
adjustments and saving left the changed stats on the armor until the game restarted).

    python tests/test_hot_reload.py

1. An ini that drops a stack puts the game's own rows, stats and weights back, with no restart.
2. An ini that adds one applies it.
3. A file is applied only once it reads the same twice in a row (an editor mid-write is ignored).
4. The reload can be undone from the panel.
5. The mod's own saves are never mistaken for an outside edit.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import picker  # noqa: E402
from harness import FakeGame  # noqa: E402

failed = []


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        failed.append(what)


MK = next(k for k, v in picker.CATALOG.items() if v[0] == "Med-Kit")
FO = next(k for k, v in picker.CATALOG.items() if v[0] == "Fortified")
HEAD = "[settings]\nname = x\n"
STACK = "[profile: Med-Kit]\nweight = heavy\nFortified = on\nraw_stats = 1 2 3\n"

app = tempfile.mkdtemp()
lua = tempfile.mktemp(suffix=".lua")
s, p = picker.load_config_text(HEAD + STACK)
with open(lua, "w", encoding="utf-8") as f:
    f.write(picker.compile_loadout(s, p))
ini = os.path.join(app, "CowboyBingus", "Helldivers2", "ArmoryForge", "loadout.ini")
os.makedirs(os.path.dirname(ini), exist_ok=True)

g = FakeGame(lua, retire=True, appdata=app)
g.tick(420)
check(len(g.rows(MK)) == 4 and len(g.stats(MK)) == 1 and g.kit_weights(MK) == [2, 2, 1], "the stack is applied at start")

with open(ini, "w", encoding="utf-8", newline="") as f:
    f.write(HEAD)
g.tick(240)
check(g.record_bytes(MK) == g.pristine_record_bytes(MK), "ini without the stack: the game's own rows and stats are back")
check(g.kit_weights(MK) == [1, 1, 1], "... and its own weight")

with open(ini, "w", encoding="utf-8", newline="") as f:
    f.write(HEAD + "[profile: Med-Kit]\nFortified = on\n")
g.tick(240)
stacked = g.record_bytes(MK)
check(stacked != g.pristine_record_bytes(MK), "ini with a stack: applied without a restart")

with open(ini, "w", encoding="utf-8", newline="") as f:
    f.write(HEAD)
g.tick(70)                                  # one check only: the editor may still be writing
check(g.record_bytes(MK) == stacked, "a file seen once is not applied yet (the editor may be mid-write)")

with open(ini, "w", encoding="utf-8", newline="") as f:
    f.write(HEAD)
g.tick(240)
g.tick(240)
check(g.record_bytes(MK) == g.pristine_record_bytes(MK), "... but applied once it stays the same")

g.state[b"pp"][b"undo"]()
g.tick(5)
check(g.record_bytes(MK) != g.pristine_record_bytes(MK), "the reload can be undone (Undo in the panel)")

# our own saves are not outside edits
g2 = FakeGame(lua, retire=True, appdata=tempfile.mkdtemp())
g2.tick(420)
g2.key(0x76)
g2.tick(120)
g2.click("sel:%d" % FO)
g2.tick(10)
n = g2.record_bytes(MK)
g2.tick(400)
check(g2.record_bytes(MK) == n, "the panel's own save is not reloaded as an outside edit")

print("\n%d failed" % len(failed))
sys.exit(1 if failed else 0)
