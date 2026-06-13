#!/usr/bin/env bash
# Run parse-treatments starting at batch_NNNN under --treatment-dir.
#
# Usage:
#   ./scripts/run_parse_from_batch.sh 4    # -> --start-batch batch_0004
#
# Defaults: seed-dispersal-traits-scraper data next to this repo
# (flora_traiter, flora_traiter_output/json, traits.html & traits.csv under output).
# Override with env vars: TREATMENT_DIR, JSON_DIR, HTML_FILE, CSV_FILE, PARSE_TIMEOUT.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# Paths relative to FloraTraiter repo root (../seed-dispersal-traits-scraper/...).
_SCRAPER_DATA="$REPO_ROOT/../seed-dispersal-traits-scraper/data"
TREATMENT_DIR="${TREATMENT_DIR:-$_SCRAPER_DATA/flora_traiter}"
JSON_DIR="${JSON_DIR:-$_SCRAPER_DATA/flora_traiter_output/json}"
HTML_FILE="${HTML_FILE:-$_SCRAPER_DATA/flora_traiter_output/traits.html}"
CSV_FILE="${CSV_FILE:-$_SCRAPER_DATA/flora_traiter_output/traits.csv}"
PARSE_TIMEOUT="${PARSE_TIMEOUT:-120}"

N="${1:?Usage: $0 <BATCH_NUMBER>  (e.g. 4 -> batch_0004)}"

if ! [[ "$N" =~ ^[0-9]+$ ]]; then
  echo "Error: BATCH_NUMBER must be a non-negative integer, got: $N" >&2
  exit 1
fi

START_BATCH=$(printf 'batch_%04d' "$N")

cd "$REPO_ROOT"

if command -v parse-treatments &>/dev/null; then
  PARSE_CMD=(parse-treatments)
else
  PARSE_CMD=(uv run parse-treatments)
fi

LOG_DIR="${LOG_DIR:-$REPO_ROOT/logs}"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_FILE:-$LOG_DIR/parse_from_${START_BATCH}_$(date +%Y%m%d_%H%M%S).log}"

echo "Starting at --start-batch $START_BATCH under $TREATMENT_DIR"
echo "Parse timeout: ${PARSE_TIMEOUT}s per treatment (0=disabled)"
echo "Streaming output to: $LOG_FILE"
"${PARSE_CMD[@]}" \
  --treatment-dir "$TREATMENT_DIR" \
  --start-batch "$START_BATCH" \
  --json-dir "$JSON_DIR" \
  --html-file "$HTML_FILE" \
  --csv-file "$CSV_FILE" \
  --parse-timeout "$PARSE_TIMEOUT" \
  2>&1 | tee "$LOG_FILE"
echo "Done."
