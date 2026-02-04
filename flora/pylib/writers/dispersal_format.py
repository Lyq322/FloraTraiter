"""
Format seed dispersal traits as 1/0 in output.
- 1 = presence of trait
- 0 = only when explicit absence (e.g. "wingless", "without pappus")
- Omit key when unknown (do not use 0 for unknown).
Only dispersal linked to fruit/seed or a fruit-type part (e.g. achene, berry) is recorded;
e.g. "winged stem" is not recorded.
"""

import csv
from pathlib import Path

from flora.pylib.const import DISPERSAL_TRAIT_NAMES

# Suffix of dynamicProperties keys for dispersal (e.g. acheneDispersalTraits)
DISPERSAL_KEY_SUFFIX = "DispersalTraits"
DISPERSAL_KEY_SUFFIX_LEN = len(DISPERSAL_KEY_SUFFIX)

# Fruit type terms path (replace column = canonical fruit type names)
_FRUIT_TYPE_TERMS_PATH = Path(__file__).resolve().parent.parent / "rules" / "terms" / "fruit_type_terms.csv"


def _allowed_dispersal_parts() -> set:
    """Parts that are valid for dispersal: fruit types + 'fruit' + 'seed'."""
    allowed = {"fruit", "seed"}
    if _FRUIT_TYPE_TERMS_PATH.exists():
        with _FRUIT_TYPE_TERMS_PATH.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                r = (row.get("replace") or "").strip().lower()
                if r:
                    allowed.add(r)
    return allowed


def _part_from_dispersal_key(key: str) -> str | None:
    """Extract part from key like 'acheneDispersalTraits' or 'dynamicProperties_acheneDispersalTraits' -> 'achene'. Returns None if not a dispersal key."""
    if not key:
        return None
    key_lower = key.lower()
    i = key_lower.rfind("dispersaltraits")
    if i == -1:
        return None
    # Part is the segment immediately before "dispersaltraits" (after last '_' if any)
    start = key_lower.rfind("_", 0, i) + 1
    part = key_lower[start:i]
    return part if part else None


def _collect_dispersal_by_allowed_parts(d: dict, allowed_parts: set) -> tuple[set, set, list]:
    """From *DispersalTraits keys whose part is in allowed_parts, collect present/absent. Return (present, absent, keys_to_remove)."""
    present = set()
    absent = set()
    keys_to_remove = []
    for key, value in list(d.items()):
        part = _part_from_dispersal_key(key)
        if part is None:
            continue
        keys_to_remove.append(key)
        if part not in allowed_parts:
            continue
        if value is not None:
            v = str(value).strip()
            if v in DISPERSAL_TRAIT_NAMES:
                present.add(v)
            elif v.endswith("_absent"):
                base = v[:-7]
                if base in DISPERSAL_TRAIT_NAMES:
                    absent.add(base)
    return present, absent, keys_to_remove


def build_dispersal_block(dyn: dict) -> dict:
    """
    Build a separate JSON object for dispersal: 0 = explicit absence, 1 = explicit presence,
    no key = unknown. Only includes dispersal linked to fruit/seed or fruit-type parts.
    Also includes fruitType if present in dyn.
    """
    if not isinstance(dyn, dict):
        return {}
    allowed = _allowed_dispersal_parts()
    present, absent, _ = _collect_dispersal_by_allowed_parts(dyn, allowed)
    block = {}
    for name in DISPERSAL_TRAIT_NAMES:
        if name in present:
            block[name] = 1
        elif name in absent:
            block[name] = 0
    # Include fruit type if available (key is fruitType from FruitType rule)
    for k, v in dyn.items():
        if k == "fruitType" and v is not None:
            block["fruitType"] = v
            break
    return block


def format_dispersal_in_dynamic_properties(dyn: dict) -> dict:
    """
    Mutate dyn: remove all *DispersalTraits keys; add binary 1/0 only for dispersal
    linked to allowed parts (fruit/seed/fruit-type). Returns dyn.
    """
    if not isinstance(dyn, dict):
        return dyn
    allowed = _allowed_dispersal_parts()
    present, absent, keys_to_remove = _collect_dispersal_by_allowed_parts(dyn, allowed)
    for k in keys_to_remove:
        dyn.pop(k, None)
    for name in DISPERSAL_TRAIT_NAMES:
        if name in present:
            dyn[name] = 1
        elif name in absent:
            dyn[name] = 0
    return dyn


def _collect_and_remove_dispersal_keys(d: dict) -> tuple[set, set]:
    """Legacy: find *DispersalTraits keys; return (present_traits, absent_traits). No part filter."""
    present = set()
    absent = set()
    keys_to_remove = []
    for key, value in list(d.items()):
        if _part_from_dispersal_key(key) is None:
            continue
        if value is not None:
            v = str(value).strip()
            if v in DISPERSAL_TRAIT_NAMES:
                present.add(v)
            elif v.endswith("_absent"):
                base = v[:-7]
                if base in DISPERSAL_TRAIT_NAMES:
                    absent.add(base)
        keys_to_remove.append(key)
    for k in keys_to_remove:
        d.pop(k, None)
    return present, absent


def format_dispersal_in_flat_dict(flat: dict) -> dict:
    """Same as format_dispersal_in_dynamic_properties but for flat dicts
    (e.g. CSV row with keys like dynamicProperties_acheneDispersalTraits).
    Uses allowed-parts filter so only fruit/seed dispersal is recorded.
    """
    if not isinstance(flat, dict):
        return flat
    allowed = _allowed_dispersal_parts()
    present, absent, keys_to_remove = _collect_dispersal_by_allowed_parts(flat, allowed)
    for k in keys_to_remove:
        flat.pop(k, None)
    for name in DISPERSAL_TRAIT_NAMES:
        if name in present:
            flat[name] = 1
        elif name in absent:
            flat[name] = 0
    return flat
