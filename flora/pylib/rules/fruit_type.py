"""Fruit type rule (drupe, achene, berry, etc.) separate from Part for correct linking."""

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

from .linkable import Linkable


def _load_keyword_to_core_fruit_type(path: Path) -> dict[str, str]:
    """Load keyword_term -> core_fruit_type from mapping CSV (only non-empty core_fruit_type)."""
    out = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            kw = (row.get("keyword_term") or "").strip().lower()
            core = (row.get("core_fruit_type") or "").strip()
            if kw and core:
                out[kw] = core
    return out


@dataclass(eq=False)
class FruitType(Linkable):
    """Extract fruit types (drupe, achene, berry, etc.) as separate entities.
    PartLinker copies .part to child traits (e.g. dispersal_traits) when linked.
    """

    fruit_type_csv: ClassVar[Path] = (
        Path(__file__).parent / "terms" / "fruit_type_terms.csv"
    )
    mapping_csv: ClassVar[Path] = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "keyword_to_dispersal_traits_mapping.csv"
    )
    replace: ClassVar[dict[str, str]] = term_util.look_up_table(
        fruit_type_csv, "replace"
    )
    _keyword_to_core_fruit_type: ClassVar[dict[str, str] | None] = None

    part: str | list[str] = None  # canonical fruit type (e.g. berry)
    matched_keyword: str = None  # original matched text (e.g. pepo) for keywords list

    @classmethod
    def _get_keyword_to_core_fruit_type(cls) -> dict[str, str]:
        if cls._keyword_to_core_fruit_type is None:
            cls._keyword_to_core_fruit_type = _load_keyword_to_core_fruit_type(
                cls.mapping_csv
            )
        return cls._keyword_to_core_fruit_type

    def _sanitize_keyword(self, keyword: str) -> str:
        return (keyword or "").replace(" ", "_").replace("-", "_").lower()

    def to_dwc(self, dwc) -> DarwinCore:
        payload = {self.key: self.part}
        if self.matched_keyword:
            payload[
                f"fruit_type_keyword_{self._sanitize_keyword(self.matched_keyword)}"
            ] = self.matched_keyword
        return dwc.add_dyn(**payload)

    @property
    def key(self) -> str:
        return self.key_builder("fruit", "type", add_data=False)

    @classmethod
    def pipe(cls, nlp: Language):
        add.term_pipe(nlp, name="fruit_type_terms", path=cls.fruit_type_csv)
        add.trait_pipe(
            nlp,
            name="fruit_type_patterns",
            compiler=cls.fruit_type_patterns(),
            overwrite=["fruit_type_term", "fruit_type"],
        )
        add.cleanup_pipe(nlp, name="fruit_type_cleanup")

    @classmethod
    def fruit_type_patterns(cls):
        decoder = {
            "(": {"TEXT": {"IN": t_const.OPEN}},
            ")": {"TEXT": {"IN": t_const.CLOSE}},
            "fruit_type": {"ENT_TYPE": "fruit_type_term"},
        }
        return [
            Compiler(
                label="fruit_type",
                on_match="fruit_type_match",
                keep="fruit_type",
                decoder=decoder,
                patterns=[
                    "  fruit_type ",
                    "( fruit_type )",
                ],
            ),
        ]

    @classmethod
    def fruit_type_match(cls, ent):
        keyword = None
        canonical = None
        for token in ent:
            if token._.term == "fruit_type_term":
                keyword = token.lower_
                # Prefer mapping CSV (keyword -> core_fruit_type); fall back to fruit_type_terms replace
                mapping = cls._get_keyword_to_core_fruit_type()
                canonical = mapping.get(keyword) or cls.replace.get(keyword, keyword)
                break
        if keyword is None or canonical is None:
            return None
        trait = cls.from_ent(ent, part=canonical, matched_keyword=keyword)
        # So PartLinker copies .part to child (dispersal_traits)
        trait._trait = "part"
        return trait


@registry.misc("fruit_type_match")
def fruit_type_match(ent):
    return FruitType.fruit_type_match(ent)
