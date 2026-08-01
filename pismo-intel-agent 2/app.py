"""
app.py — Streamlit dashboard for the Pismo Brewing trend digest.
Reads trend_digest.json (produced by fetch_intel.py) and displays it.
"""

import json
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Pismo Brewing — Trend Digest", page_icon="🍺", layout="centered")

FEED_FILE = Path("trend_digest.json")

CATEGORY_COLORS = {
    "Consumption Trends": "#2563eb",
    "Craft Beer Industry": "#d97706",
    "Consumer Behavior": "#16a34a",
    "Regulatory/Economic": "#dc2626",
    "Local Market": "#7c3aed",
}

st.title("🍺 Pismo Brewing")
st.caption("Weekly Alcohol Consumption Trend Digest")

if not FEED_FILE.exists():
    st.warning("No digest yet. Run `python fetch_intel.py` to generate one.")
    st.stop()

data = json.loads(FEED_FILE.read_text(encoding="utf-8"))
st.caption(f"Generated: {data.get('generated_at', 'unknown')}")

trends = sorted(data.get("trends", []), key=lambda t: t.get("rank", 99))

if not trends:
    st.info("No trends identified in the latest run.")

for t in trends:
    category = t.get("category", "")
    color = CATEGORY_COLORS.get(category, "#64748b")
    with st.container(border=True):
        st.markdown(
            f"<span style='color:{color};font-size:12px;font-weight:bold;text-transform:uppercase'>"
            f"#{t.get('rank','')} · {category}</span>",
            unsafe_allow_html=True,
        )
        st.subheader(t.get("headline", ""))
        st.write(t.get("summary", ""))
        st.success(f"🍺 **Why it matters for Pismo Brewing:** {t.get('why_it_matters_to_pismo_brewing', '')}")
        if t.get("sources"):
            st.caption("Sources: " + ", ".join(t["sources"]))
