from datetime import datetime
import os

# Get the absolute path to the project root directory
# Assuming config.py is in src/, and src/ is directly under the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- General Configuration ---
START_YEARS = list(range(1998, 2026))
SIMULATION_END_DATE = '2025-05-31'
MONTHLY_CONTRIBUTION = 500
ADJUST_FOR_INFLATION = True

# --- Data Files ---
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

CPI_DATA_FILE = os.path.join(DATA_DIR, "cpi_data.csv")
SP500_DATA_FILE = os.path.join(DATA_DIR, "sp500_data.csv")
SIMULATION_RESULTS_FILE = os.path.join(OUTPUT_DIR, "simulation_results.csv")
PORTFOLIO_HISTORY_FILE = os.path.join(OUTPUT_DIR, "portfolio_history.json")
SUMMARY_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "summary.csv")
SUMMARY_HTML_FILE = os.path.join(OUTPUT_DIR, "summary.html")

# --- FRED API Configuration ---
CPI_SERIES_ID = "CPIAUCSL"

# --- Yahoo Finance Configuration ---
SP500_TICKER = "^SP500TR"
DATA_FETCH_START_DATE = "1997-12-01"
DATA_FETCH_END_DATE = datetime.now().strftime("%Y-%m-%d")
