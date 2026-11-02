# cyber-epita

Plateforme CTF réutilisable de l'association de cybersécurité d'EPITA Lyon (en cours de création).

La plateforme est un moteur générique : chaque événement est décrit par un **pack** (configuration, défis, scénario, thème) stocké dans un repo privé séparé. Aucun contenu d'événement n'est versionné ici.

## Statut

Phase de conception. Voir [docs/conception-plateforme.md](docs/conception-plateforme.md).

## Organisation

| Repo | Visibilité | Rôle |
|---|---|---|
| `cyber-epita` | Public | Moteur de la plateforme, outils, documentation |
| Un repo par événement | Privé jusqu'à la fin de l'événement | Défis, flags, solutions, scénario, thème |
