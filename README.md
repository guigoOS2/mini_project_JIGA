# Retail Analytics — Company X Profitability Investigation

**Master's mini-project | Sample Superstore dataset**

This project investigates **profit leakage** at a fictional retail company (Company X), using the Sample Superstore dataset supplied for the class. The objective is to identify where profit is lost, examine the factors associated with those losses, and propose practical, evidence-based actions for management.

The Python workflow validates and cleans the raw data, compares profitability across products and geographic areas, examines discount patterns, evaluates loss drivers, and generates tables and charts for analysis and presentation. The main reproducible analysis is available in [`analysis.ipynb`](analysis.ipynb).

## Investigation Blueprint

### Team members and roles

| Team member | Project role | Main responsibility |
|---|---|---|
| Afonso | Project Owner | Define the business objective, priorities, and expected deliverables. |
| Guilherme | Project Manager | Coordinate the workflow, organize tasks and deadlines, monitor progress, and integrate deliverables. |
| Julia | Business Analyst | Translate the business problem into research questions, select relevant KPIs, and support interpretation and recommendations. |
| Italo | Data Analyst | Prepare and analyze the data, investigate patterns, and produce analytical tables and visualizations. |

The roles describe each member's area of responsibility; the work is collaborative.

### Project chosen

**Retail profitability and profit-loss analysis.** Company X represents a retailer with transactions across different product categories, customer segments, regions, and discount levels. The analysis uses the **Sample Superstore** CSV provided for the class, rather than confidential data from a real company.

### Problem statement

A retailer can generate strong sales while losing money on particular transactions, products, or locations. Company X therefore needs to understand **where its losses occur, how significant they are, and which observable factors are associated with them**. The results should help management prioritize further investigation and potential improvements.

### Research questions

1. **Where is Company X losing profit?** Which product categories, sub-categories, states/provinces, and regions have the weakest profitability?
2. **What factors are associated with the losses?** In particular, how do discount levels relate to negative profit, and how do product and geographic patterns overlap with discounts?
3. **What should management prioritize?** Which actions are supported by the data, and what additional evidence would be needed before implementing them?

The original investigation also considered stores, returns, and customer satisfaction. Those questions cannot be tested directly because the supplied dataset does not contain the corresponding fields.

### Analysis plan — Agile methodology applied

The team used a **lightweight Agile/Kanban approach** suited to a short academic project. GitHub Projects was used to organize work by status (**Backlog**, **Ready**, **In progress**, **In review**, and **Done**), while the GitHub repository served as the shared source for code and documentation. This is a Kanban-based workflow, not a claim that formal Scrum sprints were conducted.

The analytical work was organized into the following sequence:

1. **Define scope and questions:** agree on the business problem, available data, key profitability metrics, and required outputs.
2. **Validate and prepare data:** check schema, missing values, duplicates, dates, and invalid numerical values; produce a cleaned dataset.
3. **Explore performance:** calculate sales, profit, and profit margin by product, geography, time, and discount level.
4. **Investigate losses:** compare negative-profit transactions, rank candidate loss drivers, check overlaps, and quantify uncertainty.
5. **Communicate results:** prepare dashboard tables, presentation charts, conclusions, recommendations, and documented limitations.

The workflow supports incremental review and adjustment as findings emerge. Tasks and priorities can change when the data shows that an analysis is not informative or cannot be supported.

### Stakeholders and business value

- **Academic stakeholder:** the course instructor, who evaluates the investigation's method, technical reproducibility, reasoning, and communication.
- **Business stakeholders (hypothetical):** Company X's management, category/product managers, regional managers, and pricing or sales teams.
- **Business value:** identify loss-making areas, distinguish high sales from healthy margins, highlight the concentration of losses, and give decision-makers evidence for reviewing discount practices and product or regional performance.

The recommendations are exploratory; a real company would need operational validation before changing its pricing or commercial policies.

## Project structure

```text
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

Requires **Python 3.9 or newer**.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

Put the raw file `sample_-_superstore.csv` in the `DATA/` folder.

## Run

Always run the commands from the project root.

```bash
python run_pipeline.py
```

The pipeline runs, in this order: `etl.py` → `profit_by_segment.py` → `loss_drivers.py` → `dashboard_tables.py` → `slide_charts.py`. It stops at the first step that fails.

To run a single step, run it as a module (`etl` must run first because the other steps read the cleaned CSV):

```bash
python -m src.etl
python -m src.profit_by_segment
python -m src.loss_drivers
python -m src.dashboard_tables
python -m src.slide_charts
```

Running `python src/etl.py` directly is not supported because the scripts import shared modules as `src.utils`.

## Notebook

[`analysis.ipynb`](analysis.ipynb) presents the complete investigation step by step: data validation and cleaning; profitability by category, region, and state; discount analysis; loss-driver screening and uncertainty; a discount-policy scenario; limitations; and a summary of results. It reuses the modules in `src/`.

```bash
pip install notebook
jupyter notebook analysis.ipynb
```

Open the notebook from the project root (or in VS Code) and select **Restart & Run All**. This also creates `DATA/cleaned_sample_superstore.csv` using the same ETL logic as the pipeline.

## Output

| Folder | Content |
|---|---|
| `output/profit_by_segment/` | Profitability tables and charts by segment |
| `output/loss_drivers/` | Loss-driver tables (`tbl_*.csv`) and figures (`fig_*.png`) |
| `output/dashboard_tables/` | CSV tables for the three dashboard sections (`p1_`, `p2_`, `p3_`) |
| `output/slide_charts/` | Three 16:9 PNG charts for the presentation |
| `output/logs/pipeline.log` | Execution logs with timestamps and severity levels |

The `output/` directory is generated locally and is **not versioned**. Run the pipeline to reproduce its contents. The notebook contains the analytical code, recorded outputs, and findings for review on GitHub.

## Technical Report

### Summary of methodology

The investigation follows an exploratory and diagnostic data-analysis approach using Python, pandas, NumPy, and Matplotlib.

1. **Data validation and cleaning.** The original file contains **10,194 order lines and 21 columns**. The checks found no missing values, duplicate rows, or negative sales/quantity entries. Date fields were converted to datetime; no rows needed to be removed. Negative profit values were deliberately preserved because they are central to the study.
2. **Profitability metrics.** Total sales and total profit were aggregated by category, sub-category, region, state/province, and discount band. **Profit margin = total profit / total sales × 100**. A loss-making order line is one with negative `Profit`; **gross loss** sums the negative profits only, rather than offsetting them with profitable lines.
3. **Loss-driver analysis.** Candidate dimensions were screened using **adjusted eta-squared** on order-line losses. The main dimensions were then analyzed in more detail, including their overlaps. **95% cluster-bootstrap intervals** resampled whole orders rather than treating all lines within an order as independent.
4. **Discount sensitivity and scenario.** Discounts above **20%** were classified as *deep discounts*. Alternative thresholds were checked. An illustrative scenario estimated the accounting effect of capping discounts at 20% under fixed-price/cost assumptions and different hypothetical losses of sales volume.
5. **Reporting.** Results were summarized through notebook tables, dashboard-ready CSVs, and presentation charts. Conclusions distinguish measured associations from unproven causal explanations.

### Key findings

*Figures below are rounded from the recorded outputs in [`analysis.ipynb`](analysis.ipynb). Monetary amounts use the notebook's dollar convention.*

| Finding | Result |
|---|---|
| Overall business performance | Approximately **$2.33 million in sales**, **$292,297 net profit**, and **12.56% profit margin**. |
| Transactions with losses | **18.6% of order lines** have negative profit; gross loss is approximately **$157,000** before offsetting profitable lines. |
| Lowest-margin category | **Furniture: 2.61%** margin, compared with **17.22%** for Office Supplies and **17.45%** for Technology. |
| Net-loss sub-categories | **Tables, Bookcases, and Supplies** are negative in aggregate, with approximately **$23,000 combined net loss**. |
| Lowest-margin region | **Central: 7.92%**, compared with **14.98%** for West. |
| Deep discounts (>20%) | Just **13.9% of order lines** account for **88.6% of gross loss** (95% bootstrap interval: **85.5%–91.0%**). Their aggregate profit margin is approximately **−37.3%**. |
| Other major loss concentrations | **Binders, Tables, and Machines** account for **64.4% of gross loss**; **Texas, Ohio, Pennsylvania, and Illinois** account for **63.5%**. These groups overlap with each other and with deep discounts. |

### Interpretation of results

The retailer is profitable overall, but that positive total conceals a material concentration of loss-making order lines. **Sales alone are not a sufficient performance measure:** Furniture has substantial revenue yet a much lower profit margin than the other two main categories.

**Discount levels show the clearest association with losses** in this dataset. Most gross loss is concentrated in a relatively small share of highly discounted order lines. Product and geographic concentrations are also important, but many of their losses occur on those same deeply discounted lines. Their loss shares **must not be added together** because the groups overlap.

These findings support a **prioritized review of pricing and discount practices**, particularly in weak-margin product groups and locations. They do **not** establish that discounts caused the losses: discounts may be associated with other product, customer, or market factors that are not observed here.

### Recommendations

1. **Review discounts above 20% first.** Investigate their business justification, product mix, and profitability before applying new discount limits. Consider a controlled pilot rather than an immediate company-wide change.
2. **Investigate loss-making product groups.** Prioritize **Tables, Bookcases, and Supplies** for margin and pricing reviews; examine **Binders and Machines** when studying the concentration of gross loss. Net-loss sub-categories and gross-loss contributors are different measures.
3. **Examine weak-performing locations.** Review Central-region performance and the identified high-loss states, comparing category mix and discount practices before treating geography as an independent cause.
4. **Monitor measurable outcomes.** Track total profit, profit margin, share of loss-making order lines, and loss concentration by discount band and product group. Validate any intervention with actual operational data.

### Limitations

- **No causal identification:** this is an observational analysis; correlations between discounts and losses do not prove why the losses occurred.
- **Missing variables:** the dataset contains no store identifier, returns, customer satisfaction, shipping costs, or overhead breakdown. Store-level and customer-experience questions cannot be answered; shipping and full economic profitability cannot be assessed separately.
- **Derived cost:** `Product Cost` is calculated as `Sales − Profit`, not sourced from independent cost records; it should not be interpreted as an independently verified cost model.
- **Dataset scope:** the data represents a classroom dataset and only the markets present in the file. Some geographic groups have small samples; for example, Canada contains only 200 order lines.
- **Date validity:** order dates extend from **January 2023 through December 2026**, including dates after the November 2026 analysis. Time-based trends therefore require caution and should not automatically be described as verified historical outcomes.
- **Analytical choices and uncertainty:** the 20% deep-discount threshold and the 60% gross-loss coverage rule are analyst-defined. Threshold sensitivity was evaluated; the coverage choice was not independently stress-tested.
- **Scenario is not a forecast:** the 20% discount-cap exercise suggests an illustrative **$136,000–$220,000** increase in profit under its specified volume-loss assumptions. It assumes fixed list prices and costs, contains no demand-response model, and should **not** be presented as an expected financial benefit.
- **Currency labeling:** monetary outputs use `$` in the notebook and charts, but the CSV itself does not include a dedicated currency field.

## Tests

```bash
pip install pytest
pytest
```

## Notes

- Shared settings, file paths, the deep-discount threshold (`HIGH_DISCOUNT = 20%`), and discount bands are defined in `src/utils.py`.
- `Product Cost` is calculated in `src/etl.py` as `Sales - Profit` because the raw file has no standalone product-cost column.
- The dataset contains order dates through December 2026; interpret the time dimension with the limitation described above.
- All reported findings can be traced to the notebook and recreated with the pipeline. Analytical results are specific to the supplied dataset, not independently verified company records.
