#!/usr/bin/env bash
# Run parse-treatments for a single language only.
# Usage: run_parse_treatments_single_lang.sh <LANG> [TEST_NAME]
#   LANG     - language folder name (e.g. de, latin-v3, en)
#   TEST_NAME - optional; one of test_small, test_small_no_brazil (default: test_small)
# Example: ./run_parse_treatments_single_lang.sh de
# Example: ./run_parse_treatments_single_lang.sh latin-v3 test_small_no_brazil
set -euo pipefail

LANG="${1:?Usage: $0 <LANG> [TEST_NAME]}"
TEST_NAME="${2:-test_small}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SAMPLES_DIR="${SAMPLES_DIR:-$REPO_ROOT/random_samples_test_lang}"

cd "$REPO_ROOT"

test_dir="$SAMPLES_DIR/$TEST_NAME"
lang_dir="$test_dir/$LANG"
if [[ ! -d "$lang_dir" ]]; then
  echo "Error: language dir not found: $lang_dir" >&2
  echo "Available under $test_dir: $(ls -1 "$test_dir" 2>/dev/null | tr '\n' ' ' || echo 'none')" >&2
  exit 1
fi

if command -v parse-treatments &>/dev/null; then
  PARSE_CMD="parse-treatments"
else
  PARSE_CMD="uv run parse-treatments"
fi

result_dir="$SAMPLES_DIR/${TEST_NAME}_result"
out_lang_dir="$result_dir/$LANG"
mkdir -p "$out_lang_dir"
html_file="$out_lang_dir/$LANG.html"

echo "Parsing: $TEST_NAME/$LANG -> ${TEST_NAME}_result/$LANG"
$PARSE_CMD \
  --treatment-dir "$lang_dir" \
  --html-file "$html_file" \
  --json-dir "$out_lang_dir"
echo "Done."
