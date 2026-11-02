"""Configuration de l'instance, lue depuis les variables d'environnement `JACQUARD_*`.

Tout ce qui est propre à un événement vient du pack ; ici on ne trouve que ce qui est
propre au déploiement (base de données, secrets, chemins).
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JACQUARD_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres@localhost:5432/jacquard"
    secret_key: SecretStr = Field(min_length=32)
    data_dir: Path = Path("./data")
    # Pool de connexions par processus serveur. Avec 2 workers : jusqu'à 2 × (20 + 10)
    # connexions, sous la limite par défaut de PostgreSQL (100).
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_timeout: int = 10

    cookie_secure: bool = True
    session_ttl_hours: int = 72

    # Code exigé à l'inscription quand le pack déclare `registration: invite_code`.
    registration_code: SecretStr | None = None

    # Diffusion temps réel (écoute PostgreSQL au démarrage).
    realtime: bool = True

    # Limites de tentatives de connexion (fenêtre glissante).
    login_max_failures: int = 10
    login_window_seconds: int = 900

    @field_validator("registration_code", mode="before")
    @classmethod
    def _empty_is_none(cls, value: object) -> object:
        # Docker Compose transmet une variable vide plutôt que de l'omettre.
        return None if value == "" else value

    @property
    def files_dir(self) -> Path:
        return self.data_dir / "files"


@lru_cache
def get_settings() -> Settings:
    return Settings()
