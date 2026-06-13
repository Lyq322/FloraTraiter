#!/usr/bin/env bash
# Run parse-treatments for exactly one batch_NNNN folder (not from that batch onward).
#
# Usage:
#   ./scripts/run_parse_single_batch.sh 16
#   LIMIT=3000 OFFSET=0 ./scripts/run_parse_single_batch.sh 4   # first chunk only
#   LIMIT=5000 OFFSET=5356 ./scripts/run_parse_single_batch.sh 4  # resume after OOM
#
# Defaults: seed-dispersal-traits-scraper data next to this repo.
# Override with env vars: TREATMENT_DIR, JSON_DIR, HTML_FILE, CSV_FILE, LOG_DIR,
# LIMIT, OFFSET, PARSE_TIMEOUT (seconds per treatment; 0 disables).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
_SCRAPER_DATA="$REPO_ROOT/../seed-dispersal-traits-scraper/data"
TREATMENT_ROOT="${TREATMENT_DIR:-$_SCRAPER_DATA/flora_traiter}"
JSON_ROOT="${JSON_DIR:-$_SCRAPER_DATA/flora_traiter_output/json}"
HTML_ROOT="${HTML_FILE:-$_SCRAPER_DATA/flora_traiter_output/traits.html}"
CSV_ROOT="${CSV_FILE:-$_SCRAPER_DATA/flora_traiter_output/traits.csv}"

N="${1:?Usage: $0 <BATCH_NUMBER>  (e.g. 16 -> batch_0016 only)}"

if ! [[ "$N" =~ ^[0-9]+$ ]]; then
  echo "Error: BATCH_NUMBER must be a non-negative integer, got: $N" >&2
  exit 1
fi

BATCH_NAME=$(printf 'batch_%04d' "$N")
BATCH_DIR="$TREATMENT_ROOT/$BATCH_NAME"

if [[ ! -d "$BATCH_DIR" ]]; then
  echo "Error: batch directory not found: $BATCH_DIR" >&2
  exit 1
fi

OUTPUT_DIR="$(dirname "$HTML_ROOT")"
JSON_DIR="$JSON_ROOT/$BATCH_NAME"
HTML_FILE="$OUTPUT_DIR/${BATCH_NAME}.html"
CSV_FILE="$OUTPUT_DIR/${BATCH_NAME}.csv"

cd "$REPO_ROOT"

if command -v parse-treatments &>/dev/null; then
  PARSE_CMD=(parse-treatments)
else
  PARSE_CMD=(uv run parse-treatments)
fi

LOG_DIR="${LOG_DIR:-$REPO_ROOT/logs}"
mkdir -p "$LOG_DIR" "$JSON_DIR" "$OUTPUT_DIR"

LIMIT="${LIMIT:-}"
OFFSET="${OFFSET:-0}"
PARSE_TIMEOUT="${PARSE_TIMEOUT:-120}"
CHUNK_SUFFIX=""
EXTRA_ARGS=(--parse-timeout "$PARSE_TIMEOUT")
if [[ -n "$LIMIT" ]]; then
  EXTRA_ARGS+=(--limit "$LIMIT" --offset "$OFFSET")
  CHUNK_SUFFIX="_off${OFFSET}_lim${LIMIT}"
fi

LOG_FILE="${LOG_FILE:-$LOG_DIR/parse_${BATCH_NAME}${CHUNK_SUFFIX}_$(date +%Y%m%d_%H%M%S).log}"

echo "Processing only $BATCH_NAME"
echo "  treatments: $BATCH_DIR"
if [[ -n "$LIMIT" ]]; then
  echo "  chunk:      offset=$OFFSET limit=$LIMIT"
fi
echo "  timeout:    ${PARSE_TIMEOUT}s per treatment (0=disabled)"
echo "  json:       $JSON_DIR"
echo "  html:       $HTML_FILE"
echo "  csv:        $CSV_FILE"
echo "  log:        $LOG_FILE"
"${PARSE_CMD[@]}" \
  --treatment-dir "$BATCH_DIR" \
  --json-dir "$JSON_DIR" \
  --html-file "$HTML_FILE" \
  --csv-file "$CSV_FILE" \
  "${EXTRA_ARGS[@]}" \
  2>&1 | tee "$LOG_FILE"
echo "Done."
