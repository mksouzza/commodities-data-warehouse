"""
Commodities Data Pipeline - Extraction and Ingestion (EL)
Fetches financial historical data from Yahoo Finance API for major commodities
and ingests raw records into a PostgreSQL staging table.
"""

import logging
import os
from typing import List
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
import yfinance as yf

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("extract_load")

load_dotenv()

# Tracked commodity ticker symbols
COMMODITIES: List[str] = ["CL=F", "GC=F", "SI=F"]


def get_db_engine() -> Engine:
    """Creates a SQLAlchemy engine using environment variables."""
    db_host = os.getenv("DB_HOST_PROD", "localhost")
    db_port = os.getenv("DB_PORT_PROD", "5432")
    db_name = os.getenv("DB_NAME_PROD", "commodities_dw")
    db_user = os.getenv("DB_USER_PROD", "postgres")
    db_pass = os.getenv("DB_PASS_PROD", "postgres")

    connection_uri = (
        f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    )
    return create_engine(connection_uri)


def fetch_commodity_history(
    symbol: str, period: str = "5y", interval: str = "1d"
) -> pd.DataFrame:
    """
    Fetches historical market data for a single commodity symbol.

    Args:
        symbol: Market ticker symbol (e.g. 'CL=F', 'GC=F').
        period: Data retrieval window (e.g. '1y', '5y', 'max').
        interval: Data sampling interval ('1d', '1wk', '1mo').

    Returns:
        pd.DataFrame: Cleaned market data with symbol identifier.
    """
    logger.info("Fetching data for symbol: %s (period: %s, interval: %s)", symbol, period, interval)
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)

    if df.empty:
        logger.warning("No data found for symbol: %s", symbol)
        return pd.DataFrame()

    df = df.reset_index()
    df["symbol"] = symbol
    return df


def fetch_all_commodities(
    symbols: List[str], period: str = "5y", interval: str = "1d"
) -> pd.DataFrame:
    """
    Fetches and concatenates historical data across multiple commodity symbols.

    Args:
        symbols: List of commodity ticker symbols.
        period: Data retrieval window.
        interval: Data sampling interval.

    Returns:
        pd.DataFrame: Unified DataFrame containing all requested commodities.
    """
    data_frames = []
    for symbol in symbols:
        try:
            df = fetch_commodity_history(symbol, period=period, interval=interval)
            if not df.empty:
                data_frames.append(df)
        except Exception as e:
            logger.error("Failed to retrieve data for %s: %s", symbol, e)

    if not data_frames:
        raise ValueError("Failed to retrieve market data for any provided symbols.")

    unified_df = pd.concat(data_frames, ignore_index=True)
    logger.info("Extracted %d total records across %d commodities", len(unified_df), len(symbols))
    return unified_df


def load_raw_data_to_postgres(
    df: pd.DataFrame,
    table_name: str = "commodities",
    schema: str = "public",
    engine: Engine = None
) -> None:
    """
    Loads raw market data into the destination PostgreSQL table.

    Args:
        df: Processed DataFrame to ingest.
        table_name: Destination table name.
        schema: Destination database schema.
        engine: SQLAlchemy Engine instance.
    """
    if engine is None:
        engine = get_db_engine()

    logger.info("Writing %d rows to %s.%s ...", len(df), schema, table_name)
    df.to_sql(
        table_name,
        con=engine,
        if_exists="replace",
        index=False,
        schema=schema
    )
    logger.info("Successfully loaded data into %s.%s", schema, table_name)


if __name__ == "__main__":
    logger.info("Starting extraction and ingestion pipeline...")
    market_data = fetch_all_commodities(COMMODITIES, period="5y", interval="1d")
    load_raw_data_to_postgres(market_data, table_name="commodities")
    logger.info("Pipeline completed successfully.")
