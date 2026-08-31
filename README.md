# Freight Capacity Yield Optimizer

A client-ready Streamlit MVP with an Arcwise Agent Library landing page and a working portfolio-level carrier capacity allocation workflow using a synthetic freight brokerage dataset.

## Agent Library navigation

- **Trucking Consolidation Agent** opens the freight capacity workflow inside this app.
- **Buyer Consolidation Agent** opens the dedicated [Arcwise Buyer Consolidation app](https://agents-buyer-consol.arcwise.app/).
- The remaining agent cards establish the approved product-suite information architecture for future workflows.

## What the demo proves

- Broker data can be normalized without replacing the TMS, load board, or carrier network.
- Carrier capacity can be valued across the entire open freight book instead of one load at a time.
- The portfolio optimizer can reallocate existing capacity and reserve trucks for high-confidence forecast demand.
- Every recommendation can be explained through fallback cost, expected buy, acceptance, service risk, and opportunity cost.
- Operators can accept, reject, or modify recommendations and capture tribal knowledge.

## Run locally

```bash
source .venv/bin/activate
streamlit run app.py
```

The app reads deterministic sample assets from `data/`. To regenerate them:

```bash
python scripts/generate_demo_data.py
```

## Guided application workflow

1. **Data** — upload open-load and capacity CSVs, or start immediately with the included demo book.
2. **Validate** — confirm schemas, record counts, economics, history coverage, and required fields.
3. **Capacity** — review known freight, probabilistic truck supply, and forecasted demand together.
4. **Settings** — set forecast confidence, service-risk posture, and the capacity evidence floor.
5. **Optimize** — run an exact portfolio assignment across current and expected freight.
6. **Decisions** — compare plans, explain every recommendation, capture operator feedback, and export results.

## Deploy on Streamlit Community Cloud

1. Connect this repository and select the `main` branch.
2. Set the entrypoint to `app.py`.
3. Deploy. `requirements.txt` is pinned to releases with Python 3.14 wheels.

The deployed app needs no secrets, database, or external API for the demo-data path.

All data is synthetic and all company, customer, and carrier names are fictional.
