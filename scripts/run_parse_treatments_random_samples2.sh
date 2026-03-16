#!/usr/bin/env bash
# Run parse-treatments on every folder inside random_samples_test_lang/.
# Creates result folders: random_samples_test_lang/<test>_result/<lang>/<lang>.html and JSON in <lang>/.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SAMPLES_DIR="$REPO_ROOT/random_samples_test_lang"

cd "$REPO_ROOT"

# Ensure parse-treatments is available (e.g. from uv run or PATH)
if command -v parse-treatments &>/dev/null; then
  PARSE_CMD="parse-treatments"
else
  PARSE_CMD="uv run parse-treatments"
fi

# Process in this order: test_small, test_small_no_brazil
ran_any=0
for test_name in test_small test_small_no_brazil; do
  test_dir="$SAMPLES_DIR/$test_name"
  if [[ ! -d "$test_dir" ]]; then
    echo "Skipping $test_name: $test_dir not found" >&2
    continue
  fi

  result_dir="$SAMPLES_DIR/${test_name}_result"
  mkdir -p "$result_dir"

  # Use nullglob so we get no words (not a literal path) when there are no subdirs
  shopt -s nullglob
  for lang_dir in "$test_dir"/*/; do
    shopt -u nullglob 2>/dev/null || true
    lang_dir="${lang_dir%/}"
    lang="$(basename "$lang_dir")"
    [[ -d "$lang_dir" ]] || continue

    out_lang_dir="$result_dir/$lang"
    mkdir -p "$out_lang_dir"
    html_file="$out_lang_dir/$lang.html"

    echo "Parsing: $test_name/$lang -> ${test_name}_result/$lang"
    $PARSE_CMD \
      --treatment-dir "$lang_dir" \
      --html-file "$html_file" \
      --json-dir "$out_lang_dir"
    ran_any=1
  done
  shopt -u nullglob 2>/dev/null || true
done

if [[ $ran_any -eq 0 ]]; then
  echo "Nothing run. Check that $SAMPLES_DIR contains test_small/<lang>/ and test_small_no_brazil/<lang>/." >&2
  exit 1
fi
echo "Done."
