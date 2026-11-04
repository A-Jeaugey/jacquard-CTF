# Conception de la plateforme CTF

> Nom : **Jacquard**. Licence : MIT.
> Statut : étapes M0 à M4 implémentées, sauf les flags par équipe (voir le README).
> Ce document décrit la cible. Le format exact de ce qui est déjà implémenté est dans [format-pack.md](format-pack.md).

## 1. Objectif

Construire une plateforme CTF **réutilisable** pour les événements de l'association, capable d'accueillir des CTF très différents les uns des autres sans modifier son code.

Le principe directeur, qui donne son nom au projet : le métier Jacquard est une machine générique, ce sont les cartes perforées qui définissent le motif tissé. Ici, la plateforme est le métier, et chaque événement fournit ses « cartes » sous la forme d'un **pack d'événement**.

| Repo | Visibilité | Contenu |
|---|---|---|
| `cyber-epita` (ce repo) | Public | Le moteur : backend, frontend, outils, documentation, un pack d'exemple. |
| Un repo par événement (ex. `traboules`) | **Privé** jusqu'à la fin de l'événement | Le pack : configuration, défis, flags, scénario, thème, solutions. |

Aucun élément spécifique à un événement (catégories, carte, textes, couleurs, flags) ne doit se trouver dans ce repo, à l'exception du pack d'exemple utilisé pour le développement et les tests.

## 2. Ce qui est générique, ce qui vient du pack

| Fonctionnalité | Fourni par la plateforme | Défini par le pack |
|---|---|---|
| Catégories | Le concept de catégorie | Leur nombre, noms, couleurs, icônes |
| Tableau des défis | Des layouts génériques (grille, liste, image interactive) et un point d'extension | Le layout choisi, l'image, les zones, ou un composant entièrement custom |
| Déblocage | Un moteur de règles déclaratif | Les règles de chaque défi, indice, chapitre d'histoire |
| Narration | Un journal de messages débloquables | Le contenu, le nom de la vue, l'ordre |
| Score | Des stratégies (statique, dynamique, bonus premier sang) | Les paramètres et le choix par défi |
| Apparence | Des design tokens, un système de chaînes de texte surchargeables | Couleurs, polices, logo, CSS additionnel, tous les libellés |
| Grand écran | Des widgets (carte, classement, fil d'événements, compte à rebours) | La composition des écrans |
| Participation | Équipes ou solo, modes d'inscription | Le mode, la taille des équipes, les horaires |

## 3. Le pack d'événement

### 3.1 Arborescence

```
mon-ctf/
├── event.yml                 # configuration générale
├── theme/
│   ├── theme.yml             # tokens, polices, logo, libellés, layouts
│   ├── theme.css             # surcharges CSS libres (optionnel)
│   ├── assets/               # images, icônes, polices
│   └── layouts/
│       └── carte/
│           ├── layout.yml
│           └── carte.svg
├── story/                    # chapitres narratifs (Markdown + front matter)
│   └── 01-recrutement.md
├── pages/                    # pages statiques : règlement, FAQ...
│   └── reglement.md
├── challenges/
│   └── <categorie>/<defi>/
│       ├── challenge.yml
│       ├── description.md
│       ├── files/            # fichiers distribués aux joueurs
│       ├── src/              # sources et Dockerfile si le défi tourne en service
│       └── solution/         # writeup et script de résolution (jamais servis)
└── infra/
    └── docker-compose.yml    # services des défis (web, etc.)
```

Le pack est validé par un schéma strict. Toute erreur (référence vers un défi inexistant, règle mal formée, fichier manquant) est signalée avant l'import, jamais pendant l'événement.

### 3.2 `event.yml`

```yaml
id: mon-ctf-2027
name: "Nom de l'événement"
tagline: "Phrase d'accroche"
timezone: Europe/Paris

schedule:
  start: 2027-03-14T14:00:00
  end: 2027-03-14T20:00:00
  freeze: 2027-03-14T19:30:00      # gel du classement public (optionnel)

participation:
  mode: teams                      # teams | solo
  team_size: { min: 1, max: 4 }
  registration: invite_code        # open | invite_code | closed

flag_format: "FLAG{...}"           # affiché aux joueurs, utilisé pour avertir en cas de faute de frappe

difficulties: [facile, moyen, difficile]

categories:
  - id: web
    name: "Web"
    color: "#4f8cff"
    icon: theme/assets/icons/web.svg

scoring:
  default: { type: dynamic, initial: 500, minimum: 100, decay: 15 }
  first_blood: [50, 25, 10]        # bonus aux 1re, 2e et 3e équipes

submissions:
  rate_limit: { max: 10, per_seconds: 60 }   # par équipe et par défi

board:
  layout: carte                    # id d'un layout déclaré dans theme.yml
  fallback: grid                   # vue alternative toujours accessible

screens:                           # écrans projetés (voir §6)
  - id: projecteur
    widgets:
      - { type: board, layout: carte, scope: global }
      - { type: scoreboard, top: 10 }
      - { type: feed, events: [first_blood, announcement] }
      - { type: countdown }
```

### 3.3 `challenge.yml`

```yaml
id: exemple-robots               # identifiant unique et stable
name: "Titre affiché"
category: web
difficulty: facile
authors: ["pseudo"]
tags: [debutant, recon]
description: description.md

scoring: { type: static, value: 100 }    # sinon, valeur par défaut de event.yml

flags:
  - { type: static, value: "FLAG{exemple}" }
  # autres types : regex, per_team (§5.3), external (validation déléguée à un service)

parts: []                        # (prévu) défi en plusieurs flags avec points partiels

hints:
  - id: indice-1
    text: "Les robots aiment les règles."
    cost: 10
  - id: indice-2
    text: "Regarde /robots.txt."
    cost: 30
    available: { all: [{ hint_used: indice-1 }] }

files:
  - files/archive.zip

connection: "http://{challenge_host}:8001"   # affiché aux joueurs

unlock: { solved: intro }        # règle de déblocage (§4), toujours vrai si absent
when_locked: teaser              # hidden (défaut) | teaser (titre visible, contenu masqué)
locked_message: "Résous l'intro pour débloquer ce défi."   # affiché en mode teaser

on_solve:
  - { grant_item: fragment-a }
  - { notify: "Message affiché à l'équipe" }
```

Un chapitre d'histoire se débloque par sa propre règle (par exemple `{ solved: exemple-robots }`), ce qui évite une action `reveal` redondante.

### 3.4 Chapitres d'histoire (`story/*.md`)

```markdown
---
id: chapitre-2
title: "Un message chiffré"
order: 2
unlock: { solved_count: { gte: 3 } }
---

Contenu en Markdown...
```

Un chapitre `public: true` (prologue) est visible par tous, sans compte et avant le début.

Le nom de la vue (« Journal », « Messages », « Transmissions »...) est un libellé du thème.

## 4. Moteur de règles

Une seule grammaire sert partout : déblocage des défis, disponibilité des indices, chapitres d'histoire, états des zones d'un layout. Les règles sont évaluées **côté serveur**, pour chaque équipe.

### 4.1 Primitives

| Primitive | Exemple | Vraie si |
|---|---|---|
| `solved` | `{ solved: intro }` | L'équipe a résolu ce défi |
| `solved_count` | `{ solved_count: { category: web, gte: 2 } }` | Nombre de défis résolus (filtrable par catégorie, tag, difficulté) |
| `score` | `{ score: { gte: 300 } }` | Score de l'équipe |
| `item` | `{ item: fragment-a }` | L'équipe possède cet objet |
| `hint_used` | `{ hint_used: indice-1 }` | L'équipe a acheté cet indice |
| `time` | `{ time: { after: "2027-03-14T16:00:00" } }` ou `{ time: { elapsed_minutes: 60 } }` | Condition horaire, absolue ou relative au début |

### 4.2 Combinateurs

```yaml
unlock:
  all:
    - { solved: intro }
    - any:
        - { solved_count: { category: crypto, gte: 2 } }
        - { score: { gte: 400 } }
    - not: { time: { after: "2027-03-14T19:00:00" } }
```

### 4.3 Objets (inventaire)

Un défi résolu peut accorder des objets (`grant_item`) : clés, fragments, badges. Les règles peuvent les exiger. Ce mécanisme générique permet par exemple un défi final qui nécessite un fragment de chaque catégorie, sans logique spécifique dans le code.

### 4.4 Garanties

- Un défi verrouillé en mode `hidden` n'apparaît dans **aucune** réponse de l'API, et y accéder directement renvoie exactement la même erreur qu'un défi inexistant.
- Les déblocages sont **définitifs** : une fois débloqué pour une équipe, un défi le reste, même si la règle redevient fausse (score qui baisse après l'achat d'un indice, condition `before` dépassée...). Une règle `not: { time: { after: ... } }` signifie donc « déblocable jusqu'à cette heure ».
- En mode `teaser`, seuls l'identifiant, le titre et la catégorie sont envoyés ; jamais la description, les fichiers ni les indices.
- Les fichiers d'un défi verrouillé renvoient une erreur 404, et non 403, pour ne pas confirmer leur existence.
- Le validateur de pack détecte les dépendances circulaires et les défis impossibles à débloquer.

## 5. Flags, score, anti-triche

### 5.1 Types de flags

| Type | Usage |
|---|---|
| `static` | Valeur exacte, sensibilité à la casse configurable. |
| `regex` | Plusieurs réponses acceptables (ex. réponse OSINT avec variantes). |
| `per_team` | Flag unique par équipe, dérivé par HMAC (§5.3). |
| `external` | Validation déléguée à un service HTTP du défi (cas complexes). |

Les flags statiques sont stockés sous forme de condensat en base. La comparaison se fait en temps constant.

### 5.2 Score

- **Statique** : valeur fixe.
- **Dynamique** : la valeur décroît avec le nombre d'équipes ayant résolu le défi, entre `initial` et `minimum`. Toutes les équipes voient la valeur actuelle, y compris celles qui l'ont déjà résolu.
- **Bonus premier sang** : configurable par rang.
- **Indices** : leur coût est déduit du score.
- **Départage** : à score égal, l'équipe ayant atteint ce score en premier est devant.
- **Gel** : après `freeze`, le classement public est figé ; chaque équipe continue de voir son propre score réel. L'administration voit tout.

### 5.3 Flags par équipe

`flag = format(préfixe, HMAC(secret_événement, id_équipe ‖ id_défi)[:n])`

Pour les défis dont le contenu peut être généré par équipe (fichiers produits à la demande, ou service qui interroge la plateforme via une API interne authentifiée). Avantage : si l'équipe A soumet le flag de l'équipe B, la plateforme le détecte et alerte l'administration.

### 5.4 Journalisation

Toutes les soumissions (correctes ou non) sont journalisées avec l'équipe, l'utilisateur, l'horodatage et l'adresse IP. Le tableau de bord admin met en évidence les soumissions identiques entre équipes, les flags d'autres équipes et les rafales anormales.

## 6. Interface et personnalisation

### 6.1 Thème (`theme.yml`)

```yaml
tokens:                       # exposés en variables CSS (--color-bg, etc.)
  color-bg: "#0b0e14"
  color-surface: "#151a23"
  color-text: "#e6e6e6"
  color-accent: "#f5c542"
  font-body: "Inter"
  font-display: "Space Grotesk"
fonts:
  - { family: "Space Grotesk", src: assets/fonts/space-grotesk.woff2 }
logo: assets/logo.svg
favicon: assets/favicon.svg
css: theme.css
strings:                      # surcharge de tous les libellés de l'interface
  board.title: "Le plan"
  story.title: "Transmissions"
  submit.button: "Valider"
layouts:
  carte: layouts/carte/layout.yml
```

### 6.2 Layouts du tableau

> État actuel (novembre 2026) : pour le premier événement, l'interface a une direction
> artistique fixe (`frontend/DESIGN.md`) et ne rend pas encore ces layouts ; seuls les
> libellés du thème sont appliqués. Ce qui suit reste la cible.

**Layouts intégrés :**

- `grid` : colonnes par catégorie, style Jeopardy.
- `list` : liste filtrable et triable.
- `image-map` : une image (de préférence SVG) dont des zones sont reliées à des catégories ou des défis.

**Configuration d'un `image-map` :**

```yaml
type: image-map
background: carte.svg
zones:
  - element: "#zone-nord"         # id d'un élément du SVG
    target: { category: web }
  - element: "#zone-finale"
    target: { challenge: defi-final }
```

Chaque zone reçoit une classe d'état (`is-locked`, `is-available`, `is-in-progress`, `is-completed`) et une variable CSS `--progress` entre 0 et 1. Le thème décide du rendu : une zone qui s'illumine, se colore, se remplit... Avec `scope: global`, la progression agrège toutes les équipes (utile sur grand écran).

Ce seul layout couvre une carte de ville, un plan de vaisseau, une carte de monde de jeu vidéo ou un schéma de réseau, sans une ligne de code.

**Layout entièrement custom :**

```yaml
type: web-component
module: layouts/mon-layout/index.js
tag: mon-layout
```

Le module définit un Custom Element. La plateforme lui fournit une propriété `board` (contrat JSON documenté et versionné : catégories, défis visibles, états, progression, inventaire) et écoute l'événement `open-challenge` qu'il émet. Le composant peut être écrit en JavaScript pur ou avec n'importe quel framework compilé en Web Component.

### 6.3 Grand écran

Les écrans déclarés dans `event.yml` sont accessibles via une URL à jeton, sans compte. Widgets disponibles : `board`, `scoreboard`, `feed`, `countdown`, `announcement`, `stats`. Mise à jour en temps réel.

## 7. Architecture technique

### 7.1 Choix

| Couche | Choix | Raison |
|---|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic | Langage connu des étudiants, typage, validation avec Pydantic |
| Base de données | PostgreSQL | Fiabilité, `LISTEN/NOTIFY` pour le temps réel sans Redis |
| Temps réel | Server-Sent Events | Plus simple que WebSocket pour un flux serveur vers client |
| Frontend | Svelte 5, Vite, TypeScript (SPA) | Léger, rapide, facile à prendre en main |
| Déploiement | Docker Compose, Caddy (TLS automatique) | Une commande pour lancer l'ensemble |
| Outillage | CLI `jacquard` | Valider, importer, exporter les packs |

### 7.2 Composants

```
                ┌──────────────┐
 Navigateurs ──▶│    Caddy     │── /api, /events ─▶ ┌─────────────┐     ┌────────────┐
                │ (TLS, proxy) │                    │ API FastAPI │────▶│ PostgreSQL │
                │              │── / (SPA) ───────▶ └─────────────┘     └────────────┘
                └──────────────┘                          ▲
                                                          │ jacquard pack sync
                                                    ┌─────┴──────┐
                                                    │ Pack (repo │
                                                    │   privé)   │
                                                    └────────────┘

 Services des défis : hôte ou réseau séparé, jamais sur la machine de la plateforme.
```

### 7.3 Modules du backend

`auth`, `teams`, `packs` (chargement, validation, synchronisation), `rules`, `challenges`, `submissions`, `scoring`, `story`, `realtime`, `screens`, `admin`.

Le moteur de règles et le calcul du score sont des fonctions pures, sans accès à la base, pour être testés exhaustivement.

### 7.4 Modèle de données (simplifié)

- `users` (id, pseudo, email, hash du mot de passe, rôle, équipe)
- `teams` (id, nom, hash du code d'invitation)
- `challenges`, `hints`, `story_entries` (importés du pack, identifiés par leur `id` stable)
- `submissions` (équipe, utilisateur, défi, valeur soumise, correct, horodatage, IP)
- `solves` (équipe, défi, partie, horodatage), unique par équipe/défi/partie
- `hint_unlocks`, `items` (inventaire), `announcements`

### 7.5 CLI

```
jacquard pack validate <dossier>       # vérifie le pack sans rien modifier
jacquard pack sync <dossier>           # importe ou met à jour (idempotent, --dry-run)
jacquard pack export-ctfd <dossier>    # export de secours vers CTFd
jacquard admin create <pseudo>
```

La synchronisation peut se faire pendant l'événement (correction d'une coquille) : elle ne supprime jamais une résolution existante.

## 8. Sécurité

Les participants sont, par définition, des personnes qui cherchent des failles. Le règlement exclut la plateforme du périmètre, mais elle doit résister quand même.

- Sessions par cookie `HttpOnly`, `Secure`, `SameSite=Lax`, protection CSRF.
- Mots de passe hachés avec Argon2id.
- Limitation de débit sur la connexion, l'inscription et la soumission de flags.
- Markdown du pack rendu puis assaini ; tout contenu saisi par les joueurs (pseudos, noms d'équipe) est échappé.
- Contrôle d'accès systématique côté serveur sur chaque route ; tests dédiés pour vérifier qu'aucun contenu verrouillé ne fuit.
- Fichiers servis par identifiant, jamais par chemin fourni par le client.
- Dossiers `solution/` jamais importés en base ni servis.
- En-têtes de sécurité (CSP stricte, `X-Content-Type-Options`, etc.).
- Secrets (HMAC, base) passés par variables d'environnement, jamais dans un repo.
- Services des défis isolés de la plateforme (réseau ou machine séparée).
- Signalement responsable : une faille trouvée dans la plateforme et signalée à l'orga peut être récompensée (à définir dans le règlement).

## 9. Qualité et tests

- Tests unitaires du moteur de règles, du score et du validateur de pack.
- Tests d'API couvrant les contrôles d'accès (défis verrouillés, gel, rôles).
- Tests de bout en bout avec Playwright sur le parcours joueur et le parcours admin.
- Test de charge simulant 150 joueurs (soumissions et flux temps réel).
- Intégration continue sur chaque commit (lint, typage, tests).
- Un pack d'exemple complet dans `examples/`, utilisé par les tests.
- Une session de test grandeur nature avec des volontaires avant chaque événement.

## 10. Feuille de route

| Étape | Contenu |
|---|---|
| **M0** Fondations | Structure du repo, Docker Compose de développement, intégration continue, pack d'exemple minimal |
| **M1** Cœur | Comptes, équipes, import de pack, défis, soumissions, score statique, classement, layout `grid`, admin de base |
| **M2** Mécaniques | Moteur de règles, inventaire, indices, histoire, score dynamique, premier sang, gel, temps réel |
| **M3** Personnalisation | Thèmes, libellés, layouts `list` et `image-map`, Web Components, grand écran |
| **M4** Robustesse | Flags par équipe, tableau de bord anti-triche, export CTFd, test de charge, durcissement |
| **Plus tard** | Instances de défis par équipe, connexion via le compte de l'école, statistiques post-événement |

## 11. Questions ouvertes

- Hébergement le jour J : machine de l'école ou serveur loué.
- Langue de l'interface par défaut (français, avec libellés surchargeables).
