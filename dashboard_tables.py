from functools import partial
import pandas as pd

from utils import OUTPUT_ROOT, load_data, save_table, logger

# Configuration
OUTPUT_DIR = OUTPUT_ROOT / "dashboard_tables"
save = partial(save_table, output_dir=OUTPUT_DIR, decimals=2)


# Metrics
def summarize(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """Total sales, total profit and profit margin (%) for any grouping."""
    out = df.groupby(by, observed=True).agg(
        total_sales=("Sales", "sum"),
        total_profit=("Profit", "sum"),
    )
    out["profit_margin_pct"] = out["total_profit"] / out["total_sales"] * 100
    return out


# Dashboard items
def page_1_overview(df: pd.DataFrame) -> None:
    # KPIs
    kpis = pd.DataFrame({
        "total_sales": [df["Sales"].sum()],
        "total_profit": [df["Profit"].sum()],
        "profit_margin_pct": [df["Profit"].sum() / df["Sales"].sum() * 100],
    })
    save(kpis, "p1_kpis", index=False)

    # Monthly Sales & Profit Trend
    save(summarize(df, "YearMonth"), "p1_monthly_trend")

    # Profit by Region
    save(summarize(df, "Region").sort_values("total_profit", ascending=False), "p1_profit_by_region")


def page_2_products(df: pd.DataFrame) -> None:
    # Sales & Profit by Category
    save(summarize(df, "Category"), "p2_sales_profit_by_category")

    # Profit by Sub-Category
    save(summarize(df, "Sub-Category").sort_values("total_profit"), "p2_profit_by_sub_category")

    # Bottom 10 Products by Profit (one row per product, all segments together)
    bottom10 = summarize(df, "Product Name").nsmallest(10, "total_profit")
    save(bottom10, "p2_bottom_10_products")


def page_3_discounts(df: pd.DataFrame) -> None:
    # Profit Margin by Discount Range and Profit by Discount Range
    save(summarize(df, "Discount Range"), "p3_by_discount_range")


# Main
def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data()
    page_1_overview(df)
    page_2_products(df)
    page_3_discounts(df)

    logger.info("CSV tables saved to: %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()