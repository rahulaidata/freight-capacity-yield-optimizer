from __future__ import annotations

from datetime import datetime
from io import StringIO

import altair as alt
import pandas as pd
import streamlit as st

from src.data import load_demo_assets, quality_summary
from src.optimizer import Scenario, build_recommendations, run_portfolio


st.set_page_config(
    page_title="Freight Yield Optimizer",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root { --ink:#172B3A; --teal:#18A999; --navy:#153A56; --muted:#607789; --line:#D8E2EA; }
      .stApp { background: linear-gradient(180deg,#F7F9FC 0%,#FFFFFF 38%); }
      .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1500px; }
      h1, h2, h3 { color: var(--navy); letter-spacing: -0.02em; }
      [data-testid="stMetric"] { background:#FFFFFF; border:1px solid var(--line); border-radius:14px; padding:14px 16px; box-shadow:0 4px 18px rgba(25,55,75,.05); }
      [data-testid="stMetricLabel"] { color:var(--muted); font-weight:600; }
      div[data-baseweb="tab-list"] { gap:8px; }
      button[data-baseweb="tab"] { background:#EDF3F7; border-radius:10px 10px 0 0; padding:10px 18px; }
      button[data-baseweb="tab"][aria-selected="true"] { background:#153A56; color:white; }
      .hero { background:linear-gradient(115deg,#123A55,#166274 62%,#18A999); color:white; border-radius:20px; padding:26px 30px; margin-bottom:18px; box-shadow:0 12px 30px rgba(21,58,86,.16); }
      .hero h1 { color:white; margin:0 0 6px 0; font-size:2.05rem; }
      .hero p { margin:0; color:#DDF5F1; font-size:1.02rem; }
      .eyebrow { text-transform:uppercase; letter-spacing:.12em; font-size:.73rem; font-weight:800; color:#8DE7DA; margin-bottom:8px; }
      .callout { border-left:5px solid #18A999; background:#EBF8F6; padding:14px 16px; border-radius:0 12px 12px 0; margin:8px 0 16px 0; color:#254454; }
      .decision { background:#FFFFFF; border:1px solid #D8E2EA; border-radius:14px; padding:16px 18px; margin:8px 0; }
      .pill { display:inline-block; border-radius:999px; padding:4px 10px; font-size:.75rem; font-weight:800; letter-spacing:.04em; }
      .pill-assign,.pill-tender { background:#DDF5EF;color:#096A58; }
      .pill-reserve { background:#FFF1C9;color:#795A00; }
      .pill-release,.pill-spot { background:#FCE2E1;color:#9A302C; }
      .muted { color:#607789; }
      .small { font-size:.84rem; }
      #MainMenu {visibility:hidden;} footer {visibility:hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def demo_assets():
    return load_demo_assets()


def money(value: float) -> str:
    return f"${value:,.0f}"


def pct(value: float) -> str:
    return f"{value:.0%}"


def parse_uploaded(uploaded, date_columns):
    if uploaded is None:
        return None
    frame = pd.read_csv(uploaded)
    for column in date_columns:
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column])
    return frame


assets = demo_assets()

with st.sidebar:
    st.markdown("### Scenario controls")
    st.caption("Change the assumptions and the portfolio is reoptimized across every load and capacity unit.")
    forecast_multiplier = st.slider("Forecast confidence", 0.50, 1.20, 1.00, 0.05)
    risk_multiplier = st.slider("Service-risk penalty", 0.50, 2.00, 1.00, 0.10)
    confidence_floor = st.slider("Capacity confidence floor", 0.35, 0.90, 0.45, 0.05)
    st.divider()
    with st.expander("Replace demo inputs", expanded=False):
        st.caption("Optional: upload canonical-format CSVs for the live board. Files stay in this browser session.")
        open_upload = st.file_uploader("Open loads CSV", type="csv", key="open_upload")
        capacity_upload = st.file_uploader("Capacity signals CSV", type="csv", key="capacity_upload")
    st.markdown("---")
    st.markdown("**Demo anchor:** Aug 27, 2026 · 08:00")
    st.caption("Synthetic data only. All company and carrier names are fictional.")

open_override = parse_uploaded(
    open_upload,
    ["load_created_timestamp", "pickup_start", "pickup_end", "delivery_start", "delivery_end", "coverage_deadline"],
)
capacity_override = parse_uploaded(
    capacity_upload,
    ["available_from", "available_until", "observed_at", "expires_at"],
)
open_loads = open_override if open_override is not None else assets["open_loads"]
capacity_signals = capacity_override if capacity_override is not None else assets["capacity_signals"]

scenario = Scenario(
    forecast_multiplier=forecast_multiplier,
    risk_multiplier=risk_multiplier,
    capacity_confidence_floor=confidence_floor,
)
result = run_portfolio(
    open_loads,
    assets["forecast_demand"],
    capacity_signals,
    assets["carrier_lane_stats"],
    assets["carrier_preferences"],
    scenario,
)
recommendations = build_recommendations(result, open_loads, assets["carriers"])

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Bring your own network · portfolio yield management</div>
      <h1>Freight Capacity Yield Optimizer</h1>
      <p>Allocate scarce carrier capacity across the whole freight book—then explain every assign, reserve, release, and spot decision in dollars.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

current = result["current_metrics"]
optimized = result["optimized_metrics"]
uplift = optimized["expected_contribution"] - current["expected_contribution"]
headline_cols = st.columns(5)
headline_cols[0].metric("Expected 24h contribution", money(optimized["expected_contribution"]), money(uplift))
headline_cols[1].metric("Optimized carrier spend", money(optimized["carrier_spend"]), money(optimized["carrier_spend"] - current["carrier_spend"]))
headline_cols[2].metric("Open loads", f"{len(open_loads)}", f"{int((open_loads['priority'].isin(['HIGH','CRITICAL'])).sum())} urgent", delta_color="off")
headline_cols[3].metric("Capacity reserved", f"{optimized['reserved_units']} units", money(optimized["future_option_value"]))
headline_cols[4].metric("Pending decisions", f"{len(recommendations)}", f"{int((recommendations['action']=='RESERVE').sum())} reserve", delta_color="off")

tab_data, tab_live, tab_opt, tab_decisions = st.tabs(
    ["1 · Data room", "2 · Freight & capacity", "3 · Portfolio optimizer", "4 · Daily decision center"]
)

with tab_data:
    st.subheader("Client-ready data room")
    st.markdown(
        '<div class="callout"><b>Minimum proof-of-value:</b> 12–24 months of TMS history, today’s open freight, and any carrier commitment or capacity spreadsheet. The demo does not require a new TMS, load board, or carrier network.</div>',
        unsafe_allow_html=True,
    )
    quality = quality_summary({**assets, "open_loads": open_loads, "capacity_signals": capacity_signals})
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Canonical assets", len(assets))
    q2.metric("Historical loads", f"{len(assets['historical_loads']):,}")
    q3.metric("Quality score", f"{quality['quality_score'].mean():.0f}%")
    q4.metric("Blocking issues", int((quality["quality_score"] < 90).sum()))

    left, right = st.columns([1.05, 1.35])
    with left:
        st.markdown("#### Required-data checks")
        st.dataframe(
            quality,
            hide_index=True,
            use_container_width=True,
            column_config={
                "quality_score": st.column_config.ProgressColumn("Quality", min_value=0, max_value=100, format="%.0f%%"),
                "status": st.column_config.TextColumn("Status"),
            },
        )
    with right:
        st.markdown("#### Canonical asset inventory")
        inventory = pd.DataFrame(
            [
                {
                    "asset": name.replace("_", " ").title(),
                    "records": len(frame),
                    "role": (
                        "Source / state" if name in {"historical_loads", "open_loads", "carriers", "capacity_signals", "forecast_demand"}
                        else "Derived / decision"
                    ),
                    "refresh": "Per optimization run" if name in {"model_predictions", "assignment_candidates", "optimization_runs", "optimization_decisions", "recommendations"} else "Upload / event",
                }
                for name, frame in assets.items()
            ]
        )
        st.dataframe(inventory, hide_index=True, use_container_width=True, height=336)

    st.markdown("#### Historical proof-of-value preview")
    hist = assets["historical_loads"]
    actual_buy = float(hist["carrier_buy_rate"].sum())
    actual_margin = float(hist["gross_margin"].sum())
    replay_rate = min(0.05, max(0.02, uplift / max(current["carrier_spend"], 1) * 0.28))
    replay_savings = actual_buy * replay_rate
    h1, h2, h3, h4 = st.columns(4)
    h1.metric("Loads replayed", f"{len(hist):,}")
    h2.metric("Actual carrier spend", money(actual_buy))
    h3.metric("Actual gross margin", money(actual_margin))
    h4.metric("Illustrative recoverable value", money(replay_savings), pct(replay_rate))
    st.caption("Illustrative replay uses synthetic data and conservative capacity evidence tiers. A client pilot would separate committed/observed alternatives from historically inferred alternatives.")

with tab_live:
    st.subheader("Current freight and probabilistic capacity")
    filters = st.columns([1, 1, 1, 2])
    origin_options = ["All"] + sorted(open_loads["origin_market_id"].unique())
    priority_options = ["All"] + sorted(open_loads["priority"].unique())
    selected_origin = filters[0].selectbox("Origin market", origin_options)
    selected_priority = filters[1].selectbox("Priority", priority_options)
    show_forecast = filters[2].toggle("Show forecast", value=True)
    filtered_loads = open_loads.copy()
    if selected_origin != "All":
        filtered_loads = filtered_loads[filtered_loads["origin_market_id"] == selected_origin]
    if selected_priority != "All":
        filtered_loads = filtered_loads[filtered_loads["priority"] == selected_priority]

    live_cols = st.columns(4)
    live_cols[0].metric("Customer revenue", money(filtered_loads["customer_sell_rate"].sum()))
    live_cols[1].metric("Fallback buy exposure", money(filtered_loads["fallback_buy_rate"].sum()))
    live_cols[2].metric("Expected trucks", f"{(capacity_signals['truck_count'] * capacity_signals['availability_confidence']).sum():.1f}")
    live_cols[3].metric("Forecast loads", f"{assets['forecast_demand']['expected_load_count'].sum():.1f}")

    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.markdown("#### Open demand by origin")
        demand_chart_data = filtered_loads.groupby(["origin_market_id", "priority"], as_index=False).agg(loads=("load_id", "count"))
        demand_chart = (
            alt.Chart(demand_chart_data)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("origin_market_id:N", title="Origin market"),
                y=alt.Y("loads:Q", title="Open loads"),
                color=alt.Color("priority:N", scale=alt.Scale(domain=["NORMAL", "HIGH", "CRITICAL"], range=["#7AA6C2", "#F4B942", "#D95D4F"])),
                tooltip=["origin_market_id", "priority", "loads"],
            )
            .properties(height=270)
        )
        st.altair_chart(demand_chart, use_container_width=True)
    with chart_right:
        st.markdown("#### Capacity confidence by origin")
        cap_chart_data = capacity_signals.copy()
        cap_chart_data["expected_trucks"] = cap_chart_data["truck_count"] * cap_chart_data["availability_confidence"]
        cap_chart = (
            alt.Chart(cap_chart_data)
            .mark_circle(opacity=0.85, stroke="white", strokeWidth=1)
            .encode(
                x=alt.X("origin_market_id:N", title="Origin market"),
                y=alt.Y("availability_confidence:Q", title="Availability confidence", scale=alt.Scale(domain=[0.3, 1])),
                size=alt.Size("truck_count:Q", title="Truck count", scale=alt.Scale(range=[180, 800])),
                color=alt.Color("source_type:N", title="Evidence"),
                tooltip=["carrier_id", "origin_market_id", "truck_count", alt.Tooltip("availability_confidence:Q", format=".0%"), "source_type"],
            )
            .properties(height=270)
        )
        st.altair_chart(cap_chart, use_container_width=True)

    load_columns = ["load_id", "customer_name", "lane_id", "pickup_start", "priority", "coverage_status", "customer_sell_rate", "fallback_buy_rate", "coverage_deadline"]
    if show_forecast:
        st.markdown("#### Known demand")
    st.dataframe(
        filtered_loads[load_columns].sort_values(["coverage_deadline", "priority"]),
        hide_index=True,
        use_container_width=True,
        column_config={
            "customer_sell_rate": st.column_config.NumberColumn("Sell", format="$%.0f"),
            "fallback_buy_rate": st.column_config.NumberColumn("Fallback buy", format="$%.0f"),
            "pickup_start": st.column_config.DatetimeColumn("Pickup", format="MMM D, HH:mm"),
            "coverage_deadline": st.column_config.DatetimeColumn("Cover by", format="HH:mm"),
        },
    )
    if show_forecast:
        st.markdown("#### Forecast demand worth protecting")
        st.dataframe(
            assets["forecast_demand"][["forecast_id", "customer_name", "lane_id", "expected_load_count", "forecast_confidence", "expected_sell_rate", "expected_arrival_time", "reserve_until"]],
            hide_index=True,
            use_container_width=True,
            column_config={
                "forecast_confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1, format="%.0f%%"),
                "expected_sell_rate": st.column_config.NumberColumn("Expected sell", format="$%.0f"),
            },
        )
    st.markdown("#### Capacity signals")
    carrier_names = assets["carriers"][["carrier_id", "carrier_name"]]
    cap_display = capacity_signals.merge(carrier_names, on="carrier_id", how="left")
    st.dataframe(
        cap_display[["capacity_signal_id", "carrier_name", "origin_market_id", "truck_count", "expected_rate", "availability_confidence", "source_type", "expires_at", "destination_preferences"]],
        hide_index=True,
        use_container_width=True,
        column_config={
            "expected_rate": st.column_config.NumberColumn("Expected rate", format="$%.0f"),
            "availability_confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1, format="%.0f%%"),
        },
    )

with tab_opt:
    st.subheader("Current plan vs optimized portfolio")
    st.markdown(
        '<div class="callout"><b>What changed:</b> the baseline allocates the cheapest visible capacity load-by-load. The optimizer prices fallback coverage, acceptance, service risk, and forecast option value across the entire book at once.</div>',
        unsafe_allow_html=True,
    )
    compare_cols = st.columns(4)
    compare_cols[0].metric("Incremental expected contribution", money(uplift), pct(uplift / max(current["expected_contribution"], 1)))
    compare_cols[1].metric("Carrier spend change", money(optimized["carrier_spend"] - current["carrier_spend"]), "optimized vs current", delta_color="inverse")
    compare_cols[2].metric("Known capacity assignments", optimized["known_capacity_assignments"], f"{optimized['known_capacity_assignments'] - current['known_capacity_assignments']:+d}")
    compare_cols[3].metric("Future option value", money(optimized["future_option_value"]), f"{optimized['reserved_units']} units reserved")

    metric_data = pd.DataFrame(
        [
            ("Gross margin", "Current plan", current["gross_margin"]),
            ("Gross margin", "Optimized plan", optimized["gross_margin"]),
            ("Expected contribution", "Current plan", current["expected_contribution"]),
            ("Expected contribution", "Optimized plan", optimized["expected_contribution"]),
            ("Expected risk cost", "Current plan", current["expected_risk_cost"]),
            ("Expected risk cost", "Optimized plan", optimized["expected_risk_cost"]),
        ],
        columns=["metric", "plan", "value"],
    )
    comparison_chart = (
        alt.Chart(metric_data)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X("plan:N", title=None, axis=alt.Axis(labelAngle=0)),
            xOffset="metric:N",
            y=alt.Y("value:Q", title="Dollars"),
            color=alt.Color("metric:N", scale=alt.Scale(range=["#18A999", "#2E6F95", "#D95D4F"])),
            tooltip=["metric", "plan", alt.Tooltip("value:Q", format="$,.0f")],
        )
        .properties(height=320)
    )
    st.altair_chart(comparison_chart, use_container_width=True)

    current_assign = result["current_assignments"][["load_id", "carrier_id", "expected_buy_rate", "weighted_value"]].rename(
        columns={"carrier_id": "current_carrier_id", "expected_buy_rate": "current_buy", "weighted_value": "current_value"}
    )
    optimized_open = result["optimized_open"][["load_id", "carrier_id", "expected_buy_rate", "weighted_value"]].rename(
        columns={"carrier_id": "optimized_carrier_id", "expected_buy_rate": "optimized_buy", "weighted_value": "optimized_value"}
    )
    comparison = open_loads[["load_id", "customer_name", "lane_id", "priority", "fallback_buy_rate"]].merge(current_assign, on="load_id", how="left").merge(optimized_open, on="load_id", how="left")
    names = assets["carriers"].set_index("carrier_id")["carrier_name"].to_dict()
    comparison["current_carrier"] = comparison["current_carrier_id"].map(names).fillna("Spot / fallback")
    comparison["optimized_carrier"] = comparison["optimized_carrier_id"].map(names).fillna("Spot / fallback")
    comparison["decision"] = comparison.apply(
        lambda row: "UNCHANGED" if row["current_carrier"] == row["optimized_carrier"] else "REALLOCATE",
        axis=1,
    )
    comparison["expected_buy_change"] = comparison["optimized_buy"].fillna(comparison["fallback_buy_rate"]) - comparison["current_buy"].fillna(comparison["fallback_buy_rate"])
    st.markdown("#### Load-level allocation changes")
    st.dataframe(
        comparison[["load_id", "customer_name", "lane_id", "priority", "current_carrier", "optimized_carrier", "decision", "expected_buy_change"]],
        hide_index=True,
        use_container_width=True,
        column_config={"expected_buy_change": st.column_config.NumberColumn("Expected buy Δ", format="$%.0f")},
    )

    reserve = result["optimized_forecast"].merge(assets["forecast_demand"][["forecast_id", "customer_name"]], left_on=result["optimized_forecast"]["load_id"].str.split("-S").str[0] if not result["optimized_forecast"].empty else "load_id", right_on="forecast_id", how="left") if not result["optimized_forecast"].empty else pd.DataFrame()
    if not reserve.empty:
        st.markdown("#### Reserved capacity")
        reserve["carrier_name"] = reserve["carrier_id"].map(names)
        st.dataframe(
            reserve[["load_id", "customer_name", "lane_id", "carrier_name", "arrival_probability", "weighted_value", "coverage_deadline"]],
            hide_index=True,
            use_container_width=True,
            column_config={
                "arrival_probability": st.column_config.ProgressColumn("Arrival probability", min_value=0, max_value=1, format="%.0f%%"),
                "weighted_value": st.column_config.NumberColumn("Option value", format="$%.0f"),
            },
        )
    st.download_button(
        "Download optimized decisions",
        data=result["optimized_assignments"].to_csv(index=False).encode("utf-8"),
        file_name="optimized_decisions.csv",
        mime="text/csv",
    )

with tab_decisions:
    st.subheader("Daily decisions and re-decisions")
    st.markdown(
        '<div class="callout"><b>Operating model:</b> every new load, quote, capacity signal, cancellation, or missed forecast creates a new run. Operators see what changed, why it changed, and when a held option must be released.</div>',
        unsafe_allow_html=True,
    )
    action_counts = recommendations.groupby("action").size().to_dict()
    dcols = st.columns(6)
    for idx, action in enumerate(["ASSIGN", "TENDER", "RESERVE", "WAIT", "RELEASE", "USE SPOT"]):
        dcols[idx].metric(action.title(), action_counts.get(action, 0))

    decision_left, decision_right = st.columns([1.25, 0.95])
    with decision_left:
        st.markdown("#### Prioritized action queue")
        queue = recommendations[["recommendation_id", "action", "load_id", "carrier_name", "lane_id", "expected_incremental_margin", "confidence", "expires_at", "status"]].copy()
        st.dataframe(
            queue,
            hide_index=True,
            use_container_width=True,
            height=360,
            column_config={
                "expected_incremental_margin": st.column_config.NumberColumn("Value", format="$%.0f"),
                "confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1, format="%.0f%%"),
                "expires_at": st.column_config.DatetimeColumn("Expires", format="MMM D, HH:mm"),
            },
        )
        st.markdown("#### Re-decision event stream")
        events = assets["events"].sort_values("event_time", ascending=False)
        for event in events.to_dict("records"):
            st.markdown(
                f"<div class='decision'><span class='muted small'>{pd.Timestamp(event['event_time']).strftime('%H:%M')} · {event['event_type'].replace('_',' ')}</span><br>"
                f"<b>{event['event_summary']}</b><br><span class='small'>Decision change: {event['decision_change']}</span></div>",
                unsafe_allow_html=True,
            )
    with decision_right:
        st.markdown("#### Recommendation detail")
        labels = {
            row["recommendation_id"]: f"{row['action']} · {row['load_id']} · {row['carrier_name']}"
            for row in recommendations.to_dict("records")
        }
        selected_id = st.selectbox("Select a recommendation", list(labels), format_func=lambda value: labels[value])
        selected = recommendations[recommendations["recommendation_id"] == selected_id].iloc[0]
        css_action = str(selected["action"]).lower().replace("use ", "")
        st.markdown(
            f"<div class='decision'><span class='pill pill-{css_action}'>{selected['action']}</span>"
            f"<h3 style='margin:.7rem 0 .3rem'>{selected['load_id']} · {selected['carrier_name']}</h3>"
            f"<div class='muted'>{selected['lane_id']} · expires {pd.Timestamp(selected['expires_at']).strftime('%H:%M')}</div>"
            f"<p>{selected['explanation']}</p></div>",
            unsafe_allow_html=True,
        )
        x1, x2, x3 = st.columns(3)
        x1.metric("Expected value", money(float(selected["expected_incremental_margin"])))
        x2.metric("Confidence", pct(float(selected["confidence"])))
        x3.metric("Similar loads", int(selected["historical_support_loads"]))

        if "feedback_rows" not in st.session_state:
            st.session_state.feedback_rows = []
        with st.form("feedback_form", clear_on_submit=True):
            decision = st.radio("Operator decision", ["ACCEPT", "REJECT", "MODIFY"], horizontal=True)
            reason = st.selectbox(
                "Reason",
                ["AGREE_WITH_MODEL", "CARRIER_NOT_AVAILABLE", "CUSTOMER_RESTRICTION", "RATE_TOO_LOW", "REP_KNOWLEDGE", "FORECAST_WRONG", "OTHER"],
            )
            notes = st.text_area("Notes", placeholder="Capture the tribal knowledge behind the correction…")
            submitted = st.form_submit_button("Save operator feedback", use_container_width=True)
        if submitted:
            st.session_state.feedback_rows.append(
                {
                    "recommendation_id": selected_id,
                    "decision": decision,
                    "reason": reason,
                    "notes": notes,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
            st.success("Feedback saved for this demo session.")
        if st.session_state.feedback_rows:
            feedback_df = pd.DataFrame(st.session_state.feedback_rows)
            st.download_button(
                "Download session feedback",
                data=feedback_df.to_csv(index=False).encode("utf-8"),
                file_name="recommendation_feedback.csv",
                mime="text/csv",
                use_container_width=True,
            )

