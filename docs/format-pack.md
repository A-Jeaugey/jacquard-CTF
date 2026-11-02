# Référence du format de pack

Ce document décrit **exactement** ce que la version actuelle de Jacquard accepte. Tout champ absent de cette page est refusé par `jacquard pack validate` (« champ inconnu ou non pris en charge par cette version »).

Pour un exemple complet et fonctionnel, voir [examples/demo-pack](../examples/demo-pack).

## Sommaire

1. [Arborescence](#1-arborescence)
2. [event.yml](#2-eventyml)
3. [challenge.yml](#3-challengeyml)
4. [Règles de déblocage](#4-règles-de-déblocage)
5. [Chapitres d'histoire](#5-chapitres-dhistoire)
6. [Validation](#6-validation)
7. [Conseils d'écriture](#7-conseils-décriture)

## 1. Arborescence

```
mon-ctf/
├── event.yml
├── story/                      # facultatif
│   └── 01-intro.md             # chapitres, lus par ordre alphabétique de fichier
└── challenges/
    └── <n'importe quel sous-dossier>/
        ├── challenge.yml       # un défi par fichier challenge.yml
        ├── description.md
        ├── files/              # fichiers distribués (à lister dans `files`)
        ├── src/                # sources du défi : jamais lues par la plateforme
        └── solution/           # writeup : jamais lu, jamais distribuable
```

Les identifiants (`id`) sont en minuscules, chiffres et tirets, 64 caractères maximum, et ne doivent **jamais changer** une fois l'événement commencé : ils relient les résolutions aux défis.

## 2. `event.yml`

| Champ | Type | Défaut | Description |
|---|---|---|---|
| `id` | identifiant | requis | Identifiant de l'événement |
| `name` | texte | requis | Nom affiché |
| `tagline` | texte | — | Phrase d'accroche de l'accueil |
| `timezone` | fuseau IANA | `Europe/Paris` | Fuseau des dates sans fuseau explicite |
| `schedule.start` / `end` | date | requis | Début et fin (`2027-03-14T14:00:00`) |
| `schedule.freeze` | date | — | Gel du classement public, entre `start` et `end` |
| `participation.mode` | `teams` \| `solo` | `teams` | En solo, chaque joueur a son équipe à son nom |
| `participation.team_size` | `{min, max}` | `{1, 4}` | Taille des équipes (`max` appliqué) |
| `participation.registration` | `open` \| `invite_code` \| `closed` | `open` | `invite_code` : code défini par `JACQUARD_REGISTRATION_CODE` |
| `flag_format` | texte | — | Ex. `CTF{...}` ; affiché aux joueurs, avertissement si un flag statique ne le respecte pas |
| `difficulties` | liste | `[]` | Difficultés autorisées dans les défis |
| `categories` | liste | requis | `{id, name, description?, color?}` ; `color` au format `#rrggbb` |
| `scoring.default` | barème | statique 100 | Barème des défis qui n'en déclarent pas |
| `scoring.first_blood` | liste d'entiers | `[]` | Bonus des 1re, 2e… équipes à résoudre un défi |
| `submissions.rate_limit` | `{max, per_seconds}` | `{10, 60}` | Tentatives par équipe et par défi |
| `board.layout` | `grid` | `grid` | Présentation du tableau des défis |
| `items` | liste | `[]` | Objets obtenables : `{id, name, description?}` |
| `hints.require_points` | booléen | `false` | Si vrai, un indice payant exige assez de points |

### Barèmes

```yaml
{ type: static, value: 100 }
{ type: dynamic, initial: 500, minimum: 100, decay: 15 }
```

En dynamique, la valeur descend de `initial` à `minimum` (atteint quand `decay` équipes ont résolu le défi après la première). Toutes les équipes reçoivent la valeur actuelle, y compris celles qui ont résolu tôt. Les équipes masquées par l'orga ne comptent pas.

## 3. `challenge.yml`

| Champ | Type | Défaut | Description |
|---|---|---|---|
| `id` | identifiant | requis | Unique dans le pack |
| `name` | texte | requis | Titre affiché |
| `category` | id de catégorie | requis | Doit exister dans `event.yml` |
| `difficulty` | texte | — | Doit figurer dans `difficulties` |
| `authors`, `tags` | listes | `[]` | Les tags servent aussi aux règles `solved_count` |
| `description` | chemin | `description.md` | Markdown, HTML brut ignoré |
| `scoring` | barème | celui de l'événement | Voir ci-dessus |
| `flags` | liste | requis | Au moins un flag accepté (voir ci-dessous) |
| `files` | liste de chemins | `[]` | Relatifs au dossier du défi, dans le pack, hors `solution/` |
| `connection` | texte | — | Adresse du service (`nc ctf.example.org 4000`...) |
| `position` | entier | `0` | Ordre dans sa catégorie (puis ordre alphabétique) |
| `unlock` | règle | toujours débloqué | Voir §4 |
| `when_locked` | `hidden` \| `teaser` | `hidden` | `teaser` : titre visible avec un cadenas |
| `locked_message` | texte | — | Affiché sous le cadenas en mode `teaser` |
| `hints` | liste | `[]` | Voir ci-dessous |
| `on_solve` | liste | `[]` | `{ grant_item: <id> }` ou `{ notify: "Markdown" }` |

### Flags

```yaml
flags:
  - { type: static, value: "CTF{exact}" }                       # sensible à la casse
  - { type: static, value: "CTF{peu_importe}", case_sensitive: false }
  - { type: regex, pattern: 'CTF\{(lyon|lugdunum)\}', case_sensitive: false }
```

- Les espaces autour de la réponse sont ignorés.
- Une regex doit couvrir **toute** la réponse (ancrage implicite).
- Plusieurs flags = plusieurs réponses acceptées.

### Indices

```yaml
hints:
  - id: cesar-1                 # unique dans tout le pack
    text: "Pense à un empereur romain."
    cost: 0                     # gratuit
  - id: cesar-2
    text: "Cherche « ROT13 »."
    cost: 50                    # déduit du score de l'équipe
    available: { time: { elapsed_minutes: 60 } }   # règle facultative
```

Le texte d'un indice n'est envoyé qu'après son achat. Le coût est figé au moment de l'achat.

### Actions à la résolution

```yaml
on_solve:
  - grant_item: fragment-web        # l'objet doit être déclaré dans event.yml
  - notify: "Tu as trouvé un **fragment** ! Regarde ton inventaire."
```

## 4. Règles de déblocage

Une règle est un objet à **une seule clé**.

| Règle | Vraie si |
|---|---|
| `{ solved: <id> }` | l'équipe a résolu ce défi |
| `{ solved_count: { gte: N, category?: <id>, tag?: <tag>, difficulty?: <d> } }` | au moins N défis résolus, avec filtres facultatifs |
| `{ score: { gte: N } }` | score de l'équipe (indices déduits) ≥ N |
| `{ item: <id> }` | l'équipe possède cet objet |
| `{ hint_used: <id> }` | l'équipe a acheté cet indice |
| `{ time: { after: <date> } }` | après cette date |
| `{ time: { before: <date> } }` | avant cette date |
| `{ time: { elapsed_minutes: N } }` | N minutes après le début de l'événement |
| `{ all: [règles] }` | toutes vraies |
| `{ any: [règles] }` | au moins une vraie |
| `{ not: règle }` | la règle est fausse |

Exemple :

```yaml
unlock:
  all:
    - { item: fragment-web }
    - { item: fragment-crypto }
    - any:
        - { solved_count: { tag: osint, gte: 2 } }
        - { time: { elapsed_minutes: 180 } }
```

**Les déblocages sont définitifs** : ce qui a été débloqué par une équipe le reste, même si la règle redevient fausse (score qui baisse, `before` dépassé). Un défi résolu est toujours considéré comme débloqué.

Les règles sont aussi utilisables dans `hints[].available` et dans l'en-tête des chapitres d'histoire.

## 5. Chapitres d'histoire

Fichiers `story/*.md` : un en-tête YAML entre deux lignes `---`, puis le texte en Markdown.

```markdown
---
id: chapitre-2
title: "Un message chiffré"
order: 2
unlock: { solved: intro }
---

Le texte du chapitre, en **Markdown**.
```

| Champ | Type | Défaut | Description |
|---|---|---|---|
| `id` | identifiant | requis | Unique parmi les chapitres |
| `title` | texte | requis | |
| `order` | entier | `0` | Ordre d'affichage |
| `unlock` | règle | toujours débloqué | Débloqué à partir du début de l'événement |
| `public` | booléen | `false` | Visible par tous, avant le début et sans compte (prologue) ; incompatible avec `unlock` |

## 6. Validation

```bash
jacquard pack validate <dossier>
```

Erreurs bloquantes :

- fichier YAML invalide, champ inconnu, valeur hors format ;
- référence vers un défi, une catégorie, une difficulté, un objet ou un indice inexistant ;
- fichier introuvable, hors du pack ou dans un dossier `solution/` ;
- identifiant de défi, d'indice ou de chapitre en double ;
- **défi impossible à débloquer** : dépendance circulaire, score requis supérieur au maximum atteignable, date après la fin, objet que rien n'accorde…

Avertissements :

- flag statique qui ne respecte pas `flag_format` ;
- objet déclaré mais accordé par aucun défi ;
- chapitre impossible à débloquer ;
- `locked_message` sur un défi `hidden` (il ne sera jamais affiché).

La synchronisation (`jacquard pack sync`) est idempotente et peut être relancée pendant l'événement : un défi retiré est désactivé, jamais supprimé, et les résolutions, achats d'indices et déblocages sont conservés.

## 7. Conseils d'écriture

- Commencer par un défi `bienvenue` sans règle, dont le flag est dans la description : tout le monde marque un point dès la première minute.
- Préférer `teaser` pour les défis qu'on veut faire désirer, `hidden` pour les surprises.
- Toujours lancer `jacquard pack validate` avant de pousser le pack.
- Ne jamais mettre de flag dans `src/` d'un défi distribué tel quel : seuls les fichiers listés dans `files` sont servis, mais un fichier copié par erreur part avec son contenu.
