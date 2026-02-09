#!/usr/bin/env python3
"""Package metadata tests."""

import dexscraper


def test_package_version_is_resolved():
    """Version should come from package metadata (or fallback) and be non-empty."""
    assert isinstance(dexscraper.__version__, str)
    assert dexscraper.__version__.strip() != ""
