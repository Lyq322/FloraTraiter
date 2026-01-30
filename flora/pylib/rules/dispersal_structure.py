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
class DispersalStructure(Linkable):
    """Extract seed/fruit dispersal structure traits (wing, pappus, hooks, etc.).
    Linked to seed/fruit part (seed, fruit, drupe, achene, etc.) via PartLinker.
    """

    # Class vars ----------
    dispersal_csv: ClassVar[Path] = (
        Path(__file__).parent / "terms" / "dispersal_terms.csv"
    )
    replace: ClassVar[dict[str, str]] = term_util.look_up_table(
        dispersal_csv, "replace"
    )
    type_: ClassVar[dict[str, str]] = term_util.look_up_table(
        dispersal_csv, "type"
    )
    # ---------------------

    dispersal_structure: str = None

    def to_dwc(self, dwc) -> DarwinCore:
        return dwc.add_dyn(**{self.key: self.dispersal_structure})

    @property
    def key(self) -> str:
        return self.key_builder("dispersal", "structure")

    @classmethod
    def pipe(cls, nlp: Language):
        add.term_pipe(nlp, name="dispersal_terms", path=cls.dispersal_csv)
        add.trait_pipe(
            nlp,
            name="dispersal_patterns",
            compiler=cls.dispersal_patterns(),
            overwrite=["part", "part_term", "dispersal_structure"],
        )
        add.cleanup_pipe(nlp, name="dispersal_cleanup")

    @classmethod
    def dispersal_patterns(cls):
        decoder = {
            "(": {"TEXT": {"IN": t_const.OPEN}},
            ")": {"TEXT": {"IN": t_const.CLOSE}},
            "dispersal": {"ENT_TYPE": "dispersal_term"},
        }
        return [
            Compiler(
                label="dispersal_structure",
                on_match="dispersal_structure_match",
                keep="dispersal_structure",
                decoder=decoder,
                patterns=[
                    "  dispersal ",
                    "( dispersal )",
                ],
            ),
        ]

    @classmethod
    def dispersal_structure_match(cls, ent):
        # Use type from first dispersal_term token; normalize via replace
        dispersal_type = None
        for token in ent:
            if token._.term == "dispersal_term":
                key = token.lower_
                dispersal_type = cls.type_.get(key)
                if dispersal_type is None:
                    # Try replace-normalized form as key for type lookup
                    norm = cls.replace.get(key, key)
                    dispersal_type = cls.type_.get(norm)
                if dispersal_type is not None:
                    break
        return cls.from_ent(ent, dispersal_structure=dispersal_type)


@registry.misc("dispersal_structure_match")
def dispersal_structure_match(ent):
    return DispersalStructure.dispersal_structure_match(ent)
