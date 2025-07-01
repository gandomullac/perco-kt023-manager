"""
Contains the TurnstileManager class to handle all interactions
with the PERCo turnstile hardware.
"""

import logging
import os
from datetime import datetime
from typing import Optional

import pandas as pd
import ping3
import requests
from requests.auth import HTTPBasicAuth


class TurnstileManager:
    """
    Manages interactions with the turnstile system.
    """

    def __init__(self, host: str, username: str, password: str):
        """Initializes the Turnstile Manager."""
        self.base_url = f"http://{host}"
        self.auth = HTTPBasicAuth(username, password)
        self.host = host

    def _make_request(
        self, endpoint: str, params: Optional[dict] = None
    ) -> requests.Response:
        """Helper method to perform GET requests to the turnstile API."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, auth=self.auth, params=params, timeout=10)
            response.raise_for_status()
            logging.debug(
                "Request to %s successful. Status: %s", url, response.status_code
            )
            return response
        except requests.exceptions.RequestException as e:
            logging.error("Error during request to %s: %s", url, e)
            raise

    def check_ping(self) -> bool:
        """Checks if the turnstile host is reachable via ping."""
        logging.info("Pinging %s...", self.host)
        try:
            delay = ping3.ping(self.host, unit="ms")
            if delay is None or delay is False:
                logging.error("Host %s is unreachable (timeout).", self.host)
                return False
            logging.info("Host %s is reachable in %.2f ms.", self.host, delay)
            return True

        except ping3.errors.PingError as e:
            logging.error("An error occurred while pinging %s: %s", self.host, e)
            return False

    def download_backup(self, folder_path: str) -> str:
        """Downloads a backup file of the card list."""
        logging.info("Downloading card list backup file...")
        response = self._make_request("/cgi/card_get_list")

        os.makedirs(folder_path, exist_ok=True)
        file_name = f"turnstile_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bin"
        file_path = os.path.join(folder_path, file_name)

        try:
            with open(file_path, "wb") as f:
                f.write(response.content)
            logging.info("Backup file saved to: %s", file_path)
            return file_path
        except IOError as e:
            logging.error("Failed to write backup file %s: %s", file_path, e)
            raise

    def update_turnstile_cards(self, active_cards_df: pd.DataFrame):
        """Adds or updates the active cards on the turnstile."""
        total_cards = len(active_cards_df)
        logging.info(
            "Starting update of %d active cards on the turnstile.", total_cards
        )

        for index, row in active_cards_df.iterrows():
            rfid = row["Card RFID"]
            user_id = row["Card Number"]
            user = row["Username"]

            logging.info(
                "(%d/%d) Updating card %s (%s) for user '%s'...",
                index + 1,
                total_cards,
                user_id,
                rfid,
                user,
            )

            endpoint = "/cgi/card_edit"
            params = {"req": f"1+1+{rfid}"}

            response = self._make_request(endpoint, params=params)
            logging.debug("Turnstile response: %s", response.text.strip())

        logging.info("Card update process completed.")

    def generate_access_report(
        self, records_to_fetch: int, cards_df: pd.DataFrame, output_dir: str
    ):
        """Downloads access events and generates a report in Excel format."""
        logging.info("Downloading the last %d access events...", records_to_fetch)
        endpoint = "/cgi/event_get"
        params = {"req": f"-1,0,-{records_to_fetch},0,0,1,1,0,23,59,31,12,99,1,/en"}

        response = self._make_request(endpoint, params=params)
        raw_data = response.text

        logging.info("Processing data for the report...")
        rows = raw_data.strip().split("\n")
        data = [row.split("\t") for row in rows if len(row.split("\t")) == 4]

        if not data:
            logging.warning("No event data found. Skipping report generation.")
            return

        df = pd.DataFrame(
            data, columns=["request_number", "hash", "datetime", "Card RFID"]
        )

        df.dropna(inplace=True)
        df.drop(columns=["request_number", "hash"], inplace=True)
        df = df[~df["Card RFID"].str.contains("Card is not registered", na=False)]
        df = df[df["Card RFID"].str.contains("by card", na=False)]
        df["Card RFID"] = df["Card RFID"].str.extract(r"(\d+)")
        df.dropna(subset=["Card RFID"], inplace=True)
        df["Card RFID"] = pd.to_numeric(df["Card RFID"])

        df["datetime"] = pd.to_datetime(df["datetime"], format="%d/%m/%y %H:%M:%S")
        df["Date"] = df["datetime"].dt.date
        df.drop(columns=["datetime"], inplace=True)
        df.drop_duplicates(inplace=True)

        df = df.merge(cards_df, on="Card RFID", how="left")
        df.dropna(subset=["Username"], inplace=True)

        df_count = df.groupby("Card RFID")["Date"].nunique().reset_index()
        df_count.columns = ["Card RFID", "UniqueEntryDays"]
        df_result = df_count.merge(cards_df, on="Card RFID", how="left")
        df_result = df_result.sort_values(by="UniqueEntryDays", ascending=False)

        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"access_report_{timestamp}.xlsx")
        logging.info("Saving report to: %s", output_path)
        df_result.to_excel(output_path, index=False)
        logging.info("Report generated successfully.")
