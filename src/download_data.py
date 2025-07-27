import yfinance as yf
import pandas as pd
import os
from dotenv import load_dotenv

from .config import (
    SP500_TICKER,
    DATA_FETCH_START_DATE,
    DATA_FETCH_END_DATE,
    SP500_DATA_FILE,
)
from .download_cpi import download_and_save_cpi_data

load_dotenv()
FRED_API_KEY = os.getenv("FRED_API_KEY")

def download_data():
    """Downloads S&P 500 data if it doesn't already exist."""
    # Download CPI data using the dedicated function
    download_and_save_cpi_data(FRED_API_KEY)

    # Download S&P 500 data
    if not os.path.exists(SP500_DATA_FILE):
        print(f"Downloading S&P 500 data to {SP500_DATA_FILE}...")
        try:
            sp500_data = yf.download(SP500_TICKER, start=DATA_FETCH_START_DATE, end=DATA_FETCH_END_DATE)
            if sp500_data.empty:
                print("Error: No S&P 500 data retrieved.")
            else:
                # Ensure the data directory exists
                os.makedirs(os.path.dirname(SP500_DATA_FILE), exist_ok=True)
                sp500_data['Close'].to_csv(SP500_DATA_FILE)
                print("S&P 500 data downloaded successfully.")
        except Exception as e:
            print(f"Error downloading S&P 500 data: {e}")
    else:
        print(f"S&P 500 data already exists at {SP500_DATA_FILE}.")

if __name__ == "__main__":
    download_data()