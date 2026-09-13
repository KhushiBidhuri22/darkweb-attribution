"""
parser.py
=========
Converts raw HTML into a small, queryable tree structure.

Deliberately uses only Python's standard-library `html.parser` (no
BeautifulSoup/lxml dependency) so the collector has zero third-party
dependencies. If the team later wants richer CSS-selector support,
swapping in BeautifulSoup here is a contained change -- nothing outside
parser.py needs to know.

The parser does NOT know anything about threat-intel semantics (no
"handle", "wallet", etc. here) -- that belongs in extractor.py. This
file only turns HTML into `Element` objects you can query by tag,
class, or data-* attribute.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from dataclasses import dataclass, field
from typing import Optional

_WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class Element:
    tag: str
    attrs: dict
    text_parts: list = field(default_factory=list)
    children: list = field(default_factory=list)
    parent: Optional["Element"] = None

    @property
    def text(self) -> str:
        """All direct + nested text, whitespace-normalized."""
        parts = list(self.text_parts)
        for child in self.children:
            parts.append(child.text)
        joined = " ".join(p.strip() for p in parts if p and p.strip())
        return _WHITESPACE_RE.sub(" ", joined).strip()

    def has_class(self, cls: str) -> bool:
        classes = (self.attrs.get("class") or "").split()
        return cls in classes

    def data(self, key: str) -> Optional[str]:
        return self.attrs.get(f"data-{key}")

    def find_all(self, tag: Optional[str] = None, cls: Optional[str] = None,
                 data_field: Optional[str] = None) -> list["Element"]:
        results = []
        for child in self.children:
            match = True
            if tag and child.tag != tag:
                match = False
            if cls and not child.has_class(cls):
                match = False
            if data_field and child.data("field") != data_field:
                match = False
            if match:
                results.append(child)
            results.extend(child.find_all(tag=tag, cls=cls, data_field=data_field))
        return results

    def find_one(self, tag: Optional[str] = None, cls: Optional[str] = None,
                 data_field: Optional[str] = None) -> Optional["Element"]:
        found = self.find_all(tag=tag, cls=cls, data_field=data_field)
        return found[0] if found else None


_VOID_TAGS = {"br", "img", "hr", "meta", "link", "input", "time"}
# note: <time> is not technically void, handled generically below


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element(tag="root", attrs={})
        self._stack = [self.root]

    def handle_starttag(self, tag, attrs):
        el = Element(tag=tag, attrs=dict(attrs), parent=self._stack[-1])
        self._stack[-1].children.append(el)
        if tag not in ("br", "img", "hr", "meta", "link", "input"):
            self._stack.append(el)

    def handle_startendtag(self, tag, attrs):
        el = Element(tag=tag, attrs=dict(attrs), parent=self._stack[-1])
        self._stack[-1].children.append(el)

    def handle_endtag(self, tag):
        # pop back to matching tag if present; tolerate malformed HTML
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i].tag == tag:
                del self._stack[i:]
                return

    def handle_data(self, data):
        if data.strip():
            self._stack[-1].text_parts.append(data)


def parse_html(raw_html: str) -> Element:
    """Parse raw HTML into a queryable Element tree rooted at a synthetic 'root' node."""
    builder = _TreeBuilder()
    builder.feed(raw_html)
    return builder.root
