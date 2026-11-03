#!/usr/bin/env bash
# Tous les contrôles automatiques de design, dans l'ordre, pour une page rendue.
# Leur sortie est fournie telle quelle au juge (docs/refonte-ui/juge.md).
#
#   scripts/design-check.sh <url> <nom> [dossier de sortie]
#
# 1. slop-lint (notre détecteur, code Svelte et CSS)
# 2. avoid-ai-design (détecteur tiers, MIT, copié dans scripts/vendor)
# 3. Impeccable (détecteur tiers, version figée, sur la page rendue à 1280 et 390 px,
#    y compris la conformité à DESIGN.md quand il existe)
# 4. ui-audit (nos mesures : contrastes, débordements, cibles, focus, mouvement)
set -uo pipefail
cd "$(dirname "$0")/.."

URL="${1:?usage : scripts/design-check.sh <url> <nom> [sortie]}"
NAME="${2:?nom de la page}"
OUT="${3:-design-check}"
IMPECCABLE="impeccable@4.8.0"
mkdir -p "$OUT"
status=0

run() {
  local label="$1"; shift
  echo "## $label"
  "$@" > "$OUT/$NAME-$label.txt" 2>&1
  local code=$?
  cat "$OUT/$NAME-$label.txt"
  echo
  [ "$code" -ne 0 ] && status=1
}

run slop-lint node scripts/slop-lint.mjs src
run avoid-ai-design node scripts/vendor/avoid-ai-design/detect.mjs src
# Pas de télémétrie : réglage local, idempotent.
npx -y "$IMPECCABLE" telemetry off > /dev/null 2>&1
run impeccable-1280 npx -y "$IMPECCABLE" detect "$URL"
run impeccable-390 npx -y "$IMPECCABLE" detect --viewport 390x844 "$URL"
run ui-audit node scripts/ui-audit.mjs "$URL" --name "$NAME" --out "$OUT"

exit "$status"
