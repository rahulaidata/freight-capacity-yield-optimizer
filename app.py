from __future__ import annotations

from datetime import datetime
from typing import Dict

import altair as alt
import pandas as pd
import streamlit as st

from src.data import load_demo_assets, quality_summary
from src.optimizer import Scenario, build_recommendations, run_portfolio


st.set_page_config(
    page_title="CapacityOS · Freight Yield",
    page_icon="↗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      :root {
        --navy:#123663; --ink:#172235; --muted:#718096; --line:#DDE5EF;
        --wash:#F5F8FC; --blue-wash:#EBF3FC; --green:#17A673;
        --amber:#C77A12; --red:#D44D42;
      }
      .stApp { background:#FBFCFE; color:var(--ink); }
      .block-container { max-width:1450px; padding-top:2.2rem; padding-bottom:4rem; }
      h1,h2,h3 { color:var(--ink); letter-spacing:-.025em; }
      h1 { font-size:2.25rem !important; }
      h2 { font-size:1.65rem !important; margin-top:.2rem !important; }
      h3 { font-size:1.08rem !important; }
      p, .stCaption { color:var(--muted); }
      [data-testid="stHeader"] { background:rgba(251,252,254,.92); }
      [data-testid="stMetric"] {
        background:white; border:1px solid var(--line); border-radius:12px;
        padding:16px 18px; box-shadow:0 5px 16px rgba(25,52,87,.045);
      }
      [data-testid="stMetricLabel"] { color:var(--muted); font-weight:650; }
      [data-testid="stMetricValue"] { color:var(--ink); }
      [data-testid="stFileUploaderDropzone"] {
        background:white; border:1.5px dashed #C7D5E6; border-radius:14px;
        min-height:94px;
      }
      [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
      .stButton > button, .stDownloadButton > button {
        border-radius:9px; min-height:2.85rem; font-weight:700; border-color:#C8D5E5;
      }
      .stButton > button[kind="primary"] { background:var(--navy); border-color:var(--navy); }
      .stButton > button:hover { border-color:var(--navy); color:var(--navy); }
      .stButton > button[kind="primary"]:hover { color:white; background:#0D2B52; }
      div[data-baseweb="tab-list"] { gap:24px; border-bottom:1px solid var(--line); }
      button[data-baseweb="tab"] { padding:10px 4px; }
      .brandbar { display:flex; align-items:center; justify-content:space-between; padding:0 2px 20px; border-bottom:1px solid var(--line); margin-bottom:14px; }
      .brandleft { display:flex; align-items:center; gap:16px; }
      .mark { width:35px; height:35px; border-radius:10px; background:linear-gradient(145deg,#123663,#2669A8); color:white; display:grid; place-items:center; font-weight:900; font-size:1.25rem; }
      .brand { font-size:1.22rem; font-weight:850; color:var(--navy); }
      .product { border-left:1px solid #CBD7E5; padding-left:16px; color:#66778D; font-size:1.05rem; }
      .demo-badge { background:#EAF4FF; border:1px solid #C9E0F7; color:#245D93; padding:6px 11px; border-radius:8px; font-size:.78rem; font-weight:750; }
      .step-kicker { color:#7C8CA2; font-size:.84rem; font-weight:750; margin-top:30px; }
      .lead { color:#63758B; font-size:1rem; max-width:850px; margin-bottom:22px; }
      .info-card { background:white; border:1px solid var(--line); border-radius:12px; padding:17px 19px; min-height:126px; }
      .info-card h4 { margin:0 0 7px; color:var(--ink); font-size:.96rem; }
      .info-card p { margin:0; color:var(--muted); font-size:.84rem; line-height:1.48; }
      .tag { display:inline-block; margin-top:10px; background:#F2F5F9; color:#5F7188; border-radius:999px; padding:3px 8px; font-size:.7rem; font-weight:750; }
      .callout { background:#EEF4FC; border:1px solid #D4E1F1; border-radius:10px; padding:14px 17px; color:#34516F; margin:12px 0 20px; }
      .callout.success { background:#EDF9F4; border-color:#CDEBDD; color:#23664F; }
      .callout.warning { background:#FFF8EC; border-color:#F1DFC0; color:#825B22; }
      .checkline { display:flex; gap:11px; padding:8px 0; color:#42546A; }
      .check { color:var(--green); font-weight:900; }
      .source-line { color:#8391A4; font-size:.82rem; margin-top:8px; }
      .section-rule { border-top:1px solid var(--line); margin:24px 0; }
      .decision-card { background:white; border:1px solid var(--line); border-radius:12px; padding:18px; }
      .action { display:inline-block; border-radius:999px; padding:4px 9px; font-size:.72rem; font-weight:850; }
      .assign,.tender { background:#DDF6EC; color:#147151; }
      .reserve { background:#FFF0CC; color:#8A6107; }
      .release { background:#FCE5E3; color:#A13831; }
      .footer-note { color:#8A98AA; font-size:.78rem; margin-top:28px; }
      #MainMenu, footer { visibility:hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


STEPS = ["Data", "Validate", "Capacity", "Settings", "Optimize", "Decisions"]

UPLOAD_DATES = {
    "open_loads": [
        "load_created_timestamp", "pickup_start", "pickup_end", "delivery_start",
        "delivery_end", "coverage_deadline",
    ],
    "capacity_signals": ["available_from", "available_until", "observed_at", "expires_at"],
    "historical_loads": [
        "load_created_timestamp", "carrier_assigned_timestamp", "pickup_datetime", "delivery_datetime",
    ],
    "forecast_demand": ["expected_arrival_time", "expected_pickup_end", "reserve_until"],
}

REQUIRED_UPLOAD_COLUMNS = {
    "open_loads": {
        "load_id", "customer_id", "customer_name", "lane_id", "origin_market_id",
        "destination_market_id", "equipment_class", "pickup_start", "pickup_end",
        "customer_sell_rate", "fallback_buy_rate", "coverage_deadline", "priority", "service_tier",
    },
    "capacity_signals": {
        "capacity_signal_id", "carrier_id", "origin_market_id", "equipment_class",
        "available_from", "available_until", "truck_count", "expected_rate",
        "availability_confidence", "source_type",
    },
}


@st.cache_data(show_spinner=False)
def demo_assets() -> Dict[str, pd.DataFrame]:
    return load_demo_assets()


def money(value: float) -> str:
    return f"${value:,.0f}"


def percent(value: float) -> str:
    return f"{value:.0%}"


def initialize_state() -> None:
    defaults = {
        "workflow_step": 1,
        "max_step": 1,
        "data_mode": "Not selected",
        "overrides": {},
        "optimization_result": None,
        "recommendations": None,
        "forecast_multiplier": 1.0,
        "risk_multiplier": 1.0,
        "confidence_floor": 0.45,
        "decision_log": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def go_to(step: int) -> None:
    st.session_state.workflow_step = step
    st.session_state.max_step = max(st.session_state.max_step, step)
    st.rerun()


def reset_workflow() -> None:
    for key in [
        "workflow_step", "max_step", "data_mode", "overrides", "optimization_result",
        "recommendations", "decision_log", "open_loads_upload", "capacity_upload",
        "history_upload", "forecast_upload",
    ]:
        st.session_state.pop(key, None)
    st.rerun()


def active_assets() -> Dict[str, pd.DataFrame]:
    current = {name: frame.copy() for name, frame in demo_assets().items()}
    current.update(st.session_state.overrides)
    return current


def parse_upload(uploaded, asset_name: str) -> pd.DataFrame:
    frame = pd.read_csv(uploaded)
    for column in UPLOAD_DATES.get(asset_name, []):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return frame


def validate_required(frame: pd.DataFrame, asset_name: str) -> list[str]:
    required = REQUIRED_UPLOAD_COLUMNS.get(asset_name, set())
    return sorted(required - set(frame.columns))


def render_header() -> None:
    badge = "Illustrative data" if st.session_state.data_mode != "Uploaded CSVs" else "Session upload"
    st.markdown(
        f"""
        <div class="brandbar">
          <div class="brandleft">
            <div class="mark">↗</div><div class="brand">CapacityOS</div>
            <div class="product">Freight Yield Optimizer</div>
          </div>
          <div class="demo-badge">{badge}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stepper() -> None:
    columns = st.columns(6)
    for index, label in enumerate(STEPS, start=1):
        completed = index < st.session_state.workflow_step and index <= st.session_state.max_step
        text = f"✓  {label}" if completed else f"{index}  {label}"
        disabled = index > st.session_state.max_step
        if columns[index - 1].button(
            text,
            key=f"step_{index}",
            disabled=disabled,
            type="primary" if index == st.session_state.workflow_step else "secondary",
            use_container_width=True,
        ):
            st.session_state.workflow_step = index
            st.rerun()


def step_title(number: int, title: str, description: str) -> None:
    st.markdown(f'<div class="step-kicker">Step {number} of 6</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="lead">{description}</div>', unsafe_allow_html=True)


def render_bottom_navigation(back: int | None, forward: int | None, forward_label: str = "Continue") -> None:
    left, middle, _ = st.columns([1, 1.2, 4.8])
    if back is not None and left.button("Back", use_container_width=True):
        go_to(back)
    if forward is not None and middle.button(forward_label, type="primary", use_container_width=True):
        go_to(forward)


def render_data_step() -> None:
    step_title(
        1,
        "Start with the freight book",
        "Upload today’s operating files, or use the included broker dataset to walk through the complete decision flow immediately.",
    )

    upload_tab, demo_tab = st.tabs(["Upload CSVs", "Use current demo data"])
    with upload_tab:
        st.markdown("#### Required operating files")
        left, right = st.columns(2)
        open_upload = left.file_uploader(
            "Open loads CSV",
            type="csv",
            key="open_loads_upload",
            help="One row per open load from the TMS or open-load report.",
        )
        capacity_upload = right.file_uploader(
            "Carrier capacity CSV",
            type="csv",
            key="capacity_upload",
            help="One row per carrier capacity signal, commitment, or inferred truck pool.",
        )
        with st.expander("Optional history and forecast files"):
            opt_left, opt_right = st.columns(2)
            history_upload = opt_left.file_uploader(
                "Historical loads CSV", type="csv", key="history_upload"
            )
            forecast_upload = opt_right.file_uploader(
                "Forecast demand CSV", type="csv", key="forecast_upload"
            )
            st.caption("If omitted, this MVP uses the included reference history and demand forecast while replacing the live freight and capacity files.")

        if open_upload is not None or capacity_upload is not None:
            ready = open_upload is not None and capacity_upload is not None
            if not ready:
                st.info("Add both required files to continue: open loads and carrier capacity.")
            if st.button("Read uploaded files", type="primary", disabled=not ready):
                uploads = {
                    "open_loads": open_upload,
                    "capacity_signals": capacity_upload,
                    "historical_loads": history_upload,
                    "forecast_demand": forecast_upload,
                }
                overrides = {}
                problems = []
                for name, uploaded in uploads.items():
                    if uploaded is None:
                        continue
                    try:
                        frame = parse_upload(uploaded, name)
                        missing = validate_required(frame, name)
                        if missing:
                            problems.append(f"{name}: missing {', '.join(missing)}")
                        else:
                            overrides[name] = frame
                    except Exception as exc:
                        problems.append(f"{name}: {exc}")
                if problems:
                    st.error("Could not read the upload. " + " | ".join(problems))
                else:
                    st.session_state.overrides = overrides
                    st.session_state.data_mode = "Uploaded CSVs"
                    st.session_state.optimization_result = None
                    go_to(2)

    with demo_tab:
        st.markdown(
            '<div class="callout success"><b>Client-demo path:</b> use a complete fictional brokerage dataset with open freight, carrier history, probabilistic capacity, recurring demand, and prior decision events.</div>',
            unsafe_allow_html=True,
        )
        assets = demo_assets()
        cols = st.columns(4)
        cols[0].metric("Historical loads", f"{len(assets['historical_loads']):,}")
        cols[1].metric("Open loads", len(assets["open_loads"]))
        cols[2].metric("Capacity signals", len(assets["capacity_signals"]))
        cols[3].metric("Forecast patterns", len(assets["forecast_demand"]))
        st.caption("Synthetic companies, lanes, rates, and carrier behavior. No client or production information is included.")
        if st.button("Use current demo data", type="primary", use_container_width=False):
            st.session_state.overrides = {}
            st.session_state.data_mode = "Demo data"
            st.session_state.optimization_result = None
            go_to(2)

    st.markdown("#### What the product reads")
    cards = st.columns(4)
    definitions = [
        ("Open freight", "Loads, customers, lanes, pickup windows, sell rates, fallback rates, urgency, and service tiers.", "TMS · required"),
        ("Carrier capacity", "Origin pool, equipment, available window, expected buy rate, truck count, evidence source, and confidence.", "Capacity sheet · required"),
        ("Carrier history", "Booked rates, acceptance, on-time service, falloff, lane support, and relationship strength.", "TMS history · recommended"),
        ("Expected freight", "Recurring customer tenders, expected count and revenue, arrival probability, and reserve deadline.", "Forecast · optional"),
    ]
    for card, (title, body, tag) in zip(cards, definitions):
        card.markdown(
            f'<div class="info-card"><h4>{title}</h4><p>{body}</p><span class="tag">{tag}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("#### Download canonical examples")
    assets = demo_assets()
    downloads = st.columns(4)
    for column, name, label in zip(
        downloads,
        ["open_loads", "capacity_signals", "historical_loads", "forecast_demand"],
        ["Open loads", "Capacity", "History", "Forecast"],
    ):
        column.download_button(
            f"{label} example",
            assets[name].head(25).to_csv(index=False).encode("utf-8"),
            file_name=f"{name}_example.csv",
            mime="text/csv",
            use_container_width=True,
        )


def render_validate_step(assets: Dict[str, pd.DataFrame]) -> None:
    step_title(
        2,
        "Confirm what we read",
        "Before optimizing, make the source data legible: record counts, economics, required fields, and the operational assumptions inherited from each file.",
    )
    quality = quality_summary(assets)
    blocking = int((quality["quality_score"] < 90).sum())
    metrics = st.columns(6)
    metrics[0].metric("Open loads", f"{len(assets['open_loads']):,}")
    metrics[1].metric("Customers", assets["open_loads"]["customer_id"].nunique())
    metrics[2].metric("Carriers", assets["carriers"]["carrier_id"].nunique())
    metrics[3].metric("Capacity signals", len(assets["capacity_signals"]))
    metrics[4].metric("Open revenue", money(float(assets["open_loads"]["customer_sell_rate"].sum())))
    metrics[5].metric("Blocking issues", blocking)

    min_date = pd.to_datetime(assets["historical_loads"]["pickup_datetime"]).min()
    max_date = pd.to_datetime(assets["historical_loads"]["pickup_datetime"]).max()
    st.markdown(
        f'<div class="source-line">History window {min_date:%b %d, %Y} to {max_date:%b %d, %Y} · {assets["historical_loads"]["lane_id"].nunique()} lanes · {assets["open_loads"]["equipment_class"].nunique()} equipment class</div>',
        unsafe_allow_html=True,
    )

    st.markdown("#### Data quality findings")
    findings = [
        f"{len(assets['open_loads']):,} open loads have a lane, pickup window, customer sell rate, and fallback buy rate.",
        f"{len(assets['capacity_signals']):,} capacity signals include an evidence source and probability of availability.",
        f"{len(assets['historical_loads']):,} historical loads support carrier rate, acceptance, and service profiles.",
    ]
    for finding in findings:
        st.markdown(f'<div class="checkline"><span class="check">✓</span><span>{finding}</span></div>', unsafe_allow_html=True)
    if blocking:
        st.markdown('<div class="callout warning"><b>Review required:</b> at least one canonical asset is below the 90% readiness threshold.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="callout success"><b>Ready to continue:</b> no blocking schema or required-value issues were found.</div>', unsafe_allow_html=True)

    with st.expander("View required-field checks"):
        st.dataframe(
            quality,
            hide_index=True,
            use_container_width=True,
            column_config={
                "quality_score": st.column_config.ProgressColumn("Quality", min_value=0, max_value=100, format="%.0f%%"),
            },
        )
    with st.expander("Preview source-system records"):
        source = st.selectbox(
            "Dataset",
            ["open_loads", "capacity_signals", "historical_loads", "forecast_demand", "carriers"],
            format_func=lambda value: value.replace("_", " ").title(),
        )
        st.dataframe(assets[source].head(20), hide_index=True, use_container_width=True)

    render_bottom_navigation(1, 3, "Continue to capacity")


def render_capacity_step(assets: Dict[str, pd.DataFrame]) -> None:
    step_title(
        3,
        "See demand and capacity together",
        "The optimizer works across the whole book. This is the shared market picture it will use—not a one-load carrier search.",
    )
    open_loads = assets["open_loads"]
    capacity = assets["capacity_signals"].copy()
    forecast = assets["forecast_demand"]
    capacity["expected_trucks"] = capacity["truck_count"] * capacity["availability_confidence"]
    demand_market = open_loads.groupby("origin_market_id", as_index=False).agg(
        open_loads=("load_id", "count"),
        customer_revenue=("customer_sell_rate", "sum"),
        fallback_exposure=("fallback_buy_rate", "sum"),
    )
    capacity_market = capacity.groupby("origin_market_id", as_index=False).agg(
        signaled_trucks=("truck_count", "sum"), expected_trucks=("expected_trucks", "sum")
    )
    forecast_market = forecast.groupby("origin_market_id", as_index=False).agg(
        forecast_loads=("expected_load_count", "sum")
    )
    market = demand_market.merge(capacity_market, on="origin_market_id", how="outer").merge(
        forecast_market, on="origin_market_id", how="outer"
    ).fillna(0)
    market["expected_gap"] = market["expected_trucks"] - market["open_loads"]

    metrics = st.columns(5)
    metrics[0].metric("Known open loads", len(open_loads))
    metrics[1].metric("Urgent loads", int(open_loads["priority"].isin(["HIGH", "CRITICAL"]).sum()))
    metrics[2].metric("Signaled trucks", int(capacity["truck_count"].sum()))
    metrics[3].metric("Probability-weighted trucks", f"{capacity['expected_trucks'].sum():.1f}")
    metrics[4].metric("Expected future loads", f"{forecast['expected_load_count'].sum():.1f}")

    chart_data = market.melt(
        id_vars="origin_market_id",
        value_vars=["open_loads", "expected_trucks", "forecast_loads"],
        var_name="book_component",
        value_name="units",
    )
    chart = (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("origin_market_id:N", title="Origin market"),
            xOffset="book_component:N",
            y=alt.Y("units:Q", title="Loads / probability-weighted trucks"),
            color=alt.Color(
                "book_component:N",
                title=None,
                scale=alt.Scale(
                    domain=["open_loads", "expected_trucks", "forecast_loads"],
                    range=["#123663", "#38A88A", "#E2A33A"],
                ),
            ),
            tooltip=["origin_market_id", "book_component", alt.Tooltip("units:Q", format=".1f")],
        )
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)

    known_tab, capacity_tab, forecast_tab = st.tabs(["Known freight", "Carrier capacity", "Forecasted freight"])
    with known_tab:
        st.dataframe(
            open_loads[[
                "load_id", "customer_name", "lane_id", "pickup_start", "priority",
                "service_tier", "customer_sell_rate", "fallback_buy_rate", "coverage_deadline",
            ]].sort_values("coverage_deadline"),
            hide_index=True,
            use_container_width=True,
            column_config={
                "customer_sell_rate": st.column_config.NumberColumn("Sell", format="$%.0f"),
                "fallback_buy_rate": st.column_config.NumberColumn("Fallback buy", format="$%.0f"),
            },
        )
    with capacity_tab:
        carriers = assets["carriers"][["carrier_id", "carrier_name", "relationship_tier"]]
        display = capacity.merge(carriers, on="carrier_id", how="left")
        st.dataframe(
            display[[
                "carrier_name", "origin_market_id", "equipment_class", "truck_count",
                "expected_rate", "availability_confidence", "source_type", "relationship_tier", "expires_at",
            ]],
            hide_index=True,
            use_container_width=True,
            column_config={
                "expected_rate": st.column_config.NumberColumn("Expected buy", format="$%.0f"),
                "availability_confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1, format="%.0f%%"),
            },
        )
    with forecast_tab:
        st.dataframe(
            forecast[[
                "forecast_id", "customer_name", "lane_id", "expected_load_count",
                "forecast_confidence", "expected_sell_rate", "expected_arrival_time", "reserve_until",
            ]],
            hide_index=True,
            use_container_width=True,
            column_config={
                "forecast_confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1, format="%.0f%%"),
                "expected_sell_rate": st.column_config.NumberColumn("Expected sell", format="$%.0f"),
            },
        )

    render_bottom_navigation(2, 4, "Set operating assumptions")


def render_settings_step() -> None:
    step_title(
        4,
        "Set operating assumptions",
        "Choose how much uncertainty the first run should tolerate. These controls change reservation behavior and risk-adjusted contribution—not the underlying source data.",
    )
    left, middle, right = st.columns(3)
    with left:
        st.markdown("#### Future-demand confidence")
        st.session_state.forecast_multiplier = st.slider(
            "Forecast confidence multiplier",
            0.50,
            1.20,
            float(st.session_state.forecast_multiplier),
            0.05,
            help="Scales the probability that forecasted freight arrives.",
        )
        st.caption("1.00 uses the forecast as supplied. Lower values make capacity reservations less likely.")
    with middle:
        st.markdown("#### Service-risk posture")
        st.session_state.risk_multiplier = st.slider(
            "Failure-cost multiplier",
            0.50,
            2.00,
            float(st.session_state.risk_multiplier),
            0.10,
            help="Scales expected costs from rejection, falloff, and service failure.",
        )
        st.caption("1.00 is balanced. Higher values favor reliable capacity over the lowest nominal buy rate.")
    with right:
        st.markdown("#### Capacity evidence")
        st.session_state.confidence_floor = st.slider(
            "Minimum availability confidence",
            0.35,
            0.90,
            float(st.session_state.confidence_floor),
            0.05,
            help="Excludes weak or stale carrier capacity signals from allocation.",
        )
        st.caption("Signals below this floor remain visible but cannot consume an optimizer capacity unit.")

    st.markdown('<div class="callout"><b>Recommended first pass:</b> use the supplied forecast, balanced service risk, and a 45% capacity-confidence floor. This shows the economic tradeoff between immediate assignment and reservation without overstating certainty.</div>', unsafe_allow_html=True)

    with st.expander("Portfolio objective"):
        st.markdown(
            "Maximize expected customer revenue minus carrier buy cost, fallback coverage cost, and service-risk cost, plus the probability-weighted option value of capacity reserved for likely future freight."
        )
    with st.expander("Hard feasibility rules"):
        st.markdown(
            "A truck can serve at most one demand unit. Equipment, origin market, pickup window, carrier-lane support, and capacity availability must match. Every open load can fall back to spot coverage if no positive-value assignment exists."
        )
    with st.expander("Decision vocabulary"):
        st.markdown(
            "**ASSIGN** a high-confidence carrier, **TENDER** when acceptance is less certain, **RESERVE** for expected freight, **RELEASE** unused capacity, or rely on **SPOT / fallback** coverage."
        )

    left_nav, reset_col, run_col, _ = st.columns([1, 1.3, 1.8, 4])
    if left_nav.button("Back", use_container_width=True):
        go_to(3)
    if reset_col.button("Reset recommended", use_container_width=True):
        st.session_state.forecast_multiplier = 1.0
        st.session_state.risk_multiplier = 1.0
        st.session_state.confidence_floor = 0.45
        st.rerun()
    if run_col.button("Review and build", type="primary", use_container_width=True):
        go_to(5)


def render_optimize_step(assets: Dict[str, pd.DataFrame]) -> None:
    step_title(
        5,
        "Build the decision model",
        "The portfolio engine will create feasible load × carrier choices, price risk and fallback coverage, and allocate every usable capacity unit once.",
    )
    open_loads = assets["open_loads"]
    capacity = assets["capacity_signals"]
    forecast = assets["forecast_demand"]
    checks = [
        f"Reading {len(open_loads):,} open loads across {open_loads['lane_id'].nunique()} lanes.",
        f"Evaluating {int(capacity['truck_count'].sum())} signaled trucks from {capacity['carrier_id'].nunique()} carriers.",
        f"Protecting option value for {forecast['expected_load_count'].sum():.1f} expected future loads.",
        f"Applying a {percent(st.session_state.confidence_floor)} capacity floor and {st.session_state.risk_multiplier:.1f}× service-risk penalty.",
    ]
    for check in checks:
        st.markdown(f'<div class="checkline"><span class="check">✓</span><span>{check}</span></div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="callout"><b>What will run:</b> an exact maximum-value assignment across the complete demand book. The baseline covers loads first-come using the cheapest visible capacity; the optimized plan prices the opportunity cost of using that truck elsewhere.</div>',
        unsafe_allow_html=True,
    )

    back_col, run_col, _ = st.columns([1, 1.7, 5])
    if back_col.button("Back", use_container_width=True):
        go_to(4)
    if run_col.button("Run portfolio optimizer", type="primary", use_container_width=True):
        scenario = Scenario(
            forecast_multiplier=st.session_state.forecast_multiplier,
            risk_multiplier=st.session_state.risk_multiplier,
            capacity_confidence_floor=st.session_state.confidence_floor,
        )
        with st.spinner("Allocating capacity across the freight book…"):
            result = run_portfolio(
                assets["open_loads"],
                assets["forecast_demand"],
                assets["capacity_signals"],
                assets["carrier_lane_stats"],
                assets["carrier_preferences"],
                scenario,
            )
            recommendations = build_recommendations(result, assets["open_loads"], assets["carriers"])
            st.session_state.optimization_result = result
            st.session_state.recommendations = recommendations
            st.session_state.run_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        go_to(6)


def allocation_comparison(result: dict, assets: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    open_loads = assets["open_loads"]
    current = result["current_assignments"]
    optimized = result["optimized_open"]
    current_cols = current[["load_id", "carrier_id", "expected_buy_rate"]].rename(
        columns={"carrier_id": "current_carrier_id", "expected_buy_rate": "current_buy"}
    ) if not current.empty else pd.DataFrame(columns=["load_id", "current_carrier_id", "current_buy"])
    optimized_cols = optimized[["load_id", "carrier_id", "expected_buy_rate"]].rename(
        columns={"carrier_id": "optimized_carrier_id", "expected_buy_rate": "optimized_buy"}
    ) if not optimized.empty else pd.DataFrame(columns=["load_id", "optimized_carrier_id", "optimized_buy"])
    frame = open_loads[[
        "load_id", "customer_name", "lane_id", "priority", "fallback_buy_rate"
    ]].merge(current_cols, on="load_id", how="left").merge(optimized_cols, on="load_id", how="left")
    names = assets["carriers"].set_index("carrier_id")["carrier_name"].to_dict()
    frame["current_plan"] = frame["current_carrier_id"].map(names).fillna("Spot / fallback")
    frame["optimized_plan"] = frame["optimized_carrier_id"].map(names).fillna("Spot / fallback")
    frame["decision"] = frame.apply(
        lambda row: "UNCHANGED" if row["current_plan"] == row["optimized_plan"] else "REALLOCATE", axis=1
    )
    frame["expected_buy_change"] = (
        frame["optimized_buy"].fillna(frame["fallback_buy_rate"])
        - frame["current_buy"].fillna(frame["fallback_buy_rate"])
    )
    return frame


def render_decisions_step(assets: Dict[str, pd.DataFrame]) -> None:
    result = st.session_state.optimization_result
    recommendations = st.session_state.recommendations
    if result is None or recommendations is None:
        st.warning("Run the portfolio optimizer before opening decisions.")
        if st.button("Go to optimizer"):
            go_to(5)
        return

    step_title(
        6,
        "Today’s capacity decisions",
        "Compare the current operating plan with the optimized portfolio, then inspect the reasoning behind every assignment, tender, reservation, and release.",
    )
    current = result["current_metrics"]
    optimized = result["optimized_metrics"]
    uplift = optimized["expected_contribution"] - current["expected_contribution"]
    spend_change = optimized["carrier_spend"] - current["carrier_spend"]
    metrics = st.columns(5)
    metrics[0].metric("Expected contribution", money(optimized["expected_contribution"]), money(uplift))
    metrics[1].metric("Optimized carrier spend", money(optimized["carrier_spend"]), money(spend_change), delta_color="inverse")
    metrics[2].metric("Loads on known capacity", optimized["known_capacity_assignments"])
    metrics[3].metric("Capacity reserved", f"{optimized['reserved_units']} units", money(optimized["future_option_value"]))
    metrics[4].metric("Spot / fallback loads", optimized["spot_or_fallback_loads"])
    st.markdown(
        f'<div class="callout success"><b>Portfolio result:</b> the model creates {money(uplift)} of incremental expected contribution versus the load-by-load baseline while preserving {optimized["reserved_units"]} capacity units for probable future freight.</div>',
        unsafe_allow_html=True,
    )

    overview_tab, decisions_tab, changes_tab, events_tab = st.tabs(
        ["Executive summary", "Decision queue", "Allocation changes", "Re-decision history"]
    )
    with overview_tab:
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
        chart = (
            alt.Chart(metric_data)
            .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
            .encode(
                x=alt.X("plan:N", title=None, axis=alt.Axis(labelAngle=0)),
                xOffset="metric:N",
                y=alt.Y("value:Q", title="Dollars"),
                color=alt.Color("metric:N", scale=alt.Scale(range=["#2E6F95", "#18A979", "#D45B50"])),
                tooltip=["metric", "plan", alt.Tooltip("value:Q", format="$,.0f")],
            )
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)
        hist = assets["historical_loads"]
        replay_rate = min(0.05, max(0.02, uplift / max(current["carrier_spend"], 1) * 0.28))
        replay_value = float(hist["carrier_buy_rate"].sum()) * replay_rate
        st.markdown("#### Historical proof-of-value context")
        replay_cols = st.columns(4)
        replay_cols[0].metric("Loads available for replay", f"{len(hist):,}")
        replay_cols[1].metric("Historical carrier spend", money(float(hist["carrier_buy_rate"].sum())))
        replay_cols[2].metric("Historical gross margin", money(float(hist["gross_margin"].sum())))
        replay_cols[3].metric("Illustrative recoverable value", money(replay_value), percent(replay_rate))

    with decisions_tab:
        filter_cols = st.columns([1, 1, 3])
        actions = ["All"] + sorted(recommendations["action"].unique().tolist())
        selected_action = filter_cols[0].selectbox("Action", actions)
        min_confidence = filter_cols[1].slider("Minimum confidence", 0.0, 1.0, 0.0, 0.05)
        queue = recommendations.copy()
        if selected_action != "All":
            queue = queue[queue["action"] == selected_action]
        queue = queue[queue["confidence"] >= min_confidence]
        st.dataframe(
            queue[[
                "recommendation_id", "action", "load_id", "carrier_name", "lane_id",
                "expected_incremental_margin", "confidence", "expires_at", "status",
            ]],
            hide_index=True,
            use_container_width=True,
            column_config={
                "expected_incremental_margin": st.column_config.NumberColumn("Expected value", format="$%.0f"),
                "confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1, format="%.0f%%"),
            },
        )
        if not queue.empty:
            selected_id = st.selectbox("Explain a recommendation", queue["recommendation_id"].tolist())
            selected = queue[queue["recommendation_id"] == selected_id].iloc[0]
            action_class = selected["action"].lower()
            st.markdown(
                f'<div class="decision-card"><span class="action {action_class}">{selected["action"]}</span><h3>{selected["load_id"]} · {selected["carrier_name"]}</h3><p>{selected["explanation"]}</p><div class="source-line">Acceptance {percent(selected["accept_probability"]) if pd.notna(selected["accept_probability"]) else "n/a"} · Service {percent(selected["service_probability"]) if pd.notna(selected["service_probability"]) else "n/a"} · {int(selected["historical_support_loads"]) if pd.notna(selected["historical_support_loads"]) else 0} supporting historical loads</div></div>',
                unsafe_allow_html=True,
            )
            with st.form("operator_feedback"):
                disposition = st.radio("Operator response", ["ACCEPT", "REJECT", "DEFER"], horizontal=True)
                reason = st.text_input("Reason or tribal knowledge", placeholder="Example: carrier is already committed to another customer move")
                if st.form_submit_button("Save response"):
                    st.session_state.decision_log.append(
                        {
                            "recommendation_id": selected_id,
                            "response": disposition,
                            "reason": reason,
                            "created_at": datetime.now().isoformat(timespec="seconds"),
                        }
                    )
                    st.success("Response captured for the next model-learning cycle.")

    with changes_tab:
        comparison = allocation_comparison(result, assets)
        st.dataframe(
            comparison[[
                "load_id", "customer_name", "lane_id", "priority", "current_plan",
                "optimized_plan", "decision", "expected_buy_change",
            ]],
            hide_index=True,
            use_container_width=True,
            column_config={"expected_buy_change": st.column_config.NumberColumn("Expected buy Δ", format="$%.0f")},
        )

    with events_tab:
        st.markdown(
            '<div class="callout"><b>Continuous decisioning:</b> every load, quote, capacity signal, cancellation, or missed forecast can trigger a new portfolio run and change the recommendation queue.</div>',
            unsafe_allow_html=True,
        )
        st.dataframe(
            assets["events"][["event_time", "event_type", "event_summary", "decision_change"]].sort_values("event_time", ascending=False),
            hide_index=True,
            use_container_width=True,
        )

    st.markdown("#### Export and continue")
    export_cols = st.columns([1.3, 1.3, 1.3, 3])
    export_cols[0].download_button(
        "Download decisions",
        recommendations.to_csv(index=False).encode("utf-8"),
        file_name="capacity_recommendations.csv",
        mime="text/csv",
        use_container_width=True,
    )
    export_cols[1].download_button(
        "Download assignments",
        result["optimized_assignments"].to_csv(index=False).encode("utf-8"),
        file_name="optimized_assignments.csv",
        mime="text/csv",
        use_container_width=True,
    )
    if st.session_state.decision_log:
        export_cols[2].download_button(
            "Download feedback",
            pd.DataFrame(st.session_state.decision_log).to_csv(index=False).encode("utf-8"),
            file_name="operator_feedback.csv",
            mime="text/csv",
            use_container_width=True,
        )
    rerun_col, restart_col, _ = st.columns([1.5, 1.5, 4])
    if rerun_col.button("Change assumptions", use_container_width=True):
        go_to(4)
    if restart_col.button("Start with new data", use_container_width=True):
        reset_workflow()
    st.markdown(
        f'<div class="footer-note">Run created {st.session_state.get("run_at", "this session")} · Synthetic demo context · Decision support only; no carrier tender was executed.</div>',
        unsafe_allow_html=True,
    )


initialize_state()
render_header()
render_stepper()
assets = active_assets()
step = st.session_state.workflow_step

if step == 1:
    render_data_step()
elif step == 2:
    render_validate_step(assets)
elif step == 3:
    render_capacity_step(assets)
elif step == 4:
    render_settings_step()
elif step == 5:
    render_optimize_step(assets)
else:
    render_decisions_step(assets)
