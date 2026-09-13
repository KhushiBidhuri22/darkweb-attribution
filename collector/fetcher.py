"""
fetcher.py
==========
Responsible ONLY for retrieving raw source content. It does not parse,
extract, or interpret anything.

For the SIH prototype, the fetcher reads local synthetic HTML fixtures
(no live network access, no credentials, no dark-web access required).

The FetchResult it returns is the same shape regardless of where the
content came from, so parser.py never needs to know whether the content
was read from disk, a future authorized crawler, or an API dump. That is
the seam where a real (authorized) OSINT fetcher would be swapped in
later without touching parser.py, extractor.py, normalizer.py,
validator.py, or pipeline.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("collector.fetcher")


class FetchError(Exception):
    """Raised when a source cannot be fetched."""


@dataclass
class FetchResult:
    source_id: str
    url: str
    raw_content: str
    content_type: str = "text/html"


class LocalFixtureFetcher:
    """
    Fetches content from a local HTML fixture file.

    This is the ONLY fetcher used by the SIH prototype. It exists so the
    rest of the pipeline (parser/extractor/normalizer/validator) can be
    fully exercised and demoed without any live dark-web access.
    """

    def __init__(self, fixtures_dir: str | Path | None = None):
        self.fixtures_dir = Path(fixtures_dir) if fixtures_dir else None

    def fetch(self, path: str | Path, source_id: str | None = None,
              url: str | None = None) -> FetchResult:
        p = Path(path)
        if not p.is_absolute() and self.fixtures_dir:
            p = self.fixtures_dir / p
        if not p.exists():
            raise FetchError(f"Fixture not found: {p}")

        try:
            raw = p.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise FetchError(f"Could not decode fixture {p} as UTF-8") from exc

        inferred_source_id = source_id or p.stem
        inferred_url = url or f"https://synthetic-source.local/fixtures/{p.name}"

        logger.info("Fetched fixture %s (%d bytes)", p, len(raw))
        return FetchResult(
            source_id=inferred_source_id,
            url=inferred_url,
            raw_content=raw,
            content_type="text/html",
        )


class UnimplementedLiveFetcher:
    """
    Placeholder for a future authorized OSINT fetcher.

    Intentionally NOT implemented in this prototype: no live dark-web
    fetching, no credentials, no proprietary/paid services. This class
    exists purely to document the seam where that code would go later,
    so the architecture is obviously extensible without a rewrite.
    """

    def fetch(self, *args, **kwargs) -> FetchResult:
        raise NotImplementedError(
            "Live/authorized fetching is out of scope for the SIH prototype. "
            "Use LocalFixtureFetcher with synthetic fixtures instead."
        )
