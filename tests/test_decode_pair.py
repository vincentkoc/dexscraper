import os
import sys
import types

from dexscraper.protocol import clean_string, decode_pair

# Ensure the project root is on the import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Provide a minimal stub for the websockets package so dex can be imported
sys.modules.setdefault("websockets", types.ModuleType("websockets"))
# Stub out the exceptions attribute used in dex
sys.modules["websockets"].exceptions = types.SimpleNamespace(ConnectionClosed=Exception)


def test_clean_string_removes_non_printables():
    original = "foo\x00bar\nbaz\tqux\r"
    assert clean_string(original) == "foobarbaz\tqux"


def test_clean_string_truncates_garbage_patterns():
    assert clean_string("hello@world") == "hello"
    assert clean_string("test\\path") == "test"


def test_decode_pair_invalid_length_returns_none():
    # First byte declares a large length but there isn't enough data
    data = b"\xff\x00\x01"
    assert decode_pair(data) is None

    # Declared length exceeds remaining bytes
    data_short = b"\x0ahello"
    assert decode_pair(data_short) is None
