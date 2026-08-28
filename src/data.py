from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd


DATA_DIR = Path(__file__).resolve().parents[1] / "data"

ASSET_FILES = {
    "customers": "customers.csv",
    "carriers": "carriers.csv",
    "markets": "markets.csv",
    "lanes": "lanes.csv",
    "historical_loads": "historical_loads.csv",
    "open_loads": "open_loads.csv",
    "carrier_lane_stats": "carrier_lane_stats.csv",
    "carrier_preferences": "carrier_preferences.csv",
    "capacity_signals": "capacity_signals.csv",
    "forecast_demand": "forecast_demand.csv",
    "model_predictions": "model_predictions.csv",
    "assignment_candidates": "assignment_candidates.csv",
    "optimization_runs": "optimization_runs.csv",
    "optimization_decisions": "optimization_decisions.csv",
    "recommendations": "recommendations.csv",
    "recommendation_feedback": "recommendation_feedback.csv",
    "events": "events.csv",
}


DATE_COLUMNS = {
    "historical_loads": ["load_created_timestamp", "carrier_assigned_timestamp", "pickup_datetime", "delivery_datetime"],
    "open_loads": ["load_created_timestamp", "pickup_start", "pickup_end", "delivery_start", "delivery_end", "coverage_deadline"],
    "capacity_signals": ["available_from", "available_until", "observed_at", "expires_at"],
    "forecast_demand": ["expected_arrival_time", "expected_pickup_end", "reserve_until"],
    "assignment_candidates": ["coverage_deadline"],
    "optimization_runs": ["created_at"],
    "recommendations": ["expires_at"],
    "recommendation_feedback": ["created_at"],
    "events": ["event_time"],
}


def load_demo_assets(data_dir: Path = DATA_DIR) -> Dict[str, pd.DataFrame]:
    assets: Dict[str, pd.DataFrame] = {}
    missing = []
    for name, filename in ASSET_FILES.items():
        path = data_dir / filename
        if not path.exists():
            missing.append(filename)
            continue
        assets[name] = pd.read_csv(path, parse_dates=DATE_COLUMNS.get(name, []))
    if missing:
        raise FileNotFoundError(
            "Missing demo assets: " + ", ".join(missing) + ". Run scripts/generate_demo_data.py."
        )
    return assets


def quality_summary(assets: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    required = {
        "historical_loads": ["load_id", "customer_id", "carrier_id", "lane_id", "customer_sell_rate", "carrier_buy_rate"],
        "open_loads": ["load_id", "customer_id", "lane_id", "customer_sell_rate", "fallback_buy_rate", "pickup_start"],
        "carriers": ["carrier_id", "carrier_name", "equipment_types"],
        "capacity_signals": ["capacity_signal_id", "carrier_id", "origin_market_id", "truck_count", "availability_confidence"],
        "forecast_demand": ["forecast_id", "customer_id", "lane_id", "expected_load_count", "forecast_confidence"],
    }
    rows = []
    for name, columns in required.items():
        frame = assets[name]
        missing_columns = [column for column in columns if column not in frame.columns]
        nulls = int(frame[columns].isna().sum().sum()) if not missing_columns else -1
        score = 100.0 if not missing_columns and nulls == 0 else max(0.0, 100 - len(missing_columns) * 20 - max(nulls, 0))
        rows.append(
            {
                "asset": name.replace("_", " ").title(),
                "records": len(frame),
                "required_fields": len(columns),
                "missing_required_values": max(nulls, 0),
                "quality_score": score,
                "status": "Ready" if score >= 95 else "Review",
            }
        )
    return pd.DataFrame(rows)

