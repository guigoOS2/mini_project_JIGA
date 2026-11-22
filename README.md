# Project D – Retail Analytics

Group project that analyses the Sample Superstore dataset to find where a multinational retailer loses profit (profit leakage). The code cleans the raw data, compares profit by segment, product, region, date and channel, identifies the strongest loss drivers, and prepares tables and charts for the dashboard and the slides.

## Project structure

```
project/
├── run_pipeline.py            # runs the whole workflow with one command
├── requirements.txt           # Python dependencies
├── analysis.ipynb             # Jupyter notebook: cleaning, analysis, charts and key findings
├── pytest.ini                 # pytest settings
├── DATA/
│   ├── sample_-_superstore.csv            # raw data (input)
│   └── cleaned_sample_superstore.csv      # created by etl.py
├── src/
│   ├── __init__.py
│   ├── utils.py               # shared paths, settings, logging and helper functions
│   ├── etl.py                 # checks, cleans and saves the data
│   ├── profit_by_segment.py   # profit by segment x region, product, channel, date and discount
│   ├── loss_drivers.py        # strongest loss drivers, with uncertainty
│   ├── dashboard_tables.py    # one table per dashboard item
│   └── slide_charts.py        # charts ready for the slides
├── tests/                     # pytest unit tests
└── output/                    # created by the scripts (not versioned)
```

## Setup

Requires Python 3.9 or newer.

```
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

Put the raw file `sample_-_superstore.csv` in the `DATA/` folder.

## Run

Always run the commands from the project root.

```
python run_pipeline.py
```

The pipeline runs, in this order: `etl.py` -> `profit_by_segment.py` -> `loss_drivers.py` -> `dashboard_tables.py` -> `slide_charts.py`. It stops at the first step that fails.

To run a single step, run it as a module (`etl` must run first, because the others read the cleaned CSV):

```
python -m src.etl
python -m src.profit_by_segment
python -m src.loss_drivers
python -m src.dashboard_tables
python -m src.slide_charts
```

`python src/etl.py` does not work, because the scripts import each other as `src.utils`.

## Notebook

`analysis.ipynb` has the full analysis, step by step: data validation and cleaning, margins by category, region and state, discount analysis, loss drivers with uncertainty, sizing of the discount lever, limitations and a summary of the findings. It reuses the code in `src/`.

```
pip install notebook
jupyter notebook analysis.ipynb
```

Open it from the project root (or use VS Code) and choose *Restart & Run All*. It cleans the raw CSV and saves `DATA/cleaned_sample_superstore.csv`, like `etl.py` does.

## Output

| Folder | Content |
|---|---|
| `output/graphs and tables/` | Profit by segment: CSV tables and charts |
| `output/t7/` | Loss drivers: tables (`tbl_*.csv`) and charts (`fig_*.png`) |
| `output/dashboard/` | One CSV table per dashboard item (`p1_`, `p2_`, `p3_`) |
| `output/slides/` | Three charts ready for the slides (PNG, 16:9) |
| `output/logs/pipeline.log` | Log of every run, with timestamps and severity levels |

## Tests

```
pip install pytest
pytest
```

## Notes

- Settings shared by all scripts (paths, `HIGH_DISCOUNT` = 20% and the discount ranges) live in `src/utils.py`.
- `Product Cost` is not in the raw data: `etl.py` calculates it as `Sales - Profit`.
- The dataset has orders dated up to December 2026.
