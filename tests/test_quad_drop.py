#!/usr/bin/env python3
"""
Super Earth Quad Drop (7.0): the support-weapon four-item drop, built as its own zip.

    python tests/test_quad_drop.py

1. The zip: manifest, the three archive files, no scripts, credit to Antigravity in the README.
2. The archive holds the Lua under its own mod id, with the envelope length right, and it compiles.
3. Run against a fake HD2Runtime + Mod Options Menu: 4 menu categories (one row per toggle / weapon),
   22 guarded operations (17 standard racks with 4 slots written, 5 heavy), every rack asked for
   spawn_count 4, and the Supply Box replaces the extra gun only while its toggle is on.
4. An older Runtime (0.28.0) is refused with a logged error, nothing is written.
"""
import os
import struct
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import picker  # noqa: E402

failed = []


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        failed.append(what)


class A:
    def __init__(self, zip):
        self.zip = zip


tmp = tempfile.mkdtemp()
out = os.path.join(tmp, "qd.zip")
check(picker.cmd_quad_drop(A(out)) == 0, "quad-drop builds")
z = zipfile.ZipFile(out)
names = sorted(z.namelist())
check(names == ["Addon/9ba626afa44a3aa3.patch_0", "Addon/9ba626afa44a3aa3.patch_0.gpu_resources",
                "Addon/9ba626afa44a3aa3.patch_0.stream", "README.txt", "manifest.json"], "zip holds the manifest, the archive and the README only")
check(not any(n.endswith((".lua", ".py", ".exe", ".ps1", ".bat")) for n in names), "no scripts or executables in the zip")
readme = z.read("README.txt").decode()
check("Antigravity" in readme and "ayakamods.com/mods/support-weapon-quad-drop" in readme, "the README credits Antigravity and links the original")
check("HD2Runtime 0.28.1" in readme, "the README lists what it needs")
import json  # noqa: E402
man = json.loads(z.read("manifest.json"))
check(man["Name"] == "Super Earth Quad Drop v%s" % picker.VERSION and man["Options"][0]["Include"] == ["Addon"], "manifest name and Addon option")

arc = z.read("Addon/" + picker.ARCHIVE_NAME)
magic, _ver, count = struct.unpack("<III", arc[:12])
ent = struct.unpack("<7Q6I", arc[104:184])
check(magic == picker.MAGIC and count == 1 and ent[0] == picker.resource_hash(picker.QD_ID), "archive: one resource under the Quad Drop mod id")
blob = arc[ent[2]:ent[2] + ent[7]]
size, envv = struct.unpack("<II", blob[:8])
lua = blob[8:].decode("utf-8")
check(size == len(blob) - 8 and envv == picker.ENVELOPE_VERSION, "archive: envelope length and version")
check(lua.startswith("-- HD2-Addon: " + picker.QD_ID + "\n") and "@VERSION@" not in lua, "Lua has the addon marker and the version filled in")
ok, err = picker.compile_lua(lua)
check(ok is not False, "the Lua compiles %s" % (err or ""))

# ---- run it against a fake runtime
try:
    from lupa.luajit21 import LuaRuntime
except Exception:
    LuaRuntime = None
if LuaRuntime is None:
    print("skip  fake-runtime run (lupa not installed)")
else:
    HARNESS = r'''
    local function new_runtime(version)
        local log, menu_rows, ops = {}, {}, {}
        local R = {version = version, api_version = 1, fields = {payload = {entity = 'entity', spawn_count = 'spawn_count'}}}
        local function handle(kind, cfg)
            local h = {kind = kind, cfg = cfg, listeners = {}, value = cfg.default}
            function h.get(self)
                if kind == 'toggle' then return self.value end
                return cfg.values and cfg.values[self.value] or self.value
            end
            function h.subscribe(self, fn) self.listeners[#self.listeners + 1] = fn end
            return h
        end
        R.handles = {}
        function R.options(cfg)
            local o = {}
            function o:toggle(c) local h = handle('toggle', c); R.handles[cfg.id .. '.' .. c.id] = h; return h end
            function o:choice(c) local h = handle('choice', c); R.handles[cfg.id .. '.' .. c.id] = h; return h end
            return o
        end
        function R.pickup(name) if name == 'None (Empty)' then return 'empty' end return 'pickup:' .. name end
        function R.pod_rack(name)
            return {name = name, slot = function(self, n) return {rack = name, n = n} end}
        end
        function R.ensure(cfg) ops[#ops + 1] = cfg; return {status = 'ok'} end
        local menu = {api = 1, register_option = function(id, spec) menu_rows[#menu_rows + 1] = {id = id, spec = spec}; return true end}
        local ticks = {}
        local loader = {open_log = function(self, name) return {write = function(_, line) log[#log + 1] = line end, flush = function() end} end,
                        register_tick = function(fn) ticks[#ticks + 1] = fn end}
        return R, menu, loader, log, menu_rows, ops, ticks
    end
    return new_runtime
    '''

    def run(version):
        lr = LuaRuntime(unpack_returned_tuples=True)
        new_runtime = lr.execute(HARNESS)
        R, menu, loader, log, rows, ops, ticks = new_runtime(version)
        g = lr.globals()
        g.ModOptionsMenu, g.CowboyBingusModLoader, g.HD2RuntimeLibraryApi1 = menu, loader, R
        lr.eval("function(r) package.preload['mods/skyeshade/hd2runtime'] = function() return r end end")(R)
        # open_log is called as loader.open_log(name) in the addon
        lr.execute("CowboyBingusModLoader.open_log = (function(f) return function(name) return f(CowboyBingusModLoader, name) end end)(CowboyBingusModLoader.open_log)")
        state = lr.eval("function(s) return load(s, 'quad_drop')() end")(lua)
        for fn in ticks.values():
            fn()
            fn()
        return lr, state, log, rows, ops, R

    lr, state, log, rows, ops, R = run("0.28.1")
    nrows = len(rows)
    ids = [rows[i]["id"] for i in rows]
    check(nrows == len(set(ids)) and nrows > 60, "menu: %d rows, ids unique" % nrows)
    check({i.split(".")[0] for i in ids} == {"support_backpack_pairs", "support_backpack_extra", "support_backpack_gun", "support_supply_box"}, "menu: the 4 categories")
    check(state["menu"] and state["runtime"], "menu registered and the runtime started")
    n_ops = len(ops)
    check(n_ops == 22, "22 guarded operations (got %d)" % n_ops)
    std = heavy = 0
    for i in ops:
        o = ops[i]["plan"]["operations"]
        ids_ = [o[j]["id"] for j in o]
        last = o[len(o)]
        if last["id"] != "four-items" or last["value"] != 4:
            failed.append("rack %s does not end in spawn_count 4" % ops[i]["plan"]["id"])
        if len(o) == 4:
            std += 1
            check_ids = ids_ == ["extra-gun-slot-2", "backpack-slot-3", "backpack-slot-4", "four-items"]
        else:
            heavy += 1
            check_ids = ids_ == ["backpack-slot-3", "extra-gun-slot-4", "four-items"]
        if not check_ids:
            failed.append("slots of %s: %s" % (ops[i]["plan"]["id"], ids_))
    check(std == 17 and heavy == 5, "17 standard racks (slots 2,3,4) and 5 heavy racks (slots 3,4)")
    check(not any("rejected" in l.lower() or "failed" in l.lower() for l in log.values()), "no error in the log")

    # the Supply Box replaces the extra gun while its toggle is on; the extra gun comes back when it is off
    first = ops[1]["plan"]["operations"][1]            # extra-gun-slot-2 of the first standard rack
    gun = first["value"]
    check(gun.get(gun) == "pickup:pickup/v1/supply-box/d0e8fed8c01ceb1f", "Supply Box on: the opposite bay holds the Supply Box")
    sup = R.handles["support_supply_box.enabled"]
    check(sup.value is True, "Supply Box toggle defaults to on")
    sup.value = False
    check(gun.get(gun) == "pickup:MG-43 Machine Gun" or gun.get(gun) == "pickup:EAT-17 Expendable Anti-Tank", "Supply Box off: the extra gun is back (%s)" % gun.get(gun))
    R.handles["support_backpack_gun.enabled"].value = False
    check(gun.get(gun) == "empty", "Supply Box off and Extra Gun off: the bay is empty")
    b1 = ops[1]["plan"]["operations"][2]["value"]
    check(b1.get(b1) != "empty", "Bay 1 backpack is set by default")
    R.handles["support_backpack_pairs.enabled"].value = False
    check(b1.get(b1) == "empty", "Bay 1 off: empty")

    lr2, state2, log2, rows2, ops2, R2 = run("0.28.0")
    check(state2["menu"] and not state2["runtime"] and "incompatible" in (state2["error"] or ""), "Runtime 0.28.0 is refused with a logged error")
    check(len(ops2) == 0, "nothing registered on an old Runtime")

print()
print("all quad drop checks passed" if not failed else "FAILED: %d" % len(failed))
sys.exit(1 if failed else 0)
