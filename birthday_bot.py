#!/usr/bin/env python3
"""
WhatsApp Birthday Bot — version pywhatkit (gratuite, via WhatsApp Web).

Lit une liste d'anniversaires dans un CSV et envoie un message le jour J,
soit à chaque contact individuellement, soit dans un GROUPE WhatsApp.

Sécurité :
  - Python pur, multiplateforme, aucun droit administrateur.
  - Aucun identifiant stocké : la session vit dans votre navigateur
    (WhatsApp Web).
  - Mode simulation par défaut : rien n'est envoyé sans --send.
  - Journal anti-doublon : lancer le script plusieurs fois par jour
    (ex. à chaque démarrage de Windows) n'envoie jamais deux fois.

Usage :
  python birthday_bot.py                          # simulation
  python birthday_bot.py --send                   # envoi individuel
  python birthday_bot.py --send --group AB123...   # envoi dans un groupe
  python birthday_bot.py --send --all-groups       # tous les fichiers
                                                   # contacts.group.<ID>.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MESSAGE = "Joyeux anniversaire {name} ! 🎉 Passe une excellente journée."
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")
YEARLESS_FORMATS = ("%m-%d", "%d/%m")
PHONE_RE = re.compile(r"^\+\d{8,15}$")
GROUP_FILE_RE = re.compile(r"^contacts\.group\.(?P<gid>[A-Za-z0-9_-]+)\.csv$")
SENT_LOG = Path(".sent_log.json")

logger = logging.getLogger("birthday_bot")


@dataclass
class Contact:
    name: str
    phone: str          # peut etre vide en mode groupe
    month: int
    day: int
    message: str

    @property
    def key(self) -> str:
        """Identifiant stable pour le journal anti-doublon."""
        return self.phone or f"name:{self.name}"

    def rendered_message(self) -> str:
        return self.message.format(name=self.name)


# ---------------------------------------------------------------------------
# Chargement et validation du CSV
# ---------------------------------------------------------------------------

def parse_birthday(value: str) -> tuple[int, int]:
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            parsed = dt.datetime.strptime(value, fmt)
            return parsed.month, parsed.day
        except ValueError:
            continue
    # Dates sans annee : on en fixe une explicitement (bissextile, pour
    # accepter le 29/02) car strptime sans annee est deprecie en 3.13+.
    for fmt in YEARLESS_FORMATS:
        try:
            parsed = dt.datetime.strptime(f"2000 {value}", f"%Y {fmt}")
            return parsed.month, parsed.day
        except ValueError:
            continue
    raise ValueError(f"date d'anniversaire illisible : {value!r}")


def load_contacts(path: Path, default_message: str, group_mode: bool) -> list[Contact]:
    """En mode individuel, la colonne 'phone' est obligatoire et validee.
    En mode groupe, le numero est facultatif (la destination est le groupe)."""
    if not path.exists():
        raise FileNotFoundError(f"fichier de contacts introuvable : {path}")

    contacts: list[Contact] = []
    # utf-8-sig : tolere le BOM que Windows (Excel, Notepad...) ajoute
    # souvent en tete de fichier, sans effet sur un fichier UTF-8 sans BOM.
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"name", "birthday"} if group_mode else {"name", "phone", "birthday"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(
                f"le CSV doit contenir au minimum les colonnes {sorted(required)} "
                f"(trouve : {reader.fieldnames})"
            )

        for line_no, row in enumerate(reader, start=2):
            name = (row.get("name") or "").strip()
            phone = (row.get("phone") or "").strip()
            birthday = (row.get("birthday") or "").strip()
            message = (row.get("message") or "").strip() or default_message

            if not name or not birthday or (not group_mode and not phone):
                logger.warning("Ligne %d ignoree : champ obligatoire vide.", line_no)
                continue

            if phone and not PHONE_RE.match(phone):
                if group_mode:
                    phone = ""  # numero invalide tolere et ignore en mode groupe
                else:
                    logger.warning(
                        "Ligne %d ignoree : numero %r invalide "
                        "(format attendu : +33612345678).", line_no, phone,
                    )
                    continue

            try:
                month, day = parse_birthday(birthday)
            except ValueError as exc:
                logger.warning("Ligne %d ignoree : %s", line_no, exc)
                continue

            contacts.append(Contact(name, phone, month, day, message))

    logger.info("%d contact(s) valide(s) charge(s) depuis %s.", len(contacts), path)
    return contacts


def find_group_files(directory: Path) -> dict[str, Path]:
    """Trouve les fichiers contacts.group.<ID>.csv du dossier et retourne
    {ID du groupe: chemin}. Les modeles *.example.csv sont exclus."""
    result: dict[str, Path] = {}
    for p in sorted(directory.glob("contacts.group.*.csv")):
        m = GROUP_FILE_RE.match(p.name)
        if not m or m.group("gid").lower() == "example":
            continue
        result[m.group("gid")] = p
    return result


# ---------------------------------------------------------------------------
# Selection des anniversaires du jour
# ---------------------------------------------------------------------------

def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def birthdays_today(contacts: list[Contact], today: dt.date) -> list[Contact]:
    result = []
    for c in contacts:
        if c.month == today.month and c.day == today.day:
            result.append(c)
        elif (
            c.month == 2 and c.day == 29
            and today.month == 2 and today.day == 28
            and not _is_leap(today.year)
        ):
            result.append(c)
    return result


# ---------------------------------------------------------------------------
# Journal des envois (anti-doublon)
# ---------------------------------------------------------------------------

def _load_log() -> dict[str, list[str]]:
    """Journal au format {date ISO: [cles envoyees]}. Migre l'ancien
    format mono-date {"date": ..., "keys": [...]} de facon transparente."""
    if not SENT_LOG.exists():
        return {}
    try:
        data = json.loads(SENT_LOG.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    if "date" in data and "keys" in data:
        return {str(data["date"]): list(data["keys"])}
    return {d: list(k) for d, k in data.items() if isinstance(k, list)}


def load_sent_today(today: dt.date) -> set[str]:
    return set(_load_log().get(today.isoformat(), []))


def mark_sent(today: dt.date, keys: set[str]) -> None:
    log = _load_log()
    log[today.isoformat()] = sorted(keys)
    # Purge des dates vieilles de plus de 400 jours pour borner le fichier
    cutoff = (today - dt.timedelta(days=400)).isoformat()
    log = {d: k for d, k in sorted(log.items()) if d >= cutoff}
    try:
        SENT_LOG.write_text(
            json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as exc:
        logger.warning("Impossible d'ecrire le journal des envois : %s", exc)


# ---------------------------------------------------------------------------
# Envoi WhatsApp
# ---------------------------------------------------------------------------

def send_message(contact: Contact, group_id, wait_time: int) -> None:
    """Envoie via WhatsApp Web. En mode groupe, le message part dans le groupe
    et nomme la personne ; sinon il part au numero du contact."""
    try:
        import pywhatkit  # import tardif : la simulation ne le requiert pas
    except ImportError as exc:
        raise RuntimeError(
            "La bibliotheque 'pywhatkit' est requise pour l'envoi reel.\n"
            "Installez-la avec : py -m pip install -r requirements.txt\n"
            f"(detail de l'erreur d'import : {exc})"
        ) from exc

    if group_id:
        pywhatkit.sendwhatmsg_to_group_instantly(
            group_id=group_id,
            message=contact.rendered_message(),
            wait_time=wait_time,
            tab_close=True,
            close_time=3,
        )
    else:
        pywhatkit.sendwhatmsg_instantly(
            phone_no=contact.phone,
            message=contact.rendered_message(),
            wait_time=wait_time,
            tab_close=True,
            close_time=3,
        )


# ---------------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Envoie des messages d'anniversaire WhatsApp depuis un CSV.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--file", type=Path, default=Path("contacts.csv"),
                   help="Fichier CSV des contacts.")
    p.add_argument("--send", action="store_true",
                   help="Envoie reellement. Sans ce drapeau : simulation.")
    p.add_argument("--group", default=os.environ.get("WHATSAPP_GROUP_ID"),
                   help="ID du groupe (partie finale du lien chat.whatsapp.com/...). "
                        "Peut aussi etre fourni via la variable WHATSAPP_GROUP_ID.")
    p.add_argument("--all-groups", action="store_true",
                   help="Traite tous les fichiers contacts.group.<ID>.csv du "
                        "dossier courant, chacun vers son groupe. "
                        "Ignore --file et --group.")
    p.add_argument("--message", default=DEFAULT_MESSAGE,
                   help="Message par defaut. {name} = prenom du contact.")
    p.add_argument("--date", type=str, default=None,
                   help="Forcer une date (AAAA-MM-JJ) pour tester.")
    p.add_argument("--wait", type=int, default=10,
                   help="Secondes d'attente que WhatsApp Web charge, par message.")
    p.add_argument("--verbose", action="store_true", help="Journalisation detaillee.")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    # Console Windows en cp1252 par defaut : force l'UTF-8 pour que les
    # emojis des messages s'affichent au lieu de \U0001f389.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )

    today = dt.date.fromisoformat(args.date) if args.date else dt.date.today()

    # Lots a traiter : (ID de groupe ou None, fichier de contacts)
    if args.all_groups:
        group_files = find_group_files(Path("."))
        if not group_files:
            logger.warning("Aucun fichier contacts.group.<ID>.csv trouve. "
                           "Rien a faire.")
            return 0
        jobs = list(group_files.items())
    else:
        jobs = [(args.group or None, args.file)]

    def scoped_key(contact: Contact, group_id) -> str:
        """Cle anti-doublon : la meme personne peut etre souhaitee dans
        plusieurs groupes ET individuellement le meme jour."""
        return f"group:{group_id}:{contact.key}" if group_id else contact.key

    exit_code = 0
    total_sent = 0
    attempts = 0

    for group_id, path in jobs:
        destination = f"groupe {group_id}" if group_id else "envoi individuel"
        try:
            contacts = load_contacts(path, args.message, group_mode=bool(group_id))
        except (FileNotFoundError, ValueError) as exc:
            logger.error("%s", exc)
            exit_code = 1
            continue

        todays = birthdays_today(contacts, today)
        if not todays:
            logger.info("[%s] aucun anniversaire le %s.",
                        destination, today.isoformat())
            continue

        already = load_sent_today(today)
        pending = [c for c in todays if scoped_key(c, group_id) not in already]
        logger.info("[%s] %d anniversaire(s) aujourd'hui, %d a traiter.",
                    destination, len(todays), len(pending))

        if not args.send:
            logger.info("MODE SIMULATION - rien n'est envoye. "
                        "Ajoutez --send pour envoyer.")
            for c in pending:
                cible = destination if group_id else c.phone
                logger.info("  -> [%s] %s : %s", cible, c.name,
                            c.rendered_message())
            continue

        sent = set(already)
        for c in pending:
            if attempts:
                time.sleep(5)  # petite pause entre deux onglets WhatsApp Web
            attempts += 1
            logger.info("[%s] envoi pour %s...", destination, c.name)
            try:
                send_message(c, group_id, wait_time=args.wait)
                sent.add(scoped_key(c, group_id))
                mark_sent(today, sent)
                total_sent += 1
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Echec pour %s : %s", c.name, exc)
                exit_code = 1

    if args.send:
        logger.info("Termine : %d message(s) envoye(s).", total_sent)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
