#!/usr/bin/env python3
"""
The optional Armor Reimagined add-on (addons/armor-reimagined): the shipped zip matches its recorded SHA-256,
is a valid mod zip, and the release workflow attaches it.

    python tests/test_addons.py
"""
import hashlib
import json
import os
import sys
import zipfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
D = os.path.join(ROOT, "addons", "armor-reimagined")
failed = []


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        failed.append(what)


name = "Helldivers-Armor-Reimagined-Forge-1.2.0.zip"
path = os.path.join(D, name)
sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
check(open(os.path.join(D, "SHA256.txt")).read().split()[0] == sha, "the zip matches its recorded SHA-256")
z = zipfile.ZipFile(path)
check(z.testzip() is None, "the zip is intact")
m = json.loads(z.read("manifest.json"))
check(m["Name"].startswith("Armor Reimagined") and "1.2.0" in m["Name"] and "Addon/9ba626afa44a3aa3.patch_0" in z.namelist(), "it is the Armor Reimagined mod")
wf = open(os.path.join(ROOT, ".github", "workflows", "release.yml"), encoding="utf-8").read()
check(name in wf, "the release workflow attaches the add-on")
if failed:
    print("\n%d FAILED" % len(failed))
    sys.exit(1)
print("\nall add-on checks passed")
