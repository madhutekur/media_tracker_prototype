# ---- LOAD ENV FIRST ----
from dotenv import load_dotenv
load_dotenv()

import os
import streamlit as st
from datetime import datetime, timedelta
import pytz
import pandas as pd

from news_fetcher import fetch_news_combined
from docx_generator import generate_docx

# ---- CONFIG ----
st.set_page_config(page_title="Media Tracker Prototype", layout="wide")
IST = pytz.timezone("Asia/Kolkata")

# ---- SESSION STATE ----
for key, default in {
    "articles": [],
    "selected_articles": [],
    "keywords": []
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ---- API KEY CHECK ----
if not os.environ.get("NEWSAPI_KEY"):
    st.error("❌ NEWSAPI_KEY missing in .env")
    st.stop()

# ---- UI ----
st.title("Media Tracker Prototype")

keywords_input = st.text_input(
    "Keywords (comma-separated)",
    value="Jaro Education, Coursera, EdTech"
)

col1, col2 = st.columns(2)

with col1:
    ist_48h = st.checkbox("Yesterday + Today (IST)", value=True)

with col2:
    from_date = st.date_input("From date", datetime.now(IST).date() - timedelta(days=1))
    to_date = st.date_input("To date", datetime.now(IST).date())

brand_title = st.text_input("Brand / Report Subject", value="Jaro Education")
report_title = "Media Tracker Report"

# ---- SEARCH ----
if st.button("Search News"):
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
    st.session_state["keywords"] = keywords

    if ist_48h:
        today = datetime.now(IST).date()
        yesterday = today - timedelta(days=1)
        from_dt_ist = IST.localize(datetime.combine(yesterday, datetime.min.time()))
        to_dt_ist = IST.localize(datetime.combine(today, datetime.max.time()))
    else:
        from_dt_ist = IST.localize(datetime.combine(from_date, datetime.min.time()))
        to_dt_ist = IST.localize(datetime.combine(to_date, datetime.max.time()))

    articles = fetch_news_combined(
        keywords,
        from_dt_ist.astimezone(pytz.utc),
        to_dt_ist.astimezone(pytz.utc),
        max_results=100
    )

    st.session_state["articles"] = articles
    st.session_state["selected_articles"] = []

# ---- DISPLAY ----
st.subheader("Fetched Articles")

if not st.session_state["articles"]:
    st.info("No articles loaded.")
    st.stop()

df = pd.DataFrame(st.session_state["articles"])

# ---- ENSURE COLUMNS ----
for col, default in {
    "author_flag": "Named Author",
    "marked_ai": False
}.items():
    if col not in df.columns:
        df[col] = default

# ---- FILTER ----
show_only_flagged = st.checkbox("Show only articles with authorship concerns")

if show_only_flagged:
    df = df[(df["author_flag"] != "Named Author") | (df["marked_ai"] == True)]

# ---- DISPLAY LABEL ----
df["Authorship Status"] = df.apply(
    lambda r: f"{r['author_flag']}" + (" | Manually flagged" if r["marked_ai"] else ""),
    axis=1
)

# ---- INCLUDE COLUMN ----
if "Include" not in df.columns:
    df.insert(0, "Include", False)

# ---- BULK ACTION ----
st.markdown("### Bulk Actions")
if st.button("⚠️ Mark selected rows as AI-generated"):
    df.loc[df["Include"] == True, "marked_ai"] = True
    st.success("Selected articles marked as AI-generated.")

# ---- STYLING ----
def highlight_flagged(row):
    if row["author_flag"] != "Named Author" or row["marked_ai"]:
        return ["background-color: #fff3cd"] * len(row)
    return [""] * len(row)

styled_df = df.style.apply(highlight_flagged, axis=1)

edited_df = st.data_editor(
    styled_df.data,
    use_container_width=True,
    hide_index=True
)

# ---- STORE SELECTION ----
selected_articles = edited_df[edited_df["Include"]].drop(columns=["Include"])
st.session_state["selected_articles"] = selected_articles.to_dict("records")

st.success(f"Selected {len(selected_articles)} articles for report.")

# ---- REPORT ----
st.markdown("---")
st.subheader("Generate Report")

if st.button("Generate DOCX Report"):
    if not st.session_state["selected_articles"]:
        st.warning("Select at least one article.")
        st.stop()

    date_str = datetime.now(IST).strftime("%d %b %Y")
    filename = f"Media_Tracker_Report_{brand_title}_{datetime.now(IST).strftime('%d%m%y')}.docx"

    generate_docx(
        report_title,
        brand_title,
        date_str,
        st.session_state["keywords"],
        st.session_state["selected_articles"],
        filename
    )

    with open(filename, "rb") as f:
        st.download_button("⬇️ Download DOCX", f, file_name=filename)
