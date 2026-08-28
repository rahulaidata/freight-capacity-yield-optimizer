from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Scenario:
    forecast_multiplier: float = 1.0
    risk_multiplier: float = 1.0
    capacity_confidence_floor: float = 0.45


def expand_capacity(capacity_signals: pd.DataFrame, confidence_floor: float = 0.45) -> pd.DataFrame:
    """Expand probabilistic capacity signals into conservative discrete truck units."""
    rows: List[dict] = []
    for signal in capacity_signals.to_dict("records"):
        confidence = float(signal["availability_confidence"])
        if confidence < confidence_floor:
            continue
        expected = float(signal["truck_count"]) * confidence
        unit_count = max(1, int(np.floor(expected + 0.25)))
        for idx in range(unit_count):
            row = dict(signal)
            row["capacity_unit_id"] = f"{signal['capacity_signal_id']}-U{idx + 1}"
            row["unit_sequence"] = idx + 1
            rows.append(row)
    return pd.DataFrame(rows)


def _demand_book(open_loads: pd.DataFrame, forecast: pd.DataFrame, scenario: Scenario) -> pd.DataFrame:
    open_rows = open_loads.copy()
    open_rows["demand_id"] = open_rows["load_id"]
    open_rows["demand_type"] = "OPEN"
    open_rows["arrival_probability"] = 1.0
    open_rows["customer_revenue"] = open_rows["customer_sell_rate"]
    open_rows["coverage_deadline"] = pd.to_datetime(open_rows["coverage_deadline"])

    forecast_rows: List[dict] = []
    for row in forecast.to_dict("records"):
        slots = max(1, min(2, int(round(float(row["expected_load_count"])))))
        for idx in range(slots):
            forecast_rows.append(
                {
                    "demand_id": f"{row['forecast_id']}-S{idx + 1}",
                    "load_id": f"{row['forecast_id']}-S{idx + 1}",
                    "customer_id": row["customer_id"],
                    "lane_id": row["lane_id"],
                    "origin_market_id": row["origin_market_id"],
                    "destination_market_id": row["destination_market_id"],
                    "equipment_class": row["equipment_class"],
                    "pickup_start": row["expected_arrival_time"],
                    "pickup_end": row["expected_pickup_end"],
                    "coverage_deadline": row["reserve_until"],
                    "customer_sell_rate": row["expected_sell_rate"],
                    "customer_revenue": row["expected_sell_rate"],
                    "fallback_buy_rate": row["expected_fallback_rate"],
                    "priority": "FORECAST",
                    "service_tier": row["service_tier"],
                    "coverage_status": "FORECAST",
                    "demand_type": "FORECAST",
                    "arrival_probability": min(
                        0.98, float(row["forecast_confidence"]) * scenario.forecast_multiplier
                    ),
                }
            )
    forecast_df = pd.DataFrame(forecast_rows)
    if not forecast_df.empty:
        for column in ("pickup_start", "pickup_end", "coverage_deadline"):
            forecast_df[column] = pd.to_datetime(forecast_df[column])
    return pd.concat([open_rows, forecast_df], ignore_index=True, sort=False)


def build_candidates(
    open_loads: pd.DataFrame,
    forecast: pd.DataFrame,
    capacity_signals: pd.DataFrame,
    carrier_lane_stats: pd.DataFrame,
    carrier_preferences: pd.DataFrame,
    scenario: Scenario,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    units = expand_capacity(capacity_signals, scenario.capacity_confidence_floor)
    demand = _demand_book(open_loads, forecast, scenario)
    stats = carrier_lane_stats.set_index(["carrier_id", "lane_id"]).to_dict("index")
    prefs = carrier_preferences.groupby("carrier_id")["lane_id"].apply(set).to_dict()

    candidates: List[dict] = []
    for d in demand.to_dict("records"):
        for c in units.to_dict("records"):
            if d["equipment_class"] != c["equipment_class"]:
                continue
            if d["origin_market_id"] != c["origin_market_id"]:
                continue
            if pd.Timestamp(d["pickup_start"]) < pd.Timestamp(c["available_from"]):
                continue
            if pd.Timestamp(d["pickup_start"]) > pd.Timestamp(c["available_until"]):
                continue

            lane_key = (c["carrier_id"], d["lane_id"])
            lane_stats = stats.get(lane_key)
            explicitly_preferred = d["lane_id"] in prefs.get(c["carrier_id"], set())
            if lane_stats is None and not explicitly_preferred:
                continue

            if lane_stats:
                typical_buy = float(lane_stats["average_booked_rate"])
                acceptance = float(lane_stats["acceptance_rate"])
                service = float(lane_stats["on_time_pickup_rate"]) * 0.45 + float(
                    lane_stats["on_time_delivery_rate"]
                ) * 0.55
                support = int(lane_stats["loads_moved"])
            else:
                typical_buy = float(c["expected_rate"])
                acceptance = 0.62
                service = 0.92
                support = 4

            expected_buy = 0.60 * float(c["expected_rate"]) + 0.40 * typical_buy
            confidence = float(c["availability_confidence"])
            acceptance = min(0.97, acceptance * (0.92 + 0.08 * confidence))
            service_penalty = {"PLATINUM": 700, "GOLD": 450, "STANDARD": 260}.get(
                d.get("service_tier", "STANDARD"), 260
            )
            urgency_penalty = {"CRITICAL": 300, "HIGH": 180, "NORMAL": 80, "FORECAST": 0}.get(
                d.get("priority", "NORMAL"), 80
            )
            failure_cost = ((1.0 - acceptance) * urgency_penalty + (1.0 - service) * service_penalty)
            failure_cost *= scenario.risk_multiplier
            fallback_buy = float(d["fallback_buy_rate"])
            raw_value = fallback_buy - expected_buy - failure_cost
            probability = float(d["arrival_probability"])
            weighted_value = raw_value * probability
            candidates.append(
                {
                    "candidate_id": f"{d['demand_id']}::{c['capacity_unit_id']}",
                    "demand_id": d["demand_id"],
                    "load_id": d["load_id"],
                    "demand_type": d["demand_type"],
                    "carrier_id": c["carrier_id"],
                    "capacity_unit_id": c["capacity_unit_id"],
                    "capacity_signal_id": c["capacity_signal_id"],
                    "lane_id": d["lane_id"],
                    "customer_id": d["customer_id"],
                    "priority": d.get("priority", "NORMAL"),
                    "expected_buy_rate": round(expected_buy, 2),
                    "fallback_buy_rate": round(fallback_buy, 2),
                    "accept_probability": round(acceptance, 4),
                    "service_probability": round(service, 4),
                    "availability_confidence": round(confidence, 4),
                    "arrival_probability": round(probability, 4),
                    "expected_failure_cost": round(failure_cost, 2),
                    "incremental_capacity_value": round(raw_value, 2),
                    "weighted_value": round(weighted_value, 2),
                    "historical_support_loads": support,
                    "coverage_deadline": d["coverage_deadline"],
                }
            )
    return pd.DataFrame(candidates), demand


def _optimize_exact(candidates: pd.DataFrame) -> pd.DataFrame:
    """Exact maximum-value assignment using a capacity-unit bitmask dynamic program."""
    if candidates.empty:
        return candidates.copy()
    units = sorted(candidates["capacity_unit_id"].unique())
    unit_index = {unit: idx for idx, unit in enumerate(units)}
    demand_ids = sorted(candidates["demand_id"].unique())
    by_demand = {
        demand_id: list(group.to_dict("records"))
        for demand_id, group in candidates.groupby("demand_id")
    }

    states: Dict[int, Tuple[float, List[dict]]] = {0: (0.0, [])}
    for demand_id in demand_ids:
        next_states = dict(states)
        for mask, (score, assignments) in states.items():
            for candidate in by_demand[demand_id]:
                value = float(candidate["weighted_value"])
                if value <= 0:
                    continue
                bit = 1 << unit_index[candidate["capacity_unit_id"]]
                if mask & bit:
                    continue
                new_mask = mask | bit
                new_score = score + value
                previous = next_states.get(new_mask)
                if previous is None or new_score > previous[0]:
                    next_states[new_mask] = (new_score, assignments + [candidate])
        states = next_states
    best_score, best_assignments = max(states.values(), key=lambda item: item[0])
    result = pd.DataFrame(best_assignments)
    if not result.empty:
        result["portfolio_objective_value"] = round(best_score, 2)
    return result


def _current_plan(candidates: pd.DataFrame, demand: pd.DataFrame) -> pd.DataFrame:
    """Simulate a siloed first-come plan that uses the cheapest visible carrier per open load."""
    open_demand = demand[demand["demand_type"] == "OPEN"].sort_values(
        ["coverage_deadline", "pickup_start"]
    )
    used_units = set()
    chosen: List[dict] = []
    for row in open_demand.to_dict("records"):
        options = candidates[
            (candidates["demand_id"] == row["demand_id"])
            & (~candidates["capacity_unit_id"].isin(used_units))
        ].sort_values(["expected_buy_rate", "accept_probability"], ascending=[True, False])
        if options.empty:
            continue
        option = options.iloc[0].to_dict()
        chosen.append(option)
        used_units.add(option["capacity_unit_id"])
    return pd.DataFrame(chosen)


def _plan_metrics(
    open_loads: pd.DataFrame,
    assignments: pd.DataFrame,
    forecast_assignments: pd.DataFrame | None = None,
) -> dict:
    assignment_map = assignments.set_index("load_id").to_dict("index") if not assignments.empty else {}
    total_revenue = float(open_loads["customer_sell_rate"].sum())
    carrier_spend = 0.0
    expected_risk_cost = 0.0
    known_covered = 0
    for load in open_loads.to_dict("records"):
        assigned = assignment_map.get(load["load_id"])
        if assigned:
            carrier_spend += float(assigned["expected_buy_rate"])
            expected_risk_cost += float(assigned["expected_failure_cost"])
            known_covered += 1
        else:
            carrier_spend += float(load["fallback_buy_rate"])
            expected_risk_cost += 35 if load["priority"] == "NORMAL" else 90
    expected_contribution = total_revenue - carrier_spend - expected_risk_cost
    future_value = 0.0
    reserved = 0
    if forecast_assignments is not None and not forecast_assignments.empty:
        future_value = float(forecast_assignments["weighted_value"].sum())
        reserved = len(forecast_assignments)
    return {
        "revenue": total_revenue,
        "carrier_spend": carrier_spend,
        "expected_risk_cost": expected_risk_cost,
        "gross_margin": total_revenue - carrier_spend,
        "expected_contribution": expected_contribution + future_value,
        "known_capacity_assignments": known_covered,
        "spot_or_fallback_loads": len(open_loads) - known_covered,
        "reserved_units": reserved,
        "future_option_value": future_value,
    }


def run_portfolio(
    open_loads: pd.DataFrame,
    forecast: pd.DataFrame,
    capacity_signals: pd.DataFrame,
    carrier_lane_stats: pd.DataFrame,
    carrier_preferences: pd.DataFrame,
    scenario: Scenario,
) -> dict:
    candidates, demand = build_candidates(
        open_loads,
        forecast,
        capacity_signals,
        carrier_lane_stats,
        carrier_preferences,
        scenario,
    )
    optimized = _optimize_exact(candidates)
    current = _current_plan(candidates, demand)
    optimized_open = optimized[optimized["demand_type"] == "OPEN"].copy() if not optimized.empty else optimized
    optimized_forecast = (
        optimized[optimized["demand_type"] == "FORECAST"].copy() if not optimized.empty else optimized
    )
    current_metrics = _plan_metrics(open_loads, current)
    optimized_metrics = _plan_metrics(open_loads, optimized_open, optimized_forecast)
    return {
        "candidates": candidates,
        "demand": demand,
        "current_assignments": current,
        "optimized_assignments": optimized,
        "optimized_open": optimized_open,
        "optimized_forecast": optimized_forecast,
        "current_metrics": current_metrics,
        "optimized_metrics": optimized_metrics,
    }


def build_recommendations(result: dict, open_loads: pd.DataFrame, carriers: pd.DataFrame) -> pd.DataFrame:
    current = result["current_assignments"]
    optimized = result["optimized_assignments"]
    candidates = result["candidates"]
    carrier_names = carriers.set_index("carrier_id")["carrier_name"].to_dict()
    current_by_load = current.set_index("load_id").to_dict("index") if not current.empty else {}
    recommendations: List[dict] = []

    for row in optimized.to_dict("records"):
        if row["demand_type"] == "FORECAST":
            action = "RESERVE"
            explanation = (
                f"Reserve {carrier_names[row['carrier_id']]} until {pd.Timestamp(row['coverage_deadline']).strftime('%H:%M')}. "
                f"Expected forecast value is ${row['weighted_value']:,.0f} after applying a "
                f"{row['arrival_probability']:.0%} arrival probability."
            )
            current_value = 0.0
        else:
            current_row = current_by_load.get(row["load_id"])
            current_value = float(current_row["weighted_value"]) if current_row else 0.0
            action = "ASSIGN" if row["accept_probability"] >= 0.83 else "TENDER"
            explanation = (
                f"{action.title()} {carrier_names[row['carrier_id']]} on {row['load_id']}. "
                f"Expected buy is ${row['expected_buy_rate']:,.0f} versus ${row['fallback_buy_rate']:,.0f} fallback; "
                f"this use is worth ${row['weighted_value']:,.0f} and is ${row['weighted_value'] - current_value:,.0f} "
                "better than the current allocation for this load."
            )
        recommendations.append(
            {
                "recommendation_id": f"REC-{len(recommendations) + 1:03d}",
                "action": action,
                "load_id": row["load_id"],
                "carrier_id": row["carrier_id"],
                "carrier_name": carrier_names[row["carrier_id"]],
                "lane_id": row["lane_id"],
                "expected_incremental_margin": round(float(row["weighted_value"]), 2),
                "confidence": round(
                    float(row["accept_probability"]) * float(row["availability_confidence"]), 3
                ),
                "expires_at": row["coverage_deadline"],
                "status": "PENDING",
                "explanation": explanation,
                "accept_probability": row["accept_probability"],
                "service_probability": row["service_probability"],
                "historical_support_loads": row["historical_support_loads"],
            }
        )

    assigned_units = set(optimized["capacity_unit_id"]) if not optimized.empty else set()
    units = set(candidates["capacity_unit_id"]) if not candidates.empty else set()
    for unit in sorted(units - assigned_units):
        carrier_id = candidates.loc[candidates["capacity_unit_id"] == unit, "carrier_id"].iloc[0]
        recommendations.append(
            {
                "recommendation_id": f"REC-{len(recommendations) + 1:03d}",
                "action": "RELEASE",
                "load_id": "—",
                "carrier_id": carrier_id,
                "carrier_name": carrier_names[carrier_id],
                "lane_id": "—",
                "expected_incremental_margin": 0.0,
                "confidence": 0.72,
                "expires_at": pd.Timestamp.now().ceil("h"),
                "status": "PENDING",
                "explanation": f"Release {carrier_names[carrier_id]}; no positive-value use remains in the current scenario.",
                "accept_probability": np.nan,
                "service_probability": np.nan,
                "historical_support_loads": 0,
            }
        )
    return pd.DataFrame(recommendations).sort_values(
        ["expected_incremental_margin", "confidence"], ascending=[False, False]
    )

