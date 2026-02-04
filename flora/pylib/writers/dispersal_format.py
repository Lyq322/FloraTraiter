"""
Format seed dispersal traits as 1/0 in output.
- 1 = presence of trait
- 0 = only when explicit absence (e.g. "wingless", "without pappus")
- Omit key when unknown (do not use 0 for unknown).
Ensures all 9 dispersal trait names are included when any dispersal is present.
"""

from flora.pylib.const import DISPERSAL_TRAIT_NAMES


def _collect_and_remove_dispersal_keys(d: dict) -> tuple[set, set]:
    """Find *DispersalTraits keys; return (present_traits, absent_traits).
    Values in DISPERSAL_TRAIT_NAMES = present; values ending in '_absent' = absent (base name).
    """
    present = set()
    absent = set()
    keys_to_remove = []
    for key, value in list(d.items()):
        key_lower = key.lower()
        if "dispersaltraits" in key_lower or "dispersal_traits" in key_lower:
            if value is not None:
                v = str(value).strip()
                if v in DISPERSAL_TRAIT_NAMES:
                    present.add(v)
                elif v.endswith("_absent"):
                    base = v[:-7]  # strip '_absent'
                    if base in DISPERSAL_TRAIT_NAMES:
                        absent.add(base)
            keys_to_remove.append(key)
    for k in keys_to_remove:
        d.pop(k, None)
    return present, absent


def format_dispersal_in_dynamic_properties(dyn: dict) -> dict:
    """Mutate dyn: remove *DispersalTraits keys, add binary keys (1 present, 0 explicit absence)."""
    if not isinstance(dyn, dict):
        return dyn
    present, absent = _collect_and_remove_dispersal_keys(dyn)
    for name in DISPERSAL_TRAIT_NAMES:
        if name in present:
            dyn[name] = 1
        elif name in absent:
            dyn[name] = 0
    return dyn


def format_dispersal_in_flat_dict(flat: dict) -> dict:
    """Same as format_dispersal_in_dynamic_properties but for flat dicts
    (e.g. CSV row with keys like dynamicProperties_acheneDispersalTraits).
    """
    if not isinstance(flat, dict):
        return flat
    present, absent = _collect_and_remove_dispersal_keys(flat)
    for name in DISPERSAL_TRAIT_NAMES:
        if name in present:
            flat[name] = 1
        elif name in absent:
            flat[name] = 0
    return flat
