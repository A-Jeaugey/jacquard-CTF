# Refonte de l'interface — synthèse de recherche (novembre 2026)

Objectif : reconstruire le frontend de Jacquard avec une direction artistique affirmée, sans
les marqueurs d'une interface générée par IA (« AI slop »), et avec un contrôle de qualité
fiable. Ce document rassemble ce que dit la littérature récente et en tire des règles
applicables. Les sources sont listées à la fin de chaque section.

## 1. Ce qui fait « site généré par IA »

### Marqueurs de premier ordre (les plus connus)

- **Typographie** : Inter, Roboto, Arial ou la pile système pour tout ; une seule famille,
  une seule graisse, échelle plate ; un mot du titre en italique, en serif ou d'une autre
  couleur ; titres en dégradé ; petites étiquettes en capitales espacées au-dessus de chaque
  titre ; monospace pour les petites étiquettes et les badges ; Title Case partout.
- **Couleur** : dégradés violet ou indigo vers bleu ; mode sombre violet avec texte gris peu
  contrasté ; halos colorés en ombre portée ; palette fluo sans hiérarchie ou palette timide
  uniformément répartie ; couleur principale et accent à moins de 20° de teinte.
- **Mise en page** : héros centré (pastille, titre, sous-titre, deux boutons, fond dégradé) ;
  gros chiffre + petite légende en héros ; trois cartes identiques avec icône ; grille
  « bento » par défaut ; numérotation décorative 01 / 02 / 03 ; même conteneur centré et
  même espacement pour toutes les sections.
- **Composants** : même grand arrondi et même ombre partout ; cartes avec bordure colorée à
  gauche ou en haut ; soupe de pastilles et de badges ; points de statut sans signification ;
  icône dans un carré arrondi teinté ; cartes dans des cartes ; bordure autour de chaque
  bloc ; verre dépoli ; fausse fenêtre macOS ou faux terminal ; effets de bibliothèques
  « prêtes à l'emploi » ; états vide, chargement, erreur et focus absents.
- **Icônes et images** : emoji en guise d'icônes ; jeu Lucide par défaut (Sparkles, Zap,
  Rocket, Shield) ; flèche « → » accolée aux liens ; avatars à initiales ; blobs 3D.
- **Mouvement** : même apparition en fondu-montée sur chaque section ; effet au survol sur
  chaque carte ; compteurs qui défilent ; rebonds ; points qui pulsent ; fonds « aurore ».
- **Texte** : « Élevez, transformez, libérez » ; chaînes d'infos séparées par des points
  médians (`A · B · C`) ; libellés `MOT — fragment` ; chiffres ronds invérifiables ; faits
  inventés.

### Marqueurs de second ordre (ce vers quoi les modèles se replient quand on interdit les premiers)

- Polices « gratuites de bon goût » devenues des clichés : Space Grotesk, Geist, Syne, Sora,
  Instrument Serif, Fraunces, Cal Sans, Clash Display, Satoshi, JetBrains Mono, Space Mono,
  VT323, Fira Code.
- Fond crème `#F4F1EA` + accent terracotta ; serif Georgia / Fraunces / Playfair avec un mot
  en italique (style maison des modèles Claude).
- Quasi-noir avec un unique accent vert acide ou vermillon ; vert émeraude comme accent de
  repli. **Piège pour un CTF** : noir + vert acide + monospace + faux terminal est exactement
  ce repli « hacker ».
- « Cosplay de journal » : filets fins, aucun arrondi, colonnes denses.
- Simple remplacement d'une palette fixe par une autre : interdire en termes généraux
  (« évite le look IA ») ne fait que déplacer le défaut.

### Ce que l'interface actuelle de Jacquard coche

Bordures colorées à gauche des cartes, pastilles partout, arrondi et ombre uniformes, mise en
page centrée, fond bleu nuit + doré, serif par défaut pour les titres, police système pour le
texte, points médians dans les métadonnées, étiquettes de statut en série. La carte de Lyon
(polygones plats aux couleurs unies) relève du même problème.

Sources : catalogue avoid-ai-design (67 marqueurs, 2026-09) https://github.com/funboy322/avoid-ai-design ;
étude de 1 590 sites Show HN (2026-04) https://adriankrebs.ch/blog/design-slop/ ;
catalogue Impeccable https://impeccable.style/slop ; Paralect https://www.paralect.com/blog/signs-of-ai-slop-in-design ;
Mania Design (2026-07) https://www.mania.design/blog/spot-the-slop-a-ui-designers-guide-to-fixing-ai-defaults/ ;
Sailop (2026-10) https://www.sailop.com/blog/ai-slop-2026-state-of-the-ai-generated-web.

## 2. Ce qui marche pour obtenir un bon design d'un modèle

Consignes d'Anthropic (skill `frontend-design`, version 2026-09 ; guide de prompting
d'Opus 5.5) et retours de praticiens qui ont mesuré :

1. **Ancrer le design dans le sujet** : son univers, ses matériaux, son vocabulaire. Ouvrir
   sur la chose la plus caractéristique de cet univers, pas sur un héros générique.
2. **Un cahier des charges concret plutôt que des adjectifs** : 4 à 6 couleurs nommées en
   hexadécimal, rôles typographiques, arrondi, durées d'animation, règles écrites
   (« les bordures doivent porter une information »). Les règles durables vivent dans un
   fichier (DESIGN.md) pour que les pages suivantes ne dérivent pas.
3. **Des interdictions nommées, pas générales** : Opus 5.5 respecte bien « pas de fond
   crème, pas de mot en italique dans les titres, pas d'étiquettes 01/02/03, pas
   d'étiquettes en monospace, pas de boutons en pilule ». Itérer : regarder ce que le
   premier rendu a utilisé par défaut, l'ajouter à la liste.
4. **Explorer plusieurs directions avant de construire** : proposer 3 ou 4 directions
   distinctes (fond, accent, typographie, justification), en choisir une, n'implémenter
   qu'elle. Le meilleur de quatre designs parallèles, itéré, est 56 % plus utilisable que la
   moyenne des originaux (NN/g).
5. **Planifier avant de coder** : plan de jetons + maquettes ASCII, relu contre le cahier
   des charges (« un brief similaire aboutirait-il ici ? »), puis construction.
6. **De la retenue** : « dépenser son audace à un seul endroit » ; un seul moment de
   mouvement orchestré. Les anciennes consignes (dégradés maillés, grain, ombres
   dramatiques) produisent elles-mêmes du slop aujourd'hui.
7. **Boucle de captures** : le modèle prend des captures pendant la construction et corrige,
   au moins deux fois par pièce ; garder un journal de ce qui a été essayé.
8. **Le vrai contenu** : les modèles inventent des faits ; fournir les textes réels et les
   cas limites (vide, très long, erreur).

Sources : https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md ;
https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5 ;
https://platform.claude.com/cookbook/coding-prompting-for-frontend-aesthetics ;
https://claude.com/resources/articles/improving-frontend-design-through-skills ;
Muzli (2026-09) https://muz.li/blog/claude-opus-5-5-for-designers/ ;
Agentic Design School (2026-10) https://agenticdesign.school/articles/brief-an-agent-like-a-design-partner ;
NN/g https://www.nngroup.com/articles/parallel-and-iterative-design/.

## 3. Le juge automatique : ce qu'il sait faire et ce qu'il rate

- **Trop indulgent** : notes moyennes proches de celles des humains mais resserrées ;
  surévalue la facilité d'usage. Le juge d'Anthropic trouvait de vrais défauts puis « se
  convainquait qu'ils n'étaient pas graves ».
- **Préférence pour sa propre famille** : un juge Claude note plus favorablement un travail
  produit par Claude, même sur des critères objectifs.
- **Imprécis dans l'espace** : chevauchements, alignements au pixel, marges inégales lui
  échappent ; combiner le rendu avec des mesures issues du DOM.
- **Instable** : verdicts qui changent d'un essai à l'autre ; proche du hasard entre deux
  versions de qualité voisine.
- **Rendements décroissants** : au-delà de 5 à 6 itérations, les retours ne servent plus et
  une version intermédiaire est souvent la meilleure.

Ce qui le rend fiable :

- des critères **binaires** (réussi / échoué) plutôt qu'une note sur 5 ;
- **un appel par dimension** (slop, finition, ergonomie et états) ;
- chaque défaut cité avec **la page, la largeur d'écran, le sélecteur et la preuve** ;
- des **mesures déterministes fournies en entrée** (contrastes, tailles calculées, axe,
  débordements, détecteur de slop) ;
- le droit de répondre « INCONNU : il me faut telle capture » ;
- une **comparaison par paires** (dans les deux ordres) entre l'itération courante et la
  meilleure précédente, pour garder la meilleure ;
- un **plafond de 6 cycles** par page, puis arbitrage humain ;
- des **points de contrôle humains** : choix de la direction et validation finale. Les
  « utilisateurs synthétiques » ne remplacent pas des tests avec de vraies personnes.

Sources : MLLM as a UI Judge (2025-10) https://arxiv.org/html/2510.08783v1 ;
Anthropic, conception de harnais (2026-03) https://anthropic.com/engineering/harness-design-long-running-apps ;
Anthropic, évaluations d'agents (2026-01) https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents ;
WebDevJudge (ICLR 2026) https://arxiv.org/html/2510.18560v2 ;
UICrit (UIST 2024) https://arxiv.org/html/2407.08850v3 ;
ArtifactsBench https://arxiv.org/abs/2507.04952 ;
NN/g, utilisateurs synthétiques https://nngroup.com/articles/synthetic-users/.

## 4. Grille du juge

Chaque critère est réussi ou échoué ; un échec cite largeur d'écran, sélecteur et preuve.
Une page est validée quand tous les critères passent sur deux essais (captures présentées
dans un ordre différent), sans défaut bloquant ou majeur, et que les contrôles automatiques
sont propres.

| # | Critère | Échoue si |
|---|---|---|
| A1 | Marqueurs de slop | Un marqueur des listes de la section 1 sans justification écrite dans DESIGN.md |
| A2 | Ancrage dans le sujet | La page pourrait être reprise telle quelle pour un autre produit ; rien n'y vient de l'univers de l'événement ; contredit DESIGN.md |
| B1 | Hiérarchie | Plusieurs points focaux en concurrence ; l'action principale n'est pas l'élément le plus visible |
| B2 | Typographie | Plus de 2 familles ; tailles hors échelle ; texte courant sous 16 px sur mobile ; lignes au-delà d'environ 80 caractères |
| B3 | Espacement et alignement | Valeurs hors de l'échelle de jetons ; espace entre groupes pas plus grand qu'à l'intérieur ; bords décalés de plus de 1 à 2 px |
| B4 | Couleur et contraste | Texte sous 4,5:1 (3:1 en grand) ; composants ou focus sous 3:1 ; couleur hors jetons ; couleur comme seul indicateur d'état |
| B5 | Cohérence | Un même composant diffère d'une page à l'autre ; arrondis non concentriques ; styles d'ombre ou de bordure mélangés |
| C1 | Adaptation à l'écran | Défilement horizontal à 375 ou 320 px ; chevauchement ou texte coupé ; cibles sous 24 px (44 px au doigt) |
| D1 | États | Survol, appui, focus visible, désactivé, chargement, vide ou erreur absent ; état vide sans action suivante |
| D2 | Mouvement | `prefers-reduced-motion` ignoré ; `transition: all` ; propriétés de mise en page animées ; animation décorative en boucle |
| D3 | Contenu et robustesse | Texte de remplissage ; contenu long qui casse la mise en page ; message d'erreur sans solution ; erreurs console ; décalage de mise en page (CLS) > 0,1 |
| E1 | Thèmes de packs | La page casse ou perd sa lisibilité avec un autre pack (démo et Traboules) |

Sources des critères : heuristiques de Nielsen https://www.nngroup.com/articles/ten-usability-heuristics/ ;
Vercel Web Interface Guidelines https://vercel.com/design/guidelines ; WCAG 2.2 https://www.w3.org/TR/WCAG22/ ;
Refactoring UI ; agent de revue OneRedOak https://github.com/OneRedOak/claude-code-workflows.

## 5. Outils retenus

| Outil | Usage | Verdict |
|---|---|---|
| Skill `frontend-design` d'Anthropic | Méthode de base (brief, plan de jetons, retenue) | Oui, complété par notre DESIGN.md |
| Impeccable (`npx impeccable detect`) | 62 règles déterministes de détection de slop | Oui, en contrôle automatique |
| avoid-ai-design (`detect.mjs`) | Détecteur sans dépendance, utilisable en hook | Oui, en complément |
| Plugin Svelte officiel (MCP + autofixer) | Code Svelte 5 correct | Oui |
| Playwright (captures, `toHaveScreenshot`) | Boucle de captures, non-régression visuelle | Oui (déjà en place) |
| @axe-core/playwright, Lighthouse | Accessibilité, performance | Oui, en CI |
| Bits UI | Primitives accessibles sans style imposé | Oui |
| CSS natif + jetons à trois niveaux | Thèmes de packs surchargeables | Oui (pas de Tailwind) |
| GSAP (gratuit depuis 2025), Motion, View Transitions | Carte SVG, transitions de page | Oui, avec parcimonie |
| shadcn-svelte, Skeleton, Flowbite, 21st.dev, Lucide | Imposent le look générique | Non |
| Figma MCP | Utile seulement avec un·e designer humain·e | Plus tard, si besoin |

Références visuelles : guides de style du Chaos Communication Congress (38C3, 39C3),
Game UI Database (cartes et menus de jeux : Citizen Sleeper, Signalis, Exapunks, Hacknet),
SANS Holiday Hack Challenge (monde explorable), PlaidCTF (un univers par édition), 404CTF.
Polices libres hors clichés : Velvetyne, Collletttivo, choix peu courants de Google Fonts,
Departure Mono, Commit Mono, Monaspace.

## 6. Processus retenu

1. **Fondations** : brief (public, tâches, états), inventaire du contenu réel et de tous les
   états de chaque page, liste des fonctions à conserver (aucun lien, champ ou action ne doit
   disparaître), contrôles automatiques branchés (détecteurs de slop, axe, Lighthouse,
   matrice de captures pages × états × 1440 / 768 / 375 px × packs).
2. **Direction artistique** : planche de références, puis 3 directions contrastées, chacune
   avec son plan de jetons et une page d'ancrage rendue (le plan des défis). Test de
   silhouette. **Choix humain.**
3. **Système** : jetons primitifs → sémantiques → composants en CSS natif ; format de thème
   des packs étendu (polices, textures, jetons supplémentaires) ; primitives Bits UI ; règles
   de mouvement ; jeu d'icônes dessiné.
4. **Pages**, une à la fois en commençant par la page d'ancrage : construction → contrôles
   automatiques → juge (trois appels, grille de la section 4) → corrections, 6 cycles au plus,
   meilleure version gardée par comparaison par paires.
5. **Validation** : revue humaine, tests de bout en bout mis à jour, budget d'accessibilité et
   de performance, puis test réel pendant les répétitions de l'événement.
