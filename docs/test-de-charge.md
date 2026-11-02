# Test de charge

Objectif : vérifier que la plateforme tient un CTF d'environ 150 joueurs, y compris le
moment le plus dur, quand tout le monde s'inscrit en même temps à l'ouverture.

## Méthode

`scripts/load_test.py` simule des joueurs qui :

1. s'inscrivent **tous en même temps**, puis créent ou rejoignent une équipe (4 par équipe) ;
2. gardent leur flux temps réel ouvert pendant toute la partie ;
3. enchaînent au hasard, toutes les 3 à 12 secondes : liste des défis, détail d'un défi,
   classement, soumission d'un flag (bon dans 30 % des cas).

Configuration testée : 2 workers uvicorn (comme l'image Docker), PostgreSQL 16, pack de
démonstration lancé en mode répétition (`--start-now`), 4 cœurs, client et serveur sur la
même machine.

```bash
cd backend
uv run jacquard pack sync ../examples/demo-pack --start-now
uv run uvicorn jacquard.main:app --port 8000 --workers 2
uv run python ../scripts/load_test.py --joueurs 150 --duree 120
```

## Résultat final (150 joueurs, 120 s de jeu)

2912 requêtes en 132 s (22.1 req/s), 12996 événements temps réel reçus

```
route                            n   médiane      p95      p99      max  (ms)
GET /api/challenges           1245        16       30       38       67
GET /api/challenges/{id}       367        17       29       39       53
GET /api/health                150       890     1588     1667     1676
GET /api/scoreboard            470        11       18       24       29
POST /api/auth/register        150      1426     1748     1877     1966
POST /api/teams                 38       535      747      764      764
POST /api/teams/join           112       626      855      897      911
POST submit                    380        19       49       68       98

Erreurs : {'live déconnecté': 3}
```

- **Aucune erreur serveur.** Les 3 flux « déconnectés » correspondent à l'arrêt du script.
- En jeu, toutes les routes répondent en moins de 50 ms au 95ᵉ centile.
- Les 150 inscriptions simultanées aboutissent en 1,4 s de médiane : le hachage des mots
  de passe est volontairement lent et limité à 4 en parallèle par processus.

## Problèmes trouvés et corrigés

Le premier passage échouait massivement : la plupart des inscriptions expiraient au bout de
30 s, et tout le reste en découlait.

| Problème | Cause | Correction |
|---|---|---|
| Pics de mémoire à l'inscription | Argon2 réglé à 64 Mio par hachage, jusqu'à 40 en parallèle (2,5 Go) | Paramètres OWASP (19 Mio, 2 passes) et 4 hachages simultanés au plus par processus |
| Connexions à la base gardées pendant le hachage | Le hachage avait lieu en pleine transaction | Connexion rendue au pool avant de hacher ou de vérifier un mot de passe |
| Blocage au-delà de 40 requêtes simultanées | Fils et connexions s'attendaient mutuellement : la transaction n'était validée qu'après la sérialisation de la réponse, qui demande un fil libre (diagnostiqué avec py-spy) | Transaction validée dans le fil du gestionnaire (`api/routing.py`), dépendances qui rendent leur connexion, session asynchrone |
| Interblocage PostgreSQL rare | Deux requêtes d'une même équipe insérant les mêmes déblocages dans un ordre différent | Insertion dans un ordre fixe |

Avant correction : 150 inscriptions simultanées donnaient 51 erreurs et 21 s d'attente.
Après : 150 sur 150 en 1,4 s de médiane.

## Limites

- Test sur une seule machine : pas de latence réseau (wifi de l'école), pas de TLS ni de
  Caddy devant l'API. Prévoir une répétition générale sur l'infrastructure réelle.
- Le pack de démonstration est petit ; Traboules a plus de défis, mais le coût par requête
  dépend surtout du nombre de résolutions, qui reste modeste sur une soirée.
- Les services des défis (sites vulnérables, serveurs nc) ne sont pas inclus : ils tournent
  sur une autre machine et ont été testés séparément (sessions simultanées).
