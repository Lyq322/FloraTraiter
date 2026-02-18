import csv
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from spacy import Language, registry
from traiter.pylib import const as t_const
from traiter.pylib import term_util
from traiter.pylib.darwin_core import DarwinCore
from traiter.pylib.pattern_compiler import Compiler
from traiter.pylib.pipes import add

from flora.pylib.const import DISPERSAL_TRAIT_NAMES
from .linkable import Linkable


def _load_keyword_to_traits_mapping(path: Path) -> dict[str, list[str]]:
    """Load keyword_term -> list of trait names (columns with value '1')."""
    out = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        trait_cols = [
            c for c in (reader.fieldnames or [])
            if c not in ("keyword_term", "core_fruit_type", "description", "notes")
        ]
        # CSV has typo 'bouyant_structure' -> map to buoyant_structure
        col_to_trait = {
            c: "buoyant_structure" if c == "bouyant_structure" else c
            for c in trait_cols
        }
        for row in reader:
            kw = (row.get("keyword_term") or "").strip().lower()
            if not kw:
                continue
            traits = []
            for col in trait_cols:
                if (row.get(col) or "").strip() == "1":
                    trait_name = col_to_trait.get(col, col)
                    if trait_name in DISPERSAL_TRAIT_NAMES:
                        traits.append(trait_name)
            if traits:
                out[kw] = traits
    return out


@dataclass(eq=False)
class DispersalTraits(Linkable):
    """Extract seed/fruit dispersal traits (wing, pappus, hooks, etc.).
    Linked to seed/fruit part (seed, fruit, drupe, achene, etc.) via PartLinker.
    """

    # Class vars ----------
    terms_dir: ClassVar[Path] = Path(__file__).parent / "terms"
    dispersal_terms_dir: ClassVar[Path] = terms_dir / "dispersal_terms"
    dispersal_csv: ClassVar[Path] = dispersal_terms_dir / "dispersal_terms.csv"
    dispersal_negator_csv: ClassVar[Path] = dispersal_terms_dir / "dispersal_negator_terms.csv"
    dispersal_absence_csv: ClassVar[Path] = dispersal_terms_dir / "dispersal_absence_terms.csv"
    mapping_csv: ClassVar[Path] = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "keyword_to_dispersal_traits_mapping.csv"
    )
    all_csvs: ClassVar[list[Path]] = [
        dispersal_csv,
        dispersal_negator_csv,
        dispersal_absence_csv,
    ]
    type_csvs: ClassVar[list[Path]] = [dispersal_csv, dispersal_absence_csv]
    replace: ClassVar[dict[str, str]] = term_util.look_up_table(
        all_csvs, "replace"
    )
    type_: ClassVar[dict[str, str]] = term_util.look_up_table(
        type_csvs, "type"
    )
    _keyword_to_traits: ClassVar[dict[str, list[str]] | None] = None
    # ---------------------

    @classmethod
    def _get_keyword_to_traits(cls) -> dict[str, list[str]]:
        if cls._keyword_to_traits is None:
            cls._keyword_to_traits = _load_keyword_to_traits_mapping(cls.mapping_csv)
        return cls._keyword_to_traits

    dispersal_traits: str = None
    matched_keyword: str = None

    def _sanitize_keyword(self, keyword: str) -> str:
        return (keyword or "").replace(" ", "_").replace("-", "_").lower()

    def to_dwc(self, dwc) -> DarwinCore:
        # Use unique key per (part, keyword) so multiple matches for same part don't overwrite
        dyn_key = self.key
        if self.matched_keyword:
            dyn_key = f"{self.key}_{self._sanitize_keyword(self.matched_keyword)}"
        payload = {dyn_key: self.dispersal_traits}
        if self.matched_keyword:
            payload[f"dispersal_keyword_{self._sanitize_keyword(self.matched_keyword)}"] = (
                self.matched_keyword
            )
        return dwc.add_dyn(**payload)

    @property
    def key(self) -> str:
        return self.key_builder("dispersal", "traits")

    @classmethod
    def pipe(cls, nlp: Language):
        add.term_pipe(nlp, name="dispersal_terms", path=cls.all_csvs)
        add.trait_pipe(
            nlp,
            name="dispersal_patterns",
            compiler=cls.dispersal_patterns(),
            overwrite=["part", "part_term", "dispersal_traits", "dispersal_negator"],
        )
        add.cleanup_pipe(nlp, name="dispersal_cleanup")

    @classmethod
    def dispersal_patterns(cls):
        decoder = {
            "(": {"TEXT": {"IN": t_const.OPEN}},
            ")": {"TEXT": {"IN": t_const.CLOSE}},
            "negator": {"ENT_TYPE": "dispersal_negator"},
            "dispersal": {
                "ENT_TYPE": {"IN": ["dispersal_term", "dispersal_absence"]},
            },
        }
        return [
            Compiler(
                label="dispersal_traits",
                on_match="dispersal_traits_match",
                keep="dispersal_traits",
                decoder=decoder,
                patterns=[
                    "  negator? dispersal ",
                    "( negator? dispersal )",
                ],
            ),
        ]

    @classmethod
    def dispersal_traits_match(cls, ent):
        # Negator (no, without, lacking) + dispersal_term -> type_absent
        # Single dispersal_absence term (wingless, epappose) -> type already _absent
        negated = any(
            t._.term == "dispersal_negator" for t in ent
        )
        dispersal_tokens = [
            t for t in ent
            if t._.term in ("dispersal_term", "dispersal_absence")
        ]
        dispersal_type = None
        matched_keyword = None
        if dispersal_tokens:
            key = " ".join(t.lower_ for t in dispersal_tokens).strip()
            norm = cls.replace.get(key, key)
            # Prefer mapping CSV for trait(s); fall back to dispersal_terms type column
            mapping = cls._get_keyword_to_traits()
            if norm in mapping:
                traits_list = mapping[norm]
                dispersal_type = "|".join(traits_list)
                matched_keyword = key
            else:
                dispersal_type = cls.type_.get(key) or cls.type_.get(norm)
        if dispersal_type is not None and negated and not dispersal_type.endswith(
            "_absent"
        ):
            # For multiple traits, append _absent to each
            if "|" in dispersal_type:
                dispersal_type = "|".join(
                    t + "_absent" for t in dispersal_type.split("|")
                )
            else:
                dispersal_type = dispersal_type + "_absent"
        return cls.from_ent(
            ent,
            dispersal_traits=dispersal_type,
            matched_keyword=matched_keyword,
        )


@registry.misc("dispersal_traits_match")
def dispersal_traits_match(ent):
    return DispersalTraits.dispersal_traits_match(ent)
