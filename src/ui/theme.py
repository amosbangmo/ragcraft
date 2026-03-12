import streamlit as st


def apply_theme():
    st.markdown(
        """
        <style>
        :root {
            --bg: #0b1020;
            --panel: #121a2b;
            --panel-2: #182235;
            --border: rgba(255,255,255,0.08);
            --text: #e8edf7;
            --muted: #9fb0d0;
            --accent: #5b8cff;
            --accent-2: #7c5cff;
            --success: #16a34a;
            --warning: #f59e0b;
        }

        .stApp {
            background:
                radial-gradient(circle at top right, rgba(91,140,255,0.15), transparent 25%),
                radial-gradient(circle at top left, rgba(124,92,255,0.12), transparent 20%),
                linear-gradient(180deg, #0b1020 0%, #0d1324 100%);
            color: var(--text);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0a0f1d 0%, #121a2b 100%);
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] * {
            color: var(--text);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }

        .hero-card {
            background: linear-gradient(135deg, rgba(18,26,43,0.92), rgba(24,34,53,0.88));
            border: 1px solid var(--border);
            border-radius: 22px;
            padding: 28px 28px 22px 28px;
            margin-bottom: 1rem;
            box-shadow: 0 12px 40px rgba(0,0,0,0.18);
        }

        .hero-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            background: rgba(91,140,255,0.14);
            border: 1px solid rgba(91,140,255,0.25);
            color: #cfe0ff;
            font-size: 0.85rem;
            margin-bottom: 10px;
        }

        .hero-title {
            margin: 0;
            font-size: 2rem;
            line-height: 1.2;
            color: white;
        }

        .hero-subtitle {
            margin-top: 10px;
            color: var(--muted);
            font-size: 1rem;
            line-height: 1.6;
            max-width: 900px;
        }

        .section-card {
            background: linear-gradient(180deg, rgba(18,26,43,0.92), rgba(18,26,43,0.82));
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 18px 18px 10px 18px;
            margin-bottom: 1rem;
        }

        .card-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: white;
            margin-bottom: 6px;
        }

        .card-subtitle {
            color: var(--muted);
            font-size: 0.92rem;
            margin-bottom: 10px;
        }

        .kpi-card {
            background: linear-gradient(180deg, rgba(18,26,43,0.96), rgba(24,34,53,0.86));
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 14px 16px;
        }

        .source-card {
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 14px 14px 10px 14px;
            margin-bottom: 10px;
        }

        .source-title {
            font-weight: 700;
            color: white;
            margin-bottom: 6px;
        }

        .source-preview {
            color: var(--muted);
            font-size: 0.93rem;
            line-height: 1.5;
        }

        .small-muted {
            color: var(--muted);
            font-size: 0.88rem;
        }

        .stButton > button,
        .stDownloadButton > button {
            border-radius: 12px !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
            background: linear-gradient(180deg, #1d4ed8, #1e40af) !important;
            color: white !important;
            font-weight: 600 !important;
            padding: 0.55rem 1rem !important;
        }

        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] > div {
            border-radius: 12px !important;
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(18,26,43,0.96), rgba(24,34,53,0.86));
            border: 1px solid var(--border);
            padding: 10px 14px;
            border-radius: 16px;
        }

        .sidebar-project-box {
            padding: 12px;
            border-radius: 14px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            margin-top: 10px;
            margin-bottom: 12px;
        }

        .nav-title {
            text-align: center;
            font-weight: 800;
            font-size: 1.3rem;
            margin-bottom: 0.2rem;
        }

        .nav-subtitle {
            text-align: center;
            color: var(--muted);
            font-size: 0.88rem;
            margin-bottom: 1rem;
        }
        
        /* Hide default Streamlit multipage navigation */
        [data-testid="stSidebarNav"] {
            display: none;
        }

        /* Optional: hide the collapse button */
        button[kind="header"] {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
