from functools import partial
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from utils import OUTPUT_ROOT, load_data, save_table, logger

# Configuration
OUTPUT_DIR = OUTPUT_ROOT / "profit_by_segment"
save = partial(save_table, output_dir=OUTPUT_DIR)

SEGMENT = "Segment"

# Dimensions available in the dataset for comparison
DIMENSIONS = {
    "region": "Region",
    "country": "Country/Region",
    "category": "Category",
    "sub_category": "Sub-Category",
    "channel": "Ship Mode",     # (proxy: shipping mode)
}


# Metrics
def summarize(df: pd.DataFrame, by) -> pd.DataFrame:
    """Aggregates the main metrics for any grouping."""
    g = df.groupby(by, observed=True)
    out = g.agg(
        orders=("Order ID", "nunique"),
        quantity=("Quantity", "sum"),
        sales=("Sales", "sum"),
        profit=("Profit", "sum"),
        cost=("Product Cost", "sum"),
        avg_discount=("Discount", "mean"),
    )
    out["margin_pct"] = out["profit"] / out["sales"] * 100
    out["profit_per_order"] = out["profit"] / out["orders"]
    out["loss_rows_pct"] = g["Profit"].apply(lambda s: (s < 0).mean() * 100)
    return out


# Analysis
def overview(df: pd.DataFrame) -> pd.DataFrame:
    seg = summarize(df, SEGMENT).sort_values("profit", ascending=False)
    seg["profit_share_pct"] = seg["profit"] / seg["profit"].sum() * 100
    seg["sales_share_pct"] = seg["sales"] / seg["sales"].sum() * 100
    save(seg, "01_segment_overview")
    return seg


def compare_dimensions(df: pd.DataFrame) -> dict:
    """Segment x (region, country, category, subcategory, channel)."""
    results = {}
    for i, (key, col) in enumerate(DIMENSIONS.items(), start=2):
        table = summarize(df, [SEGMENT, col])
        save(table, f"{i:02d}_segment_by_{key}")

        # matrix of profit margin (%) for quick reading
        margin = table["margin_pct"].unstack(col)
        save(margin, f"{i:02d}_segment_by_{key}_margin_matrix")
        results[key] = (table, margin)
    return results


def time_analysis(df: pd.DataFrame) -> dict:
    """Segment x (year, quarter, month)."""
    yearly = summarize(df, [SEGMENT, "Year"])
    save(yearly, "07_segment_by_year")

    quarterly = summarize(df, [SEGMENT, "Quarter"])
    save(quarterly, "07_segment_by_quarter")

    monthly = summarize(df, [SEGMENT, "YearMonth"])
    save(monthly, "07_segment_by_month")

    # profit growth year by year by segment
    profit_year = yearly["profit"].unstack("Year")
    growth = profit_year.pct_change(axis=1) * 100
    save(growth, "07_segment_profit_yoy_growth")

    return {"monthly": monthly, "yearly": yearly}


def discount_analysis(df: pd.DataFrame) -> None:
    """Discount as a proxy for profit leakage."""

    table = summarize(df, [SEGMENT, "Discount Range"])
    save(table, "08_segment_by_discount_band")


def worst_performers(df: pd.DataFrame, top_n: int = 5) -> None:
    table = summarize(df, [SEGMENT, "Sub-Category"])
    rows = []
    for seg, sub in table.groupby(level=0):
        worst = sub.droplevel(0).nsmallest(top_n, "profit")
        worst.insert(0, SEGMENT, seg)
        rows.append(worst)
    save(pd.concat(rows), "09_worst_subcategories_by_segment")

    products = (
        df.groupby(["Product Name", SEGMENT])
        .agg(sales=("Sales", "sum"), profit=("Profit", "sum"), qty=("Quantity", "sum"))
        .reset_index()
        .nsmallest(10, "profit")
    )
    save(products, "10_worst_products", index=False)


# Graphs
def plot_all(seg: pd.DataFrame, dims: dict, time_res: dict) -> None:
    # 1. Sales, profit and margin by segment
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    seg[["sales", "profit"]].plot.bar(ax=axes[0], rot=0)
    axes[0].set_title("Sales and Profit by Segment")
    axes[0].set_xlabel("")
    seg["margin_pct"].plot.bar(ax=axes[1], rot=0, color="seagreen")
    axes[1].set_title("Margin (%) by Segment")
    axes[1].set_xlabel("")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "01_segment_overview.png", dpi=130)
    plt.close(fig)

    # 2. Profit by segment x each dimension
    for key in ["region", "category", "channel"]:
        table, _ = dims[key]
        col = DIMENSIONS[key]
        pivot = table["profit"].unstack(SEGMENT)
        ax = pivot.plot.bar(figsize=(9, 4.5), rot=0)
        ax.set_title(f"Profit by {col} and Segment")
        ax.set_xlabel("")
        ax.set_ylabel("Profit")
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / f"02_profit_by_{key}.png", dpi=130)
        plt.close()

    # 3. Heatmap of margin: segment x subcategory
    _, margin = dims["sub_category"]
    fig, ax = plt.subplots(figsize=(10, 3.5))
    im = ax.imshow(margin.values, aspect="auto", cmap="RdYlGn")
    ax.set_xticks(range(len(margin.columns)))
    ax.set_xticklabels(margin.columns, rotation=60, ha="right")
    ax.set_yticks(range(len(margin.index)))
    ax.set_yticklabels(margin.index)
    ax.set_title("Margin (%) - Segment x Subcategory")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "03_margin_heatmap_subcategory.png", dpi=130)
    plt.close(fig)

    # 4. Monthly profit by segment
    monthly = time_res["monthly"]["profit"].unstack(SEGMENT)
    ax = monthly.plot(figsize=(11, 4.5))
    ax.set_title("Monthly Profit by Segment")
    ax.set_xlabel("")
    ax.set_ylabel("Profit")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "04_monthly_profit_by_segment.png", dpi=130)
    plt.close()


# Main
def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data()

    seg = overview(df)
    dims = compare_dimensions(df)
    time_res = time_analysis(df)
    discount_analysis(df)
    worst_performers(df)
    plot_all(seg, dims, time_res)

    logger.info("Graphs and CSV tables saved to: %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()