import pandas as pd

df = pd.read_csv('sample_-_superstore.csv')

def quality_check(df):
    """Print and return a basic data-quality summary."""
    missing = df.isna().sum()
    missing = missing[missing > 0]
    duplicate_count = int(df.duplicated().sum())
    dtypes = df.dtypes.astype(str)
    issues = []

    if missing.empty:
        issues.append('No missing values detected.')
    else:
        issues.append('Missing values detected: ' + ', '.join(
            f'{column} ({count})' for column, count in missing.items()
        ))

    if duplicate_count == 0:
        issues.append('No duplicate rows detected.')
    else:
        issues.append(f'{duplicate_count} duplicate rows detected.')

    date_columns = [
        column for column in df.columns
        if column.endswith('Date') and not pd.api.types.is_datetime64_any_dtype(df[column])
    ]
    if date_columns:
        issues.append('Date columns require conversion: ' + ', '.join(date_columns))

    summary = {
        'rows': len(df),
        'columns': len(df.columns),
        'missing': missing.to_dict(),
        'duplicates': duplicate_count,
        'dtypes': dtypes.to_dict(),
        'issues': issues,
    }

    print('Data quality summary')
    print(f"Rows: {summary['rows']}")
    print(f"Columns: {summary['columns']}")
    print(f"Duplicate rows: {summary['duplicates']}")
    print('Missing values:', summary['missing'] or 'None')
    print('Data types:')
    print(dtypes.to_string())
    print('Documented issues:')
    for issue in issues:
        print(f'- {issue}')

    return summary

quality_check(df)

def clean_data(df):
    '''Clean the DataFrame by performing the following operations:
    - Drop rows with missing values
    - Convert date columns to datetime format
    - Remove duplicates
    - Remove leading and trailing whitespace from string columns
    - Remove rows with negative sales or quantity'''

    # Drop rows with missing values
    df = df.dropna()
    
    # Convert date columns to datetime format
    df['Order Date'] = pd.to_datetime(df['Order Date'])
    df['Ship Date'] = pd.to_datetime(df['Ship Date'])
    
    # Remove duplicates
    df = df.drop_duplicates()

    # Remove any leading or trailing whitespace from string columns
    str_cols = df.select_dtypes(include=['object']).columns
    for col in str_cols:
        df[col] = df[col].str.strip()

    # Remove any rows with negative sales or quantity
    df = df[(df['Sales'] >= 0) & (df['Quantity'] >= 0)]

    return df

df = clean_data(df)

# Create a new column 'Product Cost' based on the formula: Product Cost = Sales - (Sales * Discount) - Profit
df['Product Cost'] = (df['Sales']-(df['Sales']*df['Discount'])) - df['Profit']

# Save the cleaned data to a new CSV file
df.to_csv('cleaned_sample_superstore.csv', index=False)

quality_check(df)