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
# Mapping: keyword -> core_fruit_type and trait columns (wing, fleshy_reward, etc.)
_MAPPING_CSV = Path(__file__).resolve().parent.parent.parent.parent / "keyword_to_dispersal_traits_mapping.csv"

_core_fruit_type_to_traits: dict[str, list[str]] | None = None


def _core_fruit_type_to_dispersal_traits() -> dict[str, list[str]]:
    """Load mapping CSV and return core_fruit_type -> list of dispersal trait names (columns with value 1)."""
    global _core_fruit_type_to_traits
    if _core_fruit_type_to_traits is not None:
        return _core_fruit_type_to_traits
    out = {}
    if not _MAPPING_CSV.exists():
        _core_fruit_type_to_traits = out
        return out
    with _MAPPING_CSV.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        trait_cols = [
            c for c in (reader.fieldnames or [])
            if c not in ("keyword_term", "core_fruit_type", "description", "notes")
        ]
        col_to_trait = {
            c: "buoyant_structure" if c == "bouyant_structure" else c
            for c in trait_cols
        }
        for row in reader:
            core = (row.get("core_fruit_type") or "").strip().lower()
            if not core:
                continue
            traits = []
            for col in trait_cols:
                if (row.get(col) or "").strip() == "1":
                    name = col_to_trait.get(col, col)
                    if name in DISPERSAL_TRAIT_NAMES and name not in traits:
                        traits.append(name)
            if traits and core not in out:
                out[core] = traits
            elif traits:
                for t in traits:
                    if t not in out[core]:
                        out[core].append(t)
    _core_fruit_type_to_traits = out
    return out


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
    """Extract part from key like 'acheneDispersalTraits' or 'berryDispersalTraits_pepo' -> 'achene'/'berry'. Returns None if not a dispersal key."""
    if not key:
        return None
    key_lower = key.lower()
    i = key_lower.rfind("dispersaltraits")
    if i == -1:
        return None
    # Part is everything before "dispersaltraits", strip trailing underscores (e.g. berryDispersalTraits_pepo -> berry)
    part = key_lower[:i].rstrip("_")
    return part if part else None


def _sanitized_keyword_from_dispersal_key(key: str) -> str | None:
    """Extract sanitized keyword suffix from key like 'berryDispersalTraits_pepo' -> 'pepo'. Returns None if no suffix."""
    if not key:
        return None
    key_lower = key.lower()
    i = key_lower.rfind("dispersaltraits")
    if i == -1:
        return None
    suffix = key_lower[i + len("dispersaltraits"):].lstrip("_")
    return suffix if suffix else None


def _collect_dispersal_by_allowed_parts(d: dict, allowed_parts: set) -> tuple[set, set, list, list]:
    """From *DispersalTraits keys whose part is in allowed_parts, collect present/absent/keywords. Return (present, absent, keys_to_remove, keywords_found).
    Only dispersal keywords linked to fruit/seed or a fruit type are included in keywords_found; fruit_type_keyword_* are always included."""
    present = set()
    absent = set()
    keys_to_remove = []
    keywords_found = []
    # Build set of sanitized dispersal keywords that are linked to an allowed part (fruit/seed/fruit type)
    allowed_dispersal_sanitized = set()
    for key in d:
        part = _part_from_dispersal_key(key)
        if part is None:
            continue
        if part not in allowed_parts:
            continue
        sanitized = _sanitized_keyword_from_dispersal_key(key)
        if sanitized is not None:
            allowed_dispersal_sanitized.add(sanitized)
    for key, value in list(d.items()):
        # Collect dispersal keywords only when linked to allowed part; fruit type keywords always
        if key.startswith("dispersal_keyword_"):
            keys_to_remove.append(key)
            sanitized = key[len("dispersal_keyword_"):]
            if sanitized in allowed_dispersal_sanitized and value is not None and str(value).strip():
                keywords_found.append(str(value).strip())
            continue
        if key.startswith("fruit_type_keyword_"):
            keys_to_remove.append(key)
            if value is not None and str(value).strip():
                keywords_found.append(str(value).strip())
            continue
        part = _part_from_dispersal_key(key)
        if part is None:
            continue
        keys_to_remove.append(key)
        if part not in allowed_parts:
            continue
        if value is not None:
            v = str(value).strip()
            for trait in v.split("|"):
                trait = trait.strip()
                if trait in DISPERSAL_TRAIT_NAMES:
                    present.add(trait)
                elif trait.endswith("_absent"):
                    base = trait[:-7]
                    if base in DISPERSAL_TRAIT_NAMES:
                        absent.add(base)
    return present, absent, keys_to_remove, keywords_found


def build_dispersal_block(dyn: dict) -> dict:
    """
    Build a separate JSON object for dispersal: 0 = explicit absence, 1 = explicit presence,
    no key = unknown. Only includes dispersal linked to fruit/seed or fruit-type parts.
    Also includes fruitType if present in dyn.
    Returns a dict with:
      - keywords_found: list of original matched keywords
      - traits: dict with fruitType (if any) and 0/1 for each dispersal trait
    """
    if not isinstance(dyn, dict):
        return {"keywords_found": [], "traits": {}}
    allowed = _allowed_dispersal_parts()
    present, absent, _, keywords_found = _collect_dispersal_by_allowed_parts(dyn, allowed)
    # Add dispersal traits implied by fruit type (e.g. berry -> fleshy_reward) so we don't lose them when FruitType overwrites the token before DispersalTraits runs
    fruit_type_value = None
    fruit_type_lower = None
    for k, v in dyn.items():
        if k == "fruitType" and v is not None:
            fruit_type_value = v if isinstance(v, str) else str(v).strip()
            fruit_type_lower = fruit_type_value.lower()
            break
    if fruit_type_lower:
        type_to_traits = _core_fruit_type_to_dispersal_traits()
        for trait_name in type_to_traits.get(fruit_type_lower, ()):
            present.add(trait_name)
    traits = {}
    for name in DISPERSAL_TRAIT_NAMES:
        if name in present:
            traits[name] = 1
        elif name in absent:
            traits[name] = 0
    if fruit_type_value is not None:
        traits["fruitType"] = fruit_type_value
    return {
        "keywords_found": sorted(set(keywords_found)),
        "traits": traits,
    }


def format_dispersal_in_dynamic_properties(dyn: dict) -> dict:
    """
    Mutate dyn: remove all *DispersalTraits, dispersal_keyword_*, and fruit_type_keyword_* keys;
    add binary 1/0 only for dispersal linked to allowed parts (fruit/seed/fruit-type). Returns dyn.
    """
    if not isinstance(dyn, dict):
        return dyn
    allowed = _allowed_dispersal_parts()
    present, absent, keys_to_remove, _ = _collect_dispersal_by_allowed_parts(dyn, allowed)
    fruit_type_lower = None
    for k, v in dyn.items():
        if k == "fruitType" and v is not None:
            fruit_type_lower = (v if isinstance(v, str) else str(v)).strip().lower()
            break
    if fruit_type_lower:
        type_to_traits = _core_fruit_type_to_dispersal_traits()
        for trait_name in type_to_traits.get(fruit_type_lower, ()):
            present.add(trait_name)
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
        if key.startswith("dispersal_keyword_"):
            keys_to_remove.append(key)
            continue
        if _part_from_dispersal_key(key) is None:
            continue
        if value is not None:
            v = str(value).strip()
            for trait in v.split("|"):
                trait = trait.strip()
                if trait in DISPERSAL_TRAIT_NAMES:
                    present.add(trait)
                elif trait.endswith("_absent"):
                    base = trait[:-7]
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
    present, absent, keys_to_remove, _ = _collect_dispersal_by_allowed_parts(flat, allowed)
    fruit_type_lower = None
    for k, v in flat.items():
        if k == "fruitType" and v is not None:
            fruit_type_lower = (v if isinstance(v, str) else str(v)).strip().lower()
            break
    if fruit_type_lower:
        type_to_traits = _core_fruit_type_to_dispersal_traits()
        for trait_name in type_to_traits.get(fruit_type_lower, ()):
            present.add(trait_name)
    for k in keys_to_remove:
        flat.pop(k, None)
    for name in DISPERSAL_TRAIT_NAMES:
        if name in present:
            flat[name] = 1
        elif name in absent:
            flat[name] = 0
    return flat
