import pandas as pd
import pytest

import src.dashboard_tables as dashboard_tables
import src.profit_by_segment as profit_by_segment
from src.utils import DISCOUNT_BINS, DISCOUNT_LABELS, HIGH_DISCOUNT


def discount_range(discount: float) -> str:
    return pd.cut(pd.Series([discount]), bins=DISCOUNT_BINS, labels=DISCOUNT_LABELS).iloc[0]


# Profit margin
def make_segments() -> pd.DataFrame:
    return pd.DataFrame({
        "Segment": ["Consumer", "Consumer", "Corporate"],
        "Order ID": ["A", "A", "B"],
        "Quantity": [1, 2, 3],
        "Sales": [100.0, 300.0, 50.0],
        "Profit": [30.0, -30.0, 5.0],
        "Product Cost": [70.0, 330.0, 45.0],
        "Discount": [0.0, 0.5, 0.1],
    })


def test_margin_is_total_profit_over_total_sales():
    out = profit_by_segment.summarize(make_segments(), "Segment")
    # Consumer: (30 - 30) / (100 + 300) = 0%. The average of the row margins (30% and -10%) would be wrong.
    assert out.loc["Consumer", "margin_pct"] == pytest.approx(0.0)
    assert out.loc["Corporate", "margin_pct"] == pytest.approx(10.0)


def test_summarize_counts_orders_and_loss_rows():
    out = profit_by_segment.summarize(make_segments(), "Segment")
    assert out.loc["Consumer", "orders"] == 1  # two rows, same order
    assert out.loc["Consumer", "loss_rows_pct"] == pytest.approx(50.0)
    assert out.loc["Corporate", "loss_rows_pct"] == pytest.approx(0.0)


# Discount ranges
def test_dashboard_table_by_discount_range():
    discounts = [0, HIGH_DISCOUNT / 2, HIGH_DISCOUNT, HIGH_DISCOUNT + 0.1, 0.9]
    df = pd.DataFrame({
        "Discount Range": pd.cut(pd.Series(discounts), bins=DISCOUNT_BINS, labels=DISCOUNT_LABELS),
        "Sales": [100.0] * 5,
        "Profit": [30.0, 10.0, 5.0, -20.0, -60.0],
    })
    out = dashboard_tables.summarize(df, "Discount Range")

    assert list(out.index) == DISCOUNT_LABELS
    assert list(out["total_sales"]) == [100.0, 200.0, 100.0, 100.0]
    assert list(out["total_profit"]) == [30.0, 15.0, -20.0, -60.0]
    assert list(out["profit_margin_pct"]) == pytest.approx([30.0, 7.5, -20.0, -60.0])


def test_no_discount_has_its_own_range():
    assert discount_range(0) == DISCOUNT_LABELS[0]


def test_high_discount_is_the_edge_between_normal_and_deep():
    assert discount_range(HIGH_DISCOUNT) == DISCOUNT_LABELS[1]
    assert discount_range(HIGH_DISCOUNT + 0.01) == DISCOUNT_LABELS[2]


def test_ranges_agree_with_the_deep_discount_flag():
    # protects against HIGH_DISCOUNT and the ranges drifting apart (T16)
    for d in [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.8]:
        in_deep_range = discount_range(d) in DISCOUNT_LABELS[2:]
        assert in_deep_range == (d > HIGH_DISCOUNT)