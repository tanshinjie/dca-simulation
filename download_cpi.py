import pandas as pd
from fredapi import Fred
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# Your FRED API Key - loaded from environment variable
FRED_API_KEY = os.getenv("FRED_API_KEY")

# CPI series ID
CPI_SERIES_ID = "CPIAUCSL"

# Start date for data download
START_DATE = "1998-01-01"

# End date for data download (today's date)
END_DATE = datetime.now().strftime("%Y-%m-%d")

# File path to save the CPI data
OUTPUT_FILE = "cpi_data.csv"


# --- Main Script ---
def download_and_save_cpi_data():
    """
    Downloads CPI data from FRED and saves it to a CSV file.
    """
    if not FRED_API_KEY:
        print(
            "Error: FRED_API_KEY is not set. Please set your API key in the .env file."
        )
        print(
            "You can obtain a key from: https://fred.stlouisfed.org/docs/api/api_key.html"
        )
        return

    try:
        # Initialize FRED API
        fred = Fred(api_key=FRED_API_KEY)
        print(
            f"Attempting to download CPI data ({CPI_SERIES_ID}) from {START_DATE} to {END_DATE}..."
        )

        # Fetch CPI data
        cpi_data = fred.get_series(
            CPI_SERIES_ID, observation_start=START_DATE, observation_end=END_DATE
        )

        if cpi_data is None or cpi_data.empty:
            print(
                "Error: No CPI data retrieved. Please check the series ID and date range, or your API key."
            )
            return

        # Convert to DataFrame and resample to monthly last value
        cpi_df = pd.DataFrame(cpi_data, columns=["CPI"])
        cpi_df.index.name = "Date"
        cpi_df = cpi_df.resample("M").last()  # Ensure monthly data

        # Save to CSV
        cpi_df.to_csv(OUTPUT_FILE)
        print(f"Successfully downloaded CPI data and saved to '{OUTPUT_FILE}'")
        print(
            f"Data covers from {cpi_df.index.min().strftime('%Y-%m-%d')} to {cpi_df.index.max().strftime('%Y-%m-%d')}"
        )

    except Exception as e:
        print(f"An error occurred during data download: {e}")
        print(
            "Please ensure your FRED API key is correct and you have an active internet connection."
        )


if __name__ == "__main__":
    download_and_save_cpi_data()
