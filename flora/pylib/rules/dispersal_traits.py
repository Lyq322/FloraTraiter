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
class DispersalTraits(Linkable):
    """Extract seed/fruit dispersal traits (wing, pappus, hooks, etc.).
    Linked to seed/fruit part (seed, fruit, drupe, achene, etc.) via PartLinker.
    """

    # Class vars ----------
    terms_dir: ClassVar[Path] = Path(__file__).parent / "terms"
    dispersal_csv: ClassVar[Path] = terms_dir / "dispersal_terms.csv"
    dispersal_negator_csv: ClassVar[Path] = terms_dir / "dispersal_negator_terms.csv"
    dispersal_absence_csv: ClassVar[Path] = terms_dir / "dispersal_absence_terms.csv"
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
    # ---------------------

    dispersal_traits: str = None

    def to_dwc(self, dwc) -> DarwinCore:
        return dwc.add_dyn(**{self.key: self.dispersal_traits})

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
        if dispersal_tokens:
            key = " ".join(t.lower_ for t in dispersal_tokens).strip()
            dispersal_type = cls.type_.get(key)
            if dispersal_type is None:
                norm = cls.replace.get(key, key)
                dispersal_type = cls.type_.get(norm)
        if dispersal_type is not None and negated and not dispersal_type.endswith(
            "_absent"
        ):
            dispersal_type = dispersal_type + "_absent"
        return cls.from_ent(ent, dispersal_traits=dispersal_type)


@registry.misc("dispersal_traits_match")
def dispersal_traits_match(ent):
    return DispersalTraits.dispersal_traits_match(ent)
