from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Configuration
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "DATA"
DATA_FILE = DATA_DIR / "cleaned_sample_superstore.csv"
OUTPUT_DIR = BASE_DIR / "output" / "loss_drivers"

HIGH_DISCOUNT = 0.20    # discount above this value is considered "deep"
N_DRIVERS = 3           # how many drivers to report
COVERAGE = 0.60         # "hot" groups = fewest groups that cover 60% of the gross loss
N_BOOT = 2000           # bootstrap resamples
SEED = 42
MIN_ROWS = 100          # groups with fewer rows are flagged as unreliable
CAP_VOLUME_LOSS = [0.0, 0.25, 0.50, 0.75, 1.0]   # scenario: share of deep-discount sales lost
THRESHOLDS = [0.0, 0.10, 0.20, 0.30, 0.40, 0.50]  # sensitivity of the "deep discount" cut

HOT_COLOR = "#c0392b"
OTHER_COLOR = "#b0b7c0"

# Dimensions screened as possible loss drivers.
# High-cardinality identifiers (customer, product name) are left out on purpose.
CANDIDATES = {
    "Discount Band": "DiscountBand",
    "Sub-Category": "Sub-Category",
    "State/Province": "State/Province",
    "Region": "Region",
    "Category": "Category",
    "Segment": "Segment",
    "Ship Mode": "Ship Mode",
    "Country/Region": "Country/Region",
    "Year": "Year",
}


# Loading
def load_data() -> pd.DataFrame:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Put '{DATA_FILE.name}' in: {DATA_DIR}")

    print(f"Loading data: {DATA_FILE}")
    df = pd.read_csv(DATA_FILE, parse_dates=["Order Date", "Ship Date"])

    # derived columns created from existing columns
    df["Year"] = df["Order Date"].dt.year
    df["is_loss"] = df["Profit"] < 0
    df["loss"] = df["Profit"].clip(upper=0)  # negative profit only (0 for profitable rows)
    df["deep_discount"] = df["Discount"] > HIGH_DISCOUNT
    df["DiscountBand"] = pd.cut(
        df["Discount"],
        bins=[-0.001, 0, 0.2, 0.4, 1.0],
        labels=["0%", "1-20%", "21-40%", ">40%"],
    )
    return df


def save(table: pd.DataFrame, name: str, index: bool = True) -> None:
    table.to_csv(OUTPUT_DIR / f"{name}.csv", index=index)


# Metrics
def loss_overview(df: pd.DataFrame) -> pd.Series:
    """Size of the problem: gross gains vs gross losses."""
    gross_gain = df.loc[df["Profit"] > 0, "Profit"].sum()
    gross_loss = df["loss"].sum()
    summary = pd.Series({
        "rows": len(df),
        "orders": df["Order ID"].nunique(),
        "net_profit": df["Profit"].sum(),
        "gross_gain": gross_gain,
        "gross_loss": gross_loss,
        "loss_to_gain_pct": -gross_loss / gross_gain * 100,
        "loss_rows": int(df["is_loss"].sum()),
        "loss_rows_pct": df["is_loss"].mean() * 100,
    })
    save(summary.to_frame("value"), "tbl_01_loss_overview")
    return summary


def group_table(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Loss metrics for every group of a dimension (most negative gross loss first)."""
    g = df.groupby(col, observed=True)
    t = g.agg(
        rows=("Order ID", "size"),
        sales=("Sales", "sum"),
        profit=("Profit", "sum"),
        gross_loss=("loss", "sum"),
        loss_rows=("is_loss", "sum"),
    )
    t["row_share_pct"] = t["rows"] / t["rows"].sum() * 100
    t["loss_share_pct"] = t["gross_loss"] / t["gross_loss"].sum() * 100
    t["loss_rate_pct"] = t["loss_rows"] / t["rows"] * 100
    t["margin_pct"] = t["profit"] / t["sales"] * 100
    t["lift"] = t["loss_share_pct"] / t["row_share_pct"]  # >1 = over-represented in losses
    t["small_sample"] = t["rows"] < MIN_ROWS
    return t.sort_values("gross_loss")


def adjusted_eta_squared(df: pd.DataFrame, col: str) -> tuple:
    """Share of the variation in row-level loss explained by a dimension.

    Adjusted for the number of groups, so dimensions with many groups
    (e.g. State) are not favored. Used only to RANK dimensions.
    """
    g = df.groupby(col, observed=True)["loss"]
    ss_between = (g.count() * (g.mean() - df["loss"].mean()) ** 2).sum()
    ss_total = ((df["loss"] - df["loss"].mean()) ** 2).sum()
    n, k = len(df), g.ngroups
    eta2 = ss_between / ss_total
    return k, eta2, 1 - (1 - eta2) * (n - 1) / (n - k)


def screen_dimensions(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, col in CANDIDATES.items():
        k, eta2, adj = adjusted_eta_squared(df, col)
        rows.append({"dimension": name, "groups": k, "eta2": eta2, "adj_eta2": adj})
    ranking = pd.DataFrame(rows).set_index("dimension").sort_values("adj_eta2", ascending=False)
    save(ranking, "tbl_02_dimension_screening")
    return ranking


# Drivers
def hot_groups(table: pd.DataFrame) -> list:
    """Fewest groups that together cover COVERAGE of the gross loss."""
    cum = table["loss_share_pct"].cumsum()
    n = int((cum < COVERAGE * 100).sum()) + 1
    return list(table.index[:n])


def build_drivers(df: pd.DataFrame, ranking: pd.DataFrame) -> list:
    """Top N dimensions from the screening, each turned into a row-level flag."""
    drivers = []
    for dim in ranking.index[:N_DRIVERS]:
        col = CANDIDATES[dim]
        table = group_table(df, col)
        save(table, f"tbl_03_groups_{dim.lower().replace('/', '_').replace(' ', '_')}")

        if dim == "Discount Band":
            label = f"Deep discount (>{HIGH_DISCOUNT:.0%})"
            short = "Discount"
            mask = df["deep_discount"]
            groups = None
        else:
            groups = hot_groups(table)
            label = f"{dim}: {', '.join(map(str, groups))}"
            short = dim
            mask = df[col].isin(groups)

        drivers.append({
            "dimension": dim, "column": col, "label": label,
            "short": short, "mask": mask, "groups": groups, "table": table,
        })
    return drivers


def overlap_table(df: pd.DataFrame, drivers: list) -> pd.DataFrame:
    """Gross loss split by which drivers each row is hit by (drivers overlap)."""
    flags = pd.DataFrame({d["short"]: d["mask"] for d in drivers})
    combo = flags.apply(
        lambda r: " + ".join(c for c in flags.columns if r[c]) or "None of the drivers", axis=1
    )
    t = df.groupby(combo).agg(rows=("Order ID", "size"), gross_loss=("loss", "sum"))
    t["loss_share_pct"] = t["gross_loss"] / df["loss"].sum() * 100
    t = t.sort_values("gross_loss")
    save(t, "tbl_04_driver_overlap")
    return t


def independence_check(df: pd.DataFrame, drivers: list) -> pd.DataFrame:
    """Do product / geography losses exist without deep discounts, or are they a channel for them?"""
    deep = df["deep_discount"]
    rows = []
    for d in drivers:
        if d["dimension"] == "Discount Band":
            continue
        m = d["mask"]
        rows.append({
            "driver": d["label"],
            "deep_discount_rows_in_group_pct": deep[m].mean() * 100,
            "deep_discount_rows_elsewhere_pct": deep[~m].mean() * 100,
            "group_loss_on_deep_discount_pct": df.loc[m & deep, "loss"].sum() / df.loc[m, "loss"].sum() * 100,
            "loss_rate_in_group_no_deep_pct": df.loc[m & ~deep, "is_loss"].mean() * 100,
            "loss_rate_elsewhere_no_deep_pct": df.loc[~m & ~deep, "is_loss"].mean() * 100,
            "rows_in_group_no_deep": int((m & ~deep).sum()),
        })
    t = pd.DataFrame(rows).set_index("driver")
    save(t, "tbl_05_independence_check")
    return t


# Uncertainty
def bootstrap_drivers(df: pd.DataFrame, drivers: list) -> pd.DataFrame:
    """95% intervals using a cluster bootstrap by Order ID.

    Rows of the same order are not independent (about 2 rows per order),
    so whole orders are resampled instead of single rows.
    """
    rng = np.random.default_rng(SEED)
    is_loss = df["is_loss"].to_numpy()
    results = []

    for d in drivers:
        m = d["mask"].to_numpy()
        per_row = pd.DataFrame({
            "order": df["Order ID"].to_numpy(),
            "loss_total": df["loss"].to_numpy(),
            "loss_hot": np.where(m, df["loss"].to_numpy(), 0.0),
            "rows_hot": m.astype(float),
            "lossrows_hot": (m & is_loss).astype(float),
            "rows_rest": (~m).astype(float),
            "lossrows_rest": (~m & is_loss).astype(float),
        })
        arr = per_row.groupby("order").sum().to_numpy()
        n = len(arr)

        def stats(s):
            rate_hot = s[3] / s[2] * 100
            rate_rest = s[5] / s[4] * 100
            return np.array([s[1] / s[0] * 100, rate_hot, rate_rest, rate_hot - rate_rest])

        point = stats(arr.sum(axis=0))
        boots = np.empty((N_BOOT, 4))
        for b in range(N_BOOT):
            boots[b] = stats(arr[rng.integers(0, n, n)].sum(axis=0))
        lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)

        results.append({
            "driver": d["label"],
            "row_share_pct": m.mean() * 100,
            "loss_share_pct": point[0], "loss_share_lo": lo[0], "loss_share_hi": hi[0],
            "loss_share_ci_width_pts": hi[0] - lo[0],
            "loss_rate_group_pct": point[1], "loss_rate_elsewhere_pct": point[2],
            "loss_rate_gap_pts": point[3], "gap_lo": lo[3], "gap_hi": hi[3],
        })

    t = pd.DataFrame(results).set_index("driver")
    save(t, "tbl_06_driver_bootstrap_ci")
    return t


def threshold_sensitivity(df: pd.DataFrame) -> pd.DataFrame:
    """Does the conclusion depend on where 'deep discount' starts?"""
    rows = []
    for t in THRESHOLDS:
        m = df["Discount"] > t
        rows.append({
            "discount_above": t,
            "rows_pct": m.mean() * 100,
            "loss_share_pct": df.loc[m, "loss"].sum() / df["loss"].sum() * 100,
            "loss_rate_pct": df.loc[m, "is_loss"].mean() * 100,
            "margin_pct": df.loc[m, "Profit"].sum() / df.loc[m, "Sales"].sum() * 100,
        })
    t = pd.DataFrame(rows).set_index("discount_above")
    save(t, "tbl_07_threshold_sensitivity")
    return t


def discount_cap_scenario(df: pd.DataFrame) -> pd.DataFrame:
    """Illustrative range: profit if discounts were capped at HIGH_DISCOUNT.

    Sales = list price x quantity x (1 - discount), so capping the discount
    raises the price. Cost is kept fixed. The unknown is how much volume is lost.
    """
    deep = df["deep_discount"]
    sales_capped = np.where(
        deep, df["Sales"] * (1 - HIGH_DISCOUNT) / (1 - df["Discount"]), df["Sales"]
    )
    profit_capped = pd.Series(sales_capped - df["Product Cost"].to_numpy(), index=df.index)

    base = df["Profit"].sum()
    rest = df.loc[~deep, "Profit"].sum()
    deep_capped = profit_capped[deep].sum()

    rows = [{"scenario": "Current", "volume_lost_pct": 0, "profit": base, "gain": 0.0}]
    for v in CAP_VOLUME_LOSS:
        p = rest + (1 - v) * deep_capped
        rows.append({
            "scenario": f"Cap at {HIGH_DISCOUNT:.0%}, {v:.0%} of deep-discount sales lost",
            "volume_lost_pct": v * 100, "profit": p, "gain": p - base,
        })
    t = pd.DataFrame(rows).set_index("scenario")
    save(t, "tbl_08_discount_cap_scenarios")
    return t


# Graphs
def plot_screening(ranking: pd.DataFrame) -> None:
    r = ranking.iloc[::-1]
    colors = [HOT_COLOR if i >= len(r) - N_DRIVERS else OTHER_COLOR for i in range(len(r))]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.barh(r.index, r["adj_eta2"] * 100, color=colors)
    ax.set_xlabel("Variation in row-level loss explained (%, adjusted)")
    ax.set_title("Which dimensions separate losses best?")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_01_dimension_screening.png", dpi=130)
    plt.close(fig)


def plot_discount_bands(df: pd.DataFrame) -> None:
    t = group_table(df, "DiscountBand").reindex(["0%", "1-20%", "21-40%", ">40%"])
    x = np.arange(len(t))
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(x - 0.2, t["row_share_pct"], width=0.4, label="% of rows", color=OTHER_COLOR)
    ax.bar(x + 0.2, t["loss_share_pct"], width=0.4, label="% of gross loss", color=HOT_COLOR)
    for i, (_, r) in enumerate(t.iterrows()):
        ax.text(i + 0.2, r["loss_share_pct"] + 1, f"margin {r['margin_pct']:.0f}%", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(t.index)
    ax.set_ylim(0, max(t["row_share_pct"].max(), t["loss_share_pct"].max()) * 1.12)
    ax.set_xlabel("Discount band")
    ax.set_ylabel("%")
    ax.set_title("Deep discounts: small share of rows, most of the loss")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_02_discount_bands.png", dpi=130)
    plt.close(fig)


def plot_pareto(driver: dict, fname: str, top: int = 15) -> None:
    table = driver["table"]
    cum = table["loss_share_pct"].cumsum()
    t = table.head(top)
    hot = set(driver["groups"])
    colors = [HOT_COLOR if g in hot else OTHER_COLOR for g in t.index]

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.bar(range(len(t)), -t["gross_loss"], color=colors)
    ax.set_xticks(range(len(t)))
    ax.set_xticklabels(t.index, rotation=60, ha="right")
    ax.set_ylabel("Gross loss ($)")
    ax2 = ax.twinx()
    ax2.plot(range(len(t)), cum.head(top), color="black", marker="o", markersize=3)
    ax2.axhline(COVERAGE * 100, color="gray", linestyle="--", linewidth=1)
    ax2.set_ylabel("Cumulative % of gross loss")
    ax2.set_ylim(0, 105)
    ax.set_title(f"Gross loss by {driver['dimension']} (red = groups covering {COVERAGE:.0%} of the loss)")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / fname, dpi=130)
    plt.close(fig)


def plot_overlap(overlap: pd.DataFrame) -> None:
    t = overlap.copy()
    fig, ax = plt.subplots(figsize=(10, 4.5))
    y = np.arange(len(t))[::-1]
    ax.barh(y, -t["gross_loss"], color=HOT_COLOR)
    ax.set_yticks(y)
    ax.set_yticklabels(t.index)
    for yi, (_, r) in zip(y, t.iterrows()):
        ax.text(-r["gross_loss"], yi, f"  {r['loss_share_pct']:.1f}%", va="center", fontsize=8)
    ax.set_xlim(0, -t["gross_loss"].min() * 1.12)
    ax.set_xlabel("Gross loss ($)")
    ax.set_title("Drivers overlap: gross loss by combination of drivers")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_05_driver_overlap.png", dpi=130)
    plt.close(fig)


def plot_ci(ci: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 3.8))
    y = np.arange(len(ci))[::-1]
    err = [ci["loss_share_pct"] - ci["loss_share_lo"], ci["loss_share_hi"] - ci["loss_share_pct"]]
    ax.errorbar(ci["loss_share_pct"], y, xerr=err, fmt="o", color=HOT_COLOR, capsize=4, label="% of gross loss (95% CI)")
    ax.scatter(ci["row_share_pct"], y, marker="s", color="black", label="% of rows")
    ax.set_yticks(y)
    ax.set_yticklabels(ci.index)
    ax.set_xlim(0, 100)
    ax.set_xlabel("%")
    ax.set_title("Share of gross loss vs share of rows (cluster bootstrap by order)")
    ax.set_ylim(-0.6, len(ci) - 0.4)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_06_driver_shares_ci.png", dpi=130)
    plt.close(fig)


def plot_scenarios(scen: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.5))
    labels = ["Current"] + [f"{v:.0%} lost" for v in CAP_VOLUME_LOSS]
    colors = [OTHER_COLOR] + ["seagreen"] * len(CAP_VOLUME_LOSS)
    ax.bar(labels, scen["profit"], color=colors)
    for i, p in enumerate(scen["profit"]):
        ax.text(i, p + scen["profit"].max() * 0.01, f"{p:,.0f}", ha="center", fontsize=8)
    ax.set_xlabel(f"Cap discounts at {HIGH_DISCOUNT:.0%}: share of deep-discount sales lost")
    ax.set_ylabel("Total profit ($)")
    ax.set_title("Illustrative range, not a forecast")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_07_discount_cap_scenarios.png", dpi=130)
    plt.close(fig)


# Main
def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data()
    overview = loss_overview(df)
    ranking = screen_dimensions(df)
    drivers = build_drivers(df, ranking)
    overlap = overlap_table(df, drivers)
    indep = independence_check(df, drivers)
    ci = bootstrap_drivers(df, drivers)
    sens = threshold_sensitivity(df)
    scen = discount_cap_scenario(df)

    plot_screening(ranking)
    plot_discount_bands(df)
    pareto_n = 3
    for d in drivers:
        if d["groups"] is not None:
            plot_pareto(d, f"fig_0{pareto_n}_pareto_{d['column'].lower().replace('/', '_').replace('-', '_')}.png")
            pareto_n += 1
    plot_overlap(overlap)
    plot_ci(ci)
    plot_scenarios(scen)

    print(f"\nGraphs and CSV tables saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()