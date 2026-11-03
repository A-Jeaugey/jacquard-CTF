# Inventaire des pages, contenus et états

Ce qui doit exister après la refonte. Aucune fonction ne disparaît : chaque lien, champ,
action et état listé ici est vérifié à la fin (tests de bout en bout et revue manuelle).

## États globaux (toutes pages)

- **Phase de l'événement** : pas commencé (compte à rebours « Début dans »), en cours
  (« Fin dans »), classement gelé (30 min avant la fin), terminé.
- **Visiteur** : non connecté, connecté sans équipe, connecté avec équipe, admin.
- **Temps réel** : notifications éphémères (résolution par un coéquipier, déblocage d'un
  défi ou d'un chapitre, premier sang, annonce), déblocages groupés au-delà de 2, compteur
  de messages non lus, reconnexion automatique du flux.
- **Erreurs** : API injoignable, session expirée, limite de soumissions atteinte (429),
  page inconnue (404).

## Pages

| Page | Route | Contenu | États et actions |
|---|---|---|---|
| Accueil | `/` | Nom, accroche, dates, prologue (chapitre public), annonces | Boutons s'inscrire et se connecter (non connecté) ; accès aux défis (connecté) ; inscriptions fermées ; aucune annonce |
| Inscription | `/register` | Pseudo, mot de passe, e-mail facultatif, code d'inscription (si exigé) | Erreurs par champ (pseudo pris, mot de passe trop court, code faux) ; inscriptions fermées |
| Connexion | `/login` | Pseudo, mot de passe | Identifiants incorrects ; trop de tentatives |
| Équipe | `/team` | Sans équipe : créer (nom) ou rejoindre (code d'invitation). Avec équipe : nom, score, rang, défis résolus, code d'invitation, **fils de soie** (inventaire : nom, rang, motif binaire), membres, historique des résolutions | Équipe pleine ; code invalide ; quitter l'équipe ; inventaire vide |
| Défis (le plan) | `/challenges` | Carte de Lyon (8 quartiers, progression, filtre), progression par quartier, liste des défis | Défi résolu, disponible, verrouillé (`teaser` avec message, `hidden` invisible) ; filtre par quartier ; masquer les résolus ; vue carte ou grille ; pas commencé ; aucun défi |
| Défi ouvert | panneau | Nom, points, résolutions, difficulté, auteurs, énoncé (Markdown), connexion (`nc …`, URL), fichiers à télécharger, indices (gratuit, payant avec confirmation), champ du flag | Flag correct (célébration, objets gagnés, déblocages), incorrect, déjà résolu, limite atteinte, événement terminé, défi verrouillé |
| Classement | `/scoreboard` | Rang, équipe, défis, score ; équipe courante mise en avant | Gelé (heure du gel) ; aucune équipe ; égalités |
| Messages (journal) | `/story` | Chapitres débloqués (Markdown), nombre de chapitres encore verrouillés | Nouveau chapitre ; aucun chapitre |
| Grand écran | `/ecran/<id>` | Carte de la progression globale, top 10, fil « en direct » (premiers sangs, annonces), compte à rebours, nombre d'équipes | Gelé ; pas commencé ; terminé ; plein écran sans navigation, lisible à 5 m |
| Administration | `/admin` | Onglets : soumissions (filtrables), équipes (masquer / afficher), annonces (publier), statistiques (par défi, signaux de triche) | Chargement, vide, erreur ; actualisation périodique |
| Page inconnue | `*` | Message et retour | — |

## Contraintes de contenu

- Tous les libellés passent par `t()` (le pack peut les surcharger) : la refonte garde ce
  mécanisme même si la direction artistique est codée en dur.
- Le contenu de l'événement (histoire, énoncés, noms de défis, défis secrets) vient du pack
  privé et ne doit jamais apparaître dans le code public.
- Énoncés et chapitres sont du Markdown nettoyé côté serveur : prévoir titres, listes, code,
  liens, images, tableaux.
- Noms longs : équipes jusqu'à 128 caractères (à afficher sans casser la mise en page), pseudos jusqu'à 32, défis jusqu'à 128.
