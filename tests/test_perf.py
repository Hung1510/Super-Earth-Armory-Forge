#!/usr/bin/env python3
"""
Panel redraw cost (7.1): the width of a label is measured by the engine once, then remembered, so a
redraw (every hover change) does not ask the engine to measure the same ~150 labels again.

    python tests/test_perf.py
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


s, p = picker.load_config_text("[settings]\nname = x\n[profile: Med-Kit]\n")
path = tempfile.mktemp(suffix=".lua")
with open(path, "w", encoding="utf-8") as f:
    f.write(picker.compile_loadout(s, p, blank=True))
g = FakeGame(path, appdata=tempfile.mkdtemp())
g.tick(420)
g.key(0x76)
g.tick(150)
g.click("tab:1")
g.tick(5)
g.L.execute(b"""
EXTENTS = 0
local f = stingray.Gui.text_extents
stingray.Gui.text_extents = function(...) EXTENTS = EXTENTS + 1; return f(...) end
""")
for i in range(8):                       # the cursor crosses buttons: the panel is redrawn each time
    g.move_to(300 + (i % 2) * 40, 500)
    g.tick(1)
check(g.L.globals()[b"EXTENTS"] == 0, "redrawing a view that was already drawn measures no label again (%s calls)"
      % g.L.globals()[b"EXTENTS"])
before = g.L.globals()[b"EXTENTS"]
g.click("guide")
g.tick(3)
first = g.L.globals()[b"EXTENTS"] - before
g.click("guide")
g.click("guide")
g.tick(3)
check(first > 0 and g.L.globals()[b"EXTENTS"] - before == first, "a new view measures its own labels once (%d), then never" % first)

# 7.2: closed, nothing asks Windows whether the game is in front (two calls) unless a hotkey was just
# pressed; open, it is asked once per frame however many parts of the panel need the answer
def asks():
    return g.state[b"pp"][b"focus_asks"] or 0


g.key(0x76)                              # close the panel
g.tick(400)
a0 = asks()
g.tick(600)
check(asks() == a0, "panel closed: no focus check in 600 idle frames (%d)" % (asks() - a0))
g.key(0x76)                              # a hotkey press does ask
g.tick(150)
a0 = asks()
g.tick(60)
check(asks() - a0 <= 60, "panel open: at most one focus check a frame (%d in 60)" % (asks() - a0))

# 7.2: the wearing search reads 256 KB at a time (was 1 MB), so a frame stays near its budget
src = open(os.path.join(HERE, "..", "tools", "engine.lua"), encoding="utf-8").read()
check("local WEAR_CHUNK = 262144" in src and "math.min(1048576, r.size - W.cursor)" not in src,
      "wearing search chunks are 256 KB")
st = open(os.path.join(HERE, "..", "tools", "strat.lua"), encoding="utf-8").read()
check("local SEARCH_CHUNK = 524288" in st and "2097152" not in st, "stratagem search chunks are 512 KB, run to a time budget")

if failed:
    print("\n%d FAILED" % len(failed))
    sys.exit(1)
print("\nall performance checks passed")
