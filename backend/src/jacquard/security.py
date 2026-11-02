"""Primitives de sécurité : mots de passe, jetons, condensats de flags."""

import hashlib
import hmac
import secrets
import threading

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# Paramètres recommandés par l'OWASP pour Argon2id (19 Mio, 2 passes, 1 fil) : robustes et
# assez légers pour encaisser une vague d'inscriptions. Les anciens condensats restent
# vérifiables (leurs paramètres sont inscrits dedans).
_hasher = PasswordHasher(time_cost=2, memory_cost=19 * 1024, parallelism=1)
# Au plus 4 hachages simultanés par processus : le pic de mémoire et de processeur reste
# borné même si 150 personnes s'inscrivent dans la même seconde.
_hashing = threading.BoundedSemaphore(4)

# Haché factice pour que la vérification d'un utilisateur inconnu prenne le même temps.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    with _hashing:
        return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        with _hashing:
            valid = _hasher.verify(password_hash or _DUMMY_HASH, password)
        return valid and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_invite_code() -> str:
    # Sans caractères ambigus (0/O, 1/I/l) pour pouvoir le dicter.
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(10))


def normalize_flag(value: str, case_sensitive: bool) -> str:
    value = value.strip()
    return value if case_sensitive else value.casefold()


def flag_digest(secret: str, value: str, case_sensitive: bool) -> str:
    """HMAC du flag : une fuite de la base ne suffit pas à retrouver les flags."""
    normalized = normalize_flag(value, case_sensitive)
    return hmac.new(secret.encode(), normalized.encode(), hashlib.sha256).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
