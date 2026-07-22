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
echo [Birthday Bot] Attente de 10 s que le reseau soit pret...
echo [Birthday Bot] (fermez cette fenetre pour annuler)
timeout /t 10 /nobreak >nul

REM Utiliser le lanceur "py" si disponible (fiable sur Windows,
REM meme si "python" n'est pas dans le PATH), sinon "python".
set PYTHON=py
where py >nul 2>nul || set PYTHON=python

echo [Birthday Bot] Lancement (envoi reel)...
set ERR=0

REM --- ENVOI INDIVIDUEL (contacts.csv, s'il existe) ---
if exist contacts.csv (
    %PYTHON% birthday_bot.py --send
    if errorlevel 1 set ERR=1
)

REM --- ENVOI DANS LES GROUPES ---
REM Parcourt tous les fichiers contacts.group.<IDGROUPE>.csv du dossier
REM et envoie les anniversaires de chacun dans le groupe correspondant.
%PYTHON% birthday_bot.py --send --all-groups
if errorlevel 1 set ERR=1

REM En cas d'erreur, garder la fenetre ouverte pour lire le message
if %ERR%==1 (
    echo.
    echo [Birthday Bot] Erreur - voir les messages ci-dessus.
    pause
)
