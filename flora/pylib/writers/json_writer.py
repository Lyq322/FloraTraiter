import json
from pathlib import Path

from traiter.pylib.darwin_core import DarwinCore

from flora.pylib.treatments import Treatments
from flora.pylib.writers.dispersal_format import (
    build_dispersal_block,
    format_dispersal_in_dynamic_properties,
)


def write_json(treatments: Treatments, json_dir: Path) -> None:
    json_dir.mkdir(parents=True, exist_ok=True)

    for treatment in treatments:
        dwc = DarwinCore()
        _ = [t.to_dwc(dwc) for t in treatment.traits]

        path = json_dir / f"{treatment.path.stem}.json"
        with path.open("w") as f:
            output = dwc.to_dict()
            dyn = output.get("dwc:dynamicProperties")
            if isinstance(dyn, dict):
                output["dispersal"] = build_dispersal_block(dyn)
                format_dispersal_in_dynamic_properties(dyn)
            else:
                output["dispersal"] = {}
            output["text"] = treatment.text
            json.dump(output, f, indent=4)
