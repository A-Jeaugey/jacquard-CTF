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

Les immeubles sont de l'architecture, pas des icônes : chacun reprend son quartier (l'immeuble
de canuts et ses hautes fenêtres d'atelier, la basilique et sa tour métallique, le crayon de
la Part-Dieu, les pignons du Vieux Lyon, la traboule et son passage voûté, le musée des
Confluences, la halle de Gerland, l'école du Terrain), avec ses étages, corniches, cheminées,
portes et volets clos. Les volets clos sont le décor ; seules les fenêtres des défis portent
une lumière. **Rendu : gravure de nuit** (choix de l'orga) : l'architecture au trait `--douce`,
les façades en assises de pierre (lignes `--pierre` sur `--nuit`), les ombres hachurées, les
toits et volets au trait sur `--nuit`, les portes `--eau` ; motifs `#jq-assises` et
`#jq-hachures` posés une fois dans `App.svelte`. Un quartier en retrait devient une silhouette
`--toit` au trait `--pierre`, sans assises ni hachures.

**Une seule audace : le plan de nuit.** Tout le reste est calme, discipliné, lisible.

## Couleurs : 6 nommées, 4 dérivées (aucune autre valeur, aucune opacité pour « éteindre »)

| Jeton | Hex | Rôle |
|---|---|---|
| `--nuit` | `#2E2936` | fond, sol de la carte |
| `--eau` | `#131419` | rivières, champs de saisie, fond des zones de code ; seul quasi-noir |
| `--pierre` | `#4A4354` | façades, filets de 1 px, ponts |
| `--claire` | `#EDE7DF` | texte, bouton principal, focus, cadre « disponible » |
| `--lumignon` | `#F5A23D` | **résolu uniquement** : fenêtres, fil parcouru, score de l'équipe |
| `--lumen` | `#DDEBF7` | **verrouillé, compte à rebours, erreurs** : fenêtres froides, fil pointillé, quais ; LUMEN lui-même : sa voix (citations des messages) et la couronne de sa tour, à la Part-Dieu |
| `--pierre-sombre` | `#3A3444` | survol des rangées, fond des panneaux |
| `--toit` | `#221E29` | toits, silhouettes, façades des quartiers mis en retrait |
| `--douce` | `#BCB3C2` | texte secondaire (≥ 6,9:1), bordures des commandes |
| `--voile` | `#A6BDD1` | texte des éléments verrouillés |

Le chaud ne sert jamais d'accent d'interface : il marque seulement ce que l'équipe a gagné.

## Typographie

- **Lumignons** : Le Murmure (Jérémy Landes, Velvetyne, OFL 1.1) dont le C, le c, le Ç et
  le ç ont été redessinés. Le terminal du haut d'origine plongeait vers l'intérieur et faisait
  lire « Eroix-Rousse » ; les nouvelles lettres ont une ouverture franche, avec les terminaux
  fins de la police. Renommée parce que la licence réserve le nom « Le Murmure » ; se
  reconstruit avec `scripts/police-lumignons.py`. Logotype, titres de page, noms de quartier,
  titres d'événement en direct. **Jamais sous 21 px, jamais pour un chiffre.**
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
| 36 | logotype, nom de quartier dans la liste du plan |
| 24 | nom de quartier sur la carte large, sous l'élévation du panneau et dans la page équipe (sous un titre de section à 36), titre d'événement |
| 21 | compte à rebours ; nom de quartier sur une carte étroite |
| 18 | nom de défi, valeurs, énoncé, champ du flag |
| 16 | texte courant, navigation, boutons, légende |
| 14 | méta (difficulté, résolutions, état, étiquettes) — bureau seulement |

## Espacement et bords

Multiples de 4 : 4, 8, 12, 16, 24, 32, 48, 64. Aucune autre valeur. Rangées ≥ 56 px. Dans
une colonne, un seul bord gauche et un seul bord droit pour tout le contenu (les fonds de
survol débordent de 8 px, pas le contenu). Gouttière de page : 32 px (bureau), 16 px (mobile).
**Cadre** : au-delà de 1440 px de large, le site tient dans un cadre centré de 1440 px
(`--cadre`) ; l'en-tête et le pied gardent leur filet sur toute la largeur, mais leurs bords
(`--bord`) tombent sur ceux du cadre. Sans lui, sur un écran de 1880 ou 2560 px, le texte
restait au bord gauche et la ville au bord droit, avec un trou au milieu. Le grand écran,
lui, prend toute la largeur du projecteur.

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
  à bordure ; une ligne de chronique sous la carte, filet de 1 px au-dessus, titre en Lumignons,
  actions en ligne. Les notifications éphémères gardent la même forme, empilées en bas.
- **Panneau** (défi ouvert) : fond `--pierre-sombre`, titre 48 px, élévation de l'immeuble avec
  la fenêtre du défi cadrée et une phrase d'ordre (« Deuxième des trois défis… Après « X ».
  Ouvre ensuite « Y ». »), faits (difficulté, points, résolutions), énoncé, adresse, fichiers,
  indices, formulaire du flag fixé en bas.

## Comportement (exigences issues des passes du juge)

1. **Quartier choisi** : son immeuble garde ses couleurs et montre son fil ; les autres passent
   en silhouette (façades `--toit` au trait `--pierre`, fenêtres `--pierre`, étiquettes `--douce`). Un seul point
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

## Les autres pages

- **Accueil** : une scène d'ouverture, qui tient dans le premier écran. En haut, l'accroche
  de l'événement en grand (son nom est déjà le logotype de l'en-tête ; 72 px dès 1280 × 760,
  96 px dès 1800 × 1100) ; à sa droite dès 900 px de large, les dates, la soirée en deux
  lignes (équipes en jeu, défis résolus) et l'action suivante ; pour un joueur, la
  situation de son équipe. Puis **le panorama** sur toute la largeur de l'écran, posé au
  bas de l'écran dès que l'en-tête tient sur une ligne (1100 px) ; sa taille suit la
  largeur et la hauteur qui restent sous le titre, si bien que la ville est entière à
  l'écran de 1280 × 720 à 2560 × 1300 ; sur téléphone, elle passe sous le contenu. Les huit
  quartiers en ligne d'horizon, gravés, devant des toits lointains en silhouette ; le quai
  (`--lumen`) et la Saône (`--eau`), où chaque fenêtre allumée se reflète. Une fenêtre s'y
  allume dès qu'une équipe a résolu son défi (classement public) : avant le départ, la ville
  froide de LUMEN. Dessous, le prologue (visiteurs seulement : les joueurs le retrouvent
  dans leurs messages) et les annonces, côte à côte.
- **Accès** (connexion, inscription, page introuvable) : contenu en haut à gauche sur 480 px
  au plus, titre et phrase d'accueil dans la voix de l'événement, et le même panorama au
  pied de l'écran, plus petit : le formulaire passe avant, la ville prend la hauteur qui
  reste (sur un écran bas, elle passe sous le formulaire). Le panorama est décoratif (aria-hidden) : l'état des
  défis est dit sur le plan et au classement.
- **Joueur** (équipe, classement, messages) : une colonne de lecture de 880 px au plus,
  alignée à gauche ; l'univers passe par les mots, la couleur `--lumignon` réservée à ce qui
  est gagné et les dessins de la ville : sur le classement, chaque équipe a sa ville (la même
  silhouette pour toutes : un immeuble par quartier, qui reprend en petit la silhouette de son
  quartier sur le plan (la tour et sa pointe pour la Part-Dieu, la flèche et le fronton pour
  Fourvière, les pignons du Vieux Lyon, les sheds et la cheminée de Gerland, l'école basse du
  Terrain…, gravés au trait comme les immeubles du plan), une fenêtre de 8 × 12 par défi public
  toujours à la même place, allumée quand l'équipe l'a résolu ; les places sont mélangées une
  fois pour toutes, pour qu'une façade ne se remplisse pas comme une jauge ; un quartier fourni monte en
  étages, quatre au plus, plutôt qu'en largeur ; le nombre seul à côté, sans libellé répété ;
  une phrase sous l'introduction nomme les quartiers de gauche à droite). La ville ne prend
  jamais la place du nom : le nom garde 10 rem au moins, la ville se réduit (18 rem au plus)
  et passe sous le nom en dessous de 761 px. La page équipe commence par « Les quartiers »,
  les huit toujours présents (leur immeuble aux fenêtres de l'équipe, calé à gauche ;
  l'avancement écrit seulement pour les lecteurs d'écran ; puis les défis résolus : qui,
  quand ; une phrase quand aucun ne l'est), puis les fils de soie (description, puis le motif
  sur sa propre ligne, en disques pleins et vides dessinés à la même taille, le texte ●○
  restant pour les lecteurs d'écran et le copier-coller), puis l'atelier (code d'invitation,
  membres, départ). Les messages de l'histoire sont des lettres : titre,
  texte, signature ; la voix de LUMEN y est une citation en `--lumen` avec un filet de 2 px
  `--lumen` à gauche, seule bordure de couleur du site (elle porte l'information « c'est LUMEN
  qui parle »).
- **Grand écran** (vidéoprojecteur, 1920 × 1080, lu à cinq mètres) : rien sous 24 px en
  1920 × 1080 (21 px sur un projecteur de moins de 1001 px de haut), aucune
  interaction, rien ne défile ; la ville s'allume avec la progression de toutes les équipes, à
  côté du compte à rebours et du classement (autant d'équipes que la hauteur en montre, et la
  page le dit) ; sous la ville, la progression en une phrase et le dernier événement (la même
  chronique que sous le plan, sans action). Tailles par paliers selon la hauteur de l'écran
  (72/48/36/24 dès 1001 px, 48/36/24/21 en dessous). Si le réseau saute, la dernière image
  reste affichée. Ouvert sur un petit écran (ce n'est pas son usage), tout s'empile sans
  débordement.
- **Administration** : outil des organisateurs, pas une page du jeu. Tableaux, onglets et
  formulaires sont attendus ici ; mêmes jetons, mêmes composants, aucune illustration.
  L'onglet courant porte la marque de la page courante de l'en-tête (`--claire`, souligné de
  2 px, sans gras) ; les cellules s'alignent sur la ligne de base ; une ligne en retrait
  (équipe masquée, défi sans tentative) passe en `--douce`, `--voile` restant réservé au
  verrouillé.

## En-tête

Tous les liens de l'en-tête (navigation, accès, nom de l'équipe, « Se déconnecter ») ont un
seul traitement : `--douce` au repos, `--claire` et souligné au survol, `--claire` et souligné
de 2 px sur la page courante, sans gras (rien ne change de largeur d'une page à l'autre).
Soulignés à 4 px du texte, comme partout. Sur petit écran, la navigation et les liens
d'accès partent de la gouttière (le premier lien n'a pas de retrait), comme le reste de
l'en-tête. Le nom de l'équipe ne sort jamais de sa colonne (points de suspension) ; le nom
de l'administrateur, qui n'est pas un lien, est en `--douce`. Un nom d'événement très long
tient sur deux lignes, coupées net.

## Mouvement

Un seul moment orchestré : **l'allumage**, sur le plan comme sur le panorama de l'accueil et
des pages d'accès. Au premier affichage de la session, toutes les
fenêtres sont froides, puis les fenêtres résolues s'allument une à une dans l'ordre réel des
résolutions (110 ms d'intervalle, sans fondu). Il se décide une seule fois, à l'arrivée de la
progression de l'équipe : un rechargement ne le relance ni ne l'interrompt, et une équipe qui
n'a encore rien résolu ne le voit pas (sa première fenêtre s'allume tout de suite). Rien en
`prefers-reduced-motion`. Tout le reste
est instantané (on agit, ça change). Pas de `transition: all`, pas d'animation en boucle.

## Interdits (en plus des marqueurs de `docs/refonte-ui/recherche.md`)

Fond crème, look « hacker » (vert sur noir, faux terminal, glitch), dégradés, halos, verre
dépoli, cartes à bordure colorée, pastilles en série, capitales espacées, monospace pour des
étiquettes, « → » accolé, emoji, icônes Lucide, numérotation décorative, opacité pour
atténuer, couleur hors jetons, police hors des deux familles.
