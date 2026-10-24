"""Build the offline web builder: docs/ plus data.js (the catalog inline), no network, opens from disk.

    python tools/offline_web.py [--zip OUT.zip]

It only makes the page that writes a preset / mod zip for you. Nothing here touches the game's files.
Run `python tools/picker.py export-web` first so docs/data.json is current.
"""
import argparse, json, os, re, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(os.path.dirname(HERE), "docs")
SKIP = {"ARCHITECTURE.md"}
ROOT = "Super Earth Armory Forge Web Builder (offline)"

README = """Super Earth Armory Forge - Web Builder (offline)

1. Open index.html in your browser (double-click). No install, no internet needed.
2. Pick your passives and download the result.
3. Put the download where the Armory Forge mod reads it (see the mod's README).

This page only writes a preset / mod zip. It does not touch the game or its files.
The mod itself still needs a working Lua loader (Bingus Shared Loader) in the game.
The mod-zip icon is left out offline (browsers block reading it from disk); it is optional.
"""


def build(out):
    with open(os.path.join(DOCS, "data.json"), encoding="utf-8") as f:
        data = json.load(f)
    data_js = "window.ARMORY_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
    with open(os.path.join(DOCS, "index.html"), encoding="utf-8", newline="") as f:
        html = f.read()
    tag = '<script src="app.js"></script>'
    if html.count(tag) != 1:
        raise SystemExit("index.html: expected exactly one app.js script tag")
    html = html.replace(tag, '<script src="data.js"></script>\n' + tag)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for base, dirs, files in os.walk(DOCS):
            dirs.sort()
            for name in sorted(files):
                path = os.path.join(base, name)
                rel = os.path.relpath(path, DOCS).replace(os.sep, "/")
                if rel in SKIP or rel == "data.json" or rel == "index.html":
                    continue
                z.write(path, f"{ROOT}/{rel}")
        z.writestr(f"{ROOT}/index.html", html)
        z.writestr(f"{ROOT}/data.js", data_js)
        z.writestr(f"{ROOT}/README.txt", README)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", default=os.path.join(os.path.dirname(HERE), "dist", "Super-Earth-Armory-Forge-WebBuilder-offline.zip"))
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.zip)), exist_ok=True)
    build(a.zip)
    print("wrote", a.zip)
