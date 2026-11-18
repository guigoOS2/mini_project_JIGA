import pandas as pd
import pytest

import utils
from utils import DISCOUNT_LABELS, HIGH_DISCOUNT, load_data, money, save_table


def test_money_format():
    assert money(1234) == "$1K"
    assert money(-25700, 1) == "-$25.7K"
    assert money(500) == "$500"


def test_save_table_creates_folder_and_rounds(tmp_path):
    folder = tmp_path / "new_folder"
    save_table(pd.DataFrame({"a": [1.23456]}), "t", folder, index=False, decimals=2)
    assert (folder / "t.csv").read_text().split() == ["a", "1.23"]


def test_load_data_adds_derived_columns(tmp_path, monkeypatch):
    csv = tmp_path / "clean.csv"
    pd.DataFrame({
        "Order Date": ["2024-02-10"],
        "Ship Date": ["2024-02-14"],
        "Discount": [HIGH_DISCOUNT + 0.05],
    }).to_csv(csv, index=False)
    monkeypatch.setattr(utils, "CLEAN_FILE", csv)

    df = load_data()

    assert df.loc[0, "Year"] == 2024
    assert df.loc[0, "Quarter"] == "2024Q1"
    assert df.loc[0, "YearMonth"] == "2024-02"
    assert df.loc[0, "Ship Days"] == 4
    assert df.loc[0, "Discount Range"] == DISCOUNT_LABELS[2]


def test_load_data_fails_clearly_when_file_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "CLEAN_FILE", tmp_path / "nope.csv")
    with pytest.raises(FileNotFoundError):
        load_data()