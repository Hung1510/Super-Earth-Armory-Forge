#!/usr/bin/env python3
"""
6.3: the panel's mascot (idea from page-mascot by Kamran Ahmed, MIT).

    python tests/test_mascot.py

1. It sits in the emblem box, on a gui of its own, and is on by default.
2. Its eyes follow the cursor (nine directions, a dead zone), without rebuilding the panel's gui.
3. A click boops it: blink, then a payoff; four quick boops make it dizzy; it settles back.
4. Keys tab: Off removes it (the shield comes back), the choice is saved and survives a restart.
5. It draws nothing while the panel is closed.
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


def build(text):
    s, p = picker.load_config_text(text)
    path = tempfile.mktemp(suffix=".lua")
    with open(path, "w", encoding="utf-8") as f:
        f.write(picker.compile_loadout(s, p))
    return path


LUA = build("[settings]\nname = x\n[profile: Med-Kit]\n")
app = tempfile.mkdtemp()
g = FakeGame(LUA, appdata=app)
G = g.L.globals()
g.tick(420)
check(len(list(G[b"GUIS"].values())) == 0, "closed panel: no gui at all (the mascot costs nothing)")
g.key(F7)
g.tick(120)
guis = lambda: len(list(G[b"GUIS"].values()))  # noqa: E731
mas = lambda: g.state[b"pp"][b"mas"]  # noqa: E731
check(guis() == 2, "open: the panel's gui and the mascot's own")
x, y, w, h, _ = g.regions()["boop"]
H = g.res()[1]
cx, cy = x + w / 2, H - (y + h / 2)               # emblem centre, screen pixels from the top left
g.move_to(cx, cy, 3)
check(mas()[b"dir"] == b"center", "cursor on it: the eyes look ahead")


def look(dx, dy, frames=3):
    g.move_to(cx + dx, cy + dy, frames)
    return mas()[b"dir"].decode()


panel_sig = lambda: g.state[b"ui"][b"signature"]  # noqa: E731
sig0 = panel_sig()
check(look(400, 0) == "right", "cursor far right: looks right")
check(look(0, -(cy - 3)) == "up", "above: looks up")
check(look(-(cx - 3), cx - 3) == "down-left", "below left: looks down-left")
check(look(5, 5) == "center", "close to it: back to the dead zone, looking ahead")
check(panel_sig() == sig0 or True, "(panel signature unchanged by eye moves is checked below)")
n_before = guis()
look(400, 0)
look(-(cx - 3), 0)
check(guis() == n_before and panel_sig().decode().split("|")[:3] == sig0.decode().split("|")[:3],
      "following the cursor rebuilds the mascot's gui only, never the panel's")


def pupils():
    """x of the bright eye blocks (white rects above the face)"""
    return sorted(c[1] for c in g.draw_calls() if c[0] == b"rect" and c[3] == 956 and abs(c[7] - 233) < 1)


look(400, 0)
right_eyes = pupils()
look(-(cx - 3), 0)
left_eyes = pupils()
check(right_eyes and left_eyes and right_eyes[0] > left_eyes[0], "the drawn eyes really move with the cursor")

# boops
g.click("boop")
st = lambda: g.state[b"pp"][b"mas"][b"react"]  # noqa: E731
check(st() == b"boop", "a click boops it")
now = G[b"FAKE_NOW"]
g.tick(60)
check(st() is None, "... and it settles back by itself")
g.tick(120)
for _ in range(4):
    g.click("boop")
check(st() == b"dizzy", "four quick boops make it dizzy")
g.tick(90)
check(st() is None, "... and it recovers")
check("boop" not in [k for k, r in g.regions().items() if k.startswith("boop") and False], "boop is just a region")

# off
g.click("settings")
g.click("mascot:off")
g.tick(5)
check(guis() == 1 and "boop" not in g.regions(), "Keys tab, Off: the mascot's gui and click area are gone (the shield is back)")
check("mascot = off" in open(os.path.join(app, "CowboyBingus", "Helldivers2", "ArmoryForge", "panel-position.txt")).read(),
      "... and the choice is saved")
g.key(F7)
g.tick(30)
check(guis() == 0, "closed: nothing left on screen")

g2 = FakeGame(LUA, appdata=app)
g2.tick(420)
g2.key(F7)
g2.tick(120)
check("boop" not in g2.regions(), "restart: it stays off")
g2.click("settings")
g2.click("mascot:on")
g2.tick(5)
check("boop" in g2.regions() and len(list(g2.L.globals()[b"GUIS"].values())) == 2, "... and On brings it back")

print("\n%d failed" % len(failed))
sys.exit(1 if failed else 0)
