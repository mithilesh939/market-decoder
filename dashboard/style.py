"""
style.py -- minimal style constants for the Streamlit dashboard.
Kept intentionally small; Streamlit's own component styling handles most
of the layout, we only need a few CSS overrides for the terminal aesthetic
consistent with the rest of this project's deliverables.
"""

CUSTOM_CSS = """
<style>
    .stApp { background-color: #0B0E14; }
    h1, h2, h3 { font-family: 'Courier New', monospace !important; color: #E8E6E0; }
    .stMetric { background-color: #151922; border: 1px solid #262C3A; border-radius: 4px; padding: 10px; }
    .stMetric label { color: #7A8194 !important; font-family: 'Courier New', monospace !important; }
    .stMetric [data-testid="stMetricValue"] { color: #FFB000 !important; font-family: 'Courier New', monospace !important; }
    .real-data-badge {
        background-color: #00D9C0; color: #0B0E14; padding: 2px 8px;
        border-radius: 3px; font-family: 'Courier New', monospace; font-size: 11px;
        font-weight: bold; display: inline-block;
    }
</style>
"""