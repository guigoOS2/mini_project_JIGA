import logging
import sys
from pathlib import Path

import pandas as pd

# Paths (change the folder or file names here and every script follows)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "DATA"
RAW_FILE = DATA_DIR / "sample_-_superstore.csv"
CLEAN_FILE = DATA_DIR / "cleaned_sample_superstore.csv"
OUTPUT_ROOT = BASE_DIR / "output"  # each script saves in its own subfolder
LOG_FILE = OUTPUT_ROOT / "logs" / "pipeline.log"

# Shared analysis settings
HIGH_DISCOUNT = 0.20  # discount above this value is considered "deep"

# Discount ranges follow HIGH_DISCOUNT, so the bands and the "deep discount" flag never disagree
_pct = round(HIGH_DISCOUNT * 100)  # 20
DISCOUNT_BINS = [-0.001, 0, HIGH_DISCOUNT, 2 * HIGH_DISCOUNT, 1.0]
DISCOUNT_LABELS = ["0%", f"1-{_pct}%", f"{_pct + 1}-{2 * _pct}%", f">{2 * _pct}%"]


# Logging
def setup_logger() -> logging.Logger:
    """One shared logger: INFO and above on the terminal, everything in the log file."""
    logger = logging.getLogger("pipeline")
    if logger.handlers:  # already configured
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # avoids duplicate lines if another library configures the root logger
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(module)-18s | %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


logger = setup_logger()


def _log_uncaught(exc_type, exc_value, exc_tb) -> None:
    """Send crashes to the log too (terminal and file), not only to the terminal."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logger.critical("Uncaught exception in %s", Path(sys.argv[0]).name, exc_info=(exc_type, exc_value, exc_tb))


sys.excepthook = _log_uncaught


# Loading
def load_data() -> pd.DataFrame:
    """Load the cleaned dataset and add the columns used by more than one script."""
    if not CLEAN_FILE.exists():
        raise FileNotFoundError(f"Put '{CLEAN_FILE.name}' in: {DATA_DIR}")

    logger.info("Loading data: %s", CLEAN_FILE)
    df = pd.read_csv(CLEAN_FILE, parse_dates=["Order Date", "Ship Date"])

    # derived columns created from existing columns
    df["Year"] = df["Order Date"].dt.year
    df["Quarter"] = df["Order Date"].dt.to_period("Q").astype(str)
    df["YearMonth"] = df["Order Date"].dt.to_period("M").astype(str)
    df["Ship Days"] = (df["Ship Date"] - df["Order Date"]).dt.days
    df["Discount Range"] = pd.cut(df["Discount"], bins=DISCOUNT_BINS, labels=DISCOUNT_LABELS)
    return df


# Saving
def save_table(
    table: pd.DataFrame,
    name: str,
    output_dir: Path,
    index: bool = True,
    decimals: int = None,
) -> None:
    """Save a table as <output_dir>/<name>.csv (creates the folder if needed)."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if decimals is not None:
        table = table.round(decimals)
    table.to_csv(output_dir / f"{name}.csv", index=index)


# Formatting
def money(value: float, decimals: int = 0) -> str:
    """Short money format: $1,234 or $12K (negative values keep the sign)."""
    sign = "-" if value < 0 else ""
    v = abs(value)
    if v >= 1000:
        return f"{sign}${v / 1000:,.{decimals}f}K"
    return f"{sign}${v:,.0f}"