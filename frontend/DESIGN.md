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

## Couleurs : 6 nommées, 5 dérivées (aucune autre valeur, aucune opacité pour « éteindre »)

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
| `--table` | `#16151C` | la table sous la maquette en volume : fond de la page des défis et voiles sous le texte |

Le chaud ne sert jamais d'accent d'interface : il marque seulement ce que l'équipe a gagné.

## La ville en volume (défis, grand écran, accueil et pages d'accès)

**État : en place depuis le 12 novembre 2026, sur décision de l'orga ; aucun juge ne l'a
vue.** Elle remplace le dessin à plat sur la page des défis et le grand écran (le plan de
Lyon), sur l'accueil et les pages d'accès (le panorama du quai). Le classement et la page de
l'équipe gardent leurs immeubles dessinés : de petits dessins répétés, pas des scènes.
Partout, le dessin à plat reste le repli.

Limites connues : elle n'a été essayée que sur une carte graphique puissante, ni sur un
portable modeste ni sur un téléphone ; et les tests de bout en bout tournent dans un
navigateur sans carte graphique, donc sur le repli à plat.

Après la bande-annonce en 3D, le plan de nuit devient la maquette du film : Lyon posée sur une
table, les huit immeubles en volume entre la Saône et le Rhône, rendue en temps réel
(three.js, `lib/maquette3d.ts`, `components/ville/Ville3D.svelte`). Sur bureau, elle occupe
toute la fenêtre, sous l'en-tête et sous les colonnes de texte ; sur tablette et téléphone,
c'est un bloc au-dessus de la liste. Elle reste l'unique audace de la page.

- **Trois vues**, portées par ce que la page sait déjà : toute la ville, le quartier choisi
  (la caméra s'en approche et le regarde de trois quarts, du côté où aucun voisin ne passe
  devant), le défi ouvert (sa fenêtre est cernée ; la caméra recadre l'immeuble dans la place
  que laisse le panneau). La caméra centre toujours son sujet dans la place libre : la page lui
  dit ce que l'interface recouvre.
- **Les deux lumières viennent de la scène.** Les fenêtres, les fils, les rives et la
  couronne de la tour éclairent et rayonnent (un éclat au-dessus d'un seuil, comme dans le
  film) ; une lueur chaude grandit devant un quartier à mesure qu'il est gagné. C'est la seule
  exception à « aucune ombre, aucun halo » : rien de tel sur un élément d'interface.
- **Trois voiles `--table`** rendent le texte lisible sur la scène, comme les titres du film :
  sous l'en-tête, sous les colonnes de droite, en bas sous la légende. Ce sont les seuls
  dégradés du site.
- **Une fenêtre par défi, posée par le site** : la maquette (`public/ville/lyon.glb`) ne
  contient que les volumes. Les fenêtres et le fil viennent de `lib/ville.ts`, comme sur le
  plan à plat ; si un quartier n'a pas le nombre de défis du dessin, un pan de pierre recouvre
  les niches et les fenêtres sont posées en applique.
- **Fenêtre disponible** : éteinte, cernée de `--claire` (2 px à l'écran ; 3 px survolée,
  4 px ouverte). **Fil** : chaud sur la partie gagnée, toujours visible ; `--douce` jusqu'à la
  fenêtre ouverte et froid au-delà, seulement dans le quartier choisi.
- **Noms des immeubles** : Lumignons 24 px (21 px sur téléphone), liseré `--eau` ; au-dessus de
  l'immeuble pour la rangée du nord, à ses pieds pour les autres. Aucun nom sous l'interface,
  ni pour l'immeuble choisi (son nom est le titre de la liste).
- **Accès** : chaque immeuble garde son bouton (même libellé que sur le plan à plat), posé sur
  lui. Les fenêtres du quartier choisi sont des raccourcis à la souris, cachés aux lecteurs
  d'écran : la liste porte les mêmes liens. Survoler un défi dans la liste cerne sa fenêtre,
  et inversement. Glisser fait tourner la maquette (elle revient d'elle-même au changement de
  vue) ; sur un écran tactile, glisser de haut en bas fait défiler la page.
- **Mouvement** : le vol de la caméra d'une vue à l'autre (1,1 s), une fenêtre qui s'allume
  (0,45 s), un fil qui se tend à la résolution (0,7 s). En mouvement réduit, tout change d'un
  coup. L'allumage du premier affichage est le même que sur le plan à plat.
- **Repli** : sans WebGL 2, avec une carte graphique émulée, ou si la maquette ne se charge
  pas, le plan à plat s'affiche avec sa mise en page d'origine. Le joueur peut aussi le
  choisir (« Afficher le plan à plat », retenu dans le navigateur).
- **Coût** : three.js forme un fichier à part (environ 180 ko compressés), chargé seulement
  par les pages qui montrent la ville ; une scène ne se redessine que lorsque quelque chose
  bouge (sauf la ronde du grand écran).

### Le grand écran

La même maquette, en décor : elle occupe tout l'écran derrière le texte, cadrée dans la place
du plan à plat, et **tourne lentement** (un tour en deux minutes, trente images par seconde).
Les fenêtres non résolues sont éteintes, pas froides, comme sur le plan à plat du grand écran.
Les noms des immeubles sont au-dessus d'eux, à la taille de base de l'écran (24 px en 1080).
Un voile `--table` porte la colonne du classement.

### Le quai : l'accueil et les pages d'accès

Le premier plan de la bande-annonce, en temps réel (`components/ville/Panorama3D.svelte`) : les
huit immeubles de la maquette **alignés sur le quai**, face à la Saône, dans l'ordre du
panorama à plat ; derrière, trois plans de toits en silhouette ; devant, l'eau où tout se
reflète (les reflets s'étirent de haut en bas). La caméra regarde à l'horizontale : les
verticales restent droites.

- **Plein cadre** : sur bureau, la scène occupe toute la première vue, sous le titre et le
  formulaire ; le haut du ciel est `--nuit`, la couleur de la page, sans raccord. Sur un
  écran étroit, c'est un bloc sous le texte, et la rangée garde une taille lisible (ses bords
  sont rognés), comme le panorama à plat.
- **La ville de tous** : une fenêtre s'allume dès qu'une équipe a résolu son défi (classement
  public). Avec la part des défis résolus, le filet du quai passe du froid à l'ambre depuis la
  gauche, et les petites fenêtres des toits lointains s'allument.
- **Mouvement** : l'allumage du premier affichage (le même que le panorama à plat), et un
  léger décalage de la caméra avec la souris, qui fait glisser les toits lointains. Rien en
  mouvement réduit. Pas d'animation continue.
- **Décor** : caché aux lecteurs d'écran, sans aucune action.

### D'où vient la maquette

La maquette est produite par Blender à partir des dessins de `lib/ville.ts`, par le script
`video/3d/exporter_web.py` du pack Traboules (dépôt privé de l'événement), qui écrit
`public/ville/lyon.glb` et `lyon.json`. Les matières sont reprises par nom dans
`lib/maquette3d.ts`.

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
- **Panneau** (défi ouvert) : fond `--pierre-sombre` ; en tête, la barre du quartier
  (« Croix-Rousse, défi 2 sur 4 », Précédent, Suivant, Fermer), puis le titre 48 px,
  l'élévation de l'immeuble avec la fenêtre du défi cadrée et une phrase d'ordre (« Deuxième
  des trois défis… Après « X ». Ouvre ensuite « Y ». »), faits (difficulté, points,
  résolutions), énoncé, adresse, fichiers, indices, formulaire du flag à la suite. Après un
  flag correct, le défi suivant du quartier est proposé (bouton principal).

## Comportement (exigences issues des passes du juge)

1. **Quartier choisi** : son immeuble garde ses couleurs et montre son fil ; les autres passent
   en silhouette (façades `--toit` au trait `--pierre`, fenêtres `--pierre`, étiquettes `--douce`). Un seul point
   focal. Le choix est annoncé (`aria-live` : « Fourvière : 3 défis ») ; sur mobile, la liste
   défile jusqu'au quartier (instantané en mouvement réduit). Retirer le choix rend le focus au
   bouton du quartier.
2. **Formulaire du flag** : il suit l'énoncé (jamais de vide entre les deux) et ne se colle
   au bas du panneau que si l'énoncé dépasse l'écran ; le défilement garde une marge basse au
   moins égale à sa hauteur (`scroll-padding-bottom`) : aucun élément focalisé ni aucun texte
   n'est jamais masqué par lui.
3. **Indices** : l'indice débloqué affiche son texte, le focus va sur ce texte, le score de
   l'équipe se met à jour. Un indice payant demande confirmation ; Échap annule la
   confirmation seule (la couche la plus interne).
4. **Panneau** : jamais modal, rien n'est recouvert ni inerte (l'en-tête, la carte et la liste
   restent utilisables). Sur bureau (1100 × 700 et plus), le plan est une application : il
   prend toute la largeur de l'écran (pas le cadre de 1440 px, l'en-tête suit) et la carte est
   centrée dans sa colonne, aussi grande que celle-ci le permet. Le panneau s'y ajoute en
   troisième colonne (40 %, 520 à 760 px) : la carte se réduit, la liste se resserre (22 %,
   300 à 400 px ; 38 %, 460 à 640 px sans panneau) sur le quartier du défi, où
   la ligne du défi ouvert est repérée (fond `--pierre-sombre`, filet `--claire` de 3 px à
   gauche) ; la grille glisse en 320 ms, le panneau entre de 32 px, rien en mouvement réduit.
   Sur téléphone et tablette, le panneau devient la page sous l'en-tête. Passer d'un défi à
   l'autre (liste, Précédent, Suivant) remplace l'entrée d'historique : Échap, « Fermer » et
   le retour du navigateur ramènent toujours au plan, la liste retrouve le choix d'avant et le
   focus va à la ligne du défi, sinon au bouton du quartier sur la carte.
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
- **Joueur** (classement, messages) : une colonne de lecture de 880 px au plus,
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
  et passe sous le nom en dessous de 761 px. Les messages de l'histoire sont des lettres : titre,
  texte, signature ; la voix de LUMEN y est une citation en `--lumen` avec un filet de 2 px
  `--lumen` à gauche, seule bordure de couleur du site (elle porte l'information « c'est LUMEN
  qui parle »).
- **Équipe** : toute la largeur du cadre. Le nom, puis une bande de chiffres (rang, score,
  défis résolus, fils) en Lumignons 40 px, séparés par des filets. Puis « Les quartiers » : la
  rue des huit immeubles à la même échelle (colonnes proportionnelles à leur largeur, 1280 px
  au plus), posés sur un quai `--lumen`, leurs fenêtres allumées par les défis de l'équipe,
  le nom et l'avancement dessous (`--lumignon` quand le quartier est fini) ; chaque immeuble
  mène à son quartier sur le plan (`/challenges?quartier=…`) et se soulève de 4 px au survol.
  Sous 761 px, deux rangées de quatre, à la même échelle. Sans résolution : une phrase et
  « Aller au plan ». Puis deux colonnes : le journal de l'équipe (le plus récent d'abord : défi,
  points gagnés, quartier, qui, quand ; les six derniers, puis « Tout le journal ») et, à
  droite, le code d'invitation, les membres et le départ (avant le journal sur une colonne).
  Enfin les fils de soie (description, puis le motif sur sa propre ligne, en disques pleins
  et vides dessinés à la même taille, le texte ●○ restant pour les lecteurs d'écran et le
  copier-coller).
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
