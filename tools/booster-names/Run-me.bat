@echo off
rem Reads your Helldivers 2 install (read-only) and writes what its files say about boosters
rem next to this file: boosters.json and strings-en.json (zipped as boosters.zip).
rem Game on another drive, or "Unable to detect game install directory"? Either drag the
rem Helldivers 2 folder onto this file, or put its path on one line in game-dir.txt here.
cd /d "%~dp0"
if not "%~1"=="" set "HD2_GAME_DIR=%~1"
if exist "game-dir.txt" if not defined HD2_GAME_DIR set /p HD2_GAME_DIR=<game-dir.txt
if defined HD2_GAME_DIR echo Game folder: %HD2_GAME_DIR%
echo Reading the game files, this can take a minute...
booster-dumper.exe > boosters.json
if errorlevel 1 goto failed
call :nonempty boosters.json || goto failed
call :nonempty strings-en.json || goto failed
powershell -NoProfile -Command "Compress-Archive -Force -Path 'boosters.json','strings-en.json' -DestinationPath 'boosters.zip'"
echo Done: boosters.zip (boosters.json + strings-en.json) is next to this file. Send it to the mod author.
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
