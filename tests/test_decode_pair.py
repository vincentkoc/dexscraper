from dexscraper.protocol import clean_string, decode_pair


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
