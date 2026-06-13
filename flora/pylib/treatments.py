import logging

from tqdm import tqdm

from flora.pylib.treatment import Treatment

from .parse_worker import ParseWorker
from .pipelines import flora_pipeline


class Treatments:
    def __init__(self, treatment_dir, limit, offset, parse_timeout=None):
        self.parse_timeout = parse_timeout
        self.treatments: list[Treatment] = self.get_treatments(
            treatment_dir, limit, offset
        )
        self.nlp = None if parse_timeout else flora_pipeline.build()

    def __iter__(self):
        yield from self.treatments

    @staticmethod
    def get_treatments(treatment_dir, limit, offset):
        labels = [Treatment(p) for p in sorted(treatment_dir.glob("*"))]

        if limit:
            labels = labels[offset : limit + offset]

        return labels

    def parse(self, encoding="utf8"):
        if self.parse_timeout:
            self._parse_with_timeout(encoding)
            return

        for lb in tqdm(self.treatments, desc="parse"):
            lb.parse(self.nlp, encoding=encoding)

    def _parse_with_timeout(self, encoding: str) -> None:
        worker = ParseWorker()
        worker.start()
        skipped = 0
        try:
            for lb in tqdm(self.treatments, desc="parse"):
                text, traits, err = worker.parse(
                    lb.path, encoding, self.parse_timeout
                )
                if err:
                    skipped += 1
                    lb.text = ""
                    lb.traits = []
                    continue
                lb.text = text
                lb.traits = traits
        finally:
            worker.close()

        if skipped:
            logging.warning("Skipped %d treatment(s) due to timeout or error", skipped)
