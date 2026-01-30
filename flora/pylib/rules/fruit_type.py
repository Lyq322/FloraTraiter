"""Fruit type rule (drupe, achene, berry, etc.) separate from Part for correct linking."""

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


@dataclass(eq=False)
class FruitType(Linkable):
    """Extract fruit types (drupe, achene, berry, etc.) as separate entities.
    PartLinker copies .part to child traits (e.g. dispersal_traits) when linked.
    """

    fruit_type_csv: ClassVar[Path] = (
        Path(__file__).parent / "terms" / "fruit_type_terms.csv"
    )
    replace: ClassVar[dict[str, str]] = term_util.look_up_table(
        fruit_type_csv, "replace"
    )

    part: str | list[str] = None  # fruit type name (drupe, achene, etc.)

    def to_dwc(self, dwc) -> DarwinCore:
        return dwc.add_dyn(**{self.key: self.part})

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
        part = None
        for token in ent:
            if token._.term == "fruit_type_term":
                part = cls.replace.get(token.lower_, token.lower_)
                break
        if part is None:
            return None
        trait = cls.from_ent(ent, part=part)
        # So PartLinker copies .part to child (dispersal_traits)
        trait._trait = "part"
        return trait


@registry.misc("fruit_type_match")
def fruit_type_match(ent):
    return FruitType.fruit_type_match(ent)
