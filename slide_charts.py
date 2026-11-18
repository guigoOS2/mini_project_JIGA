import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter

from utils import HIGH_DISCOUNT, OUTPUT_ROOT, load_data, money

# Configuration
OUTPUT_DIR = OUTPUT_ROOT / "slides_charts"

N_STATES = 10            # how many lowest-profit states to show
FIG_SIZE = (13.33, 7.5)  # 16:9, same proportion as a slide
DPI = 200

POSITIVE = "#2a6f97"
NEGATIVE = "#c0392b"
TEXT = "#222222"
MUTED = "#666666"

plt.rcParams.update({
    "font.size": 14,
    "axes.labelsize": 15,
    "xtick.labelsize": 14,
    "ytick.labelsize": 13,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


# Helpers
def join_names(names: list) -> str:
    names = list(names)
    if len(names) <= 2:
        return " and ".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def bar_colors(values) -> list:
    return [NEGATIVE if v < 0 else POSITIVE for v in values]


def new_figure():
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    fig.subplots_adjust(left=0.14, right=0.64, top=0.82, bottom=0.20)
    return fig, ax


def finish(fig, title, subtitle, explanation, source, filename) -> None:
    """Title and units on top, explanation box on the right, source at the bottom."""
    fig.text(0.05, 0.95, title, fontsize=26, fontweight="bold", color=TEXT, va="top")
    fig.text(0.05, 0.89, subtitle, fontsize=15, color=MUTED, va="top")

    fig.add_artist(FancyBboxPatch(
        (0.68, 0.20), 0.30, 0.62, transform=fig.transFigure,
        boxstyle="round,pad=0.005,rounding_size=0.01",
        facecolor="#f2f4f7", edgecolor="none",
    ))
    fig.text(0.70, 0.79, "What this shows", fontsize=16, fontweight="bold", color=TEXT, va="top")
    fig.text(0.70, 0.73, textwrap.fill(explanation, 31), fontsize=15, color=TEXT,
             va="top", linespacing=1.45)

    fig.text(0.05, 0.03, source, fontsize=11, color=MUTED, va="bottom")
    fig.savefig(OUTPUT_DIR / filename, dpi=DPI, facecolor="white")
    plt.close(fig)


def horizontal_bars(ax, labels, values) -> None:
    """Bars listed top to bottom in the given order, with value labels."""
    bars = ax.barh(labels, values, color=bar_colors(values))
    ax.invert_yaxis()
    ax.axvline(0, color=TEXT, linewidth=1)
    ax.bar_label(bars, labels=[money(v, 1) for v in values], padding=4, fontsize=13)
    ax.margins(x=0.15)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: money(v)))
    ax.xaxis.grid(True, color="#dddddd")
    ax.set_axisbelow(True)


# Charts
def chart_discount_margin(df: pd.DataFrame, source: str) -> None:
    g = df.groupby("Discount Range", observed=True).agg(
        sales=("Sales", "sum"), profit=("Profit", "sum"), lines=("Sales", "size")
    )
    g["margin"] = g["profit"] / g["sales"] * 100

    deep = df[df["Discount"] > HIGH_DISCOUNT]
    deep_margin = deep["Profit"].sum() / deep["Sales"].sum() * 100
    deep_result = "a loss" if deep["Profit"].sum() < 0 else "a profit"
    explanation = (
        f"Each bar is the profit margin (profit divided by sales) of the order lines in that "
        f"discount range. Lines with no discount earn {g['margin'].iloc[0]:.1f}%. Lines with "
        f"a discount above {HIGH_DISCOUNT:.0%} earn {deep_margin:.1f}% together: {deep_result} of "
        f"{money(abs(deep['Profit'].sum()))} on {len(deep) / len(df):.0%} of the lines."
    )

    fig, ax = new_figure()
    bars = ax.bar(g.index.astype(str), g["margin"], color=bar_colors(g["margin"]), width=0.6)
    ax.axhline(0, color=TEXT, linewidth=1)
    ax.bar_label(bars, labels=[f"{v:.1f}%" for v in g["margin"]], padding=4, fontsize=15, fontweight="bold")
    ax.set_xticks(range(len(g)))
    ax.set_xticklabels([f"{r}\n{n:,} lines" for r, n in zip(g.index, g["lines"])])
    ax.set_xlabel("Discount range (% off list price)")
    ax.set_ylabel("Profit margin (% of sales)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.yaxis.grid(True, color="#dddddd")
    ax.set_axisbelow(True)
    ax.margins(y=0.15)

    finish(fig, "Profit margin by discount range",
           "Profit margin (% of sales), all order lines",
           explanation, source, "chart_01_discount_margin.png")


def chart_sub_category_profit(df: pd.DataFrame, source: str) -> None:
    profit = df.groupby("Sub-Category")["Profit"].sum().sort_values(ascending=False)
    negative = profit[profit < 0].sort_values()
    explanation = (
        f"Total profit of each sub-category, all years, regions and segments together. "
        f"{len(negative)} of {len(profit)} sub-categories lose money overall: "
        f"{join_names(negative.index)} ({money(negative.sum())} combined). "
        f"{profit.index[0]} is the most profitable ({money(profit.iloc[0])})."
    )

    fig, ax = new_figure()
    horizontal_bars(ax, profit.index, profit.values)
    ax.set_xlabel("Total profit ($, K = thousand)")

    finish(fig, "Total profit by sub-category",
           "Total profit in US dollars, sorted from highest to lowest",
           explanation, source, "chart_02_profit_by_sub_category.png")


def chart_state_profit(df: pd.DataFrame, source: str) -> None:
    profit = df.groupby("State/Province")["Profit"].sum().sort_values()
    negative = profit[profit < 0]
    lowest = profit.head(N_STATES)
    explanation = (
        f"Total profit of the {N_STATES} lowest-profit states or provinces, all years together. "
        f"{len(negative)} of {len(profit)} have negative total profit, adding up to "
        f"{money(negative.sum())}. The lowest is {lowest.index[0]} ({money(lowest.iloc[0])})."
    )

    fig, ax = new_figure()
    horizontal_bars(ax, lowest.index, lowest.values)
    ax.set_xlabel("Total profit ($, K = thousand)")

    finish(fig, f"The {N_STATES} lowest-profit states",
           "Total profit in US dollars, sorted from lowest to highest",
           explanation, source, "chart_03_lowest_profit_states.png")


# Main
def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data()
    source = (
        f"Source: cleaned Sample Superstore data, orders from "
        f"{df['Order Date'].min():%b %Y} to {df['Order Date'].max():%b %Y}."
    )

    chart_discount_margin(df, source)
    chart_sub_category_profit(df, source)
    chart_state_profit(df, source)

    print(f"\nSlide charts saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()