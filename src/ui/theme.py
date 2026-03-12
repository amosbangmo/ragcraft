import streamlit as st


def apply_theme():
    st.markdown(
        """
        <style>
        :root {
            --sidebar-bg-1: #0a0f1d;
            --sidebar-bg-2: #121a2b;
            --sidebar-border: rgba(255,255,255,0.08);
            --sidebar-text: #e8edf7;
            --sidebar-muted: #9fb0d0;

            --main-bg: #f6f8fc;
            --main-panel: #ffffff;
            --main-panel-2: #f8fafc;
            --main-border: rgba(15,23,42,0.08);
            --main-text: #0f172a;
            --main-muted: #475569;

            --accent: #2563eb;
            --accent-2: #1d4ed8;
            --success: #16a34a;
            --warning: #f59e0b;
        }

        /* Global app background */
        .stApp {
            background: var(--main-bg);
            color: var(--main-text);
        }

        /* Sidebar dark theme */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--sidebar-bg-1) 0%, var(--sidebar-bg-2) 100%);
            border-right: 1px solid var(--sidebar-border);
        }

        [data-testid="stSidebar"] * {
            color: var(--sidebar-text);
        }

        .sidebar-metric {
            font-size: 28px;
            font-weight: 700;
            text-align: center;
            padding: 8px;
            border-radius: 10px;
            margin-top: 4px;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: white;
            box-shadow: 0 4px 12px rgba(37,99,235,0.35);
        }

        /* Hide default Streamlit page nav */
        [data-testid="stSidebarNav"] {
            display: none;
        }

        /* Optional: hide top Streamlit header */
        header {
            visibility: hidden;
        }

        /* Main layout container */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }

        /* Hero section */
        .hero-card {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid var(--main-border);
            border-radius: 22px;
            padding: 28px 28px 22px 28px;
            margin-bottom: 1rem;
            box-shadow: 0 8px 28px rgba(15,23,42,0.06);
        }

        .hero-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            background: rgba(37,99,235,0.08);
            border: 1px solid rgba(37,99,235,0.18);
            color: var(--accent-2);
            font-size: 0.85rem;
            margin-bottom: 10px;
            font-weight: 600;
        }

        .hero-title {
            margin: 0;
            font-size: 2rem;
            line-height: 1.2;
            color: var(--main-text);
        }

        .hero-subtitle {
            margin-top: 10px;
            color: var(--main-muted);
            font-size: 1rem;
            line-height: 1.6;
            max-width: 900px;
        }

        /* Generic cards */
        .section-card {
            background: var(--main-panel);
            border: 1px solid var(--main-border);
            border-radius: 18px;
            padding: 18px 18px 10px 18px;
            margin-bottom: 1rem;
            box-shadow: 0 6px 20px rgba(15,23,42,0.04);
        }

        .card-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--main-text);
            margin-bottom: 6px;
        }

        .card-subtitle {
            color: var(--main-muted);
            font-size: 0.92rem;
            margin-bottom: 10px;
        }

        .source-card {
            background: #ffffff;
            border: 1px solid var(--main-border);
            border-radius: 14px;
            padding: 14px 14px 10px 14px;
            margin-bottom: 10px;
            box-shadow: 0 4px 14px rgba(15,23,42,0.04);
        }

        .source-title {
            font-weight: 700;
            color: var(--main-text);
            margin-bottom: 6px;
        }

        .source-preview {
            color: var(--main-muted);
            font-size: 0.93rem;
            line-height: 1.5;
        }

        .small-muted {
            color: var(--main-muted);
            font-size: 0.88rem;
        }

        /* Buttons */

        .stButton > button,
        .stDownloadButton > button,
        div[data-testid="stButton"] button {
            background: linear-gradient(180deg, #2563eb, #1d4ed8) !important;
            color: #ffffff !important;
            border: 1px solid rgba(37,99,235,0.25) !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            padding: 0.55rem 1rem !important;
            box-shadow: 0 4px 14px rgba(37,99,235,0.18);
        }

        .stButton > button:hover {
            background: linear-gradient(180deg, #1d4ed8, #1e40af) !important;
            color: white !important;
        }
        

        /* Inputs */
        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] > div {
            border-radius: 12px !important;
            background: white !important;
            color: var(--main-text) !important;
            border: 1px solid rgba(15,23,42,0.10) !important;
        }

        /* Metrics */
        div[data-testid="stMetric"] {
            background: var(--main-panel);
            border: 1px solid var(--main-border);
            padding: 10px 14px;
            border-radius: 16px;
            box-shadow: 0 4px 14px rgba(15,23,42,0.04);
        }

        /* Sidebar custom blocks */
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
            color: white;
        }

        .nav-subtitle {
            text-align: center;
            color: var(--sidebar-muted);
            font-size: 0.88rem;
            margin-bottom: 1rem;
        }

        /* Chat messages readability on light main area */
        [data-testid="stChatMessage"] {
            background: transparent;
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
