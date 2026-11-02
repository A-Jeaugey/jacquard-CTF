#!/usr/bin/env bash
# Lance un backend jetable pour les tests de bout en bout : base vidée, pack de démo
# importé, compte admin créé. Utilisé par frontend/playwright.config.ts.
set -euo pipefail
cd "$(dirname "$0")/../backend"

export JACQUARD_DATABASE_URL="${JACQUARD_E2E_DATABASE_URL:-postgresql+psycopg://postgres@localhost:5432/jacquard_e2e}"
export JACQUARD_SECRET_KEY="e2e-secret-key-not-for-production-0123456789"
export JACQUARD_COOKIE_SECURE=false
export JACQUARD_DATA_DIR="$(mktemp -d)"

uv run python - <<'PY'
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
import os

url = make_url(os.environ["JACQUARD_DATABASE_URL"])
admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
with admin.connect() as connection:
    connection.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
    connection.execute(text(f'CREATE DATABASE "{url.database}"'))
PY
uv run jacquard db upgrade
uv run jacquard pack sync ../examples/demo-pack
JACQUARD_ADMIN_PASSWORD="admin-password-123" uv run jacquard admin create orga
exec uv run uvicorn jacquard.main:app --port "${E2E_API_PORT:-8001}"
