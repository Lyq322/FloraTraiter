from spacy.language import Language
from spacy.tokens import Doc
from traiter.pylib.pipes import add
import logging


def pipe(nlp: Language):
    add.custom_pipe(nlp, "flora_post_process")


@Language.factory("flora_post_process")
class FloraPostProcess:
    def __init__(self, nlp: Language, name: str):
        super().__init__()
        self.nlp = nlp
        self.name = name

    def __call__(self, doc: Doc) -> Doc:
        entities = list(doc.ents)
        # Map fruit types to their underlying part (fruit or seed)
        # Most fruit types map to "fruit", but some might map to "seed"
        fruit_type_to_part = {
            # Achene types -> fruit
            "achene": "fruit",
            "cypsela": "fruit",
            "anthocarp": "fruit",
            # Berry types -> fruit
            "berry": "fruit",
            "amphisarca": "fruit",
            "arillocarpium": "fruit",
            "balausta": "fruit",
            "cactidium": "fruit",
            "epispermatium": "fruit",
            "hesperidium": "fruit",
            "pepo": "fruit",
            "syncarp": "fruit",
            # Capsule types -> fruit
            "capsule": "fruit",
            "circumscissile": "fruit",
            "loculicidal": "fruit",
            "poricidal": "fruit",
            "pyxis": "fruit",
            "septicidal": "fruit",
            "silicle": "fruit",
            "silique": "fruit",
            # Caryopsis -> fruit (or seed? usually fruit)
            "caryopsis": "fruit",
            "grain": "fruit",
            # Drupe types -> fruit
            "drupe": "fruit",
            "drupelet": "fruit",
            "drupetum": "fruit",
            "pseudodrupe": "fruit",
            "stone fruit": "fruit",
            # Follicle -> fruit
            "follicle": "fruit",
            # Gymnosperm cones -> could be fruit or seed depending on context
            "cone": "fruit",
            "megastrobilus": "fruit",
            "microstrobilus": "fruit",
            "strobili": "fruit",
            "strobilus": "fruit",
            "berry-like cone": "fruit",
            "cone berry": "fruit",
            "galbulus": "fruit",
            # Legume types -> fruit
            "legume": "fruit",
            "loment": "fruit",
            "pod": "fruit",
            # Nut types -> fruit (or seed? usually fruit)
            "nut": "fruit",
            "nutlet": "fruit",
            # Pome -> fruit
            "pome": "fruit",
            "nuculanium": "fruit",
            # Samara -> fruit
            "samara": "fruit",
            "samaroid": "fruit",
            # Schizocarp types -> fruit
            "schizocarp": "fruit",
            "camara": "fruit",
            "carcerulus": "fruit",
            "coccus": "fruit",
            "cremocarp": "fruit",
            "mericarp": "fruit",
            "regma": "fruit",
            # Sorosis -> fruit
            "sorosis": "fruit",
            # Syconium -> fruit
            "syconium": "fruit",
            # Utricle -> fruit
            "utricle": "fruit",
        }

        # First pass: collect fruit/seed part entities
        fruit_seed_parts = []  # List of (entity, part_value) tuples

        for ent in entities:
            if ent.label_ == "name":
                continue

            if ent.label_ == "part" and hasattr(ent, "_trait"):
                trait = ent._trait
                if hasattr(trait, "part") and hasattr(trait, "type"):
                    part = trait.part
                    part_type = trait.type

                    # Collect fruit/seed parts (fruit_part type with part="fruit" or "seed")
                    if part_type == "fruit_part":
                        if isinstance(part, str):
                            if part.lower() in ("fruit", "seed", "fruits", "seeds"):
                                fruit_seed_parts.append((ent, part.lower()))
                        elif isinstance(part, list):
                            for p in part:
                                if p.lower() in ("fruit", "seed", "fruits", "seeds"):
                                    fruit_seed_parts.append((ent, p.lower()))
                                    break
        logging.info(f"fruit_seed_parts: {fruit_seed_parts}")
        # Second pass: for subparts linked to fruit_types, also link to fruit/seed
        for ent in entities:
            if ent.label_ == "subpart" and hasattr(ent, "_trait"):
                trait = ent._trait
                if hasattr(trait, "part"):
                    part = trait.part

                    # Check if this subpart is linked to a fruit_type
                    if isinstance(part, str):
                        part_lower = part.lower()
                        if part_lower in fruit_type_to_part:
                            # This subpart is linked to a fruit_type
                            # Find the underlying fruit/seed part
                            underlying_part = fruit_type_to_part[part_lower]

                            # Try to find a nearby fruit/seed part entity
                            # If found, link to it; otherwise use the generic part name
                            closest_fruit_seed = None
                            min_dist = float("inf")

                            for fruit_seed_ent, fruit_seed_part in fruit_seed_parts:
                                # Calculate distance between entities
                                dist = min(
                                    abs(fruit_seed_ent.start - ent.end),
                                    abs(ent.start - fruit_seed_ent.end),
                                )
                                if dist < min_dist and dist < 50:  # Within reasonable distance
                                    min_dist = dist
                                    closest_fruit_seed = fruit_seed_ent
                                    underlying_part = fruit_seed_part

                            # Update the subpart's part to the underlying fruit/seed
                            # This associates the subpart with fruit/seed instead of the fruit_type
                            trait.part = underlying_part

                    elif isinstance(part, list):
                        # Handle list of parts - check if any are fruit_types
                        updated_parts = []
                        found_fruit_type = False
                        for p in part:
                            p_lower = p.lower()
                            if p_lower in fruit_type_to_part:
                                found_fruit_type = True
                                underlying_part = fruit_type_to_part[p_lower]
                                # Try to find nearby fruit/seed part
                                closest_fruit_seed = None
                                min_dist = float("inf")
                                for fruit_seed_ent, fruit_seed_part in fruit_seed_parts:
                                    dist = min(
                                        abs(fruit_seed_ent.start - ent.end),
                                        abs(ent.start - fruit_seed_ent.end),
                                    )
                                    if dist < min_dist and dist < 50:
                                        min_dist = dist
                                        closest_fruit_seed = fruit_seed_ent
                                        underlying_part = fruit_seed_part
                                # Add the underlying part instead of the fruit_type
                                if underlying_part not in updated_parts:
                                    updated_parts.append(underlying_part)
                            else:
                                updated_parts.append(p)

                        if found_fruit_type:
                            trait.part = updated_parts if len(updated_parts) > 1 else updated_parts[0]

        entities.reverse()
        doc.ents = entities
        return doc
