import os

import requests
import streamlit as st

st.set_page_config(
    page_title="Pitstop Prediction",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
COMPOUNDS = ("SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

    :root {
        --apex-bg: #0c0e12;
        --apex-panel: #13161d;
        --apex-panel-soft: #171a22;
        --apex-line: rgba(255,255,255,.075);
        --apex-muted: #858a98;
        --apex-white: #f5f5f4;
        --apex-red: #ed263a;
        --apex-green: #60d9a1;
    }

    html, body, [class*="css"], [data-testid="stAppViewContainer"] {
        background: var(--apex-bg);
        color: var(--apex-white);
        font-family: 'DM Sans', sans-serif;
    }

    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stAppViewContainer"] > .main { background: var(--apex-bg); }
    [data-testid="stMainBlockContainer"] {
        max-width: 1440px;
        padding: 2rem clamp(1.1rem, 3.5vw, 3.5rem) 4rem;
    }
    [data-testid="stSidebar"] {
        background: #101218;
        border-right: 1px solid var(--apex-line);
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.4rem;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #b6b9c3;
    }

    .apex-brand {
        display: flex;
        align-items: center;
        gap: 11px;
        color: var(--apex-white);
        font: 700 15px 'Space Grotesk', sans-serif;
        letter-spacing: 2.4px;
    }
    .apex-logo {
        display: grid;
        width: 54px;
        height: 38px;
        flex: 0 0 54px;
        place-items: center;
    }
    .apex-logo svg {
        display: block;
        width: 54px;
        height: 38px;
    }
    .apex-kicker {
        color: #a7abb7;
        font: 500 10px 'DM Mono', monospace;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    .apex-hero {
        position: relative;
        display: flex;
        min-height: 330px;
        overflow: hidden;
        align-items: center;
        justify-content: space-between;
        margin: 22px 0 25px;
        padding: clamp(26px, 5vw, 54px);
        border: 1px solid rgba(255,255,255,.13);
        border-radius: 20px;
        background:
            radial-gradient(ellipse at 77% 55%, rgba(237,38,58,.28), transparent 40%),
            radial-gradient(ellipse at 91% 13%, rgba(25,186,225,.16), transparent 31%),
            repeating-linear-gradient(0deg, rgba(255,255,255,.018) 0 1px, transparent 1px 5px),
            linear-gradient(118deg, #15171e 0%, #12141b 54%, #17141b 100%);
        box-shadow: inset 0 1px rgba(255,255,255,.07), 0 20px 70px rgba(0,0,0,.24);
    }
    .apex-hero:after {
        position: absolute;
        right: 0;
        bottom: 0;
        left: 0;
        height: 5px;
        background: linear-gradient(90deg, #ff3c33 0 18%, #ff8a24 18% 28%, #23c8c3 38% 49%, #4268ff 58% 69%, #ea4f9d 82%, transparent 100%);
        content: "";
    }
    .apex-hero-copy { position: relative; z-index: 2; max-width: 55%; }
    .apex-hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 9px;
        padding: 8px 11px;
        border: 1px solid rgba(255,255,255,.14);
        border-radius: 999px;
        background: rgba(8,10,14,.62);
        color: #e4e6eb;
        font: 500 9px 'DM Mono', monospace;
        letter-spacing: 1.4px;
        text-transform: uppercase;
    }
    .apex-hero-badge:before {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #64e3af;
        box-shadow: 0 0 13px rgba(100,227,175,.8);
        content: "";
    }
    .apex-hero h1 {
        margin: 19px 0 12px;
        color: var(--apex-white);
        font: 700 clamp(40px, 6vw, 70px)/.93 'Space Grotesk', sans-serif;
        letter-spacing: -4px;
        text-transform: uppercase;
    }
    .apex-hero h1 span {
        color: transparent;
        background: linear-gradient(100deg, #ff514b 5%, #ff8a43 48%, #f8d082 100%);
        background-clip: text;
        -webkit-background-clip: text;
    }
    .apex-hero p {
        max-width: 410px;
        margin: 0;
        color: #b6b9c3;
        font-size: 13px;
        line-height: 1.75;
    }
    .apex-hero-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 9px;
        margin-top: 24px;
    }
    .apex-hero-meta span {
        padding: 7px 10px;
        border: 1px solid rgba(255,255,255,.11);
        border-radius: 6px;
        background: rgba(255,255,255,.035);
        color: #d3d5dc;
        font: 10px 'DM Mono', monospace;
        letter-spacing: .8px;
    }
    .apex-race-art {
        position: absolute;
        inset: 0 0 0 auto;
        width: 58%;
        overflow: hidden;
        pointer-events: none;
    }
    .apex-livery-wall {
        position: absolute;
        top: -18%;
        right: -8%;
        bottom: -18%;
        display: grid;
        width: 82%;
        grid-template-columns: repeat(7, 1fr);
        transform: skewX(-13deg);
        opacity: .62;
        mask-image: linear-gradient(90deg, transparent 0%, rgba(0,0,0,.25) 14%, #000 65%);
    }
    .apex-livery-wall span:nth-child(1) { background: linear-gradient(180deg,#f7931e,#f35522 66%,#16171c); }
    .apex-livery-wall span:nth-child(2) { background: linear-gradient(180deg,#27c4c6,#14757e 65%,#16171c); }
    .apex-livery-wall span:nth-child(3) { background: linear-gradient(180deg,#416aff,#242c87 65%,#16171c); }
    .apex-livery-wall span:nth-child(4) { background: linear-gradient(180deg,#f33b4c,#a41436 65%,#16171c); }
    .apex-livery-wall span:nth-child(5) { background: linear-gradient(180deg,#ece9e1,#888991 65%,#16171c); }
    .apex-livery-wall span:nth-child(6) { background: linear-gradient(180deg,#57caa6,#177560 65%,#16171c); }
    .apex-livery-wall span:nth-child(7) { background: linear-gradient(180deg,#da64ab,#74275f 65%,#16171c); }
    .apex-livery-wall span { border-left: 1px solid rgba(255,255,255,.12); }
    .apex-race-art:after {
        position: absolute;
        right: -5%;
        bottom: 7%;
        left: 2%;
        height: 1px;
        background: linear-gradient(90deg,transparent,rgba(255,255,255,.55),transparent);
        box-shadow: 0 8px 0 rgba(255,255,255,.15), 0 16px 0 rgba(255,255,255,.08);
        content: "";
        transform: skewY(-5deg);
    }
    .apex-speed-line {
        position: absolute;
        right: 15%;
        height: 2px;
        border-radius: 2px;
        background: linear-gradient(90deg,transparent,rgba(255,255,255,.75));
        animation: apex-speed 3.2s ease-in-out infinite;
    }
    .apex-speed-line.one { top: 28%; width: 36%; }
    .apex-speed-line.two { top: 38%; right: 6%; width: 25%; animation-delay: .6s; }
    .apex-speed-line.three { top: 49%; right: 11%; width: 32%; animation-delay: 1.1s; }
    @keyframes apex-speed {
        0%, 100% { opacity: .18; transform: translateX(0); }
        50% { opacity: .8; transform: translateX(12px); }
    }
    .apex-car-illustration {
        position: absolute;
        right: -4%;
        bottom: 6%;
        width: 96%;
        height: 69%;
        overflow: visible;
        filter: drop-shadow(0 22px 20px rgba(0,0,0,.6));
    }
    .apex-car-glow {
        position: absolute;
        right: 12%;
        bottom: 14%;
        width: 65%;
        height: 16%;
        border-radius: 50%;
        background: rgba(237,38,58,.55);
        filter: blur(26px);
        transform: skewX(-27deg);
    }
    .apex-livery-tag {
        position: absolute;
        right: 7%;
        bottom: 5%;
        z-index: 1;
        color: rgba(255,255,255,.7);
        font: 9px 'DM Mono', monospace;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    .apex-divider {
        height: 1px;
        margin: 26px 0 21px;
        background: var(--apex-line);
    }
    .apex-section-title {
        margin: 0 0 5px;
        color: var(--apex-white);
        font: 600 18px 'Space Grotesk', sans-serif;
        letter-spacing: -.3px;
    }
    .apex-section-subtitle {
        margin: 0 0 19px;
        color: var(--apex-muted);
        font-size: 12px;
    }
    .apex-result {
        margin: 10px 0 16px;
        padding: 25px;
        border: 1px solid rgba(255,255,255,.09);
        border-radius: 15px;
        background: linear-gradient(135deg, #171a22, #12151b);
    }
    .apex-result-box { border-color: rgba(237,38,58,.38); }
    .apex-result-stay { border-color: rgba(96,217,161,.28); }
    .apex-result-kicker {
        color: #a4a8b3;
        font: 500 10px 'DM Mono', monospace;
        letter-spacing: 1.7px;
    }
    .apex-result-call {
        margin: 8px 0 4px;
        color: var(--apex-white);
        font: 700 clamp(27px, 4vw, 38px)/1.1 'Space Grotesk', sans-serif;
        letter-spacing: -1px;
    }
    .apex-red { color: var(--apex-red); }
    .apex-green { color: var(--apex-green); }
    .apex-result-note {
        margin: 0;
        color: #a0a4af;
        font-size: 13px;
    }
    .apex-footer {
        padding-top: 22px;
        color: #676c79;
        font: 10px 'DM Mono', monospace;
        letter-spacing: .6px;
        text-align: center;
    }
    div[data-testid="stMetric"] {
        padding: 15px 16px;
        border: 1px solid var(--apex-line);
        border-radius: 12px;
        background: var(--apex-panel);
    }
    div[data-testid="stMetricLabel"] {
        color: var(--apex-muted);
        font-size: 11px;
    }
    div[data-testid="stMetricValue"] {
        color: var(--apex-white);
        font-family: 'Space Grotesk', sans-serif;
        font-size: 25px;
    }
    div[data-testid="stButton"] > button,
    div[data-testid="stFormSubmitButton"] > button {
        min-height: 47px;
        border: 1px solid var(--apex-red);
        border-radius: 9px;
        background: var(--apex-red);
        color: white;
        font: 700 12px 'DM Sans', sans-serif;
        letter-spacing: 1.1px;
        transition: .18s ease;
    }
    div[data-testid="stButton"] > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {
        border-color: #ff4355;
        background: #ff4355;
        color: white;
        box-shadow: 0 5px 24px rgba(237,38,58,.19);
    }
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
        border-color: rgba(255,255,255,.1);
        border-radius: 8px;
        background-color: #11141a;
    }
    [data-testid="stForm"] {
        padding: 23px 24px 12px;
        border: 1px solid rgba(255,255,255,.11);
        border-radius: 16px;
        background:
            linear-gradient(135deg,rgba(255,255,255,.025),transparent 28%),
            rgba(19,22,29,.86);
        box-shadow: 0 16px 45px rgba(0,0,0,.2);
    }
    [data-testid="stForm"] [data-testid="stMarkdownContainer"] strong {
        color: #f0b879;
        font: 500 10px 'DM Mono', monospace;
        letter-spacing: 1.7px;
    }
    [data-testid="stMetric"] {
        position: relative;
        overflow: hidden;
        transition: transform .2s ease, border-color .2s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        border-color: rgba(255,255,255,.2);
    }
    [data-testid="stMetric"]:after {
        position: absolute;
        top: 0;
        left: 15px;
        width: 38px;
        height: 2px;
        background: linear-gradient(90deg,#ff514b,#ffb84e);
        content: "";
    }
    div[data-testid="stProgressBar"] > div > div { background: var(--apex-red); }
    @media (prefers-reduced-motion: reduce) {
        .apex-speed-line { animation: none; }
        [data-testid="stMetric"] { transition: none; }
    }
    @media (max-width: 700px) {
        [data-testid="stMainBlockContainer"] { padding-top: 1rem; }
        .apex-hero { min-height: 340px; align-items: flex-start; padding: 25px 20px; }
        .apex-hero-copy { max-width: 100%; }
        .apex-hero h1 { font-size: clamp(39px, 11vw, 58px); letter-spacing: -2.5px; }
        .apex-hero p { max-width: 95%; font-size: 12px; }
        .apex-race-art { inset: auto 0 0 auto; width: 72%; height: 59%; }
        .apex-livery-wall { width: 95%; }
        .apex-car-illustration { width: 112%; height: 76%; }
        [data-testid="stForm"] { padding: 16px 14px 8px; }
    }
    @media (max-width: 420px) {
        .apex-hero { min-height: 365px; }
        .apex-hero-meta { gap: 6px; }
        .apex-hero-meta span { font-size: 8px; }
        .apex-race-art { width: 84%; height: 52%; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="apex-brand">
      <span class="apex-logo" role="img" aria-label="Formula racing car">
        <svg viewBox="0 0 110 72" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M7 47h13l9-10 14-4 12-15 17-3 15 5 10 11-2 8 13 3 6 8H88l-5-7H31l-6 7H7v-3Z" fill="#ed263a"/>
          <path d="m43 32 10-12 15-2-3 14-22 2Z" fill="#1b1d23"/>
          <path d="m25 37 19-1 18 2 15-2 12 3 5 7H29l-4 5H11" stroke="#f5f5f4" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M15 44h13m55 0h19" stroke="#ed263a" stroke-width="3" stroke-linecap="round"/>
          <circle cx="34" cy="50" r="8" fill="#0c0e12" stroke="#f5f5f4" stroke-width="3"/>
          <circle cx="82" cy="50" r="8" fill="#0c0e12" stroke="#f5f5f4" stroke-width="3"/>
          <path d="M52 32h14" stroke="#f5f5f4" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </span>
      <span>PITSTOP <span style="color:#858a98;font-weight:400">PREDICTION</span></span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <section class="apex-hero">
      <div class="apex-hero-copy">
        <div class="apex-hero-badge">PIT WALL · STRATEGY SYSTEM</div>
        <h1>Own the<br><span>pit window.</span></h1>
        <p>Race-day energy. Data-backed calls. Feed the telemetry to your virtual pit wall and find out whether to box or stay out.</p>
        <div class="apex-hero-meta">
          <span>11 TELEMETRY SIGNALS</span>
          <span>28 MODEL FEATURES</span>
          <span>NEXT-LAP CALL</span>
        </div>
      </div>
      <div class="apex-race-art" aria-hidden="true">
        <div class="apex-livery-wall"><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>
        <i class="apex-speed-line one"></i>
        <i class="apex-speed-line two"></i>
        <i class="apex-speed-line three"></i>
        <div class="apex-car-glow"></div>
        <svg class="apex-car-illustration" viewBox="0 0 800 360" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M70 249 122 236 185 227 231 204 294 193 343 143 430 129 482 146 537 180 592 188 644 207 704 215 749 237 748 253 663 257 631 234 592 234 570 262 326 270 299 246 248 248 226 271 136 269 112 256 70 257Z" fill="#101218" stroke="#F3F4F6" stroke-width="5" stroke-linejoin="round"/>
          <path d="m233 205 61-12 49-50 87-14 52 17-28 42-96 15-61 27-66 1 2-26Z" fill="#ED263A"/>
          <path d="m385 146 39-2 23 38-79 7 17-43Z" fill="#222630" stroke="#F3F4F6" stroke-width="4" stroke-linejoin="round"/>
          <path d="m479 147 58 34-48 8-44-31 34-11Z" fill="#20BFC1"/>
          <path d="m126 237 59-10 45-23 4 28-53 20-55-15Z" fill="#F28C38"/>
          <path d="m536 180 56 8 52 19-1 13-84-5-23-35Z" fill="#4770FF"/>
          <path d="m62 224 70 2-1 12-55 16-23-4 9-26Zm592 6 54-3 45 12 4 14-66 4-37-27Z" fill="#F3F4F6" stroke="#F3F4F6" stroke-width="3" stroke-linejoin="round"/>
          <path d="M113 256h96m91 0h284m72 0h79" stroke="#ED263A" stroke-width="7" stroke-linecap="round"/>
          <path d="m344 214 36-9m59-4 33 7m-143 9 23 1" stroke="#F3F4F6" stroke-width="4" stroke-linecap="round"/>
          <circle cx="247" cy="255" r="48" fill="#0A0B0F" stroke="#A8ADB8" stroke-width="7"/>
          <circle cx="247" cy="255" r="24" fill="#242833" stroke="#ED263A" stroke-width="5"/>
          <circle cx="615" cy="255" r="48" fill="#0A0B0F" stroke="#A8ADB8" stroke-width="7"/>
          <circle cx="615" cy="255" r="24" fill="#242833" stroke="#20BFC1" stroke-width="5"/>
          <path d="M84 202h71m-94 19h58m499-46h89" stroke="#F7F7F4" stroke-opacity=".7" stroke-width="3" stroke-linecap="round"/>
          <path d="M107 213h30m-55 18h42m555-38h39" stroke="#F28C38" stroke-width="4" stroke-linecap="round"/>
        </svg>
        <div class="apex-livery-tag">TELEMETRY // RACE MODE</div>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### 🏁  PIT WALL")
    st.caption("Connect to your live prediction service.")
    api_base_url = st.text_input("FastAPI address", value=API_BASE_URL).strip().rstrip("/")
    st.caption("Start the API with `python -m uvicorn app:app`.")


@st.cache_data(ttl=10, show_spinner=False)
def check_api_health(base_url: str) -> tuple[bool, str]:
    try:
        response = requests.get(f"{base_url}/health", timeout=3)
        response.raise_for_status()
        health_payload = response.json()
        if not isinstance(health_payload, dict):
            return False, "The API health endpoint returned an unexpected response."
        if health_payload.get("status") != "ready":
            return False, "API is running, but the model is not ready."
        return True, "Model online"
    except requests.RequestException as error:
        return False, str(error)
    except ValueError:
        return False, "The API health endpoint returned invalid JSON."


if not api_base_url:
    st.sidebar.error("Enter a FastAPI address to connect.")
    api_ready = False
    api_message = "API address is empty."
else:
    api_ready, api_message = check_api_health(api_base_url)

if api_ready:
    st.sidebar.success(f"●  {api_message}")
else:
    st.sidebar.error("●  API offline")
    st.sidebar.caption(api_message)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "<span class='apex-kicker'>INFERENCE SERVICE</span>",
    unsafe_allow_html=True,
)
st.sidebar.caption("XGBoost · Pit next lap · FastAPI")
st.sidebar.markdown("---")
st.sidebar.caption("Strategy is a model prediction, not a live team radio.")

st.markdown(
    '<div class="apex-kicker">01 / Race snapshot</div>'
    '<div class="apex-section-title">Configure your telemetry</div>'
    '<div class="apex-section-subtitle">A complete trackside picture gives the model its best shot.</div>',
    unsafe_allow_html=True,
)

with st.form("race_telemetry"):
    st.markdown("**CAR & TYRE STATE**")
    compound_col, stint_col, tyre_life_col, pit_stop_col = st.columns(4)
    with compound_col:
        compound = st.selectbox("Tyre compound", options=COMPOUNDS, index=2)
    with stint_col:
        stint = st.number_input("Current stint", min_value=1, max_value=8, value=2)
    with tyre_life_col:
        tyre_life = st.number_input(
            "Tyre age · laps",
            min_value=0.0,
            max_value=100.0,
            value=39.0,
            step=1.0,
        )
    with pit_stop_col:
        pit_stop_label = st.selectbox(
            "Pit stop this lap?",
            options=("No", "Yes"),
            index=0,
        )

    lap_col, position_col, progress_col = st.columns(3)
    with lap_col:
        lap_number = st.number_input("Current lap", min_value=1, max_value=100, value=50)
    with position_col:
        position = st.number_input("Track position", min_value=1, max_value=20, value=8)
    with progress_col:
        race_progress = st.slider(
            "Race completed · %",
            min_value=0.0,
            max_value=100.0,
            value=71.4,
            step=0.1,
            format="%.1f%%",
        )

    st.markdown("**LIVE TIMING & DEGRADATION**")
    lap_time_col, lap_delta_col, degradation_col, position_change_col = st.columns(4)
    with lap_time_col:
        lap_time = st.number_input(
            "Lap time · seconds",
            min_value=1.0,
            max_value=300.0,
            value=78.491,
            step=0.001,
            format="%.3f",
        )
    with lap_delta_col:
        lap_delta = st.number_input(
            "Lap-time delta · sec",
            min_value=-300.0,
            max_value=300.0,
            value=-7.564,
            step=0.001,
            format="%.3f",
        )
    with degradation_col:
        cumulative_degradation = st.number_input(
            "Cumulative degradation",
            min_value=-1000.0,
            max_value=1000.0,
            value=21.019,
            step=0.001,
            format="%.3f",
        )
    with position_change_col:
        position_change = st.number_input(
            "Position change",
            min_value=-20,
            max_value=20,
            value=5,
            step=1,
        )

    st.markdown("")
    submit_col, hint_col = st.columns([1, 2.8], vertical_alignment="center")
    with submit_col:
        submitted = st.form_submit_button(
            "RUN ANALYSIS  →",
            use_container_width=True,
        )
    with hint_col:
        st.caption("11 telemetry inputs · One next-lap strategy call")

if submitted:
    payload = {
        "Compound": compound,
        "PitStop": int(pit_stop_label == "Yes"),
        "LapNumber": lap_number,
        "Stint": stint,
        "TyreLife": tyre_life,
        "Position": position,
        "LapTime (s)": lap_time,
        "LapTime_Delta": lap_delta,
        "Cumulative_Degradation": cumulative_degradation,
        "RaceProgress": race_progress / 100,
        "Position_Change": position_change,
    }

    with st.spinner("Sending telemetry to the pit wall…"):
        try:
            response = requests.post(
                f"{api_base_url}/predict",
                json=payload,
                timeout=15,
            )
            response.raise_for_status()
            result = response.json()
            required_fields = {
                "pit_probability",
                "recommendation",
                "urgency_score",
                "tyre_life_laps",
            }
            if not required_fields.issubset(result):
                raise ValueError("The prediction API returned an incomplete response.")
            if not 0 <= float(result["pit_probability"]) <= 1:
                raise ValueError("The prediction API returned an invalid probability.")
            st.session_state["apex_prediction"] = {
                **result,
                "lap": lap_number,
                "compound": compound,
                "position": position,
            }
        except requests.HTTPError as error:
            try:
                detail = error.response.json().get("detail", error.response.text)
            except (ValueError, AttributeError):
                detail = error.response.text if error.response is not None else str(error)
            st.error(f"Prediction API returned an error: {detail}")
        except requests.RequestException as error:
            st.error(f"Could not reach the FastAPI prediction service: {error}")
        except (ValueError, TypeError, KeyError) as error:
            st.error(f"Could not read the prediction response: {error}")

prediction = st.session_state.get("apex_prediction")
if prediction:
    probability = float(prediction["pit_probability"])
    recommendation = str(prediction["recommendation"])
    is_box_call = recommendation == "BOX THIS LAP"
    action_class = "apex-red" if is_box_call else "apex-green"
    result_class = "apex-result-box" if is_box_call else "apex-result-stay"
    action_note = (
        "Pit-stop probability crossed the model's 50% decision threshold."
        if is_box_call
        else "Model recommends extending the current stint for another lap."
    )

    st.markdown(
        '<div class="apex-divider"></div>'
        '<div class="apex-kicker">02 / Pit-wall call</div>'
        '<div class="apex-section-title">Next lap, decided</div>'
        '<div class="apex-section-subtitle">Model output for this telemetry snapshot.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <section class="apex-result {result_class}">
          <div class="apex-result-kicker">PIT WINDOW · LAP {prediction["lap"]} · {prediction["compound"]}</div>
          <div class="apex-result-call"><span class="{action_class}">{recommendation}</span></div>
          <p class="apex-result-note">{action_note}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    probability_col, urgency_col, tyre_col, position_result_col = st.columns(4)
    with probability_col:
        st.metric("PIT NEXT LAP", f"{probability:.1%}")
    with urgency_col:
        st.metric("TYRE URGENCY", f'{float(prediction["urgency_score"]):.1f}')
    with tyre_col:
        st.metric("TYRE AGE", f'{float(prediction["tyre_life_laps"]):g} laps')
    with position_result_col:
        st.metric("TRACK POSITION", f'P{prediction["position"]}')

    st.progress(probability, text="Pit-stop probability")
    st.caption("Prediction threshold: 50% · Decision support only; use race context before acting.")
else:
    st.markdown(
        """
        <div class="apex-divider"></div>
        <div class="apex-kicker">02 / Pit-wall call</div>
        <div class="apex-section-title">Waiting for telemetry</div>
        <div class="apex-section-subtitle">Submit a race snapshot above to reveal the model's next-lap strategy call.</div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="apex-footer">PITSTOP PREDICTION &nbsp;·&nbsp; XGBOOST INFERENCE &nbsp;·&nbsp; STRATEGY BEGINS HERE</div>',
    unsafe_allow_html=True,
)
