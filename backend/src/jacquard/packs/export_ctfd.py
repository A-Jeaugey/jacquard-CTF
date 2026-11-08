"""Export de secours vers CTFd, au format de son outil ctfcli.

Chaque défi devient `<catégorie>/<id>/challenge.yml` (+ ses fichiers), installable avec
`ctf challenge install`. Ce que CTFd ne sait pas faire est signalé dans le rapport.
"""

import shutil
from pathlib import Path
from typing import Any

import yaml

from jacquard.packs.loader import LoadedChallenge, Pack
from jacquard.packs.schema import AllRule, DynamicScoring, GrantItem, Notify, Rule, SolvedRule


def _requirements(rule: Rule | None, names: dict[str, str]) -> list[str] | None:
    """Prérequis CTFd (« défis à résoudre avant »), si la règle se résume à cela."""
    if rule is None:
        return []
    if isinstance(rule, SolvedRule):
        return [names[rule.solved]]
    if isinstance(rule, AllRule) and all(isinstance(r, SolvedRule) for r in rule.all):
        return [names[r.solved] for r in rule.all]  # type: ignore[union-attr]
    return None


def _challenge(
    loaded: LoadedChallenge, pack: Pack, names: dict[str, str], issues: list[str]
) -> dict[str, Any]:
    config = loaded.config
    scoring = config.scoring or pack.event.scoring.default
    category = next(c.name for c in pack.event.categories if c.id == config.category)
    data: dict[str, Any] = {
        "name": config.name,
        "author": ", ".join(config.authors) or "orga",
        "category": category,
        "description": loaded.description_md.replace(
            "{challenge_host}", pack.event.challenge_host or ""
        ),
        "type": "dynamic" if isinstance(scoring, DynamicScoring) else "standard",
        "state": "visible",
        "version": "0.1",
    }
    if isinstance(scoring, DynamicScoring):
        data["value"] = scoring.initial
        data["extra"] = {
            "initial": scoring.initial,
            "decay": scoring.decay,
            "minimum": scoring.minimum,
        }
    else:
        data["value"] = scoring.value
    data["flags"] = [
        {
            "type": flag.type,
            "content": flag.value if flag.type == "static" else flag.pattern,
            "data": "" if flag.case_sensitive else "case_insensitive",
        }
        for flag in config.flags
    ]
    if config.tags:
        data["tags"] = list(config.tags)
    if config.connection:
        data["connection_info"] = config.connection.replace(
            "{challenge_host}", pack.event.challenge_host or ""
        )
    if loaded.files:
        data["files"] = [f"files/{f.name}" for f in loaded.files]
    if config.hints:
        data["hints"] = [
            {
                "content": h.text.replace("{challenge_host}", pack.event.challenge_host or ""),
                "cost": h.cost,
            }
            for h in config.hints
        ]
        if any(h.available is not None for h in config.hints):
            issues.append(
                f"{config.id} : indices à disponibilité différée, "
                "disponibles tout de suite dans CTFd"
            )
    requirements = _requirements(config.unlock, names)
    if requirements is None:
        issues.append(
            f"{config.id} : règle de déblocage non transposable (objet, score, horaire...), "
            "défi masqué dans CTFd : à rendre visible à la main au bon moment"
        )
        data["state"] = "hidden"
    elif requirements:
        data["requirements"] = requirements
    for action in config.on_solve:
        if isinstance(action, GrantItem):
            issues.append(f"{config.id} : l'objet « {action.grant_item} » n'existe pas dans CTFd")
        elif isinstance(action, Notify):
            issues.append(f"{config.id} : le message de résolution n'est pas affiché par CTFd")
    return data


def export_ctfd(pack: Pack, out: Path) -> list[str]:
    """Écrit l'export dans `out` (créé s'il n'existe pas) et renvoie la liste des limites."""
    issues: list[str] = []
    names = {c.config.id: c.config.name for c in pack.challenges}
    out.mkdir(parents=True, exist_ok=True)
    for loaded in pack.challenges:
        target = out / loaded.config.category / loaded.config.id
        target.mkdir(parents=True, exist_ok=True)
        data = _challenge(loaded, pack, names, issues)
        (target / "challenge.yml").write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        for pack_file in loaded.files:
            (target / "files").mkdir(exist_ok=True)
            shutil.copyfile(pack_file.path, target / "files" / pack_file.name)
    if pack.story:
        issues.append(
            f"histoire : {len(pack.story)} chapitre(s) sans équivalent dans CTFd "
            "(à publier en annonces)"
        )
    if pack.event.scoring.first_blood:
        issues.append("bonus de premier sang : non pris en charge par CTFd de base")
    if pack.theme is not None:
        issues.append("thème, carte interactive et grand écran : propres à Jacquard")
    items = ""
    if pack.event.items:
        issues.append(
            "objets : CTFd n'a pas d'inventaire ; leurs descriptions (listées dans README.md) "
            "doivent être remises aux équipes autrement si un défi en dépend"
        )
        items = (
            "\n## Objets à remettre aux équipes\n\n"
            + "\n".join(
                f"- **{item.name}** ({item.id}) : {item.description or ''}"
                for item in pack.event.items
            )
            + "\n"
        )
    report = "\n".join(f"- {issue}" for issue in issues) or "- aucune"
    (out / "README.md").write_text(
        f"# Export CTFd de « {pack.event.name} »\n\n"
        "Plan de secours : installer chaque défi avec ctfcli depuis ce dossier.\n\n"
        "```bash\npip install ctfcli\n"
        "ctf init            # URL et jeton d'admin de l'instance CTFd\n"
        'for c in */*/challenge.yml; do ctf challenge install "$(dirname "$c")"; done\n```\n\n'
        f"## Limites de l'export\n\n{report}\n{items}",
        encoding="utf-8",
    )
    return issues
