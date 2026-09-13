"""
pipeline.py
===========
Orchestrates: fetch -> parse -> extract -> normalize -> validate -> JSON.

CLI usage (works the same on Windows/macOS/Linux since it's pure Python):

    python -m collector.pipeline --fixture fixtures/forum_post_01.html
    python -m collector.pipeline --fixtures-dir fixtures
    python -m collector.pipeline --fixture fixtures/forum_post_01.html --out out.json

A failed source is logged and skipped (when running --fixtures-dir over
multiple files) rather than crashing the whole run.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from urllib.parse import urlparse

from .fetcher import LocalFixtureFetcher, FetchError
from .parser import parse_html
from .adapters import ADAPTERS, detect_adapter
from .normalizer import normalize
from .validator import validate, DuplicateTracker

logger = logging.getLogger("collector.pipeline")


def _domain_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc or "synthetic-source.local"
    except Exception:
        return "synthetic-source.local"


def process_fixture(path: Path, fetcher: LocalFixtureFetcher, adapter_key: str | None,
                     tracker: DuplicateTracker) -> dict:
    """
    Runs one fixture through the full pipeline. Returns a result dict with
    keys: observation (dict or None), validation (dict), source_id, ok (bool).
    Raises nothing outward for expected failure modes -- callers that want
    strict behaviour can check `ok`.
    """
    result = {"fixture": str(path), "ok": False, "observation": None,
              "validation": None, "error": None}
    try:
        fetch_result = fetcher.fetch(path)
    except FetchError as exc:
        logger.error("Fetch failed for %s: %s", path, exc)
        result["error"] = f"fetch_error: {exc}"
        return result

    try:
        root = parse_html(fetch_result.raw_content)
    except Exception as exc:  # parser should be robust, but never crash the batch
        logger.error("Parse failed for %s: %s", path, exc)
        result["error"] = f"parse_error: {exc}"
        return result

    adapter = ADAPTERS[adapter_key] if adapter_key else detect_adapter(path.name)

    try:
        extraction = adapter.extract(root)
        observation = normalize(
            extraction,
            source_id=fetch_result.source_id,
            url=fetch_result.url,
            domain=_domain_from_url(fetch_result.url),
            category=adapter.category(extraction),
            observation_type=adapter.observation_type(extraction),
        )
    except Exception as exc:
        logger.error("Extraction/normalization failed for %s: %s", path, exc)
        result["error"] = f"processing_error: {exc}"
        return result

    validation = validate(observation, tracker=tracker)
    result["observation"] = observation.to_dict()
    result["validation"] = {
        "is_valid": validation.is_valid,
        "errors": validation.errors,
        "warnings": validation.warnings,
    }
    result["ok"] = validation.is_valid
    result["source_id"] = fetch_result.source_id
    result["adapter"] = adapter.name

    if not validation.is_valid:
        logger.warning("Validation failed for %s: %s", path, validation.errors)
    if validation.warnings:
        logger.info("Validation warnings for %s: %s", path, validation.warnings)

    return result


def run(fixture: str | None, fixtures_dir: str | None, adapter_key: str | None,
        out_path: str | None) -> list[dict]:
    fetcher = LocalFixtureFetcher()
    tracker = DuplicateTracker()
    results = []

    if fixture:
        results.append(process_fixture(Path(fixture), fetcher, adapter_key, tracker))
    elif fixtures_dir:
        dir_path = Path(fixtures_dir)
        html_files = sorted(dir_path.glob("*.html"))
        if not html_files:
            logger.warning("No .html fixtures found in %s", dir_path)
        for f in html_files:
            results.append(process_fixture(f, fetcher, adapter_key, tracker))
    else:
        raise SystemExit("Must pass either --fixture or --fixtures-dir")

    payload = json.dumps(results if len(results) > 1 else results[0], indent=2)
    if out_path:
        Path(out_path).write_text(payload, encoding="utf-8")
        logger.info("Wrote output to %s", out_path)
    print(payload)
    return results


def main():
    parser = argparse.ArgumentParser(
        prog="python -m collector.pipeline",
        description="Run a synthetic HTML fixture through the collector pipeline.",
    )
    parser.add_argument("--fixture", help="Path to a single HTML fixture file.")
    parser.add_argument("--fixtures-dir", help="Directory of .html fixtures to process in a batch.")
    parser.add_argument("--adapter", choices=sorted(ADAPTERS.keys()), default=None,
                         help="Force a specific adapter instead of filename auto-detection.")
    parser.add_argument("--out", help="Optional path to also write JSON output to a file.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,  # keep stdout clean for the JSON payload
    )

    run(args.fixture, args.fixtures_dir, args.adapter, args.out)


if __name__ == "__main__":
    main()
