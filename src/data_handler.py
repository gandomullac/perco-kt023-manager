"""
Handles data loading and processing, specifically from the cards Excel file.
"""

import logging
from datetime import datetime
from typing import Tuple
import pandas as pd


def load_and_filter_cards(file_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Loads the cards' Excel file and filters for active cards.
    """
    logging.info("Reading card file from: %s", file_path)
    try:
        df = pd.read_excel(file_path)
    except FileNotFoundError:
        logging.error("File not found: %s", file_path)
        raise
    except Exception as e:
        logging.error("Error reading the Excel file: %s", e)
        raise

    df["Active"] = df["Active"].astype(str)

    today = pd.to_datetime(datetime.now().date())

    active_cards_df = df[
        (df["Active"].str.lower() == "true")
        & (df["Card RFID"].notna())
        & (pd.to_datetime(df["Expiration date"], errors="coerce") >= today)
    ].copy()

    logging.info(
        "Found %d active cards out of %d total.", len(active_cards_df), len(df)
    )
    return df, active_cards_df
