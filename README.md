# Jacquard

Plateforme CTF réutilisable de l'association de cybersécurité d'EPITA Lyon (en cours de création).

La plateforme est un moteur générique : chaque événement est décrit par un **pack** (configuration, défis, scénario, thème) stocké dans un repo privé séparé. Aucun contenu d'événement n'est versionné ici, à part le pack de démonstration.

- Conception : [docs/conception-plateforme.md](docs/conception-plateforme.md)
- Format des packs : [docs/format-pack.md](docs/format-pack.md) et [examples/demo-pack](examples/demo-pack)

## Organisation

| Repo | Visibilité | Rôle |
|---|---|---|
| `jacquard-CTF` (ce repo) | Public | Moteur de la plateforme, outils, documentation |
| Un repo par événement | Privé jusqu'à la fin de l'événement | Défis, flags, solutions, scénario, thème |

```
backend/     API FastAPI, CLI `jacquard`, migrations, tests (Python 3.12+)
frontend/    Interface Svelte 5 + Vite, tests de bout en bout Playwright
deploy/      Caddyfile et image du frontend
examples/    Pack de démonstration (flags publics, pour les tests uniquement)
scripts/     Utilitaires de développement
```

## Statut

| Étape | État |
|---|---|
| M0 Fondations | ✅ |
| M1 Cœur (comptes, équipes, défis, flags, score, classement, admin) | ✅ |
| M2 Mécaniques (règles de déblocage, inventaire, indices, histoire, temps réel) | ✅ |
| M3 Personnalisation (thèmes, layouts `image-map` et `list`, grand écran) | ✅ |
| M4 Robustesse (flags par équipe, anti-triche, export CTFd, test de charge) | À faire |

## Développement

Prérequis : Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 22, PostgreSQL 16.

```bash
createdb jacquard
cd backend
uv sync
export JACQUARD_SECRET_KEY=dev-secret-key-not-for-production-0123456789
export JACQUARD_COOKIE_SECURE=false
uv run jacquard db upgrade
uv run jacquard pack sync ../examples/demo-pack
uv run jacquard admin create orga
uv run uvicorn jacquard.main:app --reload
```

Dans un second terminal :

```bash
cd frontend
npm install
npm run dev
```

L'interface est sur http://localhost:5173 (les appels `/api` sont relayés vers le port 8000). La documentation interactive de l'API est sur http://localhost:8000/api/docs.

### Tests

```bash
createdb jacquard_test
cd backend && uv run pytest              # tests unitaires et API
uv run ruff check . && uv run mypy src   # lint et typage
cd ../frontend && npm run check          # typage Svelte
npx playwright test                      # bout en bout (base jacquard_e2e recréée)
```

## Déploiement

```bash
cp .env.example .env    # remplir les secrets
docker compose up -d --build
docker compose run --rm api jacquard pack sync /pack
docker compose run --rm api jacquard admin create <pseudo>
```

Le pack est monté en lecture seule depuis `JACQUARD_PACK_DIR`. Après une modification du pack, relancer `jacquard pack sync` : l'import est idempotent et ne supprime jamais de résolution.

## Licence

[MIT](LICENSE)

## Commandes utiles

```bash
jacquard pack validate <dossier>   # vérifie un pack sans rien modifier
jacquard pack sync <dossier>       # importe ou met à jour (--dry-run pour simuler)
jacquard pack sync <dossier> --start-now   # répétition : l'événement commence maintenant
jacquard pack export-ctfd <dossier> <sortie>   # plan de secours CTFd (format ctfcli)
jacquard admin create <pseudo>     # crée ou promeut un compte admin
jacquard db upgrade                # applique les migrations
```
