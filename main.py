"""
Main entry point for the Turnstile Manager application.
Orchestrates the command-line interface, configuration, and main logic.
"""

import argparse
import logging
import sys

from src.config import HOST, USERNAME, PASSWORD, BACKUP_DIR, REPORT_DIR
from src.data_handler import load_and_filter_cards
from src.turnstile import TurnstileManager

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main():
    """
    Main function to run the script.
    """
    parser = argparse.ArgumentParser(
        description="Turnstile Manager: Update cards and create access reports."
    )
    parser.add_argument(
        "--host",
        type=str,
        default=HOST,
        help="The IP address of the turnstile (default: from .env).",
    )
    parser.add_argument(
        "--file",
        type=str,
        default="cards.xlsx",
        help="Path to the Excel file with the card list.",
    )
    parser.add_argument(
        "--records-to-fetch",
        type=int,
        default=10000,
        help="Number of event records to download.",
    )
    parser.add_argument(
        "--skip-update",
        action="store_true",
        help="Skip updating cards on the turnstile.",
    )
    parser.add_argument(
        "--skip-report", action="store_true", help="Skip generating the access report."
    )
    parser.add_argument(
        "--skip-clear-all-cards",
        action="store_true",
        help="Skip clearing all cards from the turnstile.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Increase output verbosity to DEBUG level.",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Use the credentials and paths imported from the config file
        manager = TurnstileManager(args.host, USERNAME, PASSWORD)

        if not manager.check_ping():
            logging.error("The turnstile is not reachable. Halting operations.")
            sys.exit(1)

        full_cards_df, active_cards_df = load_and_filter_cards(args.file)

        if not args.skip_update:
            manager.download_backup(BACKUP_DIR)

            if args.skip_clear_all_cards:
                logging.info("Skipping card clearing as requested.")
            else:
                manager.clear_all_cards()
                logging.info("All cards cleared successfully.")

            manager.update_turnstile_cards(active_cards_df)
        else:
            logging.info("Skipping card update as requested.")

        if not args.skip_report:
            manager.generate_access_report(
                args.records_to_fetch, full_cards_df, REPORT_DIR
            )
        else:
            logging.info("Skipping report generation as requested.")

        logging.info("All operations completed successfully.")

    except (ValueError, FileNotFoundError) as e:
        logging.critical("Configuration or file error: %s", e)
        sys.exit(1)
    except Exception as e:  # pylint: disable=broad-exception-caught
        # Catch all other errors (e.g., network) as a last resort
        logging.critical("A fatal error occurred during operations: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
