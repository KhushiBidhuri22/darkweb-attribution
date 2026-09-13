"""
adapters/base.py
=================
An Adapter is a thin, declarative description of "what kind of source is
this and what defaults apply", NOT a place to re-implement parsing logic.
Parsing stays generic in parser.py; extraction stays generic in
extractor.py. Adapters only supply source-type-specific defaults
(observation_type, category, source_id prefix) and, if genuinely needed,
a tiny post-processing hook.

Add a new source type by adding a new Adapter subclass here (or in a new
file in this package) -- you should NOT need to touch fetcher.py,
parser.py, extractor.py, normalizer.py, or validator.py to support a new
page layout, as long as the page uses the same structured markup
conventions (data-field=... attributes) or the regex fallback patterns
in extractor.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..extractor import ExtractionResult, extract
from ..parser import Element


@dataclass
class Adapter:
    name: str
    default_observation_type: str
    default_category: Optional[str] = None

    def extract(self, root: Element) -> ExtractionResult:
        """Default extraction just delegates to the generic extractor."""
        return extract(root)

    def observation_type(self, extraction: ExtractionResult) -> str:
        if extraction.migration_signal:
            return "migration_signal"
        return self.default_observation_type

    def category(self, extraction: ExtractionResult) -> Optional[str]:
        return extraction.category_hint or self.default_category
