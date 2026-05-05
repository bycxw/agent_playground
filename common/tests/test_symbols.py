import pytest

from common.symbols import Symbol


# ── parse: accepts all 5 formats ─────────────────────────────────────────────

@pytest.mark.parametrize("raw", [
    "600000.SH",
    "sh.600000",
    "SH600000",
    "sh600000",
    "stock_sh_600000",
])
def test_parse_accepts_all_formats(raw: str) -> None:
    s = Symbol.parse(raw)
    assert s.exchange == "SH"
    assert s.code == "600000"


def test_parse_is_case_insensitive_on_exchange() -> None:
    assert Symbol.parse("sh600000") == Symbol.parse("SH600000")
    assert Symbol.parse("SH.600000") == Symbol.parse("sh.600000")


def test_parse_strips_whitespace() -> None:
    assert Symbol.parse("  SH600000  ") == Symbol.parse("SH600000")


# ── render: each format renders correctly ────────────────────────────────────

def test_renderers() -> None:
    s = Symbol.parse("600000.SH")
    assert s.canonical() == "SH600000"
    assert s.baostock()  == "sh.600000"
    assert s.qlib()      == "sh600000"
    assert s.display()   == "600000.SH"
    assert str(s)        == "SH600000"


def test_round_trip_through_every_renderer() -> None:
    s = Symbol(exchange="SZ", code="000001")
    for fmt in (s.canonical(), s.baostock(), s.qlib(), s.display()):
        assert Symbol.parse(fmt) == s


# ── identity: equality and hashing for set/dict use ──────────────────────────

def test_equality_across_formats() -> None:
    a = Symbol.parse("600000.SH")
    b = Symbol.parse("SH600000")
    c = Symbol.parse("stock_sh_600000")
    assert a == b == c


def test_set_dedup_across_formats() -> None:
    a = Symbol.parse("600000.SH")
    b = Symbol.parse("SH600000")
    assert {a, b} == {a}


# ── validation: invalid inputs raise ─────────────────────────────────────────

def test_invalid_exchange_rejected() -> None:
    with pytest.raises(ValueError):
        Symbol(exchange="NYSE", code="600000")


def test_a_share_code_must_be_6_digits() -> None:
    with pytest.raises(ValueError):
        Symbol(exchange="SH", code="60000")    # 5 digits
    with pytest.raises(ValueError):
        Symbol(exchange="SZ", code="0000001")  # 7 digits


def test_unrecognised_format_rejected() -> None:
    with pytest.raises(ValueError):
        Symbol.parse("not a symbol")
    with pytest.raises(ValueError):
        Symbol.parse("AAPL")
    with pytest.raises(ValueError):
        Symbol.parse("600000")  # missing exchange


def test_non_digit_code_rejected() -> None:
    with pytest.raises(ValueError):
        Symbol(exchange="SH", code="60ABCD")


# ── HK: shorter code length tolerated ────────────────────────────────────────

def test_hk_5_digit_code() -> None:
    s = Symbol(exchange="HK", code="00700")
    assert s.canonical() == "HK00700"
    assert Symbol.parse("HK00700") == s


def test_hk_4_digit_code() -> None:
    # baostock uses 5-digit padding but some sources don't; tolerate both
    assert Symbol(exchange="HK", code="0700").canonical() == "HK0700"
