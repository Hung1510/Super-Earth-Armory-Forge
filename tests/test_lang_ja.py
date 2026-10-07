#!/usr/bin/env python3
"""
6.4: the panel in Japanese (tools/lang_ja.lua). Passive and armor names are the game's own
Japanese text (FileDiver's dump, tools/armor_names.py --lang ja); the rest is translated.

    python tests/test_lang_ja.py

1. Keys tab, 日本語: labels, passive names, effects and messages are Japanese; names inside
   sentences are looked up too ("Reset Scout" -> "Scout をリセット" with the Japanese name).
2. The data stays English: loadout.ini and share codes don't change with the language.
3. A game font without the characters: the panel stays English and the Keys tab says why;
   punctuation the font lacks gets an ASCII stand-in instead of a "?".
4. The table lines up with the Chinese one: same strings, same sentence patterns, and the
   official names of every armor and passive the mod knows.
5. Every view, both editions: nothing left in English but key names and codes.
"""
import base64
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import picker  # noqa: E402
from harness import FakeGame  # noqa: E402

F7 = 0x76
failed = []
JA = re.compile(r"[぀-ヿ一-鿿]")


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        failed.append(what)


def pid(name):
    return next(k for k, v in picker.CATALOG.items() if v[0].lower() == name.lower())


def build(text, **kw):
    s, p = picker.load_config_text(text)
    path = tempfile.mktemp(suffix=".lua")
    with open(path, "w", encoding="utf-8") as f:
        f.write(picker.compile_loadout(s, p, **kw))
    return path


def forge(app, name):
    return os.path.join(app, "CowboyBingus", "Helldivers2", "ArmoryForge", name)


def session(lua, lang="ja", missing=None, wear=None):
    app = tempfile.mkdtemp()
    os.makedirs(os.path.dirname(forge(app, "x")))
    with open(forge(app, "panel-position.txt"), "w", encoding="utf-8") as f:
        f.write("lang = %s\n" % lang)
    g = FakeGame(lua, appdata=app)
    g.missing_glyphs = missing
    if wear:
        g.wear(wear)
    g.tick(420)
    g.key(F7)
    g.tick(120)
    return g, app


def joined(g):
    return " | ".join(g.texts())


SINK = open(os.path.join(HERE, "..", "presets", "01-kitchen-sink.ini"), encoding="utf-8").read()

# ------------------------------------------------------------------ 1. Japanese
g, app = session(build(SINK), wear=pid("Med-Kit"))
t = joined(g)
check("兵器庫" in t and "鍛造" in t and "+ アーマー" in t and "プリセット" in t, "title and tabs in Japanese")
check("医療キット" in t and "追加パッド" in t, "passive names: the game's own Japanese names")
check("医療キット：" in t and "パッシブを適用中" in t, "the header (what you're wearing) in Japanese")
g.click("sel:%d" % pid("Scout"))
t = joined(g)
check("偵察 をリセット" in t, "names inside sentences are looked up too: 'Reset Scout'")
g.click("guide")
t = joined(g)
check("使い方" in t and "操作" in t and "CTRL+Z" in t and "BACK" in t, "Guide tab in Japanese; key names stay as printed on the keys")
check(not any(x.startswith(("、", "。", "）", "」", "ー", "・")) for x in g.texts()), "wrapped Japanese lines never start with a closing mark")
g.click("settings")
check(all("lang:" + c in g.regions() for c in ("en", "zh", "ja")), "Keys tab: Language buttons English / 简体中文 / 日本語")
g.click("lang:zh")
check("军械" in joined(g), "switching to Chinese from the Japanese panel works")
g.click("lang:ja")
check("兵器庫" in joined(g) or "キー" in joined(g), "... and back to Japanese")

# ------------------------------------------------------------------ 2. data stays English
g.click("tab:1")
g.click("copy")
code = (g.clipboard() or "").split("#ini=")[1]
share = base64.urlsafe_b64decode(code + "=" * (-len(code) % 4)).decode()
check("[profile: %d]" % pid("Med-Kit") in share and not JA.search(share), "share codes stay as they were (no Japanese)")
g.click("tick:%d" % pid("Servo-Assisted"))
g.key(F7)
saved = open(forge(app, "loadout.ini"), encoding="utf-8").read()
check("[profile: Med-Kit]" in saved and "Servo-Assisted" in saved and not JA.search(saved), "loadout.ini stays English")
pos = open(forge(app, "panel-position.txt"), encoding="utf-8").read()
check("lang = ja" in pos, "the language is remembered")
s, p = picker.load_config_text(saved)
check(any(x["perk"] == pid("Med-Kit") for x in p), "... and loads anywhere (English panel, web builder)")
check(b"can be drawn" in (g.state[b"pp"][b"font_result"] or b""), "the font test finds the characters")

# ------------------------------------------------------------------ 3. the game font
gn, _ = session(build(SINK), missing="all")
t = joined(gn)
check("ARMORY" in t and "兵器庫" not in t, "a font without Japanese: the panel stays English")
gn.click("settings")
check(any("set the game's text language to match" in x for x in gn.texts()), "... and the Keys tab says why")
gp, _ = session(build(SINK), missing={"、", "。"})
t = joined(gp)
check("兵器庫" in t and "、" not in t and "。" not in t, "punctuation the font lacks gets an ASCII stand-in, the rest is Japanese")

# ------------------------------------------------------------------ 4. the table
zh, ja = picker.lang_names(picker.LANG_ZH), picker.lang_names(picker.LANG_JA)
check(all(set(zh[g_]) == set(ja[g_]) for g_ in zh), "same strings as the Chinese table in every group: " + ", ".join(
    "%s %d/%d" % (g_, len(ja[g_]), len(zh[g_])) for g_ in zh))


def patterns(path):
    text = open(path, encoding="utf-8").read()
    body = re.search(r"^    pat = \{\n(.*?)^    \},", text, re.S | re.M).group(1)
    return re.findall(r"\{ ('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"),", body)


check(patterns(picker.LANG_ZH) == patterns(picker.LANG_JA), "same sentence patterns, in the same order")
names = json.load(open(os.path.join(HERE, "..", "tools", "armor-names.json"), encoding="utf-8"))["kits"]
official = {v["name"]: v["names"]["ja"] for v in names.values() if v.get("name") and v.get("names", {}).get("ja")
            and re.search(r"[A-Za-z]{3}", v["name"])}
missing = sorted(n for n in official if n not in ja["armor"])
check(not missing, "every armor in the dump has its Japanese name in the table%s" % (": " + ", ".join(missing[:5]) if missing else ""))
check(all(ja["armor"][n] == official[n] for n in official if n in ja["armor"]), "armor names are exactly the game's text")
passives = json.load(open(os.path.join(HERE, "..", "tools", "passive-text.json"), encoding="utf-8"))["passives"]
bad = [k for k, v in passives.items() if v["ja"]["name"] not in ja["perk"].values()]
check(not bad, "every armor passive has the game's own Japanese name%s" % (": " + ", ".join(bad) if bad else ""))
check(ja["perk"]["Med-Kit"] == "医療キット" and ja["perk"]["Electrical Conduit"] == "導電管", "spot check: Med-Kit, Electrical Conduit")
long_ = [(k, v) for k, v in ja["ui"].items() if len(v) > 2.2 * len(k) + 12]
check(not long_, "no translation far longer than its English (layout)%s" % (": " + repr(long_[:2]) if long_ else ""))

# ------------------------------------------------------------------ 5. coverage
ALLOWED = re.compile(r"(?i)(F\d+|CTRL.*|PGUP.*|PGDN|ENTER|ESC|BACK|START|D-PAD|LB|RB|R-STICK|CLICK|WHEEL|DRAG|V[\d.]+|"
                     r"KEYS TAB|ENGLISH|English|LANGUAGE  /  语言|.*CTRL.*|.*loadout\.ini.*|.*SHODAN.*|.*bug.*|.*Esc.*)")


def leftovers(g, seen):
    for x in g.texts():
        y = re.sub(r"(?<![A-Za-z_])(Mod|Web|Armory Forge|Nexus|SHODAN Stat Editor|loadout\.ini|hotkey|swap_hotkey)(?![A-Za-z_])", "", x)
        if re.search(r"[A-Za-z]{3,}", y) and not ALLOWED.fullmatch(x):
            seen.add(x)


seen = set()
g, _ = session(build(SINK), wear=pid("Med-Kit"))
for k in ["sel:summary", "sel:weight", "sel:%d" % pid("Med-Kit"), "sel:%d" % pid("Siege-Ready"), "add", "addcancel",
          "presets", "settings", "guide", "tab:1", "remove"]:
    if k in g.regions():
        g.click(k)
        leftovers(g, seen)
gs, _ = session(build("[settings]\nname = x\n[profile: Med-Kit]\n", blank=True, swap_only=True), wear=pid("Siege-Ready"))
leftovers(gs, seen)
gs.click("wear")
gs.click([k for k in gs.regions() if k.startswith("swap:")][2])
leftovers(gs, seen)
gs.click("guide")
leftovers(gs, seen)
check(not seen, "every view, both editions: nothing left in English but keys and codes%s"
      % ("".join("\n        " + x for x in sorted(seen))))

if failed:
    print("\n%d FAILED" % len(failed))
    sys.exit(1)
print("\nall Japanese language checks passed")
