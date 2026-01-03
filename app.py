# ---- LOAD ENV FIRST ----
from dotenv import load_dotenv
load_dotenv()

import os
import streamlit as st
from datetime import datetime, timedelta
import pytz
import pandas as pd
import altair as alt

from news_fetcher import fetch_news_combined
from docx_generator import generate_docx

IST = pytz.timezone("Asia/Kolkata")

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def fetch_and_store_articles(
    *,
    keywords,
    from_date,
    to_date,
    target_key,
    max_results=200
):
    from_dt = IST.localize(datetime.combine(from_date, datetime.min.time()))
    to_dt = IST.localize(datetime.combine(to_date, datetime.max.time()))

    articles = fetch_news_combined(
        keywords,
        from_dt.astimezone(pytz.utc),
        to_dt.astimezone(pytz.utc),
        max_results=max_results
    )

    st.session_state[target_key] = articles
    return articles

def enrich_articles_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure all required columns exist safely for analytics & UI"""

    required_columns = {
        "date": None,
        "title": "",
        "source": "Unknown",
        "author": "",
        "url": "",
        "author_flag": "Named Author",
        "marked_ai": False,
    }

    for col, default in required_columns.items():
        if col not in df.columns:
            df[col] = default

    # ---- Normalize date ----
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

    # ---- Blog / News detection ----
    def is_blog(row):
        url = str(row.get("url", "")).lower()
        source = str(row.get("source", "")).lower()
        author = str(row.get("author", "")).lower()

        blog_indicators = ["/blog", "/insights", "/resources", "/articles"]

        if any(b in url for b in blog_indicators):
            return True
        if author and source and author in source:
            return True
        return False

    if "content_type" not in df.columns:
        df["content_type"] = df.apply(
            lambda r: "Blog" if is_blog(r) else "News",
            axis=1
        )

    return df



# --------------------------------------------------
# App Config
# --------------------------------------------------
st.set_page_config(page_title="Media Tracker Prototype", layout="wide")

for key in ["articles", "selected_articles", "keywords", "analytics_articles"]:
    if key not in st.session_state:
        st.session_state[key] = []

if not os.environ.get("NEWSAPI_KEY"):
    st.error("❌ NEWSAPI_KEY missing in .env")
    st.stop()

st.title("Media Tracker Prototype")
tab1, tab2 = st.tabs(["📰 Media Coverage", "📊 Analytics"])

if "analytics_ran" not in st.session_state:
    st.session_state["analytics_ran"] = False

if "analytics_articles" not in st.session_state:
    st.session_state["analytics_articles"] = []


# ==================================================
# TAB 1 — MEDIA COVERAGE (UNCHANGED CORE)
# ==================================================
with tab1:
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

    if st.button("Search News"):
        keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
        st.session_state["keywords"] = keywords

        if ist_48h:
            today = datetime.now(IST).date()
            from_date = today - timedelta(days=1)
            to_date = today

        fetch_and_store_articles(
            keywords=keywords,
            from_date=from_date,
            to_date=to_date,
            target_key="articles",
            max_results=100
        )

        st.session_state["selected_articles"] = []




    if not st.session_state["articles"]:
        st.info("Run a search to see articles.")


    df = enrich_articles_df(pd.DataFrame(st.session_state["articles"]))

    st.subheader("Fetched Articles")
    st.dataframe(df, use_container_width=True)
    st.markdown("---")
    st.subheader("📄 Export Media Coverage Report")

    if st.button("Generate Media Coverage DOCX"):
        filename = f"Media_Coverage_{datetime.now(IST).strftime('%d%m%y')}.docx"

        generate_docx(
            report_title=report_title,
            brand_title=brand_title,
            date_str=f"{from_date} → {to_date}",
            keywords=st.session_state.get("keywords", []),
            articles=st.session_state["articles"],
            out_path=filename
        )

        with open(filename, "rb") as f:
            st.download_button(
                "⬇️ Download Media Coverage Report",
                f,
                file_name=filename
            )

# ==================================================
# TAB 2 — ANALYTICS (OPTION B — FIXED & STABLE)
# ==================================================
with tab2:
    st.header("📊 Media Analytics")

    # ---- Analytics Controls ----
    a_keywords_input = st.text_input(
        "Analytics Keywords (comma-separated)",
        value="Jaro Education, Coursera, EdTech",
        key="analytics_keywords"
    )

    a_col1, a_col2 = st.columns(2)
    with a_col1:
        a_from = st.date_input(
            "Analytics From Date",
            datetime.now(IST).date() - timedelta(days=7),
            key="analytics_from"
        )
    with a_col2:
        a_to = st.date_input(
            "Analytics To Date",
            datetime.now(IST).date(),
            key="analytics_to"
        )

    # ---- FETCH DATA ----

        if not st.session_state.get("articles"):
            st.warning("Run Media Coverage search first.")
            st.stop()

        st.session_state["analytics_articles"] = st.session_state["articles"]
        st.session_state["analytics_meta"] = {
            "from": "Same as Media Coverage",
            "to": "Same as Media Coverage",
            "keywords": st.session_state.get("keywords", [])
        }
        st.session_state["analytics_ran"] = True
        st.success("Using Media Coverage results for analytics.")


    # ---- GUARDS ----
    if not st.session_state.get("analytics_ran"):
        st.info("Run analytics to view insights.")
        st.stop()

    if not st.session_state.get("analytics_articles"):
        st.warning("No articles found for the selected analytics period.")
        st.stop()

    # ---- DATAFRAME (ENRICHED & DEFENSIVE) ----
    df = enrich_articles_df(
        pd.DataFrame(st.session_state["analytics_articles"])
    )

    if df.empty:
        st.warning("No usable data available for analytics.")
        st.stop()

    meta = st.session_state.get("analytics_meta", {
        "from": "N/A",
        "to": "N/A",
        "keywords": []
    })

    # ---- SAFE DATE NORMALIZATION (CRITICAL FIX) ----
    if "date" not in df.columns:
        st.warning("No date field found in data.")
        st.stop()

    df["date"] = df["date"].apply(
        lambda d: pd.to_datetime(d).date()
        if pd.notna(d) and str(d).strip() != ""
        else None
    )

    df = df[df["date"].notna()]

    if df.empty:
        st.warning("No valid dated articles available for analytics.")
        st.stop()

    # ---- ANALYSIS PERIOD ----
    st.caption(
        f"📅 **Analysis Period:** {meta['from']} → {meta['to']}  |  "
        f"🔑 **Keywords:** {', '.join(meta['keywords'])}"
    )

    # ---- KPIs (SAFE COUNTS) ----
    total = len(df)

    news = len(df[df.get("content_type", "") == "News"])
    blogs = len(df[df.get("content_type", "") == "Blog"])
    sources = df["source"].nunique() if "source" in df.columns else 0

    risk = (
        round(
            100 * len(
                df[
                    (df.get("author_flag", "") != "Named Author")
                    | (df.get("marked_ai", False))
                ]
            ) / total,
            1
        )
        if total else 0
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Articles", total)
    k2.metric("News / Blogs", f"{news} / {blogs}")
    k3.metric("Unique Sources", sources)
    k4.metric("Authorship Risk", f"{risk}%")

    st.markdown("---")
    # ---- Mentions Over Time (DATE ONLY — FIXED SCALE) ----
    st.subheader("📈 Mentions Over Time")

    daily = (
        df.groupby("date")
        .size()
        .reset_index(name="count")
        .sort_values("date")
    )

    st.altair_chart(
        alt.Chart(daily).mark_line(point=True).encode(
            x=alt.X(
                "date:T",
                title="Date",
                axis=alt.Axis(format="%d %b")
            ),
            y=alt.Y("count:Q", title="Number of Articles"),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("count:Q", title="Articles")
            ]
        ),
        use_container_width=True
    )

    # ---- Top Publications ----
    st.subheader("🗞️ Top Publications")

    if "source" in df.columns:
        top_sources = (
            df["source"]
            .fillna("Unknown")
            .value_counts()
            .head(10)
            .reset_index()
        )
        top_sources.columns = ["source", "count"]

        st.altair_chart(
            alt.Chart(top_sources).mark_bar().encode(
                y=alt.Y(
                    "source:N",
                    sort="-x",
                    title="Publication"
                ),
                x=alt.X("count:Q", title="Articles"),
                tooltip=[
                    alt.Tooltip("source:N", title="Publication"),
                    alt.Tooltip("count:Q", title="Articles")
                ]
            ),
            use_container_width=True
        )
    else:
        st.info("Source data not available.")

    # ---- Keyword Performance ----
    st.subheader("🔑 Keyword Performance")

    keyword_hits = []
    for kw in meta["keywords"]:
        mentions = (
            df["title"].astype(str).str.contains(kw, case=False, na=False).sum()
            if "title" in df.columns else 0
        )
        keyword_hits.append({"Keyword": kw, "Mentions": mentions})

    kw_df = pd.DataFrame(keyword_hits)

    st.altair_chart(
        alt.Chart(kw_df).mark_bar().encode(
            x=alt.X("Keyword:N", title="Keyword"),
            y=alt.Y("Mentions:Q", title="Mentions"),
            tooltip=["Keyword", "Mentions"]
        ),
        use_container_width=True
    )

    # ---- Authorship Quality ----
    st.subheader("✍️ Authorship Quality")

    auth = (
        df.apply(
            lambda r: "AI / Flagged"
            if r.get("marked_ai", False)
            else r.get("author_flag", "Unknown"),
            axis=1
        )
        .value_counts()
        .reset_index()
    )
    auth.columns = ["Category", "Count"]

    st.altair_chart(
        alt.Chart(auth).mark_arc().encode(
            theta="Count:Q",
            color="Category:N",
            tooltip=["Category", "Count"]
        ),
        use_container_width=True
    )

    # ---- News vs Blogs ----
    st.subheader("📰 News vs Blogs")

    nb = (
        df["content_type"]
        .value_counts()
        .reset_index()
    )
    nb.columns = ["Type", "Count"]

    st.altair_chart(
        alt.Chart(nb).mark_arc().encode(
            theta="Count:Q",
            color="Type:N",
            tooltip=["Type", "Count"]
        ),
        use_container_width=True
    )

    # ---- Key Insights ----
    st.markdown("### 🧠 Key Insights")

    if not daily.empty:
        peak = daily.sort_values("count", ascending=False).iloc[0]
        st.write(
            f"- 📌 Peak coverage on **{peak['date']}** with **{peak['count']} articles**."
        )

    st.write(
        f"- ⚠️ **{risk}%** of coverage shows authorship or AI-related risk."
    )
    #-- Export as document --
    st.markdown("---")
    st.subheader("📤 Export Analytics")

    if st.button("📄 Export Analytics as DOCX"):
        from analytics_docx_generator import generate_analytics_docx

        filename = f"Analytics_Report_{datetime.now(IST).strftime('%d%m%y')}.docx"

        generate_analytics_docx(
            df=df,
            meta=meta,
            out_path=filename
        )

        with open(filename, "rb") as f:
            st.download_button("⬇️ Download Analytics DOCX", f, file_name=filename)


