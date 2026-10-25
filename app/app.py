"""
Commodities Market Analytics Platform - Interactive BI Dashboard
Built with Streamlit & Plotly to visualize commodities prices, technical indicators,
and trading transactions from the Commodities Data Warehouse.
"""

import os
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Commodities Market Analytics Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        border-left: 5px solid #1f77b4;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
</style>
""", unsafe_allow_html=True)


def get_db_engine():
    """Initializes database connection engine."""
    db_host = os.getenv("DB_HOST_PROD", "localhost")
    db_port = os.getenv("DB_PORT_PROD", "5432")
    db_name = os.getenv("DB_NAME_PROD", "commodities_dw")
    db_user = os.getenv("DB_USER_PROD", "postgres")
    db_pass = os.getenv("DB_PASS_PROD", "postgres")

    url = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    return create_engine(url)


@st.cache_data(ttl=300)
def load_market_data() -> pd.DataFrame:
    """Loads daily market data from the warehouse or generates synthetic fallback data."""
    try:
        engine = get_db_engine()
        # Prefer analytical datamart if available, fallback to raw
        query = """
            SELECT 
                trade_date,
                symbol,
                commodity_name,
                close_price,
                daily_price_change,
                daily_return_pct,
                moving_avg_7d,
                moving_avg_30d,
                trade_volume
            FROM analytics.dm_commodities_daily
            ORDER BY trade_date DESC;
        """
        df = pd.read_sql(query, engine)
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        return df
    except Exception:
        # Fallback query to public.commodities if datamart is not yet built
        try:
            engine = get_db_engine()
            raw_query = """
                SELECT 
                    cast("Date" as date) as trade_date,
                    symbol,
                    case 
                        when symbol = 'CL=F' then 'Crude Oil (WTI)'
                        when symbol = 'GC=F' then 'Gold'
                        when symbol = 'SI=F' then 'Silver'
                        else symbol
                    end as commodity_name,
                    round(cast("Close" as numeric), 4) as close_price,
                    0 as daily_price_change,
                    0 as daily_return_pct,
                    round(cast("Close" as numeric), 4) as moving_avg_7d,
                    round(cast("Close" as numeric), 4) as moving_avg_30d,
                    coalesce(cast("Volume" as bigint), 0) as trade_volume
                FROM public.commodities
                ORDER BY "Date" DESC;
            """
            df = pd.read_sql(raw_query, engine)
            df["trade_date"] = pd.to_datetime(df["trade_date"])
            return df
        except Exception:
            # Generate offline demonstration dataset
            dates = pd.date_range(end=datetime.now(), periods=180, freq="B")
            demo_data = []
            symbols = [
                ("CL=F", "Crude Oil (WTI)", 75.0, 1.2),
                ("GC=F", "Gold", 2400.0, 15.0),
                ("SI=F", "Silver", 31.0, 0.4),
            ]
            import numpy as np
            np.random.seed(42)
            for sym, name, base_price, vol in symbols:
                noise = np.random.normal(0, vol, len(dates))
                prices = np.maximum(base_price + np.cumsum(noise * 0.2), 10.0)
                for d, p in zip(dates, prices):
                    demo_data.append({
                        "trade_date": d,
                        "symbol": sym,
                        "commodity_name": name,
                        "close_price": round(float(p), 4),
                        "daily_price_change": round(float(np.random.normal(0, vol * 0.1)), 4),
                        "daily_return_pct": round(float(np.random.normal(0.05, 1.2)), 2),
                        "moving_avg_7d": round(float(p * 0.99), 4),
                        "moving_avg_30d": round(float(p * 0.98), 4),
                        "trade_volume": int(np.random.randint(50000, 250000)),
                    })
            demo_df = pd.DataFrame(demo_data)
            demo_df["trade_date"] = pd.to_datetime(demo_df["trade_date"])
            return demo_df


# Header Section
st.title("Commodities Market Analytics Platform")
st.caption(
    "Automated Data Pipeline (ELT) | Apache Airflow · PostgreSQL · dbt-core · Streamlit"
)

# Load data
df = load_market_data()

# Sidebar Filters
st.sidebar.header("Filter Criteria")

commodity_options = ["All"] + list(df["commodity_name"].unique())
selected_commodity = st.sidebar.selectbox("Select Commodity", commodity_options)

min_date = df["trade_date"].min().date()
max_date = df["trade_date"].max().date()
date_range = st.sidebar.date_input(
    "Date Range",
    value=(max_date - timedelta(days=90), max_date),
    min_value=min_date,
    max_value=max_date
)

# Apply filters
filtered_df = df.copy()
if selected_commodity != "All":
    filtered_df = filtered_df[filtered_df["commodity_name"] == selected_commodity]

if len(date_range) == 2:
    start_dt, end_dt = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    filtered_df = filtered_df[
        (filtered_df["trade_date"] >= start_dt) & (filtered_df["trade_date"] <= end_dt)
    ]

# KPI Metrics Summary
st.subheader("Market Summary & KPIs")
metric_cols = st.columns(4)

latest_records = filtered_df.sort_values("trade_date").groupby("symbol").last()

if not latest_records.empty:
    avg_price = latest_records["close_price"].mean()
    latest_return = latest_records["daily_return_pct"].mean()
    total_volume = filtered_df["trade_volume"].sum()
    active_symbols = filtered_df["symbol"].nunique()

    with metric_cols[0]:
        st.metric("Tracked Assets", f"{active_symbols} Commodities")
    with metric_cols[1]:
        st.metric(
            "Latest Avg Price",
            f"${avg_price:,.2f}",
            delta=f"{latest_return:.2f}%" if pd.notnull(latest_return) else None
        )
    with metric_cols[2]:
        st.metric("Total Traded Volume", f"{total_volume:,.0f}")
    with metric_cols[3]:
        st.metric("Observation Window", f"{len(filtered_df['trade_date'].unique())} Days")

st.markdown("---")

# Main Content Tabs
tab_charts, tab_data, tab_architecture = st.tabs([
    "Price Trends & Indicators",
    "Data Explorer",
    "Data Architecture"
])

with tab_charts:
    st.subheader("Price Evolution & Moving Averages")
    symbols = filtered_df["symbol"].unique()

    for sym in symbols:
        sym_df = filtered_df[filtered_df["symbol"] == sym].sort_values("trade_date")
        sym_name = sym_df["commodity_name"].iloc[0]

        st.markdown(f"#### {sym_name} (`{sym}`)")
        chart_data = sym_df.set_index("trade_date")[["close_price", "moving_avg_7d", "moving_avg_30d"]]
        chart_data.columns = ["Close Price", "7-Day SMA", "30-Day SMA"]
        st.line_chart(chart_data)

with tab_data:
    st.subheader("Curated Market Datamart")
    st.dataframe(
        filtered_df.sort_values("trade_date", ascending=False),
        use_container_width=True
    )
    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Filtered Data as CSV",
        data=csv,
        file_name="commodities_analytics.csv",
        mime="text/csv"
    )

with tab_architecture:
    st.subheader("Pipeline & Data Warehouse Architecture")
    st.markdown("""
    This project demonstrates an enterprise-grade **ELT (Extract, Load, Transform)** architecture:

    1. **Extraction & Ingestion:** Python pipeline (`src/extract_load.py`) pulls data from Yahoo Finance API and ingests it into PostgreSQL (`public.commodities`).
    2. **Staging Layer (dbt):** `stg_commodities` and `stg_commodity_transactions` standardize types, names, and deduplicate records.
    3. **Analytics Layer (dbt Datamart):** `dm_commodities_daily` computes financial indicators (7-day and 30-day moving averages, returns).
    4. **Quality Gates:** dbt tests (`unique`, `not_null`, `accepted_values`) ensure pipeline data governance.
    5. **Serving Layer:** Streamlit interactive application delivering live analytics for trading desks.
    """)
