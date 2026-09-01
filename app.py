from __future__ import annotations

import time
from datetime import datetime
from html import escape
from typing import Dict

import altair as alt
import pandas as pd
import streamlit as st

from src.data import load_demo_assets, quality_summary
from src.optimizer import Scenario, build_recommendations, run_portfolio


st.set_page_config(
    page_title="Arcwise · Agent Library",
    page_icon="↗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      :root {
        --navy:#0E3472; --ink:#11213F; --muted:#667792; --line:#DDE5EF;
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
      .stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"] {
        background:var(--navy) !important; border-color:var(--navy) !important;
        color:white !important; opacity:1 !important;
      }
      .stButton > button[kind="primary"] p, button[data-testid="stBaseButton-primary"] p {
        color:white !important; opacity:1 !important;
      }
      .stButton > button:hover { border-color:var(--navy); color:var(--navy); }
      .stButton > button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {
        color:white !important; background:#0D2B52 !important;
      }
      div[data-baseweb="tab-list"] { gap:24px; border-bottom:1px solid var(--line); }
      button[data-baseweb="tab"] { padding:10px 4px; }
      .brandbar { display:flex; align-items:center; justify-content:space-between; padding:0 2px 20px; border-bottom:1px solid var(--line); margin-bottom:14px; }
      .brandleft { display:flex; align-items:center; gap:16px; }
      .arcwise-mark { width:35px; height:35px; display:grid; place-items:center; flex:0 0 auto; }
      .arcwise-mark svg { width:31px; height:31px; display:block; }
      .brand { font-size:1.22rem; font-weight:850; color:var(--navy); }
      .product { border-left:1px solid #CBD7E5; padding-left:16px; color:#66778D; font-size:1.05rem; }
      .library-link { color:#66778D !important; text-decoration:none !important; }
      .library-link:hover { color:var(--navy) !important; }
      .demo-badge { background:#EAF4FF; border:1px solid #C9E0F7; color:#245D93; padding:6px 11px; border-radius:8px; font-size:.78rem; font-weight:750; }
      .step-kicker { color:#7C8CA2; font-size:.84rem; font-weight:750; margin-top:30px; }
      .lead { color:#63758B; font-size:1rem; max-width:850px; margin-bottom:22px; }
      .info-card { background:white; border:1px solid var(--line); border-radius:12px; padding:17px 19px 24px; height:176px; box-sizing:border-box; display:flex; flex-direction:column; }
      .info-card h4 { margin:0 0 7px; color:var(--ink); font-size:.96rem; }
      .info-card p { margin:0; color:var(--muted); font-size:.84rem; line-height:1.48; }
      .info-card .tag { align-self:flex-start; margin-top:auto; }
      .tag { display:inline-block; margin-top:10px; background:#F2F5F9; color:#5F7188; border-radius:999px; padding:3px 8px; font-size:.7rem; font-weight:750; }
      .demo-stat-card { position:relative; display:flex; flex-direction:column; min-height:132px; box-sizing:border-box; padding:18px 19px 16px; background:white; border:1px solid var(--line); border-radius:12px; text-decoration:none !important; box-shadow:0 5px 16px rgba(25,52,87,.045); transition:transform .14s ease,border-color .14s ease,box-shadow .14s ease; }
      a.demo-stat-card:hover { transform:translateY(-2px); border-color:#8DB7F5; box-shadow:0 8px 20px rgba(25,52,87,.09); }
      .demo-stat-card.active { border-color:#6FA3EE; background:#F8FBFF; box-shadow:0 0 0 1px rgba(111,163,238,.18),0 8px 20px rgba(25,52,87,.08); }
      .demo-stat-source { position:absolute; top:14px; right:14px; display:inline-block; max-width:110px; background:#EEF4FC; color:#496B94; border-radius:999px; padding:3px 8px; font-size:.65rem; line-height:1.25; font-weight:800; white-space:nowrap; }
      .demo-stat-label { color:var(--muted); font-size:.84rem; line-height:1.25; font-weight:700; padding-right:105px; }
      .demo-stat-value { color:var(--ink); font-size:2rem; line-height:1.1; font-weight:760; margin-top:14px; }
      .demo-stat-action { color:#245D93; font-size:.7rem; line-height:1.2; font-weight:800; margin-top:auto; padding-top:10px; }
      [data-testid="stExpander"] { background:white; border-color:var(--line); border-radius:10px; }
      [data-testid="stExpander"] summary { min-height:50px; }
      .callout { background:#EEF4FC; border:1px solid #D4E1F1; border-radius:10px; padding:14px 17px; color:#34516F; margin:12px 0 20px; }
      .callout.success { background:#EDF9F4; border-color:#CDEBDD; color:#23664F; }
      .callout.warning { background:#FFF8EC; border-color:#F1DFC0; color:#825B22; }
      .checkline { display:flex; gap:11px; padding:8px 0; color:#42546A; }
      .check { color:var(--green); font-weight:900; }
      .build-stage { display:flex; gap:12px; padding:10px 0; }
      .build-stage-icon { width:22px; flex:0 0 22px; color:#718197; font-weight:850; }
      .build-stage.complete .build-stage-icon { color:var(--green); }
      .build-stage.current .build-stage-icon { color:var(--navy); }
      .build-stage-title { color:var(--ink); font-weight:780; margin-bottom:2px; }
      .build-stage-detail { color:var(--muted); font-size:.84rem; line-height:1.45; }
      .source-line { color:#8391A4; font-size:.82rem; margin-top:8px; }
      .section-rule { border-top:1px solid var(--line); margin:24px 0; }
      .decision-card { background:white; border:1px solid var(--line); border-radius:12px; padding:18px; }
      .action { display:inline-block; border-radius:999px; padding:4px 9px; font-size:.72rem; font-weight:850; }
      .assign,.tender { background:#DDF6EC; color:#147151; }
      .reserve { background:#FFF0CC; color:#8A6107; }
      .release { background:#FCE5E3; color:#A13831; }
      .footer-note { color:#8A98AA; font-size:.78rem; margin-top:28px; }
      .library-title { margin:22px 0 2px; color:var(--navy); font-size:2.15rem; line-height:1.15; font-weight:850; letter-spacing:-.035em; }
      .library-subtitle { margin:0 0 8px; color:#657692; font-size:1rem; }
      .library-controls [data-testid="stTextInput"] input,
      .library-controls [data-testid="stSelectbox"] > div > div { background:white; }
      .featured-agent { display:grid; grid-template-columns:minmax(330px,1.35fr) minmax(440px,1.55fr) 180px; gap:26px; align-items:center; background:#F8FBFF; border:1px solid #91B8F8; border-radius:12px; padding:18px 22px; margin:10px 0 16px; }
      .featured-identity { display:flex; gap:18px; align-items:center; min-width:0; }
      .featured-icon { width:96px; height:96px; border-radius:13px; background:white; display:grid; place-items:center; color:#0E3A83; box-shadow:0 4px 14px rgba(20,54,105,.06); flex:0 0 auto; }
      .featured-icon svg { width:62px; height:62px; }
      .featured-copy h3 { color:var(--navy); font-size:1.18rem !important; margin:0 0 6px !important; }
      .featured-copy p { margin:0 0 8px; font-size:.88rem; line-height:1.42; }
      .mini-flow { display:grid; grid-template-columns:repeat(6,1fr); position:relative; gap:6px; }
      .mini-flow:before { content:""; position:absolute; height:1px; background:#AFC9F4; left:8%; right:8%; top:17px; }
      .mini-step { position:relative; z-index:1; text-align:center; color:#15366E; font-size:.72rem; }
      .mini-step span { width:34px; height:34px; display:grid; place-items:center; margin:0 auto 6px; border:1px solid #91B8F8; background:white; color:#1261D8; border-radius:50%; font-weight:800; }
      .open-agent { display:inline-flex; align-items:center; justify-content:center; min-height:44px; border-radius:8px; background:var(--navy); color:white !important; text-decoration:none !important; font-weight:750; padding:0 17px; white-space:nowrap; }
      .open-agent:hover { background:#092A61; }
      .section-heading { display:flex; align-items:center; gap:10px; margin:13px 0 8px; color:var(--navy); font-weight:800; font-size:.96rem; }
      .section-heading:after { content:""; height:1px; background:var(--line); flex:1; }
      .agent-card { position:relative; display:flex; gap:13px; height:142px; box-sizing:border-box; padding:15px 14px; background:white; border:1px solid var(--line); border-radius:10px; text-decoration:none !important; box-shadow:0 2px 7px rgba(25,52,87,.035); transition:transform .14s ease,border-color .14s ease,box-shadow .14s ease; }
      a.agent-card:hover { transform:translateY(-2px); border-color:#8DB7F5; box-shadow:0 7px 18px rgba(25,52,87,.09); }
      .agent-card.available:after { content:""; position:absolute; width:8px; height:8px; border-radius:50%; background:#2FB43B; top:12px; right:12px; }
      .agent-icon { width:48px; height:48px; border-radius:10px; display:grid; place-items:center; flex:0 0 auto; }
      .agent-icon svg { width:29px; height:29px; }
      .agent-copy { min-width:0; height:100%; padding-right:5px; display:flex; flex-direction:column; }
      .agent-title { margin:0 0 4px; color:var(--navy); font-size:.89rem; line-height:1.24; font-weight:800; }
      .agent-copy p { margin:0 0 8px; color:#60718B; font-size:.75rem; line-height:1.37; }
      .agent-tag { display:inline-block; align-self:flex-start; margin-top:auto; border:1px solid currentColor; border-radius:4px; padding:2px 6px; font-size:.59rem; line-height:1.15; font-weight:850; letter-spacing:.02em; background:white; }
      .tone-blue { color:#1767DA; background:#EEF5FF; } .tone-violet { color:#7C3FD4; background:#F6F0FF; }
      .tone-teal { color:#0795A4; background:#ECFBFC; } .tone-indigo { color:#4B5FE4; background:#F0F2FF; }
      .tone-amber { color:#D68100; background:#FFF7E8; } .tone-coral { color:#ED584C; background:#FFF0EE; }
      .tone-purple { color:#8741C5; background:#F8F0FF; } .tone-green { color:#4B961F; background:#F1F9EC; }
      .tone-red { color:#D94F3F; background:#FFF0ED; } .tone-cyan { color:#0099C4; background:#ECFAFE; }
      .tone-slate { color:#5263D9; background:#F0F2FF; }
      @media (max-width:1000px) {
        .featured-agent { grid-template-columns:1fr; }
        .featured-identity { align-items:flex-start; }
        .open-agent { justify-self:start; }
      }
      #MainMenu, footer { visibility:hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


STEPS = ["Data", "Validate", "Capacity", "Settings", "Optimize", "Decisions"]
BUILD_STAGE_SECONDS = 2.5

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

BUYER_CONSOLIDATION_URL = "https://agents-buyer-consol.arcwise.app/"

AGENT_GROUPS = {
    "Consolidation": [
        {
            "name": "Buyer Consolidation Agent",
            "description": "Show any client, in their own numbers, whether buyer's consolidation pays off.",
            "tag": "SELL-SIDE",
            "tone": "violet",
            "icon": "users",
            "url": BUYER_CONSOLIDATION_URL,
        },
        {
            "name": "Container Shipment Consolidation Agent",
            "description": "Pack every client's cargo into the fewest containers the schedule allows.",
            "tag": "OPTIMIZATION",
            "tone": "amber",
            "icon": "container",
        },
        {
            "name": "Forward Consolidation Agent",
            "description": "See next month's containers before they're booked, and merge them early.",
            "tag": "PLANNING",
            "tone": "blue",
            "icon": "calendar",
        },
        {
            "name": "Consolidation Forecast Agent",
            "description": "Group cargo into containers weeks before the booking window opens.",
            "tag": "FORECAST",
            "tone": "teal",
            "icon": "chart",
        },
    ],
    "Trucking": [
        {
            "name": "Trucking Consolidation Agent",
            "description": "Merge the truck moves running the same lane on the same day.",
            "tag": "TRUCKING",
            "tone": "blue",
            "icon": "truck",
            "url": "?agent=trucking",
        },
        {
            "name": "Drayage Consolidation Agent",
            "description": "Stop tendering two trucks where one round trip clears both containers.",
            "tag": "DRAYAGE",
            "tone": "teal",
            "icon": "drayage",
        },
    ],
    "D&D & Charges": [
        {
            "name": "Detention & Demurrage Agent",
            "description": "Check every D&D line against free time before it reaches the invoice.",
            "tag": "CHARGES",
            "tone": "coral",
            "icon": "dollar",
        },
        {
            "name": "Demurrage Audit Agent",
            "description": "Catch the miscounted free days before you pay the carrier for them.",
            "tag": "AUDIT",
            "tone": "purple",
            "icon": "clipboard",
        },
        {
            "name": "Charge Recovery Agent",
            "description": "Rebill the D&D that belongs to the client and challenge the rest.",
            "tag": "BILLING",
            "tone": "green",
            "icon": "file",
        },
        {
            "name": "D&D Dispute Agent",
            "description": "Pull the port record and build the dispute the trucker can't wave off.",
            "tag": "DISPUTES",
            "tone": "amber",
            "icon": "scale",
        },
    ],
    "Visibility": [
        {
            "name": "Shipment Inbox Agent",
            "description": "Read every shipment email and say where the freight actually stands.",
            "tag": "VISIBILITY",
            "tone": "cyan",
            "icon": "inbox",
        },
        {
            "name": "Shipment Story Agent",
            "description": "Ask any shipment what happened and get it from the email trail.",
            "tag": "IN-TRANSIT",
            "tone": "slate",
            "icon": "route",
        },
    ],
}


def arcwise_logo() -> str:
    return """
    <span class="arcwise-mark" aria-hidden="true">
      <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="arcwise-a" x1="7.483" y1="0" x2="7.483" y2="20.213" gradientUnits="userSpaceOnUse" gradientTransform="translate(1.788 3.584) scale(.83276)">
            <stop stop-color="#3E6AC5"/><stop offset="1" stop-color="#808692" stop-opacity="0"/>
          </linearGradient>
          <linearGradient id="arcwise-b" x1="16.083" y1="6.506" x2="16.083" y2="20.213" gradientUnits="userSpaceOnUse" gradientTransform="translate(1.788 3.584) scale(.83276)">
            <stop stop-color="#3E6AC5"/><stop offset="1" stop-color="#808692" stop-opacity="0"/>
          </linearGradient>
        </defs>
        <path d="M2.333 20.416h3.481l7.893-13.93-1.542-2.903-9.832 16.833Z" fill="#093796"/>
        <path d="M2.333 20.416h3.481l7.893-13.93-1.542-2.903-9.832 16.833Z" fill="url(#arcwise-a)"/>
        <path d="M8.694 20.416h3.441l3.118-5.418 2.976 5.418h3.439L15.247 9.001 8.694 20.416Z" fill="#093796"/>
        <path d="M8.694 20.416h3.441l3.118-5.418 2.976 5.418h3.439L15.247 9.001 8.694 20.416Z" fill="url(#arcwise-b)"/>
      </svg>
    </span>
    """


def agent_icon(name: str) -> str:
    paths = {
        "users": '<circle cx="9" cy="8" r="3"/><circle cx="18" cy="9" r="2.5"/><path d="M3 21v-2c0-3.2 2.7-5.5 6-5.5s6 2.3 6 5.5v2"/><path d="M15 14.5c3.3 0 6 1.9 6 4.5v2"/>',
        "container": '<path d="M3 7h18v14H3z"/><path d="M7 7v14M11 7v14M15 7v14M19 7v14M7 4h10"/>',
        "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18M8 14h3M14 14h3M8 18h3"/>',
        "chart": '<path d="M4 21V11h4v10M10 21V5h4v16M16 21V8h4v13"/>',
        "truck": '<path d="M3 6h11v11H3zM14 10h4l3 4v3h-7z"/><circle cx="7" cy="19" r="2"/><circle cx="18" cy="19" r="2"/>',
        "drayage": '<path d="M5 7h14v14H5zM3 7h18M8 7V4h8v3M9 11v6M15 11v6"/>',
        "dollar": '<circle cx="12" cy="12" r="9"/><path d="M15 8.5c-.8-.7-1.7-1-2.9-1-1.7 0-3.1.8-3.1 2.2 0 3.6 6.2 1.8 6.2 5.4 0 1.4-1.3 2.4-3.2 2.4-1.3 0-2.5-.4-3.3-1.2M12 5v14"/>',
        "clipboard": '<rect x="5" y="5" width="14" height="17" rx="2"/><path d="M9 5V3h6v2M8 13l2.5 2.5L16 10"/>',
        "file": '<path d="M6 3h8l5 5v13H6zM14 3v5h5"/><path d="M14.5 12c-.6-.5-1.3-.7-2.1-.7-1.2 0-2.2.6-2.2 1.5 0 2.4 4.4 1.3 4.4 3.7 0 1-1 1.7-2.3 1.7-.9 0-1.8-.3-2.4-.8M12.3 9.5V20"/>',
        "scale": '<path d="M12 4v17M6 6h12M5 6l-3 7h6L5 6ZM19 6l-3 7h6l-3-7ZM8 21h8"/>',
        "inbox": '<path d="M4 5h16l2 10v5H2v-5L4 5Z"/><path d="M2 15h6l2 3h4l2-3h6"/>',
        "route": '<circle cx="17" cy="6" r="3"/><path d="M17 9c-3 4-3 5-3 5M5 7h4a3 3 0 0 1 0 6H6a3 3 0 0 0 0 6h13"/>',
    }
    path = paths.get(name, paths["chart"])
    return f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{path}</svg>'


def agent_card(agent: dict) -> str:
    url = agent.get("url")
    wrapper = "a" if url else "div"
    target = "_blank" if url and url.startswith("https://") else "_self"
    rel = ' rel="noopener noreferrer"' if target == "_blank" else ""
    href = f' href="{escape(url, quote=True)}" target="{target}"{rel}' if url else ""
    available = " available" if url else ""
    return f"""
    <{wrapper} class="agent-card{available}"{href}>
      <span class="agent-icon tone-{agent['tone']}">{agent_icon(agent['icon'])}</span>
      <span class="agent-copy">
        <div class="agent-title">{escape(agent['name'])}</div>
        <p>{escape(agent['description'])}</p>
        <span class="agent-tag tone-{agent['tone']}">{escape(agent['tag'])}</span>
      </span>
    </{wrapper}>
    """


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
    st.markdown(
        f"""
        <div class="brandbar">
          <div class="brandleft">
            {arcwise_logo()}<div class="brand">Arcwise</div>
            <a class="product library-link" href="./" target="_self">Trucking Consolidation</a>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_library_header() -> None:
    st.markdown(
        f"""
        <div class="brandbar">
          <div class="brandleft">
            {arcwise_logo()}<div class="brand">Arcwise</div>
            <div class="product">Agent Library</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_featured_agent() -> None:
    steps = "".join(
        f'<div class="mini-step"><span>{index}</span>{label}</div>'
        for index, label in enumerate(STEPS, start=1)
    )
    st.markdown(
        f"""
        <div class="featured-agent">
          <div class="featured-identity">
            <div class="featured-icon">{agent_icon('truck')}</div>
            <div class="featured-copy">
              <h3>Trucking Consolidation Agent</h3>
              <p>Merge the truck moves running the same lane on the same day.</p>
              <span class="agent-tag tone-blue">TRUCKING</span>
            </div>
          </div>
          <div class="mini-flow">{steps}</div>
          <a class="open-agent" href="?agent=trucking" target="_self">Open workflow&nbsp; →</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_agent_library() -> None:
    render_library_header()
    st.markdown('<div class="library-title">Agent Library</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="library-subtitle">Deploy specialist workflows across your freight operation</div>',
        unsafe_allow_html=True,
    )

    search_col, filter_col, status_col = st.columns([3.8, 4.1, 1.35], vertical_alignment="bottom")
    with search_col:
        search = st.text_input(
            "Search agents",
            placeholder="Search agents…",
            label_visibility="collapsed",
        )
    with filter_col:
        category = st.segmented_control(
            "Agent category",
            ["All", "Consolidation", "Trucking", "D&D", "Visibility"],
            default="All",
            label_visibility="collapsed",
        )
    with status_col:
        st.selectbox(
            "Agent status",
            ["All statuses"],
            label_visibility="collapsed",
            disabled=True,
        )

    query = search.strip().casefold()
    selected = category or "All"
    featured_text = "trucking consolidation agent merge the truck moves running the same lane on the same day"
    if selected in ("All", "Trucking") and (not query or query in featured_text):
        render_featured_agent()

    category_map = {
        "All": set(AGENT_GROUPS),
        "Consolidation": {"Consolidation"},
        "Trucking": {"Trucking"},
        "D&D": {"D&D & Charges"},
        "Visibility": {"Visibility"},
    }
    visible_cards = 0
    for group, agents in AGENT_GROUPS.items():
        if group not in category_map[selected]:
            continue
        matches = [
            agent
            for agent in agents
            if not query
            or query in f"{agent['name']} {agent['description']} {agent['tag']}".casefold()
        ]
        if not matches:
            continue
        visible_cards += len(matches)
        st.markdown(f'<div class="section-heading">{escape(group)}</div>', unsafe_allow_html=True)
        for start in range(0, len(matches), 4):
            row = matches[start : start + 4]
            columns = st.columns(4)
            for column, agent in zip(columns, row):
                column.markdown(agent_card(agent), unsafe_allow_html=True)

    if visible_cards == 0 and not (selected in ("All", "Trucking") and query in featured_text):
        st.info("No agents match that search yet.")


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

    upload_tab, demo_tab = st.tabs(
        ["Upload CSVs", "Use current demo data"],
        default="Use current demo data",
    )
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
        preview_options = [
            ("historical_loads", "Historical loads", "TMS history"),
            ("open_loads", "Open loads", "TMS"),
            ("capacity_signals", "Capacity signals", "Capacity sheet"),
            ("forecast_demand", "Forecast patterns", "Forecast"),
        ]
        selected_preview = st.query_params.get("preview")
        cols = st.columns(4)
        for column, (name, label, source) in zip(cols, preview_options):
            active = " active" if selected_preview == name else ""
            column.markdown(
                f'<a class="demo-stat-card{active}" href="?agent=trucking&amp;preview={name}" target="_self">'
                f'<span class="demo-stat-source">{source}</span>'
                f'<span class="demo-stat-label">{label}</span>'
                f'<span class="demo-stat-value">{len(assets[name]):,}</span>'
                '<span class="demo-stat-action">View rows →</span>'
                '</a>',
                unsafe_allow_html=True,
            )

        preview_lookup = {name: (label, source) for name, label, source in preview_options}
        if selected_preview in preview_lookup:
            preview_label, preview_source = preview_lookup[selected_preview]
            preview_frame = assets[selected_preview]
            st.markdown(f"#### {preview_label} rows")
            st.caption(f"Showing the first 20 of {len(preview_frame):,} rows · Source: {preview_source}")
            st.dataframe(preview_frame.head(20), hide_index=True, use_container_width=True)

        st.caption("Synthetic companies, lanes, rates, and carrier behavior. No client or production information is included.")
        if st.button("Use current demo data", type="primary", use_container_width=False):
            st.session_state.overrides = {}
            st.session_state.data_mode = "Demo data"
            st.session_state.optimization_result = None
            go_to(2)

    with st.expander("What the product reads", expanded=False):
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

    with st.expander("Download canonical examples", expanded=False):
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
        st.session_state.optimization_result = None
        st.session_state.recommendations = None
        go_to(5)


def build_stage_markup(
    stages: list[tuple[str, str]],
    completed_count: int,
    current_index: int | None = None,
) -> str:
    rows = []
    for index, (title, detail) in enumerate(stages):
        if index < completed_count:
            state, icon = "complete", "✓"
        elif index == current_index:
            state, icon = "current", "●"
        else:
            continue
        rows.append(
            f'<div class="build-stage {state}">'
            f'<span class="build-stage-icon">{icon}</span>'
            f'<div><div class="build-stage-title">{title}</div>'
            f'<div class="build-stage-detail">{detail}</div></div></div>'
        )
    return "".join(rows)


def render_optimize_step(assets: Dict[str, pd.DataFrame]) -> None:
    step_title(
        5,
        "Review today’s dispatch plan",
        "We’ll compare every open load with the trucks you can use, then recommend where each truck should go—or whether to hold it for likely upcoming freight.",
    )
    open_loads = assets["open_loads"]
    capacity = assets["capacity_signals"]
    forecast = assets["forecast_demand"]
    usable_capacity = capacity[
        capacity["availability_confidence"] >= st.session_state.confidence_floor
    ]
    stages = [
        (
            "Reading today’s freight",
            f"{len(open_loads):,} open loads across {open_loads['lane_id'].nunique()} lanes are ready to plan.",
        ),
        (
            "Checking available trucks",
            f"{int(usable_capacity['truck_count'].sum())} usable trucks from {usable_capacity['carrier_id'].nunique()} carriers have a strong enough availability signal.",
        ),
        (
            "Matching lanes, equipment, and pickup times",
            "Removing choices where the truck is in the wrong market, has the wrong equipment, or cannot meet the pickup window.",
        ),
        (
            "Reviewing carrier history",
            "Using past lane support, acceptance, and on-time service to judge which matches are dependable.",
        ),
        (
            "Keeping upcoming freight in view",
            f"Checking {len(forecast):,} recurring freight patterns before using all of today’s capacity.",
        ),
        (
            "Comparing regular and backup coverage",
            "Checking known-carrier choices against spot coverage so every open load still has a workable backup.",
        ),
        (
            "Building the best overall dispatch plan",
            "Placing each truck where it helps the full book of freight—not simply the first load in the queue.",
        ),
        (
            "Checking every recommendation",
            "Confirming that no truck is used twice and every recommendation follows the operating rules.",
        ),
    ]

    if st.session_state.optimization_result is not None and st.session_state.recommendations is not None:
        st.markdown(build_stage_markup(stages, len(stages)), unsafe_allow_html=True)
        recommendation_count = len(st.session_state.recommendations)
        st.markdown(
            f'<div class="callout success"><b>Dispatch plan ready:</b> {recommendation_count} recommendations passed the final checks. Review the proposed assignments, reserves, releases, and backup coverage when you are ready.</div>',
            unsafe_allow_html=True,
        )
        back_col, results_col, _ = st.columns([1, 1.7, 5])
        if back_col.button("Back", use_container_width=True):
            go_to(4)
        if results_col.button("See results", type="primary", use_container_width=True):
            go_to(6)
        return

    st.markdown(
        '<div class="callout"><b>What happens next:</b> we compare all open loads and available trucks at the same time. You will see each check as it finishes, and the app will wait here until you choose to open the results.</div>',
        unsafe_allow_html=True,
    )

    back_col, run_col, _ = st.columns([1, 1.7, 5])
    if back_col.button("Back", use_container_width=True):
        go_to(4)
    if run_col.button("Build recommended plan", type="primary", use_container_width=True):
        scenario = Scenario(
            forecast_multiplier=st.session_state.forecast_multiplier,
            risk_multiplier=st.session_state.risk_multiplier,
            capacity_confidence_floor=st.session_state.confidence_floor,
        )
        progress = st.progress(0, text="Starting the dispatch review…")
        stage_area = st.empty()
        result = None
        recommendations = None
        try:
            for index in range(6):
                stage_area.markdown(
                    build_stage_markup(stages, index, index),
                    unsafe_allow_html=True,
                )
                progress.progress(
                    (index + 1) / len(stages),
                    text=f"Step {index + 1} of {len(stages)} · {stages[index][0]}",
                )
                time.sleep(BUILD_STAGE_SECONDS)

            stage_area.markdown(
                build_stage_markup(stages, 6, 6),
                unsafe_allow_html=True,
            )
            progress.progress(7 / len(stages), text=f"Step 7 of {len(stages)} · {stages[6][0]}")
            result = run_portfolio(
                assets["open_loads"],
                assets["forecast_demand"],
                assets["capacity_signals"],
                assets["carrier_lane_stats"],
                assets["carrier_preferences"],
                scenario,
            )
            time.sleep(BUILD_STAGE_SECONDS)
            recommendations = build_recommendations(result, assets["open_loads"], assets["carriers"])

            stage_area.markdown(
                build_stage_markup(stages, 7, 7),
                unsafe_allow_html=True,
            )
            progress.progress(1.0, text=f"Step 8 of {len(stages)} · {stages[7][0]}")
            time.sleep(BUILD_STAGE_SECONDS)

            st.session_state.optimization_result = result
            st.session_state.recommendations = recommendations
            st.session_state.run_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.rerun()
        except Exception:
            progress.empty()
            stage_area.empty()
            st.error("We couldn’t finish the dispatch plan. Please review the inputs and try again.")


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
    has_feedback = bool(st.session_state.decision_log)
    action_cols = st.columns(5 if has_feedback else 4)
    action_cols[0].download_button(
        "Download decisions",
        recommendations.to_csv(index=False).encode("utf-8"),
        file_name="capacity_recommendations.csv",
        mime="text/csv",
        width="stretch",
    )
    action_cols[1].download_button(
        "Download assignments",
        result["optimized_assignments"].to_csv(index=False).encode("utf-8"),
        file_name="optimized_assignments.csv",
        mime="text/csv",
        width="stretch",
    )
    action_index = 2
    if has_feedback:
        action_cols[action_index].download_button(
            "Download feedback",
            pd.DataFrame(st.session_state.decision_log).to_csv(index=False).encode("utf-8"),
            file_name="operator_feedback.csv",
            mime="text/csv",
            width="stretch",
        )
        action_index += 1
    if action_cols[action_index].button("Change assumptions", type="primary", width="stretch"):
        go_to(4)
    if action_cols[action_index + 1].button("Start with new data", type="primary", width="stretch"):
        reset_workflow()
    st.markdown(
        f'<div class="footer-note">Run created {st.session_state.get("run_at", "this session")} · Synthetic demo context · Decision support only; no carrier tender was executed.</div>',
        unsafe_allow_html=True,
    )


initialize_state()

if st.query_params.get("agent") == "trucking":
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
else:
    render_agent_library()
