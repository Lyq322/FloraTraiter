"""
Format seed dispersal traits as 1/0 in output.
- 1 = presence of trait
- 0 = only when explicit absence (e.g. "wingless", "without pappus")
- Omit key when unknown (do not use 0 for unknown).
Ensures all 9 dispersal trait names are included when any dispersal is present.
"""

from flora.pylib.const import DISPERSAL_TRAIT_NAMES


def _collect_and_remove_dispersal_keys(d: dict) -> set:
    """Find *DispersalStructure keys; return set of present trait names."""
    present = set()
    keys_to_remove = []
    for key, value in list(d.items()):
        key_lower = key.lower()
        if "dispersalstructure" in key_lower or "dispersal_structure" in key_lower:
            if value is not None and str(value).strip() in DISPERSAL_TRAIT_NAMES:
                present.add(str(value).strip())
            keys_to_remove.append(key)
    for k in keys_to_remove:
        d.pop(k, None)
    return present


def format_dispersal_in_dynamic_properties(dyn: dict) -> dict:
    """Mutate dyn: remove *DispersalStructure keys, add binary keys (1 when present only)."""
    if not isinstance(dyn, dict):
        return dyn
    present = _collect_and_remove_dispersal_keys(dyn)
    for name in DISPERSAL_TRAIT_NAMES:
        if name in present:
            dyn[name] = 1
    return dyn


def format_dispersal_in_flat_dict(flat: dict) -> dict:
    """Same as format_dispersal_in_dynamic_properties but for flat dicts
    (e.g. CSV row with keys like dynamicProperties_acheneDispersalStructure).
    """
    if not isinstance(flat, dict):
        return flat
    present = _collect_and_remove_dispersal_keys(flat)
    for name in DISPERSAL_TRAIT_NAMES:
        if name in present:
            flat[name] = 1
    return flat
