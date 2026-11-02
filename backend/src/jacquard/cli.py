"""Interface en ligne de commande : `jacquard --help`."""

from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from jacquard.clock import utcnow
from jacquard.config import get_settings
from jacquard.db import get_sessionmaker
from jacquard.models import User
from jacquard.packs.export_ctfd import export_ctfd
from jacquard.packs.loader import Pack, PackError, load_pack
from jacquard.packs.rehearsal import override_challenge_host, shift_schedule
from jacquard.packs.sync import sync_pack
from jacquard.security import hash_password

app = typer.Typer(help="Plateforme CTF Jacquard.", no_args_is_help=True)
db_app = typer.Typer(help="Base de données.", no_args_is_help=True)
pack_app = typer.Typer(help="Packs d'événement.", no_args_is_help=True)
admin_app = typer.Typer(help="Comptes d'administration.", no_args_is_help=True)
app.add_typer(db_app, name="db")
app.add_typer(pack_app, name="pack")
app.add_typer(admin_app, name="admin")

PackDir = Annotated[Path, typer.Argument(exists=True, file_okay=False, help="Dossier du pack")]


def _alembic_config() -> Config:
    migrations = Path(__file__).parent / "migrations"
    config = Config(str(migrations / "alembic.ini"))
    config.set_main_option("script_location", str(migrations))
    return config


@db_app.command("upgrade")
def db_upgrade() -> None:
    """Applique les migrations en attente."""
    command.upgrade(_alembic_config(), "head")


@db_app.command("revision", hidden=True)
def db_revision(message: str) -> None:
    """Génère une migration (développement)."""
    command.revision(_alembic_config(), message=message, autogenerate=True)


def _load_or_exit(path: Path) -> Pack:
    try:
        pack = load_pack(path)
    except PackError as exc:
        typer.secho(f"✗ {len(exc.errors)} erreur(s) :", fg="red", err=True)
        for issue in exc.errors:
            typer.echo(f"  - {issue}", err=True)
        raise typer.Exit(1) from exc
    for warning in pack.warnings:
        typer.secho(f"  ! {warning}", fg="yellow")
    return pack


@pack_app.command("validate")
def pack_validate(path: PackDir) -> None:
    """Vérifie un pack sans rien modifier."""
    pack = _load_or_exit(path)
    typer.secho(
        f"✓ Pack « {pack.event.name} » valide : {len(pack.challenges)} défi(s), "
        f"{len(pack.event.categories)} catégorie(s).",
        fg="green",
    )


@pack_app.command("sync")
def pack_sync(
    path: PackDir,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Affiche les changements sans les appliquer")
    ] = False,
    start_now: Annotated[
        bool,
        typer.Option("--start-now", help="Répétition : l'événement commence maintenant"),
    ] = False,
    start: Annotated[
        datetime | None,
        typer.Option(
            "--start",
            help="Répétition : date de début (heure du fuseau de l'événement)",
            formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"],
        ),
    ] = None,
    challenge_host: Annotated[
        str | None,
        typer.Option(
            "--challenge-host",
            help="Remplace challenge_host d'event.yml (ex. machine de répétition)",
        ),
    ] = None,
) -> None:
    """Importe ou met à jour un pack dans la base (idempotent)."""
    pack = _load_or_exit(path)
    if challenge_host is not None:
        try:
            pack = override_challenge_host(pack, challenge_host)
        except ValueError:
            typer.secho(f"Nom d'hôte invalide : {challenge_host!r}", fg="red", err=True)
            raise typer.Exit(1) from None
        typer.secho(f"Services de défis : {challenge_host} (event.yml inchangé)", fg="yellow")
    if start_now and start:
        typer.secho("--start-now et --start sont incompatibles.", fg="red", err=True)
        raise typer.Exit(1)
    if start_now or start:
        begin = utcnow() if start_now else start.replace(tzinfo=pack.event.tz)  # type: ignore[union-attr]
        pack = shift_schedule(pack, begin)
        schedule = pack.event.schedule
        typer.secho(
            f"Répétition : {schedule.start.astimezone(pack.event.tz):%d/%m %H:%M} → "
            f"{schedule.end.astimezone(pack.event.tz):%d/%m %H:%M} (fichiers du pack inchangés)",
            fg="yellow",
        )
    settings = get_settings()
    with get_sessionmaker()() as session:
        report = sync_pack(
            session,
            pack,
            secret=settings.secret_key.get_secret_value(),
            files_dir=settings.files_dir,
            now=utcnow(),
            dry_run=dry_run,
        )
    prefix = "[simulation] " if dry_run else ""
    typer.echo(f"{prefix}Événement : {'modifié' if report.event_changed else 'inchangé'}")
    for label, items in (
        ("Créés", report.created),
        ("Modifiés", report.updated),
        ("Désactivés", report.deactivated),
        ("Chapitres créés", report.story_created),
        ("Chapitres modifiés", report.story_updated),
        ("Chapitres désactivés", report.story_deactivated),
    ):
        if items:
            typer.echo(f"{prefix}{label} ({len(items)}) : {', '.join(items)}")
    typer.echo(f"{prefix}Inchangés : {len(report.unchanged)}")
    if not dry_run:
        typer.secho("✓ Synchronisation terminée.", fg="green")


@pack_app.command("export-ctfd")
def pack_export_ctfd(
    path: PackDir,
    out: Annotated[Path, typer.Argument(file_okay=False, help="Dossier de sortie")],
) -> None:
    """Exporte le pack au format ctfcli (plan de secours CTFd), avec ses limites."""
    pack = _load_or_exit(path)
    issues = export_ctfd(pack, out)
    typer.secho(f"✓ {len(pack.challenges)} défi(s) exportés dans {out}", fg="green")
    for issue in issues:
        typer.secho(f"  ! {issue}", fg="yellow")


@admin_app.command("create")
def admin_create(
    username: str,
    password: Annotated[
        str,
        typer.Option(
            prompt=True, hide_input=True, confirmation_prompt=True, envvar="JACQUARD_ADMIN_PASSWORD"
        ),
    ],
) -> None:
    """Crée un compte administrateur, ou promeut un compte existant."""
    if len(password) < 12:
        typer.secho(
            "Le mot de passe d'un admin doit faire au moins 12 caractères.", fg="red", err=True
        )
        raise typer.Exit(1)
    with get_sessionmaker()() as session:
        user = session.scalar(select(User).where(User.username_key == username.casefold()))
        if user is None:
            user = User(username=username, username_key=username.casefold(), password_hash="")
            session.add(user)
        user.password_hash = hash_password(password)
        user.role = "admin"
        user.team_id = None
        session.commit()
    typer.secho(f"✓ {username} est administrateur.", fg="green")


if __name__ == "__main__":
    app()
