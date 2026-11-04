# Direction artistique : Lumignons

Référence de l'interface de Jacquard (refonte de novembre 2026). Toute page, tout composant
s'y conforme ; le juge de design (`docs/refonte-ui/juge.md`) la reçoit en entrée. Méthode et
recherche : `docs/refonte-ui/`. La direction a été choisie parmi quatre prototypes (dépôt de
l'événement, `design/`).

## Concept

La ville est vue de nuit comme une architecture. Un système, LUMEN, la tient sous une lumière
froide ; chaque défi résolu pose une lumière chaude (un lumignon) à une fenêtre de son quartier,
comme le 8 décembre à Lyon. Chaque quartier (catégorie) est un immeuble ; chaque défi, une
fenêtre, rangée dans l'ordre où les défis s'ouvrent. La structure de déblocage n'apparaît qu'à
la demande : un fil de soie court d'appui en appui dans l'immeuble choisi.

**Une seule audace : le plan de nuit.** Tout le reste est calme, discipliné, lisible.

## Couleurs : 6 nommées, 4 dérivées (aucune autre valeur, aucune opacité pour « éteindre »)

| Jeton | Hex | Rôle |
|---|---|---|
| `--nuit` | `#2E2936` | fond, sol de la carte |
| `--eau` | `#131419` | rivières, champs de saisie, fond des zones de code ; seul quasi-noir |
| `--pierre` | `#4A4354` | façades, filets de 1 px, ponts |
| `--claire` | `#EDE7DF` | texte, bouton principal, focus, cadre « disponible » |
| `--lumignon` | `#F5A23D` | **résolu uniquement** : fenêtres, fil parcouru, score de l'équipe |
| `--lumen` | `#DDEBF7` | **verrouillé, compte à rebours, erreurs** : fenêtres froides, fil pointillé, quais |
| `--pierre-sombre` | `#3A3444` | survol des rangées, fond des panneaux |
| `--toit` | `#221E29` | toits, silhouettes, façades des quartiers mis en retrait |
| `--douce` | `#BCB3C2` | texte secondaire (≥ 6,9:1), bordures des commandes |
| `--voile` | `#A6BDD1` | texte des éléments verrouillés |

Le chaud ne sert jamais d'accent d'interface : il marque seulement ce que l'équipe a gagné.

## Typographie

- **Le Murmure** (Velvetyne, OFL 1.1) : logotype, titres de page, noms de quartier, titres
  d'événement en direct. **Jamais sous 21 px, jamais pour un chiffre.**
- **Luciole** (Laurent Bourcellier et Jonathan Fabreguettes, CC BY 4.0, **crédit affiché en
  pied de page**) : tout le reste. Chiffres en `tabular-nums` ; ordinal « 2e » en
  `font-variant-position: super`.
- Italique : noms de rivières et italique présent dans un contenu fourni (Markdown).
- Typographie française : espace fine insécable avant « : ; ? ! », à l'intérieur des
  guillemets « », apostrophe typographique.

Échelle (seules tailles rendues) : **14 · 16 · 18 · 21 · 24 · 36 · 48** px (72 réservé au
grand écran). À 640 px et moins, rien sous 16 px.

| Taille | Usage |
|---|---|
| 48 | titre de page, titre du défi ouvert |
| 36 | logotype, nom de quartier dans la liste |
| 24 | nom de quartier sur la carte large et sous l'élévation du panneau, titre d'événement |
| 21 | compte à rebours ; nom de quartier sur une carte étroite |
| 18 | nom de défi, valeurs, énoncé, champ du flag |
| 16 | texte courant, navigation, boutons, légende |
| 14 | méta (difficulté, résolutions, état, étiquettes) — bureau seulement |

## Espacement et bords

Multiples de 4 : 4, 8, 12, 16, 24, 32, 48, 64. Aucune autre valeur. Rangées ≥ 56 px. Dans
une colonne, un seul bord gauche et un seul bord droit pour tout le contenu (les fonds de
survol débordent de 8 px, pas le contenu). Gouttière de page : 32 px (bureau), 16 px (mobile).

## Formes

- Arrondis : **0** pour l'architecture (panneaux, rangées, carte), **2 px** pour les commandes,
  l'arc pour les fenêtres de certains immeubles. Aucune ombre, aucun dégradé, aucun flou.
- Filets : 1 px `--pierre`.
- **Fenêtre-marque** 12 × 18 : pleine chaude (résolu), vide cadrée `--claire` (disponible),
  pleine froide (verrouillé). Même forme partout (liste, légende, panneau).
- **Fil de soie** : 3 px à l'écran, posé sur une façade (jamais sur l'eau), pend entre deux
  appuis. Chaud plein (parcouru), `--douce` plein (jusqu'à la fenêtre ouverte), `--lumen`
  pointillé 4/4 (au-delà). Visible seulement pour le quartier choisi et dans le panneau.

## Composants (un style chacun)

- **Principal** (Valider, Créer, Se connecter) : plein `--claire`, texte `--nuit`, 48 px de haut.
- **Secondaire** (Copier, Voir l'indice, Voir le quartier) : cadre 2 px `--douce`, 44 px.
- **Texte** (Fermer, Annuler, Revoir toute la ville) : souligné, 44 px de haut.
- **Champ** : fond `--eau`, cadre 2 px `--douce` (`--claire` au survol et au focus).
  **Erreur** : cadre 3 px `--lumen` **et** message précédé du mot « Refusé » en gras (pas la
  couleur seule).
- **Événement en direct** (premier sang, annonce) : pas de boîte ni de notification flottante
  à bordure ; une ligne de chronique sous la carte, filet de 1 px au-dessus, titre en Le Murmure,
  actions en ligne. Les notifications éphémères gardent la même forme, empilées en bas.
- **Panneau** (défi ouvert) : fond `--pierre-sombre`, titre 48 px, élévation de l'immeuble avec
  la fenêtre du défi cadrée et une phrase d'ordre (« Deuxième des trois défis… Après « X ».
  Ouvre ensuite « Y ». »), faits (difficulté, points, résolutions), énoncé, adresse, fichiers,
  indices, formulaire du flag fixé en bas.

## Comportement (exigences issues des passes du juge)

1. **Quartier choisi** : son immeuble garde ses couleurs et montre son fil ; les autres passent
   en silhouette (façades `--toit`, fenêtres `--pierre`, étiquettes `--douce`). Un seul point
   focal. Le choix est annoncé (`aria-live` : « Fourvière : 3 défis ») ; sur mobile, la liste
   défile jusqu'au quartier (instantané en mouvement réduit). Retirer le choix rend le focus au
   bouton du quartier.
2. **Formulaire du flag fixé en bas du panneau** : le contenu défilant a une marge basse au
   moins égale à sa hauteur (`scroll-padding-bottom`) ; aucun élément focalisé ni aucun texte
   n'est jamais masqué par lui.
3. **Indices** : l'indice débloqué affiche son texte, le focus va sur ce texte, le score de
   l'équipe se met à jour. Un indice payant demande confirmation ; Échap annule la
   confirmation seule (la couche la plus interne).
4. **Panneau** : se comporte comme une fenêtre modale à toutes les largeurs (le reste est
   inerte, Tab boucle dans le panneau) ; Échap et « Fermer » le ferment ; le focus revient au
   déclencheur, sinon au bouton du quartier sur la carte. Le retour arrière du navigateur ferme
   le panneau avec le même retour de focus.
5. **Résultats visibles** : flag correct (la fenêtre s'allume, score et rang à jour, message de
   réussite), flag faux (message avec solution), envoi en cours (bouton désactivé et libellé
   « Vérification… »).
6. **États** : chargement (texte simple, pas de squelette animé), erreur d'API (message avec
   action), vide (phrase et action suivante), session expirée.

## Mouvement

Un seul moment orchestré : **l'allumage**. Au premier affichage de la session, toutes les
fenêtres sont froides, puis les fenêtres résolues s'allument une à une dans l'ordre réel des
résolutions (110 ms d'intervalle, sans fondu). Rien en `prefers-reduced-motion`. Tout le reste
est instantané (on agit, ça change). Pas de `transition: all`, pas d'animation en boucle.

## Interdits (en plus des marqueurs de `docs/refonte-ui/recherche.md`)

Fond crème, look « hacker » (vert sur noir, faux terminal, glitch), dégradés, halos, verre
dépoli, cartes à bordure colorée, pastilles en série, capitales espacées, monospace pour des
étiquettes, « → » accolé, emoji, icônes Lucide, numérotation décorative, opacité pour
atténuer, couleur hors jetons, police hors des deux familles.
