# WhatsApp Birthday Bot 🎂

Envoie automatiquement des messages d'anniversaire WhatsApp à partir d'un
fichier CSV, **gratuitement**, via WhatsApp Web (bibliothèque `pywhatkit`).
Fonctionne en envoi individuel **ou dans un groupe WhatsApp**.

## Sécurité

- Python pur, multiplateforme, aucun droit administrateur.
- Aucun identifiant stocké : l'authentification reste dans votre session
  **WhatsApp Web**, dans le navigateur.
- Mode simulation par défaut : rien n'est envoyé sans `--send`.
- Journal anti-doublon : le script peut tourner plusieurs fois par jour
  (ex. à chaque démarrage de Windows) sans jamais envoyer deux fois.

## Installation

Nécessite **Python 3.9+**.

```bash
pip install -r requirements.txt

# Envoi individuel :
cp contacts.example.csv contacts.csv

# OU envoi en groupe :
cp contacts.group.example.csv contacts.csv
```

Éditez ensuite `contacts.csv` avec vos vrais contacts.

## Envoi individuel

Le fichier `contacts.csv` doit contenir une colonne `phone` :

```csv
name,phone,birthday,message
Awa,+22507010203,1990-07-22,Joyeux anniversaire {name} ! 🎉
Kwame,+233241234567,22/07,
```

```bash
python birthday_bot.py            # simulation (n'envoie rien)
python birthday_bot.py --send     # envoi réel
```

## Envoi dans un groupe WhatsApp

En mode groupe, la colonne `phone` n'est pas nécessaire — la destination
est le groupe, et chaque message y nomme la personne.

```csv
name,birthday,message
Awa,1990-07-22,Joyeux anniversaire {name} ! 🎉
Kwame,22/07,
```

### Trouver l'ID du groupe

L'ID du groupe se trouve dans son **lien d'invitation** :
`https://chat.whatsapp.com/AB123CDEFGHijklmn` → l'ID est `AB123CDEFGHijklmn`.
Seul un **administrateur** du groupe peut générer ce lien (dans WhatsApp :
Infos du groupe → Inviter via un lien).

```bash
# Simulation
python birthday_bot.py --group AB123CDEFGHijklmn

# Envoi réel dans le groupe
python birthday_bot.py --send --group AB123CDEFGHijklmn
```

Vous pouvez aussi fixer l'ID une fois pour toutes via la variable
d'environnement `WHATSAPP_GROUP_ID` (pratique avec le lanceur Windows).

> Note : chaque anniversaire du jour donne lieu à un message distinct dans
> le groupe. C'est un vrai message posté dans la conversation, visible par
> tous les membres.

## Format du CSV (détails)

- **name** — prénom, réutilisable dans le message via `{name}`.
- **phone** — format international (`+22507010203`). Obligatoire en mode
  individuel, facultatif en mode groupe.
- **birthday** — année facultative. Formats : `AAAA-MM-JJ`, `JJ/MM/AAAA`,
  `JJ/MM`, `MM-JJ`.
- **message** — facultatif ; si vide, le message par défaut est utilisé.

Les lignes invalides sont ignorées avec un avertissement.

## Automatiser au démarrage de Windows

Un lanceur `run_birthday_bot.bat` est fourni. Il se place dans le bon
dossier, attend 10 s que la connexion et WhatsApp Web soient prêts, puis
lance le bot (augmentez ce délai dans le `.bat` si votre PC met du temps
à se connecter au réseau après le démarrage). Pour le mode groupe, ouvrez le `.bat` et décommentez la
ligne prévue (ou renseignez `WHATSAPP_GROUP_ID`).

**Planificateur de tâches Windows** :

1. Ouvrez « Planificateur de tâches » → « Créer une tâche… ».
2. Onglet **Général** : cochez « Exécuter avec les autorisations maximales »
   n'est PAS nécessaire ici ; laissez les réglages par défaut.
3. Onglet **Déclencheurs** → « Nouveau » → « Au démarrage » (ou « À
   l'ouverture de session »).
4. Onglet **Actions** → « Nouveau » → « Démarrer un programme » →
   Programme : le chemin complet de `run_birthday_bot.bat`.
5. Validez.

> **Conseil de fiabilité.** Le déclencheur « au démarrage » ne se produit
> qu'aux redémarrages : si le PC ne redémarre pas le jour d'un anniversaire,
> le message est manqué. Ajoutez un **second déclencheur quotidien** (onglet
> Déclencheurs → « Nouveau » → « Quotidien », à l'heure de votre choix).
> Grâce au journal anti-doublon, avoir les deux déclencheurs n'envoie jamais
> de message en double.

## Prérequis d'exécution

- Être connecté à **WhatsApp Web** dans le navigateur par défaut (scan du
  QR code une première fois ; la session est ensuite mémorisée).
- `pywhatkit` ouvre un onglet de navigateur par message et laisse quelques
  secondes de chargement (`--wait`, 10 s par défaut — augmentez la valeur,
  par ex. `--wait 30`, si votre connexion ou votre PC est lent). C'est la
  contrepartie de la gratuité : la méthode est un peu plus lente et dépend
  de WhatsApp Web.

## Utilisation responsable

Respectez les conditions d'utilisation de WhatsApp et la vie privée de vos
contacts : consentement, fréquence raisonnable, pas d'envois massifs.

## Licence

MIT.
