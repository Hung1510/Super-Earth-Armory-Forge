#!/usr/bin/env python3
"""
The offline loadout.ini editor: validation is the mod's own parser, install/restore keep a backup,
and the standalone zip runs on its own.

    python tests/test_offline_editor.py
"""
import os
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, "..", "tools")
sys.path.insert(0, TOOLS)
import offline_editor as ed  # noqa: E402
import picker  # noqa: E402

failed = []


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        failed.append(what)


# ------------------------------------------------------------------ 1. validation = the mod's parser
tpl = ed.fresh_template()
n, err = ed.validate_text(tpl)
check(err is None and n == 1, "the starter file is valid (1 profile)")
check(ed.validate_text("[profile: Med-Kit]\nconflicts = stack   ; comment\n")[1] is None, "inline ; comments are accepted, like the mod")
check("conflicts" in (ed.validate_text("[profile: Med-Kit]\nconflicts = best\n")[1] or ""), "bad conflicts value is named")
check("weight" in (ed.validate_text("[profile: Med-Kit]\nweight = huge\n")[1] or ""), "bad weight value is named")
check(ed.validate_text("[settings]\nname = x\n")[1] is not None, "no profile at all is rejected")
check(ed.validate_text("[profile: Med-Kit]\n[profile: Med-Kit]\n")[1] is not None, "duplicate section is rejected")
check(ed.validate_text("[profile: Not A Passive]\n")[1] is not None, "unknown passive is rejected")

# ------------------------------------------------------------------ 2. install / restore
with tempfile.TemporaryDirectory() as d:
    dest = os.path.join(d, "Armory", "loadout.ini")
    ed.install(tpl, dest)
    check(open(dest, encoding="utf-8").read() == tpl and not os.path.exists(dest + ".backup"), "first install writes the file, nothing to back up")
    second = tpl.replace("My Armory Build", "Second")
    ed.install(second, dest)
    check(open(dest + ".backup", encoding="utf-8").read() == tpl, "second install backs up the first")
    try:
        ed.install("[profile: Nope]\n", dest)
        check(False, "an invalid file is refused")
    except ValueError:
        check(open(dest, encoding="utf-8").read() == second, "an invalid file is refused and the installed one is untouched")
    check(ed.restore(dest) and open(dest, encoding="utf-8").read() == tpl, "restore puts the backup back")
    check(open(os.path.join(d, "Armory", "loadout.ini.before-restore"), encoding="utf-8").read() == second, "restore keeps the file it replaced")
    check(not ed.restore(os.path.join(d, "none", "loadout.ini")), "restore with no backup says so")

# ------------------------------------------------------------------ 3. the standalone zip
with tempfile.TemporaryDirectory() as d:
    zp = os.path.join(d, "ed.zip")
    check(ed.main(["--zip", zp]) == 0, "--zip builds")
    z = zipfile.ZipFile(zp)
    names = set(z.namelist())
    want = {ed.PACKAGE_ROOT + "/" + f for f in ed.PACKAGE_FILES + ("Run-Offline-Editor.bat", "README.txt")}
    check(names == want, "zip holds the editor, parser, catalog, launcher and README only")
    z.extractall(d)
    root = os.path.join(d, ed.PACKAGE_ROOT)
    ini = os.path.join(root, "t.ini")
    open(ini, "w", encoding="utf-8").write(tpl)
    r = subprocess.run([sys.executable, "-I", os.path.join(root, "offline_editor.py"), "--check", ini], capture_output=True, text=True, cwd=root)
    check(r.returncode == 0 and "OK" in r.stdout, "the extracted copy validates a file on its own (--check)")
    open(ini, "w", encoding="utf-8").write("[profile: Nope]\n")
    r = subprocess.run([sys.executable, "-I", os.path.join(root, "offline_editor.py"), "--check", ini], capture_output=True, text=True, cwd=root)
    check(r.returncode == 1 and "INVALID" in r.stdout, "--check exits 1 on a bad file")
    check(picker.VERSION in z.read(ed.PACKAGE_ROOT + "/README.txt").decode(), "README carries the version")

if failed:
    print("\n%d FAILED" % len(failed))
    sys.exit(1)
print("\nall offline editor checks passed")
