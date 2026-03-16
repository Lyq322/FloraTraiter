import csv
import json
from pathlib import Path

from traiter.pylib.darwin_core import DarwinCore

from flora.pylib import const
from flora.pylib.treatments import Treatments
from flora.pylib.writers.dispersal_format import (
    build_dispersal_block,
    format_dispersal_in_dynamic_properties,
)

FRUIT_TYPE_KEY = "fruitType"


def write_json(treatments: Treatments, json_dir: Path) -> None:
    json_dir.mkdir(parents=True, exist_ok=True)
    dispersal_rows: list[dict] = []

    for treatment in treatments:
        dwc = DarwinCore()
        _ = [t.to_dwc(dwc) for t in treatment.traits]

        path = json_dir / f"{treatment.path.stem}.json"
        output = dwc.to_dict()
        dyn = output.get("dwc:dynamicProperties")
        if isinstance(dyn, dict):
            output["dispersal"] = build_dispersal_block(dyn)
            format_dispersal_in_dynamic_properties(dyn)
        else:
            output["dispersal"] = {"keywords_found": [], "traits": {}}
        output["text"] = treatment.text

        with path.open("w") as f:
            json.dump(output, f, indent=4)

        # One row for dispersal CSV: txt file name, binary traits, fruit type
        traits = output["dispersal"].get("traits") or {}
        row = {"txt_file": f"{treatment.path.stem}.txt"}
        for name in const.DISPERSAL_TRAIT_NAMES:
            v = traits.get(name)
            row[name] = (1 if v == 1 else 0) if v is not None and v != "" else ""
        row["fruit_type"] = traits.get(FRUIT_TYPE_KEY) or ""
        dispersal_rows.append(row)

    if dispersal_rows:
        _write_dispersal_csv(json_dir / "dispersal_traits.csv", dispersal_rows)


def _write_dispersal_csv(csv_path: Path, rows: list[dict]) -> None:
    fieldnames = ["txt_file"] + list(const.DISPERSAL_TRAIT_NAMES) + ["fruit_type"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
