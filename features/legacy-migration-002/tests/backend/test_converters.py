"""R1 / R2 — exact money->cents and ownership->per-mille conversion.

This is the highest-value test surface: a weak test here is worse than none.
The float-artifact values (832.06, 5293.11, ...) are the point — a naive
int(value * 100) truncates them to the wrong cent.
"""
import pytest

from app.legacy_import import to_cents, to_permille


@pytest.mark.parametrize(
    "dollars,cents",
    [
        (0.0, 0),
        (371.4, 37140),
        (625.44, 62544),
        (3981.85, 398185),
        (122489.78, 12248978),
        (832.06, 83206),    # 832.06 * 100 == 83205.99999999999 in binary float
        (5293.11, 529311),
        (5954.75, 595475),
        (5700.27, 570027),
        (26.00, 2600),
        (18000.00, 1800000),
    ],
)
def test_to_cents_exact(dollars, cents):
    assert to_cents(dollars) == cents


def test_to_cents_none_passthrough():
    assert to_cents(None) is None


def test_to_cents_negative_preserves_sign():
    assert to_cents(-50.25) == -5025
    assert to_cents(-0.01) == -1


def test_to_cents_returns_int():
    result = to_cents(100.0)
    assert isinstance(result, int) and not isinstance(result, bool)


@pytest.mark.parametrize(
    "fraction,permille",
    [(0.117, 117), (0.104, 104), (0.112, 112), (0.1, 100), (0.999, 999)],
)
def test_to_permille_exact(fraction, permille):
    assert to_permille(fraction) == permille


def test_to_permille_within_schema_bound():
    # new schema requires 0 < pct <= 1000
    for fraction in (0.117, 0.104, 0.112):
        pct = to_permille(fraction)
        assert 0 < pct <= 1000
