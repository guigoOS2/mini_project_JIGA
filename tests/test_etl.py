import pandas as pd
import pytest

import etl
from etl import REQUIRED_COLUMNS, add_columns, clean_data, validate_columns


def make_raw() -> pd.DataFrame:
    """Five raw rows: A-1 twice (duplicate), A-2 (ok), A-3 (negative sales), A-4 (missing segment)."""
    return pd.DataFrame({
        "Order ID": ["A-1", "A-1", "A-2", "A-3", "A-4"],
        "Order Date": ["2024-01-01"] * 5,
        "Ship Date": ["2024-01-03"] * 5,
        "Segment": [" Consumer ", " Consumer ", "Corporate", "Corporate", None],
        "Sales": [100.0, 100.0, 50.0, -5.0, 10.0],
        "Quantity": [1, 1, 2, 1, 1],
        "Profit": [20.0, 20.0, -5.0, 1.0, 2.0],
    })


# clean_data
def test_clean_data_drops_duplicates_negative_sales_and_missing_values():
    clean = clean_data(make_raw())
    assert list(clean["Order ID"]) == ["A-1", "A-2"]


def test_clean_data_strips_whitespace():
    clean = clean_data(make_raw())
    assert list(clean["Segment"]) == ["Consumer", "Corporate"]


def test_clean_data_converts_dates():
    clean = clean_data(make_raw())
    assert pd.api.types.is_datetime64_any_dtype(clean["Order Date"])
    assert pd.api.types.is_datetime64_any_dtype(clean["Ship Date"])


def test_clean_data_keeps_negative_profit():
    # losses are what we analyse: only negative sales/quantity are removed
    clean = clean_data(make_raw())
    assert (clean["Profit"] < 0).any()


# add_columns
def test_product_cost_is_sales_minus_profit():
    df = pd.DataFrame({"Sales": [100.0, 50.0], "Profit": [30.0, -10.0]})
    assert list(add_columns(df)["Product Cost"]) == [70.0, 60.0]


# schema validation (T20)
def test_validate_columns_accepts_complete_file():
    validate_columns(pd.DataFrame(columns=REQUIRED_COLUMNS))  # no error


def test_validate_columns_lists_the_missing_columns():
    columns = [c for c in REQUIRED_COLUMNS if c not in ("Sales", "Profit")]
    with pytest.raises(ValueError) as error:
        validate_columns(pd.DataFrame(columns=columns))
    assert "Sales" in str(error.value)
    assert "Profit" in str(error.value)


def test_load_raw_data_rejects_file_without_required_columns(tmp_path, monkeypatch):
    bad_file = tmp_path / "raw.csv"
    pd.DataFrame({"Order ID": ["A-1"], "Sales": [10.0]}).to_csv(bad_file, index=False)
    monkeypatch.setattr(etl, "RAW_FILE", bad_file)

    with pytest.raises(ValueError, match="missing required"):
        etl.load_raw_data()