@echo off
REM ============================================================
REM  Lanceur du WhatsApp Birthday Bot pour Windows.
REM  A declencher au demarrage / a l'ouverture de session via
REM  le Planificateur de taches (voir README).
REM ============================================================

REM Se placer dans le dossier de ce script
cd /d "%~dp0"

REM Laisser le temps au reseau et a WhatsApp Web d'etre prets
REM (augmentez la valeur si votre PC met du temps a se connecter)
timeout /t 45 /nobreak >nul

REM --- ENVOI INDIVIDUEL (a chaque contact) ---
python birthday_bot.py --send

REM --- OU ENVOI DANS UN GROUPE ---
REM Commentez la ligne ci-dessus, decommentez celle-ci et
REM remplacez l'ID par celui de votre groupe :
REM python birthday_bot.py --send --group AB123CDEFGHijklmn
