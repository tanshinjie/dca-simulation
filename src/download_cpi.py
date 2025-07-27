import pandas as pd
from fredapi import Fred
import os

from .config import (
    CPI_SERIES_ID,
    DATA_FETCH_START_DATE,
    DATA_FETCH_END_DATE,
    CPI_DATA_FILE,
)

def download_and_save_cpi_data(fred_api_key):
    """
    Downloads CPI data from FRED and saves it to a CSV file.
    """
    if not fred_api_key:
        print("Error: FRED_API_KEY is not set. Please set it in your environment variables or .env file.")
        print("You can obtain a key from: https://fred.stlouisfed.org/docs/api/api_key.html")
        return

    if os.path.exists(CPI_DATA_FILE):
        print(f"CPI data already exists at {CPI_DATA_FILE}. Skipping download.")
        return

    try:
        # Initialize FRED API
        fred = Fred(api_key=fred_api_key)
        print(f"Attempting to download CPI data ({CPI_SERIES_ID}) from {DATA_FETCH_START_DATE} to {DATA_FETCH_END_DATE}...")

        # Fetch CPI data
        cpi_data = fred.get_series(
            CPI_SERIES_ID, observation_start=DATA_FETCH_START_DATE, observation_end=DATA_FETCH_END_DATE
        )

        if cpi_data is None or cpi_data.empty:
            print("Error: No CPI data retrieved. Please check the series ID and date range, or your API key.")
            return

        # Convert to DataFrame and resample to monthly last value
        cpi_df = pd.DataFrame(cpi_data, columns=["CPI"])
        cpi_df.index.name = "Date"
        cpi_df = cpi_df.resample("M").last()  # Ensure monthly data

        # Ensure the data directory exists
        os.makedirs(os.path.dirname(CPI_DATA_FILE), exist_ok=True)

        # Save to CSV
        cpi_df.to_csv(CPI_DATA_FILE)
        print(f"Successfully downloaded CPI data and saved to '{CPI_DATA_FILE}'")
        print(f"Data covers from {cpi_df.index.min().strftime('%Y-%m-%d')} to {cpi_df.index.max().strftime('%Y-%m-%d')}")

    except Exception as e:
        print(f"An error occurred during data download: {e}")
        print("Please ensure your FRED API key is correct and you have an active internet connection.")


if __name__ == "__main__":
    # This script is intended to be called by download_data.py, but can be run directly for testing
    # If run directly, it will attempt to load FRED_API_KEY from environment variables
    from dotenv import load_dotenv
    load_dotenv()
    FRED_API_KEY = os.getenv("FRED_API_KEY")
    download_and_save_cpi_data(FRED_API_KEY)