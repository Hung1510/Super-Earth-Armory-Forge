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

if failed:
    print("\n%d FAILED" % len(failed))
    sys.exit(1)
print("\nall performance checks passed")
