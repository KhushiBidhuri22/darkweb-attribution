"""
Concrete source-type adapters.

Each adapter is registered in ADAPTERS below by a short key, used by
pipeline.py's --adapter CLI flag and by the auto-detection fallback.
"""

from .base import Adapter

forum_adapter = Adapter(
    name="forum",
    default_observation_type="post",
    default_category="general",
)

marketplace_adapter = Adapter(
    name="marketplace",
    default_observation_type="profile",
    default_category="vendor_profile",
)

thread_adapter = Adapter(
    name="thread",
    default_observation_type="reply",
    default_category="general_discussion",
)

ADAPTERS = {
    "forum": forum_adapter,
    "marketplace": marketplace_adapter,
    "thread": thread_adapter,
}


def detect_adapter(fixture_filename: str) -> Adapter:
    """
    Very small heuristic auto-detection based on filename, used only when
    --adapter isn't explicitly passed. Real source-type detection would
    likely live in the fetcher's source registry instead; this is a
    convenience for the demo CLI.
    """
    lower = fixture_filename.lower()
    if "marketplace" in lower or "vendor" in lower:
        return marketplace_adapter
    if "thread" in lower or "discussion" in lower:
        return thread_adapter
    return forum_adapter
