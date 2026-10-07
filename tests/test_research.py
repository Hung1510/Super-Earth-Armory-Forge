#!/usr/bin/env python3
"""
The research build (python tools/picker.py research): armor kit dump + weight experiment.

    python tests/test_research.py

1. Release and web-builder builds carry none of the research code.
2. The research build finds armor kit records (absolute pointers as loaded, and file-form
   relative ones), writes them to kits-dump.txt with every piece's slot and weight, and
   counts every table type it sees.
3. With --weight light, only the ARMOR pieces of ARMOR kits change; undergarments,
   helmets and capes are left alone, and passives still apply as usual.
4. With --weight none, nothing in memory changes.
"""
import json
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import picker  # noqa: E402
from harness import GAME_BASE, FakeGame  # noqa: E402

TYPE_KIT = 0xD9A55AA0
failed = []


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        failed.append(what)


def lut_of(kid, slot):
    """a colour LUT hash too big for a Lua number, so a lossy copy would show"""
    return 0xFC00000000000001 + (kid << 20) + (slot << 4)


def kit_block(at, kid, ktype, passive, bodies, relative=False):
    """One LDLD block holding a HelldiverCustomizationKit at address `at` (the header).
    bodies: [(body_type, [(slot, piece_type, weight), ...]), ...]"""
    rec = at + 24
    body_off = 64
    piece_off = body_off + 24 * len(bodies)
    blob = bytearray(64)
    struct.pack_into("<IIIIIIII", blob, 0, kid, 0, 0x5E7, 1, 2, 3, 1, passive)
    struct.pack_into("<QII", blob, 32, 0xA0C1100000000000 + kid, ktype, 0)
    struct.pack_into("<qq", blob, 48, body_off if relative else rec + body_off, len(bodies))
    pieces = bytearray()
    weights_at = []
    for btype, plist in bodies:
        start = piece_off + len(pieces)
        blob += struct.pack("<IIqq", btype, 0, start if relative else rec + start, len(plist))
        for slot, ptype, weight in plist:
            weights_at.append((rec + piece_off + len(pieces) + 16, ptype, weight))
            p = bytearray(96)
            struct.pack_into("<QIIIIQ", p, 0, 0x9A7B000000000000 + slot, slot, ptype, weight, 0, lut_of(kid, slot))
            pieces += p
    blob += pieces
    hdr = b"LDLD" + struct.pack("<III", 1, TYPE_KIT, len(blob)) + b"\0" * 8
    return hdr + bytes(blob), weights_at


def game_with_kits(lua_path):
    g = FakeGame(lua_path, appdata=tempfile.mkdtemp())
    mem = g.mem[GAME_BASE]
    pieces = {}
    at = 0x10000
    for name, args in (
        ("armor", dict(kid=0x1111, ktype=0, passive=7, bodies=[(1, [(2, 0, 2), (3, 1, 1), (6, 0, 2)])])),
        ("helmet", dict(kid=0x2222, ktype=1, passive=0, bodies=[(1, [(0, 0, 2)])])),
        ("file-form", dict(kid=0x3333, ktype=0, passive=11, bodies=[(0, [(2, 0, 1)]), (1, [(2, 0, 1)])], relative=True)),
        ("cape", dict(kid=0x4444, ktype=2, passive=0, bodies=[(3, [(1, 0, 1)])])),
    ):
        block, weights = kit_block(GAME_BASE + at, **args)
        mem[at:at + len(block)] = block
        pieces[name] = weights
        at += (len(block) + 64 + 15) & ~15
    return g, pieces


def weight_now(g, addr):
    return struct.unpack("<I", g._read(addr, 4))[0]


def dump_of(g):
    path = os.path.join(os.environ["LOCALAPPDATA"], "CowboyBingus", "Helldivers2", "ArmoryForge", "kits-dump.txt")
    return open(path, encoding="utf-8").read() if os.path.exists(path) else ""


def build(weight, lut=16):
    s, _ = picker.load_config_text("[settings]\nname = x\n[profile: Med-Kit]\n")
    path = tempfile.mktemp(suffix=".lua")
    with open(path, "w", encoding="utf-8") as f:
        f.write(picker.research_lua(s, weight, lut))
    return path


# ------------------------------------------------------------------ 1. not in releases
s, p = picker.load_config_text("[settings]\nname = x\n[profile: Med-Kit]\nFortified = on\n")
normal = picker.compile_loadout(s, p) + picker.compile_loadout(s, [], blank=True, swap_only=True)
check("research build only" not in normal and "research = {" not in normal,
      "normal and Passive Swap builds carry no research code")
check("research.lua" not in picker.RELEASE_TOOLS, "research.lua is not shipped in release zips")

# ------------------------------------------------------------------ 2 + 3. dump and light experiment
g, pieces = game_with_kits(build(0))
g.tick(1200)
text = dump_of(g)
check(g.phase() == "ready", "the research build still starts and applies passives")
check(all("kit 0x0000%s " % k in text for k in ("1111", "2222", "3333")), "kits-dump.txt lists the test's three kits")
check("kit 0x00001111 type 0 passive 7 (Med-Kit) weight heavy" in text, "a kit line has its passive and weight (as found)")
check("piece torso          type 0 weight heavy  path" in text and "-> light" in text,
      "every piece is listed with slot and weight, and changed ones say so")
check("type 0xD9A55AA0 " in text and "type 0x63CE0FEB " in text, "table types seen are counted")
check("  head " in text, "the first kits' raw bytes are included for checking the layout")
arm = pieces["armor"]
check(weight_now(g, arm[0][0]) == 0 and weight_now(g, arm[2][0]) == 0, "armor kit: armor pieces are now light")
check(weight_now(g, arm[1][0]) == 1, "armor kit: the undergarment piece is left alone")
check(weight_now(g, pieces["helmet"][0][0]) == 2, "helmet kits are left alone")
check(all(weight_now(g, a) == 0 for a, _, _ in pieces["file-form"]), "file-form (relative) pointers are followed too")
check("failed 0" in text and "pieces changed 0," not in text, "the dump counts the changes (%s)" %
      next((ln for ln in text.splitlines() if ln.startswith("pieces changed")), "-"))

# ------------------------------------------------------------------ 5. F10: where is the equipped armor?
LOAD = 0x30000000
g3, _ = game_with_kits(build(None, lut=7))
g3.mem[LOAD] = bytearray(0x10000)
struct.pack_into("<III", g3.mem[LOAD], 0x100, 0x1111, 0, 0)      # a loadout: armor, helmet, cape
struct.pack_into("<I", g3.mem[LOAD], 0x108, 0x2222)
struct.pack_into("<I", g3.mem[LOAD], 0x110, 0x4444)
struct.pack_into("<I", g3.mem[LOAD], 0x800, 0x1111)               # an armor id on its own: not a loadout
struct.pack_into("<I", g3.mem[LOAD], 0x120, 1)                    # the equipped booster (1 = Vitality) sits next to it
g3.tick(420)
lpath = os.path.join(os.environ["LOCALAPPDATA"], "CowboyBingus", "Helldivers2", "ArmoryForge", "loadout-research.txt")
g3.key(0x79)
g3.tick(300)
lt = open(lpath, encoding="utf-8").read() if os.path.exists(lpath) else ""
check("at 0x30000100: armor 0x00001111 (Med-Kit) | helmet 0x00002222 (+8) | cape 0x00004444 (+16)" in lt,
      "F10 finds the armor + helmet + cape ids stored together")
check("0x30000800" not in lt, "... and not an armor id on its own")
check(not any("0x%X" % (GAME_BASE + 0x10000) in ln for ln in lt.splitlines()), "... nor the kit records themselves")
struct.pack_into("<I", g3.mem[LOAD], 0x100, 0x3333)               # the player equips another armor
struct.pack_into("<I", g3.mem[LOAD], 0x120, 2)                    # ... and Stamina instead of Vitality
g3.key(0x79)
g3.tick(300)
lt = open(lpath, encoding="utf-8").read()
check("CHANGED 0x30000100: armor 0x00001111 (Med-Kit) -> armor 0x00003333 (Inflammable)" in lt,
      "F10 again: the place that now holds the new armor is reported")

check("place 0x30000100: " in lt and "+32: 1 -> 2   <- booster?" in lt,
      "F10 again: the word that went from booster 1 to booster 2 next to the armor id is flagged")
check("+0: 4369 -> 13107   <- booster?" not in lt, "... and the armor id changing is not mistaken for a booster")

# ------------------------------------------------------------------ 6. F11: another armor's colours
arm_pieces = [GAME_BASE + 0x10000 + 24 + 64 + 24 + i * 96 for i in range(3)]   # kit 0x1111, one body
before = [bytes(g3._read(a + 24, 8)) for a in arm_pieces]
known = {struct.pack("<Q", lut_of(0x3333, 2))} | {struct.pack("<Q", g3.lut(kid, s)) for kid in g3.kit_pieces for s in range(10)}
g3.key(0x7A)
after = [bytes(g3._read(a + 24, 8)) for a in arm_pieces]
check(after != before and all(a in known for a in after),
      "F11: the Med-Kit armor takes another armor's colour LUT, all 64 bits exact")
for presses in range(1, 60):  # noqa: B007 (reported below)
    if [bytes(g3._read(a + 24, 8)) for a in arm_pieces] == before:
        break
    g3.key(0x7A)
check([bytes(g3._read(a + 24, 8)) for a in arm_pieces] == before, "F11 after the last armor: its own colours back (%d presses)" % presses)

# ------------------------------------------------------------------ 4. dump only
g2, pieces2 = game_with_kits(build(None))
g2.tick(1200)
text2 = dump_of(g2)
check("experiment none (dump only)" in text2 and "pieces changed 0" in text2, "--weight none only dumps")
check(all(weight_now(g2, a) == w for kind in pieces2.values() for a, _, w in kind), "... and changes nothing in memory")

# ------------------------------------------------------------------ 7. boosters: where are the definitions?
ANCH = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools", "booster-anchors.json")))
by_name = {}
for k, v in ANCH.items():
    by_name.setdefault(v, int(k))
check(len(ANCH) >= 28 and len(by_name) == 15, "booster-anchors.json: 15 booster titles, upper and cased ids (%d ids)" % len(ANCH))
check("[%s]=%s" % (by_name["Dead Sprint"], json.dumps("Dead Sprint")) in open(build(None), encoding="utf-8").read(),
      "the research build carries the anchor ids")
g4, _ = game_with_kits(build(None))
BLK = len(g4.mem[GAME_BASE])                               # appended after the kits
payload = bytearray(1024)
for i, name in enumerate(("Dead Sprint", "Stun Pods", "Armed Resupply Pods")):
    struct.pack_into("<IIff", payload, i * 64, by_name[name], i + 10, 1.5 + i, 0.25)
struct.pack_into("<I", payload, 700, 0x12345678)
hdr = b"LDLD" + struct.pack("<III", 1, 0xB0057E50, len(payload)) + b"\0" * 8
g4.mem[GAME_BASE][BLK:BLK + len(hdr) + len(payload)] = hdr + bytes(payload)
EFF = bytearray(512)                                          # a table that reuses the armor passives' modifier ids
struct.pack_into("<IIfIIf", EFF, 0x20, 0x2875F44A, 1, 2.0, 0x93EB16A7, 1, 5.0)
ehdr = b"LDLD" + struct.pack("<III", 1, 0xB0057E51, len(EFF)) + b"\0" * 8
at2 = len(g4.mem[GAME_BASE]) + 16
g4.mem[GAME_BASE][at2:at2 + len(ehdr) + len(EFF)] = ehdr + bytes(EFF)
g4.mem[0x31000000] = bytearray(0x4000)                       # not an LDLD block: a cluster in plain memory
for i, name in enumerate(("Firebomb Hellpods", "Dead Sprint", "Muscle Enhancement")):
    struct.pack_into("<II", g4.mem[0x31000000], 0x200 + i * 48, by_name[name], i)
g4.tick(1200)
bpath = os.path.join(os.environ["LOCALAPPDATA"], "CowboyBingus", "Helldivers2", "ArmoryForge", "boosters-research.txt")
bt = open(bpath, encoding="utf-8").read() if os.path.exists(bpath) else ""
check("block 0x%X type 0xB0057E50 payload 1024 hits 3" % (GAME_BASE + BLK) in bt, "the scan finds the unknown LDLD block that holds booster titles")
check("hit +0x0000 Dead Sprint" in bt and "hit +0x0040 Stun Pods" in bt and "hit +0x0080 Armed Resupply Pods" in bt,
      "... and says which title sits at which offset (stride 0x40)")
check("%08X" % by_name["Stun Pods"] in bt and "0000000B" in bt, "... with the words around each hit in hex")
bt = open(bpath, encoding="utf-8").read()
check("## whole-memory scan 1" in bt, "the whole-memory scan starts by itself, no key needed")
check("type 0xB0057E51 payload 512 hits 2" in bt and "hit +0x0020 stims" in bt and "hit +0x002C stim_duration" in bt,
      "a non-passive table using the passives' modifier ids is reported, with the ids' names")
check("type 0xB0057E51 1 512 512" in bt and "type 0xB0057E50 1 1024 1024" in bt and "head +0x0000: " in bt,
      "every other table type is listed with its size and first bytes")
g4.key(0x73)
g4.tick(600)
bt = open(bpath, encoding="utf-8").read()
check("## whole-memory scan 2" in bt and "cluster at 0x31000200, " in bt and "3 distinct title(s)" in bt,
      "F4 scans again: titles close together in plain memory are reported as a cluster")
check("hit 0x31000260 Muscle Enhancement" in bt, "... with each hit's address and title")
check(os.path.exists(bpath) and "0x12345678" not in bt and "12345678" not in bt, "words far from any hit are not dumped")

if failed:
    print("\n%d FAILED" % len(failed))
    sys.exit(1)
print("\nall research checks passed")
