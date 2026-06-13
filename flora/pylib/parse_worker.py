"""Parse treatments in a subprocess so hung spaCy runs can be killed."""

from __future__ import annotations

import logging
import multiprocessing as mp
import queue
from pathlib import Path


def _worker_loop(request_queue: mp.Queue, response_queue: mp.Queue) -> None:
    from flora.pylib.pipelines import flora_pipeline
    from flora.pylib.treatment import Treatment

    nlp = flora_pipeline.build()
    response_queue.put(("ready", None))

    while True:
        msg = request_queue.get()
        if msg is None:
            break
        path_str, encoding = msg
        try:
            treatment = Treatment(Path(path_str))
            treatment.parse(nlp, encoding=encoding)
            response_queue.put(("ok", (treatment.text, treatment.traits)))
        except Exception as exc:
            response_queue.put(("error", str(exc)))


class ParseWorker:
    """Long-lived worker process; restarted when a parse exceeds the timeout."""

    _STARTUP_TIMEOUT = 300

    def __init__(self) -> None:
        self._ctx = mp.get_context("spawn")
        self._request_queue: mp.Queue | None = None
        self._response_queue: mp.Queue | None = None
        self._process: mp.Process | None = None

    def start(self) -> None:
        self._restart()

    def _restart(self) -> None:
        self._stop(force=True)
        self._request_queue = self._ctx.Queue()
        self._response_queue = self._ctx.Queue()
        self._process = self._ctx.Process(
            target=_worker_loop,
            args=(self._request_queue, self._response_queue),
            daemon=True,
        )
        self._process.start()
        status, _ = self._response_queue.get(timeout=self._STARTUP_TIMEOUT)
        if status != "ready":
            raise RuntimeError(f"parse worker failed to start: {status}")

    def _stop(self, *, force: bool = False) -> None:
        if self._process is None:
            return
        if (
            not force
            and self._request_queue is not None
            and self._process.is_alive()
        ):
            self._request_queue.put(None)
        if self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=5)
            if self._process.is_alive():
                self._process.kill()
                self._process.join(timeout=5)
        self._process = None
        self._request_queue = None
        self._response_queue = None

    def parse(
        self, path: Path, encoding: str, timeout: float
    ) -> tuple[str, list, str | None]:
        """Return (text, traits, error). error is None on success."""
        if self._request_queue is None or self._response_queue is None:
            raise RuntimeError("parse worker is not running")

        self._request_queue.put((str(path), encoding))
        try:
            status, payload = self._response_queue.get(timeout=timeout)
        except queue.Empty:
            logging.error("SKIP (timeout %ss): %s", timeout, path.name)
            self._restart()
            return "", [], f"timed out after {timeout}s"

        if status == "ok":
            text, traits = payload
            return text, traits, None

        logging.error("SKIP (error): %s: %s", path.name, payload)
        return "", [], str(payload)

    def close(self) -> None:
        self._stop(force=False)
