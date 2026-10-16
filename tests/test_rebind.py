#!/usr/bin/env python3
"""
Rebind (7.4): click Rebind, press any key (with Ctrl / Alt / Shift held), for the panel key, the quick-swap
key and the stratagem key. The names are saved to loadout.ini and read back by Python, the web builder and Lua.

    python tests/test_rebind.py
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import picker  # noqa: E402
from harness import FakeGame  # noqa: E402

F = {n: 0x6F + n for n in range(1, 13)}
CTRL, ALT, SHIFT, ESC = 0x11, 0x12, 0x10, 0x1B
K, L, Z = 0x4B, 0x4C, 0x5A
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


def is_open(g):
    return bool(g.state[b"ui"][b"open"])


def press(g, vk, mods=()):
    keys = g.L.globals()[b"KEYS"]
    for m in mods:
        keys[m] = True
    g.tick(2)
    g.key(vk)
    for m in mods:
        keys[m] = None
    g.tick(2)


def forge(appdata):
    return os.path.join(appdata, "CowboyBingus", "Helldivers2", "ArmoryForge")


# ------------------------------------------------------------------ 1. the names
pk = picker.parse_keyname
check(pk("F7") == "F7" and pk("f12") == "F12" and pk("F13") is None, "F1..F12 only")
check(pk("ctrl+k") == "Ctrl+K" and pk("Alt + Shift + F3") == "Alt+Shift+F3", "modifiers, any case, in a fixed order")
check(pk("K") is None and pk("5") is None and pk("Insert") is None, "a bare letter, digit or Insert is refused (it would fire while you play)")
check(pk("Alt+PageDown") == "Alt+PageDown" and pk("Ctrl+Home") == "Ctrl+Home", "Ctrl or Alt makes them valid")
check(pk("Ctrl+Z") is None and pk("Ctrl+F") is None and pk("Ctrl+0") is None, "the panel's own shortcuts are refused")
check(pk("Ctrl+K+L") is None and pk("") is None and pk(None) is None, "nonsense is refused")
s, _ = picker.load_config_text("[settings]\nhotkey = ctrl+k\nswap_hotkey = Alt+L\n[profile: Med-Kit]\n")
check(s["hotkey"] == "Ctrl+K" and s["swap_hotkey"] == "Alt+L", "loadout.ini accepts them")
try:
    picker.load_config_text("[settings]\nhotkey = K\n[profile: Med-Kit]\n")
    check(False, "a bare letter in loadout.ini is an error")
except picker.ConfigError:
    check(True, "a bare letter in loadout.ini is an error")

# ------------------------------------------------------------------ 2. in game: the panel key
appdata = tempfile.mkdtemp()
lua = build(open(os.path.join(ROOT, "presets", "01-kitchen-sink.ini"), encoding="utf-8").read())
g = FakeGame(lua, appdata=appdata)
g.tick(420)
g.key(F[7])
g.tick(120)
g.click("settings")
regs = g.regions()
check("rebind:hotkey" in regs and "rebind:swap_hotkey" in regs, "the Keys tab has a Rebind button for each key")
g.click("rebind:hotkey")
g.tick(5)
check(bool(g.state[b"ui"][b"capture"]), "Rebind waits for a key")
press(g, K)                                                      # a bare letter
check(bool(g.state[b"ui"][b"capture"]) and any("Ctrl or Alt" in t for t in g.texts()), "a bare letter is refused and says why")
press(g, K, (CTRL,))
check(not g.state[b"ui"][b"capture"] and any("opens with Ctrl+K" in t for t in g.texts()), "Ctrl+K is taken")
check(is_open(g), "the panel stays open while the key changes")
press(g, F[7])
check(is_open(g), "the old key no longer closes the panel")
press(g, K)
check(is_open(g), "a plain K does nothing")
press(g, K, (CTRL, SHIFT))
check(is_open(g), "Ctrl+Shift+K is not Ctrl+K")
press(g, K, (CTRL,))
check(not is_open(g), "Ctrl+K closes the panel")
press(g, K, (CTRL,))
g.tick(120)
check(is_open(g), "... and opens it")
g.tick(200)
ini = open(os.path.join(forge(appdata), "loadout.ini"), encoding="utf-8").read()
check("hotkey = Ctrl+K" in ini, "saved to loadout.ini")
g2 = FakeGame(lua, appdata=appdata)
g2.tick(420)
press(g2, K, (CTRL,))
g2.tick(120)
check(is_open(g2), "after a restart Ctrl+K opens the panel")

# Esc cancels; an F-key still works; the quick-swap key can't take the panel key
g2.click("settings")
g2.click("rebind:hotkey")
g2.tick(5)
press(g2, ESC)
check(not g2.state[b"ui"][b"capture"] and is_open(g2), "Esc cancels and leaves the panel open")
g2.click("rebind:swap_hotkey")
g2.tick(5)
press(g2, K, (CTRL,))
check(bool(g2.state[b"ui"][b"capture"]) and any("panel key" in t for t in g2.texts()), "the quick-swap key can't be the panel key")
press(g2, L, (ALT,))
g2.tick(200)
ini = open(os.path.join(forge(appdata), "loadout.ini"), encoding="utf-8").read()
check("swap_hotkey = Alt+L" in ini, "Alt+L is the quick-swap key")
g2.click("rebind:hotkey")
g2.tick(5)
press(g2, F[8])
g2.tick(200)
ini = open(os.path.join(forge(appdata), "loadout.ini"), encoding="utf-8").read()
check("hotkey = F8" in ini, "an F-key can be pressed in Rebind too")
press(g2, Z, (CTRL,))
check(is_open(g2), "Ctrl+Z is still undo, not a key")

# ------------------------------------------------------------------ 3. a hand-edited ini
appdata3 = tempfile.mkdtemp()
os.makedirs(forge(appdata3))
with open(os.path.join(forge(appdata3), "loadout.ini"), "w", encoding="utf-8") as f:
    f.write("[settings]\nname = x\nhotkey = Ctrl+Alt+Insert\nswap_hotkey = k\n[profile: Med-Kit]\n")
g3 = FakeGame(build("[settings]\nname = x\n[profile: Med-Kit]\n", blank=True), appdata=appdata3)
g3.tick(420)
press(g3, 0x2D, (CTRL, ALT))
g3.tick(120)
check(is_open(g3), "Ctrl+Alt+Insert from loadout.ini opens the panel")

# ------------------------------------------------------------------ 4. the stratagem key
appdata4 = tempfile.mkdtemp()
g4 = FakeGame(lua, appdata=appdata4)
g4.tick(420)
g4.key(F[7])
g4.tick(120)
g4.click("strat")
g4.tick(10)
check("rebind:strat" in g4.regions(), "the Stratagems tab has a Rebind button")
g4.click("rebind:strat")
g4.tick(5)
press(g4, K, (CTRL, SHIFT))
check(bool(g4.state[b"ui"][b"capture"]) and any("Shift" in t for t in g4.texts()), "Shift is refused for the stratagem key (Shift goes back)")
press(g4, K, (CTRL,))
g4.tick(10)
saved = open(os.path.join(forge(appdata4), "stratagem-key.txt"), encoding="utf-8").read().lower()
check("key = ctrl+k" in saved, "Ctrl+K is saved as the stratagem key")

if failed:
    print("\n%d FAILED" % len(failed))
    sys.exit(1)
print("\nall rebind checks passed")
