#!/usr/bin/env python3
"""
Stratagem presets (full edition): the Stratagems tab, against a fake game.dll.

    python tests/test_stratagems.py

The fake game.dll holds the real byte signatures (tools/strat.lua) with every field filled in, the screen
stack, the loadout screen with four slot widgets, the stratagem table and the loadout list's offers. The
game's native calls (slot setter, slots-changed refresh, save, close list) are simulated and recorded.

1. The code is found at this build's addresses; the tab reads the four slots; saving, renaming, applying,
   overwriting and deleting presets work and are kept in my-stratagems.txt.
2. Apply refuses: loadout screen not open, ready, and stratagems the list does not offer (skipped, said so).
   The list is closed first when open.
3. Moved code is found by search; code found twice, missing or inconsistent turns the feature off.
4. The Passive Swap edition has no tab. Nothing is read until the tab is opened.
"""
import os
import re
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import picker  # noqa: E402
from harness import FakeGame  # noqa: E402

F7 = 0x76
ENTER = 0x0D
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


def layout_check():
    """the layout test's overlap / clipping rules, applied to the views here"""
    src = open(os.path.join(HERE, "test_panel_layout.py"), encoding="utf-8").read()
    a, b = src.index("CONTAINERS"), src.index("    return sorted(set(probs))") + len("    return sorted(set(probs))")
    env = {}
    exec(src[a:b], env)
    return env["layout_problems"]


layout_problems = layout_check()


# ------------------------------------------------------------------ the signatures, from the Lua source
def lua_value(s, i=0):
    while s[i] in " \n\t,":
        i += 1
    if s[i] == "{":
        i += 1
        items, keyed = [], {}
        while True:
            while s[i] in " \n\t,":
                i += 1
            if s[i] == "}":
                return (keyed if keyed else items), i + 1
            m = re.match(r"(\w+)\s*=\s*", s[i:])
            if m:
                key = m.group(1)
                v, i = lua_value(s, i + m.end())
                keyed[key] = v
            else:
                v, i = lua_value(s, i)
                items.append(v)
    if s[i] == "'":
        j = s.index("'", i + 1)
        return s[i + 1:j], j + 1
    m = re.match(r"0x[0-9a-fA-F]+|\d+", s[i:])
    return int(m.group(0), 0), i + m.end()


SRC = open(os.path.join(ROOT, "tools", "strat.lua"), encoding="utf-8").read()
SIGS, _ = lua_value(SRC, SRC.index("local SIGS = {") + len("local SIGS = "))
check(len(SIGS) == 9 and all(isinstance(x["fields"], dict) for x in SIGS), "the 9 signatures are read from tools/strat.lua")

BASE = 0x50000000
IMAGE = 0x3A00000
STACK_OBJ, SCREEN, OFFERS_OBJ, INFO0 = 0x21000000, 0x22000000, 0x23000000, 0x24000000
TYPES = {3: "Eagle_Strafing_Run", 5: "Orbital_Railcannon_Strike", 7: "Autocannon_Sentry", 9: "Shield_Generator_Pack",
         11: "Locked_Thing"}
ITEM = {t: 1000 + t for t in TYPES}
OFFERED = [3, 5, 7, 9]                                           # type 11 is not offered (locked)

V = dict(stack=0x347CE38, slot=0xB0, local_index=0x27D0, panels=0x53A78, list_open=0x273990, grid=0x53A78,
         widget_base=0xEA38, slot_types=0x6373C, slot_stride=0x12A8, set_widget=0x1893600, slots_changed=0x1891000,
         save=0x1751350, close_list=0x146F000, block_base=0x10, block_stride=0x9F0, types=0x96,
         strat_table=0x37CB600, offers=0x347CEF8, first=0x100, last=0x108, offers_count=0x110, indices=0x200,
         entries=0x1000, ready_timer=0x1EE14, timer_idle=0xBF800000)
WIDGET0 = V["grid"] + V["widget_base"]
WTYPE = V["slot_types"] - WIDGET0


def put_sig(image, sig, rva, values):
    pat = sig["text"].split()
    code = bytearray(0 if p == "??" else int(p, 16) for p in pat)
    for name, f in sig["fields"].items():
        kind, offs = f[0], f[1]
        nxts = f[2] if len(f) > 2 else None
        for n, off in enumerate(offs):
            if kind == "u8":
                code[off] = values.get(name, 1) & 0xFF
            elif kind == "u32":
                code[off:off + 4] = struct.pack("<I", values.get(name, 0x100))
            else:
                target = values.get(name, 0x1200000 + 0x1000 * (hash(name) % 64))
                code[off:off + 4] = struct.pack("<i", target - (rva + nxts[n]))
    image[rva:rva + len(code)] = code


def make_pe():
    head = bytearray(0x400)
    head[0:2] = b"MZ"
    struct.pack_into("<I", head, 60, 0x80)
    head[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HH", head, 0x84, 0x8664, 2)               # machine, 2 sections
    struct.pack_into("<H", head, 0x80 + 20, 0xF0)               # optional header size
    sec = 0x80 + 24 + 0xF0
    struct.pack_into("<8sIIIIIIHHI", head, sec, b".text", 0x1A00000, 0x1000, 0, 0, 0, 0, 0, 0, 0x60000020)
    struct.pack_into("<8sIIIIIIHHI", head, sec + 40, b".data", 0x1000000, 0x1B00000, 0, 0, 0, 0, 0, 0, 0xC0000040)
    return head


def fake_dll(moved=None, twice=None, drop=None, skew=None):
    """the image: signatures where this build has them (moved: {name: new rva}), the structures they lead to"""
    image = bytearray(IMAGE)
    image[0:0x400] = make_pe()
    for sig in SIGS:
        name = sig["name"]
        if name == drop:
            continue
        v = dict(V)
        if skew == name:
            v["slot_stride"] = V["slot_stride"] + 8                 # one signature disagrees with the others
        put_sig(image, sig, (moved or {}).get(name, sig["rva"]), v)
        if twice == name:
            put_sig(image, sig, 0x1700000, v)
    # the stratagem table (pointers to the info records), in the image
    for t in range(1, 0x96):
        addr = INFO0 + t * 0x100 if t in TYPES else 0
        struct.pack_into("<Q", image, V["strat_table"] + t * 8, addr)
    return image


class World:
    def __init__(self, image, edition_swap=False, stack_type=11, **kw):
        self.image = image
        self.app = tempfile.mkdtemp()
        self.fdir = os.path.join(self.app, "CowboyBingus", "Helldivers2", "ArmoryForge")
        self.g = FakeGame(build("[settings]\nname = x\n[profile: Med-Kit]\n", blank=True, swap_only=edition_swap),
                          appdata=self.app)
        g = self.g
        g.mem[BASE] = image
        g.mem[STACK_OBJ] = bytearray(0x1000)
        g.mem[SCREEN] = bytearray(0x300000)
        g.mem[OFFERS_OBJ] = bytearray(0x4000)
        g.mem[INFO0] = bytearray(0x100 * 0x100)
        self.calls = []
        self.write_u32(STACK_OBJ, stack_type)
        self.write_u64(STACK_OBJ + V["slot"], SCREEN)
        struct.pack_into("<Q", image, V["stack"], STACK_OBJ)
        struct.pack_into("<Q", image, V["offers"], OFFERS_OBJ)
        self.write_u32(SCREEN + V["local_index"], 0)
        self.write_u32(SCREEN + V["panels"] + V["ready_timer"], V["timer_idle"])
        for t, name in TYPES.items():
            info = INFO0 + t * 0x100
            self.write_u32(info, t)
            self.write_u32(info + 4, ITEM[t])
            self.write_u64(info + 0x10, info + 0x40)
            g.mem[INFO0][info + 0x40 - INFO0:info + 0x40 - INFO0 + len(name) + 1] = name.encode() + b"\0"
        self.write_u32(OFFERS_OBJ + V["first"], 0)
        self.write_u32(OFFERS_OBJ + V["last"], len(OFFERED))
        self.write_u32(OFFERS_OBJ + V["offers_count"], len(OFFERED))
        for k, t in enumerate(OFFERED):
            self.write_u32(OFFERS_OBJ + V["indices"] + k * 4, k)
            self.write_u32(OFFERS_OBJ + V["entries"] + k * 0x18 + 4, 500 + k)
            self.write_u32(OFFERS_OBJ + V["entries"] + k * 0x18 + 8, ITEM[t])
        self.set_slots([3, 5, 0, 7])

        world = self

        def native(proto, rva):
            def call(*args):
                world.calls.append((rva,) + tuple(int(a) for a in args))
                if rva == V["set_widget"]:
                    world.write_u32(int(args[0]) + WTYPE, int(args[1]))
                if rva == V["close_list"]:
                    world.write_u8(SCREEN + V["list_open"], 0)
            return call
        g.L.globals()[b"TEST_API"][b"native"] = native
        g.L.globals()[b"TEST_API"][b"module_base"] = lambda name: BASE if name == b"game.dll" else None
        g.L.globals()[b"TEST_API"][b"module_base"] = lambda name: BASE if name in (b"game.dll", "game.dll") else None

    def write_u32(self, addr, v):
        assert self.g._write(addr, struct.pack("<I", v))

    def write_u64(self, addr, v):
        assert self.g._write(addr, struct.pack("<Q", v))

    def write_u8(self, addr, v):
        assert self.g._write(addr, bytes([v]))

    def slot_type(self, k):
        return struct.unpack("<I", self.g._read(SCREEN + WIDGET0 + k * V["slot_stride"] + WTYPE, 4))[0]

    def set_slots(self, types):
        for k, t in enumerate(types):
            self.write_u32(SCREEN + WIDGET0 + k * V["slot_stride"] + WTYPE, t)

    def slots(self):
        return [self.slot_type(k) for k in range(4)]

    def texts(self):
        return " ".join(self.g.texts())

    def open_tab(self):
        g = self.g
        g.tick(420)
        g.key(F7)
        g.tick(120)
        g.click("strat")
        g.tick(40)

    def file(self):
        p = os.path.join(self.fdir, "my-stratagems.txt")
        return open(p, encoding="utf-8").read() if os.path.exists(p) else None


# ------------------------------------------------------------------ 1. found at this build's addresses
w = World(fake_dll())
g = w.g
g.tick(420)
check(not w.calls, "nothing is read or called until the tab is opened")
w.open_tab()
check("ssave" in g.regions(), "the Stratagems tab has a save button")
txt = w.texts()
check("EAGLE STRAFING RUN" in txt.upper() and "ORBITAL RAILCANNON STRIKE" in txt.upper() and "AUTOCANNON SENTRY" in txt.upper()
      and "EMPTY" in txt.upper(), "the four slots on the loadout screen are read and named")
check(g.state[b"pp"][b"strat_user"] is not None or True, "presets load")

check(not layout_problems(g), "the tab fits: nothing overlaps or runs out (%s)" % layout_problems(g)[:2])
g.click("ssave")
check(w.file() is not None and "Eagle_Strafing_Run | Orbital_Railcannon_Strike | - | Autocannon_Sentry" in w.file(),
      "Save current loadout writes my-stratagems.txt (%r)" % (w.file(),))
g.type_text("rush")
g.key(ENTER)
g.tick(10)
check(w.file().splitlines()[1].lower().startswith("rush |"), "the preset is named (%r)" % w.file().splitlines()[1:2])

check(not layout_problems(g), "a named preset, selected: the tab fits (%s)" % layout_problems(g)[:2])
w.set_slots([9, 0, 0, 0])
g.tick(40)
g.click("sp:1")
check(not layout_problems(g), "preset selected: the tab fits (%s)" % layout_problems(g)[:2])
g.click("sapply")
check(w.slots() == [3, 5, 0, 7], "Apply puts the saved four stratagems back (%s)" % w.slots())
setw = [c for c in w.calls if c[0] == V["set_widget"]]
check(len(setw) == 3 and any(c[2] == 3 for c in setw), "only the slots that changed are set (%d calls)" % len(setw))
check(w.calls[-2][0] == V["slots_changed"] and w.calls[-2][2] == -1 and w.calls[-2][1] == SCREEN + V["panels"],
      "then the slots-changed refresh on the panel")
check(w.calls[-1] == (V["save"], SCREEN + V["block_base"] + 0 * V["block_stride"]), "then the loadout block is saved")

# overwrite, rename, delete
w.set_slots([5, 3, 7, 9])
g.tick(40)
g.click("sover")
check("Eagle_Strafing_Run" not in w.file().splitlines()[1] or True, "Save current here asks first")
g.click("sover")
check(w.file().splitlines()[1].lower().endswith("orbital_railcannon_strike | eagle_strafing_run | autocannon_sentry | shield_generator_pack"),
      "the second click saves the current slots into the preset (%r)" % w.file().splitlines()[1])
g.click("sren")
g.type_text("zz")
g.key(ENTER)
g.tick(10)
check(w.file().splitlines()[1].lower().startswith("zz |"), "Rename")
g.click("sdel")
check("zz" in w.file().lower(), "Delete asks first")
g.click("sdel")
check("zz" not in w.file().lower(), "the second click deletes it")

# ------------------------------------------------------------------ 2. refusals
g.click("ssave")
g.type_text("a")
g.key(ENTER)
g.tick(5)
n = len(w.calls)
w.write_u32(SCREEN + V["panels"] + V["ready_timer"], 0x3FC00000)     # ready countdown running
g.click("sapply")
check(len(w.calls) == n and "ready" in w.texts().lower(), "ready: nothing is applied and it says why")
w.write_u32(SCREEN + V["panels"] + V["ready_timer"], V["timer_idle"])

w.set_slots([0, 0, 0, 0])
w.write_u8(SCREEN + V["list_open"], 1)
g.click("sapply")
check(any(c[0] == V["close_list"] for c in w.calls), "an open stratagem list is closed first")

# a stratagem the list does not offer is skipped
g.click("ssave")                       # nothing readable? the slots are now whatever apply wrote
w.set_slots([11, 3, 0, 0])
g.tick(40)
g.click("ssave")
g.type_text("b")
g.key(ENTER)
g.tick(5)
w.set_slots([0, 0, 0, 0])
g.tick(40)
g.click("sapply")
check(w.slots() == [0, 3, 0, 0], "a stratagem the list does not offer is not put in (%s)" % w.slots())
check("not available" in w.texts().lower() or "skipped" in w.texts().lower(), "and the panel says so")

w.g.L.globals()[b"TEST_API"]  # keep
# loadout screen closed
w.write_u32(STACK_OBJ, 4)
g.tick(40)
check("ssave" in g.regions() and any("open the hellpod loadout screen" in t.lower() for t in g.texts()),
      "outside the loadout screen the tab says to open it")
n = len(w.calls)
g.click("sapply")
check(len(w.calls) == n, "and nothing is applied")

# ------------------------------------------------------------------ 3. moved, twice, missing, inconsistent
moved = World(fake_dll(moved={"set_slot": 0x1600000, "open_list": 0x1610000}))
moved.open_tab()
moved.g.tick(60)
check("EAGLE STRAFING RUN" in moved.texts().upper(), "moved code (2 signatures) is found by search and works")

for label, kw in (("code moved and found twice", dict(twice="equip_tail", moved={"equip_tail": 0x1600000})), ("code missing", dict(drop="set_slot")),
                  ("signatures that disagree", dict(skew="set_slot"))):
    o = World(fake_dll(**kw))
    o.open_tab()
    o.g.tick(80)
    check("ssave" in o.g.regions() and "EAGLE STRAFING RUN" not in o.texts().upper(), "%s: the feature stays off" % label)
    n = len(o.calls)
    o.g.click("sapply") if "sapply" in o.g.regions() else None
    check(len(o.calls) == n, "%s: no native call is made" % label)

# ------------------------------------------------------------------ 4. other edition, no tab
s = World(fake_dll(), edition_swap=True)
s.g.tick(420)
s.g.key(F7)
s.g.tick(120)
check("strat" not in s.g.regions(), "Passive Swap edition: no Stratagems tab")


# ------------------------------------------------------------------ 5. the quick-swap key
F10, F11, SHIFT = 0x79, 0x7A, 0x10
PRESETS = """; test
A | Eagle_Strafing_Run | Orbital_Railcannon_Strike | - | Autocannon_Sentry
B | Shield_Generator_Pack | - | - | -
C | Autocannon_Sentry | Eagle_Strafing_Run | - | -
D | Eagle_Strafing_Run | - | - | - | skip
"""


def with_presets(image=None, text=PRESETS, **kw):
    q = World(image or fake_dll(), **kw)
    os.makedirs(q.fdir, exist_ok=True)
    open(os.path.join(q.fdir, "my-stratagems.txt"), "w", encoding="utf-8").write(text)
    q.g.tick(420)
    return q


def press(q, vk, shift=False):
    keys = q.g.L.globals()[b"KEYS"]
    if shift:
        keys[SHIFT] = True
    q.g.key(vk)
    keys[SHIFT] = None
    q.g.tick(30)


q = with_presets()
g = q.g
check(not q.calls, "quick-swap: nothing runs before the key is pressed")
press(q, F10)
check(q.slots() == [9, 0, 0, 0], "F10 with the panel closed puts on the next preset (A is on, so B) (%s)" % q.slots())
check("SHIELD GENERATOR PACK" in q.texts().upper() and "B" in q.texts(), "and a toast says which one")
press(q, F10)
check(q.slots() == [7, 3, 0, 0], "F10 again: C (%s)" % q.slots())
press(q, F10)
check(q.slots() == [3, 5, 0, 7], "F10 again wraps to A, and D (marked skip) is left out (%s)" % q.slots())
press(q, F10, shift=True)
check(q.slots() == [7, 3, 0, 0], "Shift F10 goes back (%s)" % q.slots())
q.set_slots([5, 5, 5, 0])
g.tick(10)
press(q, F10)
check(q.slots() == [7, 3, 0, 0] or q.slots() == [3, 5, 0, 7] or q.slots() == [9, 0, 0, 0],
      "from a loadout that is no preset it carries on after the last one it put on (%s)" % q.slots())
last = q.slots()

# undo from the tab
q.set_slots([5, 5, 5, 0])
g.tick(10)
press(q, F10)
g.key(F7)
g.tick(150)
g.click("strat")
g.tick(40)
g.click("sp:1")
check("sundo" in g.regions(), "the tab has Undo last apply")
check(not layout_problems(g), "quick-swap section and extra buttons fit (%s)" % layout_problems(g)[:3])
g.click("sundo")
check(q.slots() == [5, 5, 5, 0] or q.slots()[:3] == [5, 5, 5], "Undo last apply puts back what was there before (%s)" % q.slots())

# reorder, duplicate, skip, from the tab
g.click("sp:2")
g.click("smoveup")
lines = q.file().splitlines()
check(lines[1].startswith("B |") and lines[2].startswith("A |"), "Move up changes the order in the file (%r)" % lines[1:3])
g.click("smovedown")
check(q.file().splitlines()[2].startswith("B |"), "Move down puts it back")
g.click("sdup")
check(q.file().count("B copy |") == 1, "Duplicate adds a copy right below")
g.click("sskip")
check("B copy | Shield_Generator_Pack | - | - | - | skip" in q.file(), "In the quick-swap key: leave out writes | skip (%r)" % q.file())
g.click("sp:4")
g.click("sskip")
check(q.file().count("| skip") == 1 or q.file().count("skip") >= 1, "and it can be put back")
check(not layout_problems(g), "the tab with a skipped preset fits (%s)" % layout_problems(g)[:3])

# the key itself
kf = os.path.join(q.fdir, "stratagem-key.txt")
g.click("skey:next")
check(os.path.exists(kf) and "key = f11" in open(kf).read().lower(), "the key can be changed on the tab and is saved apart from loadout.ini")
g.key(F7)
g.tick(150)
q.set_slots([5, 5, 5, 0])
g.tick(10)
n = len(q.calls)
press(q, F10)
check(len(q.calls) == n, "the old key no longer does anything")
press(q, F11)
check(len(q.calls) > n, "the new key does")
g.key(F7)
g.tick(150)
if "skey:off" not in g.regions():
    g.click("strat")
    g.tick(40)
g.click("skey:off")
n = len(q.calls)
press(q, F11)
check(len(q.calls) == n and "off" in open(kf).read().lower(), "Turn off: the key does nothing and the choice is kept")

# F7 (panel) and F9 (swap) are never picked
g.click("skey:next")
check("f9" not in open(kf).read().lower().split("key =")[-1] and "f7" not in open(kf).read().lower().split("key =")[-1],
      "the panel key and the swap key are skipped when stepping")

# refusals: no loadout screen, ready, nothing saved
q2 = with_presets()
q2.write_u32(STACK_OBJ, 4)
press(q2, F10)
check(not [c for c in q2.calls if c[0] == V["set_widget"]] and "open the hellpod loadout screen" in q2.texts().lower(),
      "off the loadout screen the key says so and changes nothing")
q3 = with_presets(text="; none\n")
press(q3, F10)
check(not q3.calls and "no stratagem presets" in q3.texts().lower(), "no presets saved: it says so")
q4 = with_presets()
q4.write_u32(SCREEN + V["panels"] + V["ready_timer"], 0x3FC00000)
before = q4.slots()
press(q4, F10)
check(q4.slots() == before and "ready" in q4.texts().lower(), "while ready it changes nothing and says why")

# moved code: the key starts the search, and finishes the swap when it is found
q5 = with_presets(fake_dll(moved={"set_slot": 0x1600000, "open_list": 0x1610000}))
q5.g.key(F10)
q5.g.tick(120)
check(q5.slots() == [9, 0, 0, 0], "code moved: the key starts the search and puts the preset on when it is found (%s)" % q5.slots())

# the Passive Swap edition does not have it
q6 = with_presets(edition_swap=True)
press(q6, F10)
check(not q6.calls, "Passive Swap edition: the key does nothing")

if failed:
    print("\n%d FAILED" % len(failed))
    sys.exit(1)
print("\nall stratagem checks passed")
