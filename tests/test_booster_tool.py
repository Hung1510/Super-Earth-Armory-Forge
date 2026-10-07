#!/usr/bin/env python3
"""
The booster names tool (tools/booster-names/): FileDiver plus a small dumper that reads a
game install and writes what its files say about boosters. The Windows exe is built in CI
(.github/workflows/booster-names-tool.yml); here: the pieces are all there and consistent.

    python tests/test_booster_tool.py
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
TOOL = os.path.join(ROOT, "tools", "booster-names")
failed = []


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        failed.append(what)


def read(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


build, bat, src = read(TOOL, "build.sh"), read(TOOL, "Run-me.bat"), read(TOOL, "dumper", "main.go")
flow = read(ROOT, ".github", "workflows", "booster-names-tool.yml")
check(all(os.path.exists(os.path.join(TOOL, f)) for f in ("build.sh", "Run-me.bat", "README.txt", "dumper/main.go")),
      "build.sh, Run-me.bat, README.txt and the dumper source are there")
if shutil.which("bash"):
    ok = subprocess.run(["bash", "-n", os.path.join(TOOL, "build.sh")]).returncode == 0
    check(ok, "build.sh is valid shell")
check("booster-dumper" in build and "dumper/main.go" in build and "booster-names-tool.zip" in build,
      "build.sh builds booster-dumper from dumper/main.go into booster-names-tool.zip")
check("booster-dumper.exe > boosters.json" in bat and "strings-en.json" in bat and "boosters.zip" in bat
      and "HD2_GAME_DIR" in bat and "game-dir.txt" in bat,
      "Run-me.bat writes boosters.json + strings-en.json, zips them, and takes a game folder (drag-and-drop / game-dir.txt)")
check("HD2_GAME_DIR" in src and "DetectGameDir" in src, "the dumper takes HD2_GAME_DIR, else detects the install")
for key in ("booster_enum", "known_booster_names", "entities", "files", "strings", "match_phrases"):
    check('json:"%s"' % key in src, "output has %s" % key)
check("tools/booster-names/build.sh" in flow and "booster-names-tool" in flow and "workflow_dispatch" in flow,
      "the workflow builds it and attaches booster-names-tool.zip")
if shutil.which("gofmt"):
    out = subprocess.run(["gofmt", "-l", os.path.join(TOOL, "dumper")], capture_output=True, text=True).stdout
    check(not out.strip(), "dumper/main.go is gofmt-clean")
check(not re.search(r"\bwrite\w*\(\s*\"[^\"]*(Helldivers|data)", src), "the dumper only reads the game install")

if failed:
    print("\n%d FAILED" % len(failed))
    sys.exit(1)
print("\nall booster tool checks passed")
