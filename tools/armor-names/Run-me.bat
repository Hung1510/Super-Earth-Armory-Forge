@echo off
rem Reads your Helldivers 2 install (read-only) and writes the armor names next to this file:
rem armors.json (English), armors-ja.json (Japanese), armors-zh.json (Chinese, Simplified).
rem Game on another drive, or "Unable to detect game install directory"? Either drag the
rem Helldivers 2 folder onto this file, or put its path on one line in game-dir.txt here.
cd /d "%~dp0"
if not "%~1"=="" set "HD2_GAME_DIR=%~1"
if exist "game-dir.txt" if not defined HD2_GAME_DIR set /p HD2_GAME_DIR=<game-dir.txt
if defined HD2_GAME_DIR echo Game folder: %HD2_GAME_DIR%
echo Reading the game files in English, this can take a minute...
set ARMOR_NAMES_LANG=English (US)
armor-set-json-dumper.exe > armors.json
if errorlevel 1 goto failed
call :nonempty armors.json || goto failed
echo Japanese...
set ARMOR_NAMES_LANG=Japanese
armor-set-json-dumper.exe > armors-ja.json
if errorlevel 1 goto failed
call :nonempty armors-ja.json || goto failed
echo Chinese (Simplified)...
set ARMOR_NAMES_LANG=Chinese (Simplified)
armor-set-json-dumper.exe > armors-zh.json
if errorlevel 1 goto failed
call :nonempty armors-zh.json || goto failed
echo Done: armors.json, armors-ja.json and armors-zh.json are next to this file. Send all three to the mod author.
goto end
:nonempty
for %%F in (%1) do if %%~zF==0 exit /b 1
exit /b 0
:failed
echo.
echo Something went wrong (an empty file means the game was not found or could not be read).
echo Send the text above to the mod author. Game on another drive: drag its folder onto Run-me.bat.
:end
pause
