# Freight Capacity Yield Optimizer

A client-ready Streamlit MVP that demonstrates portfolio-level carrier capacity allocation using a synthetic freight brokerage dataset.

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

## Application views

1. **Data room** — canonical assets, validation checks, and historical proof-of-value preview.
2. **Freight & capacity** — open loads, forecast demand, probabilistic capacity, and market views.
3. **Portfolio optimizer** — current versus optimized economics, reassignments, and reserved capacity.
4. **Daily decision center** — prioritized recommendations, re-decision events, explanations, and operator feedback.

All data is synthetic and all company, customer, and carrier names are fictional.
