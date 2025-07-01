"""
Handles loading and validation of application configuration from environment variables.
"""

import os
from dotenv import load_dotenv

project_dir = os.path.join(os.path.dirname(__file__), "..")
load_dotenv(os.path.join(project_dir, ".env"))

HOST = os.getenv("TURNSTILE_HOST")
USERNAME = os.getenv("TURNSTILE_USERNAME")
PASSWORD = os.getenv("TURNSTILE_PASSWORD")

BACKUP_DIR = os.getenv("BACKUP_DIR", "backups/")
REPORT_DIR = os.getenv("REPORT_DIR", "reports/")

if not all([HOST, USERNAME, PASSWORD]):
    raise ValueError(
        "Error: TURNSTILE_HOST, TURNSTILE_USERNAME, and TURNSTILE_PASSWORD "
        "must be set in the .env file"
    )
