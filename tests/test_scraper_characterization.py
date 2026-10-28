"""Characterization tests for DexScraper's binary extraction heuristics.

These pin the current output of every extraction helper on a deterministic
synthetic corpus, so refactors (moving code between modules, narrowing
exception handling) can prove they did not change behaviour.

The expected values live in ``tests/fixtures/scraper_characterization.json``.
They describe what the code does today, not what it should do. If a change is
meant to alter extraction output, regenerate the fixture with::

    DEXSCRAPER_REGEN_CHARACTERIZATION=1 pytest tests/test_scraper_characterization.py

and review the fixture diff as part of that change.
"""

import asyncio
from collections.abc import Iterable, Iterator
import contextlib
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import random
import struct
import sys
from typing import Any

import pytest

from dexscraper import DexScraper
from dexscraper.models import TokenProfile

FIXTURE = Path(__file__).parent / "fixtures" / "scraper_characterization.json"
REGEN = os.environ.get("DEXSCRAPER_REGEN_CHARACTERIZATION") == "1"

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
SOL_MINT = "So11111111111111111111111111111111111111112"


def _b58encode(raw: bytes) -> str:
    value = int.from_bytes(raw, "big")
    out = ""
    while value:
        value, rem = divmod(value, 58)
        out = _B58[rem] + out
    pad = len(raw) - len(raw.lstrip(b"\x00"))
    return "1" * pad + out


def _record(rng: random.Random, symbol: str, style: int) -> bytes:
    """Build one synthetic token record: text markers, metadata and numerics."""
    parts: list[bytes] = []
    labels = [
        f'"symbol":"{symbol}"',
        f"symbol:{symbol}",
        f"${symbol}",
        f'"name":"{symbol.capitalize()}coin"',
        f"token:{symbol}",
    ]
    parts.append(labels[style % len(labels)].encode())
    parts.append(bytes(rng.randrange(256) for _ in range(rng.randrange(4, 24))))
    parts.append(_b58encode(bytes(rng.randrange(256) for _ in range(32))).encode())
    parts.append(b" ")
    if style % 2 == 0:
        parts.append(SOL_MINT.encode() + b" ")
    urls = [
        f"https://twitter.com/{symbol.lower()}",
        f"https://t.me/{symbol.lower()}",
        f"https://{symbol.lower()}.io",
        f"https://x.com/{symbol.lower()}",
        "https://example.net/path",
    ]
    parts.append(urls[style % len(urls)].encode() + b" ")
    parts.append(["pumpfun", "pumpswap", "PumpFun", "raydium"][style % 4].encode())
    parts.append(b" " + ["5m", "1h", "6h", "24h"][style % 4].encode() + b" ")
    parts.append(struct.pack("<d", rng.uniform(0.00001, 0.09)))
    parts.append(struct.pack("<d", rng.uniform(1_000_000, 9_000_000)))
    parts.append(struct.pack("<d", rng.uniform(100_000, 900_000)))
    parts.append(struct.pack("<d", rng.uniform(10_000, 90_000)))
    parts.append(struct.pack("<f", rng.uniform(12, 900)))
    parts.append(struct.pack("<I", rng.randrange(1000, 50_000)))
    parts.append(struct.pack("<I", rng.randrange(10, 1000)))
    parts.append(struct.pack("<d", rng.uniform(-90, 900)))
    parts.append(struct.pack("<f", rng.uniform(-50, 50)))
    parts.append(bytes(rng.randrange(256) for _ in range(rng.randrange(16, 96))))
    parts.append(b" The Server Error HTTP JSON Phantom Coiny WLFI BONK ")
    return b"".join(parts)


def build_corpus(seed: int, records: int) -> bytes:
    rng = random.Random(seed)
    symbols = ["PEPE", "BONK", "WLFI", "MROCKS", "KAIROS", "ZETA", "Coiny", "AB"]
    body = b"".join(
        _record(rng, symbols[(seed + i) % len(symbols)], seed + i)
        for i in range(records)
    )
    return b"\x00\x01handshake-prefix\x00pairs" + bytes(15) + body


CORPORA = {"small": (7, 3), "medium": (42, 8), "noisy": (1337, 14)}


class _InsertionOrderedSet(dict[Any, None]):
    """Set stand-in that iterates in insertion order.

    The symbol heuristics iterate over ``set(...)`` of regex matches, so with
    hash randomisation the order of equal-confidence symbols (and which ones
    survive the top-20 cut) differs between runs. Any insertion order is a
    possible set order, so pinning it keeps the characterization faithful
    while making it reproducible.
    """

    def __init__(self, items: Iterable[Any] = ()) -> None:
        super().__init__((item, None) for item in items)

    def add(self, item: Any) -> None:
        self[item] = None


@contextlib.contextmanager
def _deterministic_sets() -> Iterator[None]:
    modules = {
        sys.modules[getattr(DexScraper, name).__module__]
        for name in dir(DexScraper)
        if name.startswith(("_extract", "_build"))
    }
    for module in modules:
        module.set = _InsertionOrderedSet  # type: ignore[attr-defined]
    try:
        yield
    finally:
        for module in modules:
            del module.set  # type: ignore[attr-defined]


def _plain(value: Any) -> Any:
    """Convert extraction output into JSON-comparable data."""
    if isinstance(value, TokenProfile):
        data = dataclasses.asdict(value)
        data.pop("timestamp", None)
        return {key: item for key, item in data.items() if item is not None}
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def _digest(value: Any) -> str:
    """Short stable digest for bulky numeric output (keeps the fixture small)."""
    blob = json.dumps(_plain(value), sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def characterize(seed: int, records: int) -> dict[str, Any]:
    with _deterministic_sets():
        return _characterize(seed, records)


def _characterize(seed: int, records: int) -> dict[str, Any]:
    scraper = DexScraper(debug=False)
    message = build_corpus(seed, records)
    data_start = message.find(b"pairs") + 20
    data = message[data_start:]
    printable = "".join(chr(b) if 32 <= b <= 126 else " " for b in data)

    names = scraper._extract_real_token_names(printable, data_start)
    metadata = scraper._extract_metadata_patterns(data, data_start)
    records_out = {
        str(pos): _plain(
            scraper._extract_validated_token_record(
                name,
                data[max(0, pos - data_start - 500) : pos - data_start + 500],
                pos,
            )
        )
        for pos, name in sorted(names.items())
    }
    tokens = asyncio.run(scraper._extract_all_tokens(data, data_start))

    return {
        "real_token_names": _plain(names),
        "metadata": _plain(metadata),
        "token_symbols": _plain(scraper._extract_token_symbols(printable, data_start)),
        "validated_records": records_out,
        "all_tokens": _plain(tokens),
    }


def _load_fixture() -> dict[str, Any]:
    if REGEN:
        FIXTURE.write_text(
            json.dumps(
                {name: characterize(*args) for name, args in CORPORA.items()},
                indent=1,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )
    loaded: dict[str, Any] = json.loads(FIXTURE.read_text())
    return loaded


@pytest.fixture(scope="module")
def expected() -> dict[str, Any]:
    return _load_fixture()


@pytest.mark.parametrize("corpus", sorted(CORPORA))
def test_extraction_matches_characterization(
    corpus: str, expected: dict[str, Any]
) -> None:
    actual = json.loads(json.dumps(characterize(*CORPORA[corpus]), sort_keys=True))
    for key, value in expected[corpus].items():
        assert actual[key] == value, f"{corpus}: {key} changed"
    assert set(actual) == set(expected[corpus])


def test_fixture_is_not_trivial(expected: dict[str, Any]) -> None:
    """Guard against a regenerated fixture that pins nothing useful."""
    for corpus, data in expected.items():
        assert data["all_tokens"], corpus
        assert data["metadata"]["addresses"], corpus
        assert data["metadata"]["urls"], corpus
        assert data["metadata"]["protocols"], corpus


@pytest.mark.parametrize(
    ("address", "kind"),
    [
        (SOL_MINT, "SOL_token"),
        ("A" * 40, "potential_contract"),
        ("A" * 32, "unknown"),
    ],
)
def test_classify_address(address: str, kind: str) -> None:
    assert DexScraper()._classify_address(address) == kind


@pytest.mark.parametrize(
    ("url", "kind"),
    [
        ("https://twitter.com/a", "twitter"),
        ("https://x.com/a", "twitter"),
        ("https://t.me/a", "telegram"),
        ("https://telegram.org/a", "telegram"),
        ("https://a.io", "website"),
        ("https://a.xyz", "website"),
        ("https://a.net", "unknown"),
    ],
)
def test_classify_url(url: str, kind: str) -> None:
    assert DexScraper()._classify_url(url) == kind


def test_validated_record_needs_three_fields() -> None:
    scraper = DexScraper()
    pad = b"\x00" * 8
    assert scraper._extract_validated_token_record("X", pad * 8, 0) is None
    # Two uint32 counts only yield txns_24h and makers: below the threshold.
    counts = pad + struct.pack("<I", 2000) + pad + struct.pack("<I", 50) + pad
    assert scraper._extract_validated_token_record("X", counts, 0) is None
    # A lone market-cap double also decodes to two more fields at shifted
    # offsets, which is exactly enough.
    mcap = pad + struct.pack("<d", 2_000_000.0) + pad
    profile = scraper._extract_validated_token_record("X", mcap, 10)
    assert profile is not None
    assert profile.field_count == 3
    assert profile.market_cap == 2_000_000.0
    assert profile.confidence_score == pytest.approx(0.85)
    full = struct.pack("<d", 0.005) + struct.pack("<d", 2_000_000.0)
    full += struct.pack("<d", 200_000.0) + pad
    profile = scraper._extract_validated_token_record("X", full, 10)
    assert profile is not None
    assert (profile.symbol, profile.price, profile.field_count) == ("X", 0.005, 6)
    assert profile.confidence_score == 0.95


@pytest.mark.parametrize("seed", range(5))
def test_numeric_decoders_never_raise_on_arbitrary_bytes(seed: int) -> None:
    """The decoders slice fixed-width windows, so struct.unpack cannot fail.

    Includes NaN/inf bit patterns and lengths shorter than one value.
    """
    rng = random.Random(seed)
    scraper = DexScraper()
    specials = [
        struct.pack("<d", float("nan")),
        struct.pack("<d", float("inf")),
        struct.pack("<f", float("-inf")),
        b"\xff" * 8,
    ]
    for length in [0, 1, 3, 4, 5, 7, 8, 9, 16, 257, 700, 1201]:
        data = bytes(rng.randrange(256) for _ in range(length))
        data = rng.choice(specials) + data + rng.choice(specials)
        scraper._extract_validated_token_record("X", data, 0)
