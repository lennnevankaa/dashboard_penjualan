import logging
import time
import traceback

import config
from clustering import runner
from etl import extract, load, transform

logger = logging.getLogger(__name__)


class StepError(Exception):
    def __init__(self, step, original):
        super().__init__(f"Langkah '{step}' gagal: {type(original).__name__}: {original}")
        self.step = step
        self.original = original


def latest_upload():
    files = [p for p in config.UPLOAD_DIR.glob("*") if p.suffix.lower() in config.ALLOWED_EXT]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def _timed(step, func, *args, **kwargs):
    start = time.perf_counter()
    try:
        result = func(*args, **kwargs)
    except Exception as exc:
        logger.error("Langkah %s gagal\n%s", step, traceback.format_exc())
        raise StepError(step, exc) from exc
    result["step"] = step
    result["seconds"] = round(time.perf_counter() - start, 2)
    return result


def run_extract(path):
    return _timed("extract", extract.run, path)


def run_transform(path=None):
    return _timed("transform", transform.run, path) if path else _timed("transform", transform.run)


def run_load():
    return _timed("load", load.run)


def run_clustering():
    return _timed("clustering", runner.run)


def run_all(path, on_step=None):
    steps = (
        lambda: run_extract(path),
        lambda: run_transform(path),
        run_load,
        run_clustering,
    )
    results = []
    for step in steps:
        result = step()
        results.append(result)
        if on_step:
            on_step(result)
    return results