import pandas as pd

from src.utils import CLEAN_FILE, DATA_DIR, RAW_FILE, logger

# Configuration
DATE_COLUMNS = ["Order Date", "Ship Date"]

REQUIRED_COLUMNS = [
    "Order ID", "Order Date", "Ship Date", "Ship Mode", "Segment",
    "Country/Region", "State/Province", "Region", "Category", "Sub-Category",
    "Product Name", "Sales", "Quantity", "Discount", "Profit",
]


# Loading
def load_raw_data() -> pd.DataFrame:
    if not RAW_FILE.exists():
        raise FileNotFoundError(f"Put '{RAW_FILE.name}' in: {DATA_DIR}")

    logger.info("Loading raw data: %s", RAW_FILE)
    # Postal Code as text to keep leading zeros and Canadian codes (e.g. M5V)
    df = pd.read_csv(RAW_FILE, dtype={"Postal Code": str})
    validate_columns(df)
    return df


def validate_columns(df: pd.DataFrame) -> None:
    """Stop early, with a clear message, if the raw CSV is missing a required column."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Raw CSV is missing required column(s): {', '.join(missing)}")
    logger.info("Schema check passed: all %d required columns found", len(REQUIRED_COLUMNS))


# Data quality
def quality_check(df: pd.DataFrame, title: str = "") -> dict:
    """Print and return a basic data-quality summary."""
    missing = df.isna().sum()
    missing = missing[missing > 0]
    duplicate_count = int(df.duplicated().sum())
    dtypes = df.dtypes.astype(str)
    issues = []

    if missing.empty:
        issues.append("No missing values detected.")
    else:
        issues.append("Missing values detected: " + ", ".join(
            f"{column} ({count})" for column, count in missing.items()
        ))

    if duplicate_count == 0:
        issues.append("No duplicate rows detected.")
    else:
        issues.append(f"{duplicate_count} duplicate rows detected.")

    date_columns = [
        column for column in df.columns
        if column.endswith("Date") and not pd.api.types.is_datetime64_any_dtype(df[column])
    ]
    if date_columns:
        issues.append("Date columns require conversion: " + ", ".join(date_columns))

    summary = {
        "rows": len(df),
        "columns": len(df.columns),
        "missing": missing.to_dict(),
        "duplicates": duplicate_count,
        "dtypes": dtypes.to_dict(),
        "issues": issues,
    }

    logger.info("Data quality summary %s", title)
    logger.info("Rows: %s | Columns: %s", summary["rows"], summary["columns"])
    logger.debug("Data types:\n%s", dtypes.to_string())
    for issue in issues:
        log = logger.info if issue.startswith("No ") else logger.warning
        log(issue)

    return summary


# Cleaning
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the DataFrame by performing the following operations:
    - Drop rows with missing values
    - Convert date columns to datetime format
    - Remove duplicates
    - Remove leading and trailing whitespace from string columns
    - Remove rows with negative sales or quantity
    """
    # Drop rows with missing values
    df = df.dropna().copy()

    # Convert date columns to datetime format
    for col in DATE_COLUMNS:
        df[col] = pd.to_datetime(df[col])

    # Remove any leading or trailing whitespace from string columns
    str_cols = [col for col in df.columns if pd.api.types.is_string_dtype(df[col])]
    for col in str_cols:
        df[col] = df[col].str.strip()

    # Remove duplicates
    df = df.drop_duplicates()

    # Remove any rows with negative sales or quantity
    df = df[(df["Sales"] >= 0) & (df["Quantity"] >= 0)]

    return df.copy()


# Derived columns
def add_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Create new columns from existing ones."""
    # Product Cost = Sales - Profit
    df["Product Cost"] = df["Sales"] - df["Profit"]
    return df


# Saving
def save_data(df: pd.DataFrame) -> None:
    df.to_csv(CLEAN_FILE, index=False)
    logger.info("Cleaned data saved to: %s", CLEAN_FILE)


# Main
def main() -> None:
    df = load_raw_data()
    quality_check(df, "(before cleaning)")

    df = clean_data(df)
    df = add_columns(df)
    quality_check(df, "(after cleaning)")

    save_data(df)


if __name__ == "__main__":
    main()