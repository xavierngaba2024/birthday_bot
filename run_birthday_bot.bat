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
echo [Birthday Bot] Attente de 45 s que le reseau soit pret...
echo [Birthday Bot] (fermez cette fenetre pour annuler)
timeout /t 45 /nobreak >nul

REM Utiliser le lanceur "py" si disponible (fiable sur Windows,
REM meme si "python" n'est pas dans le PATH), sinon "python".
set PYTHON=py
where py >nul 2>nul || set PYTHON=python3.13

echo [Birthday Bot] Lancement (envoi reel)...

REM --- ENVOI INDIVIDUEL (a chaque contact) ---
%PYTHON% birthday_bot.py --send

REM --- OU ENVOI DANS UN GROUPE ---
REM Commentez la ligne ci-dessus, decommentez celle-ci et
REM remplacez l'ID par celui de votre groupe :
REM %PYTHON% birthday_bot.py --send --group AB123CDEFGHijklmn

REM En cas d'erreur, garder la fenetre ouverte pour lire le message
if errorlevel 1 (
    echo.
    echo [Birthday Bot] Erreur - voir le message ci-dessus.
    pause
)
