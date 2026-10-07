Booster names for Super Earth Armory Forge
==========================================
Double-click Run-me.bat. It finds your Helldivers 2 install, READS its data files
(nothing in the game folder is changed), and writes next to it:
  boosters.json     what the game files say about boosters: the booster enums and types,
                    entities with a booster component, files named after boosters, and every
                    text that looks like a booster name or description (English, Japanese,
                    Chinese) with its string id
  strings-en.json   every English text in the game, to match offline
  boosters.zip      both of them: send this one to the mod author

booster-dumper.exe is a small program added to FileDiver (https://github.com/xypwn/filediver,
commit @COMMIT@, BSD-3-Clause, by xypwn and contributors), built for Windows x64 by
tools/booster-names/build.sh in the Super Earth Armory Forge repository. LICENSE-filediver.txt
is FileDiver's licence; the added source is dumper/main.go.

Game not found (an empty boosters.json, or "Unable to detect game install directory")?
Drag your Helldivers 2 folder (the one holding "data") onto Run-me.bat, or put its path on
one line in a file called game-dir.txt next to it, e.g. E:\SteamLibrary\steamapps\common\Helldivers 2

Windows SmartScreen may warn because the exe isn't signed: More info > Run anyway.
