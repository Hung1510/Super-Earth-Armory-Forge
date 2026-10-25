#!/usr/bin/env python3
"""Offline editor for Armory Forge's loadout.ini (Windows, Python 3.10+ with Tk).

    python tools/offline_editor.py                 # open the editor
    python tools/offline_editor.py --check FILE    # validate a loadout.ini, no window (exit 1 on error)
    python tools/offline_editor.py --zip OUT.zip   # the standalone download (editor + parser + catalog)

It edits one text file: the loadout.ini the mod reads from
%LOCALAPPDATA%\\CowboyBingus\\Helldivers2\\ArmoryForge\\loadout.ini (the in-game panel and the web
builder write the same format). Validation is the mod's own parser, so "Valid" here means the mod
accepts the file. The editor never touches the game, its archives or any other file.
"""
import argparse
import contextlib
import io
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import picker  # noqa: E402  (stdlib only; the same file the build tool and the tests use)

APP = "Armory Forge Offline Editor"
LOCAL = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
CONFIG = LOCAL / "CowboyBingus" / "Helldivers2" / "ArmoryForge" / "loadout.ini"
BACKUP = CONFIG.with_name("loadout.ini.backup")
BEFORE_RESTORE = CONFIG.with_name("loadout.ini.before-restore")
PACKAGE_ROOT = "Armory-Forge-Offline-Editor"
PACKAGE_FILES = ("offline_editor.py", "picker.py", "passives.json", "armor-names.json")

RUN_BAT = """@echo off
cd /d "%~dp0"
py -3 offline_editor.py
if errorlevel 1 python offline_editor.py
if errorlevel 1 pause
"""

README = """Super Earth Armory Forge - Offline Editor (v{v})

A small Windows editor for Armory Forge's loadout.ini. It edits that one text file and
nothing else: it never touches the game, its archives or any other mod's files.

You need: Python 3.10 or newer from python.org (tick "Add python.exe to PATH" in the
installer; it includes Tk, which the editor uses), plus Armory Forge and Bingus Shared
Loader installed in your mod manager as usual.

RUN
1. Extract this folder somewhere you can write (Documents is fine).
2. Double-click Run-Offline-Editor.bat. If the window closes at once, open Command
   Prompt in this folder and run:  python offline_editor.py   (it prints the error).
3. The editor offers to open your current loadout.ini. Or press New for a fresh one.
   Double-click a passive in the list on the right to add it at the cursor.
4. Press Validate. It uses the mod's own parser, so it names the exact line/section the
   mod would reject (unknown passive, bad value, two profiles on one trigger, ...).
5. Press Install config. It saves to
     %LOCALAPPDATA%\\CowboyBingus\\Helldivers2\\ArmoryForge\\loadout.ini
   after backing up the old one. The running mod reloads the file within a couple of
   seconds; no game restart.
6. Something off? Restore config backup puts the previous file back (the file you had
   before the restore is kept as loadout.ini.before-restore).

Command line: python offline_editor.py --check my.ini   (validate without a window)

The in-game panel (F7) and the web builder edit the same file, so you can mix them.
Single-player / private lobbies only.
"""


def validate_text(text):
    """(profile_count, error_or_None) using the mod's own loadout.ini parser."""
    try:
        _settings, profiles = picker.load_config_text(text, "loadout.ini")
    except picker.ConfigError as e:
        return 0, str(e)
    except Exception as e:      # configparser errors: duplicate section, line without "=", ...
        return 0, "%s: %s" % (type(e).__name__, e)
    return len(profiles), None


def fresh_template():
    """The same starter file `picker.py init` writes."""
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "loadout.ini")
        with contextlib.redirect_stdout(io.StringIO()):
            picker.cmd_init(argparse.Namespace(output=out, force=True))
        with open(out, encoding="utf-8") as f:
            return f.read()


def install(text, dest=None, backup=None):
    """Validate, back up the existing file, write the new one. Raises ValueError if it is invalid."""
    dest = Path(dest or CONFIG)
    backup = Path(backup or dest.with_name("loadout.ini.backup"))
    _n, err = validate_text(text)
    if err:
        raise ValueError(err)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.copy2(dest, backup)
    dest.write_text(text, encoding="utf-8", newline="\n")
    return dest


def restore(dest=None, backup=None, before=None):
    """Put the backup back, keeping the current file as loadout.ini.before-restore. False if no backup."""
    dest = Path(dest or CONFIG)
    backup = Path(backup or dest.with_name("loadout.ini.backup"))
    before = Path(before or dest.with_name("loadout.ini.before-restore"))
    if not backup.exists():
        return False
    if dest.exists():
        shutil.copy2(dest, before)
    shutil.copy2(backup, dest)
    return True


def build_zip(out):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in PACKAGE_FILES:
            z.write(os.path.join(HERE, name), "%s/%s" % (PACKAGE_ROOT, name))
        z.writestr("%s/Run-Offline-Editor.bat" % PACKAGE_ROOT, RUN_BAT.replace("\n", "\r\n"))
        z.writestr("%s/README.txt" % PACKAGE_ROOT, README.format(v=picker.VERSION).replace("\n", "\r\n"))


def run_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    class App(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title(APP)
            self.geometry("1040x700")
            self.minsize(820, 520)
            self.path = None

            bar = ttk.Frame(self)
            bar.pack(fill="x", padx=8, pady=8)
            for label, cmd in (("New", self.new_file), ("Open", self.open_file), ("Save", self.save_file),
                               ("Save As...", self.save_as), ("Validate", self.validate),
                               ("Install config", self.install_config), ("Restore config backup", self.restore_backup)):
                ttk.Button(bar, text=label, command=cmd).pack(side="left", padx=3)

            body = ttk.Frame(self)
            body.pack(fill="both", expand=True, padx=8)
            side = ttk.Frame(body)
            side.pack(side="right", fill="y", padx=(8, 0))
            ttk.Label(side, text="Passives (double-click to add)").pack(anchor="w")
            self.names = [v[0] for k, v in picker.CATALOG.items() if k != 7]
            self.listbox = tk.Listbox(side, width=30, exportselection=False)
            for n in self.names:
                self.listbox.insert("end", n)
            self.listbox.pack(fill="y", expand=True)
            self.listbox.bind("<Double-Button-1>", self.add_passive)

            self.text = tk.Text(body, wrap="none", undo=True, font=("Consolas", 10))
            ys = ttk.Scrollbar(body, orient="vertical", command=self.text.yview)
            self.text.configure(yscrollcommand=ys.set)
            ys.pack(side="right", fill="y")
            self.text.pack(side="left", fill="both", expand=True)

            self.status = tk.StringVar(value="Ready. Edits loadout.ini only.")
            ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", padx=8, pady=6)

            self.text.insert("1.0", fresh_template())
            self.text.edit_reset()
            if CONFIG.exists() and messagebox.askyesno(APP, "Found your current loadout:\n%s\n\nOpen it?" % CONFIG):
                self.load_path(CONFIG)

        def body(self):
            return self.text.get("1.0", "end-1c")

        def set_body(self, data):
            self.text.delete("1.0", "end")
            self.text.insert("1.0", data)

        def new_file(self):
            self.set_body(fresh_template())
            self.path = None
            self.status.set("New loadout (not saved yet)")

        def load_path(self, p):
            try:
                self.set_body(Path(p).read_text(encoding="utf-8-sig"))
                self.path = Path(p)
                self.status.set("Opened %s" % p)
            except Exception as e:
                messagebox.showerror(APP, str(e))

        def open_file(self):
            p = filedialog.askopenfilename(title="Open loadout.ini", filetypes=[("INI files", "*.ini"), ("All files", "*.*")])
            if p:
                self.load_path(p)

        def save_as(self):
            p = filedialog.asksaveasfilename(defaultextension=".ini", initialfile="loadout.ini", filetypes=[("INI files", "*.ini")])
            if p:
                self.path = Path(p)
                self.save_file()

        def save_file(self):
            if not self.path:
                return self.save_as()
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(self.body(), encoding="utf-8", newline="\n")
                self.status.set("Saved %s" % self.path)
            except Exception as e:
                messagebox.showerror(APP, str(e))

        def add_passive(self, _event=None):
            sel = self.listbox.curselection()
            if sel:
                self.text.insert("insert", "%-34s = on\n" % self.names[sel[0]])

        def validate(self):
            n, err = validate_text(self.body())
            if err:
                messagebox.showwarning("Not valid", "The mod would reject this file:\n\n%s" % err)
                self.status.set("Not valid")
            else:
                messagebox.showinfo("Valid", "The mod accepts this file. %d profile(s)." % n)
                self.status.set("Valid, %d profile(s)" % n)

        def install_config(self):
            n, err = validate_text(self.body())
            if err:
                messagebox.showwarning("Not installed", "Fix this first, the mod would reject it:\n\n%s" % err)
                return
            if not messagebox.askyesno("Install config", "Save this as your Armory Forge loadout?\n\n%s\n\nThe current file is backed up first." % CONFIG):
                return
            try:
                install(self.body())
                self.status.set("Installed to %s (the mod reloads it within a couple of seconds)" % CONFIG)
                messagebox.showinfo("Installed", "Saved to:\n%s\n\nIf the game is running, the mod reloads it within a couple of seconds. No restart needed." % CONFIG)
            except Exception as e:
                messagebox.showerror("Install failed", str(e))

        def restore_backup(self):
            if not BACKUP.exists():
                messagebox.showinfo("No backup", "No backup found at:\n%s" % BACKUP)
                return
            if not messagebox.askyesno("Restore", "Restore the previous loadout?\n\nYour current file is kept as loadout.ini.before-restore."):
                return
            try:
                restore()
                self.load_path(CONFIG)
                self.status.set("Restored the previous loadout")
            except Exception as e:
                messagebox.showerror("Restore failed", str(e))

    App().mainloop()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", metavar="FILE", help="validate a loadout.ini and exit")
    ap.add_argument("--zip", metavar="OUT.zip", help="write the standalone editor download")
    a = ap.parse_args(argv)
    if a.check:
        n, err = validate_text(open(a.check, encoding="utf-8-sig").read())
        print(("INVALID: " + err) if err else "OK: %d profile(s)" % n)
        return 1 if err else 0
    if a.zip:
        os.makedirs(os.path.dirname(os.path.abspath(a.zip)), exist_ok=True)
        build_zip(a.zip)
        print("wrote", a.zip)
        return 0
    run_gui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
