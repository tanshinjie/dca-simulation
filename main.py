import yfinance as yf
import pandas as pd
from fredapi import Fred
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import numpy as np
from datetime import datetime
import io
import base64
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# List of start years for investor cohorts
START_YEARS = list(range(1998, 2026)) # Includes 2025
# End date for the simulation
END_DATE = '2025-05-31'
# Monthly investment contribution in nominal dollars
MONTHLY_CONTRIBUTION = 500
# Flag to adjust for inflation (True by default as per prompt)
ADJUST_FOR_INFLATION = True
# CPI data file
CPI_DATA_FILE = "cpi_data.csv"


# FRED API Key - loaded from environment variable
FRED_API_KEY = os.getenv("FRED_API_KEY")

# Initialize FRED API
try:
    fred = Fred(api_key=FRED_API_KEY)
except Exception as e:
    print(f"Warning: Could not initialize FRED API. Inflation adjustment might fail if no API key is provided or valid. Error: {e}")
    # If FRED API fails, set ADJUST_FOR_INFLATION to False to prevent further errors
    ADJUST_FOR_INFLATION = False

# --- Data Fetching ---

def get_sp500_data(start_year, end_date_str):
    """
    Fetches historical S&P 500 Total Return Index data from Yahoo Finance.
    The ticker '^SP500TR' represents the S&P 500 Total Return.
    """
    print(f"Fetching S&P 500 data from {start_year}-01-01 to {end_date_str}...")
    # Fetch data starting a bit earlier to ensure we have data for the first trading day of the first month
    data = yf.download('^SP500TR', start=f'{start_year-1}-12-01', end=end_date_str)
    if data.empty:
        print(f"Error: Could not fetch S&P 500 data for the specified period.")
        return None
    # yfinance auto-adjusts by default, so 'Close' is the adjusted price.
    # We squeeze the result to ensure it's a Series, not a DataFrame.
    return data['Close'].squeeze()

def get_cpi_data(start_year, end_date_str):
    """
    Fetches U.S. Consumer Price Index (CPI) data from FRED.
    'CPIAUCSL' is the series ID for Consumer Price Index for All Urban Consumers: All Items, Seasonally Adjusted.
    """
    global ADJUST_FOR_INFLATION # Declare global here to modify the global variable
    if not ADJUST_FOR_INFLATION:
        print("Inflation adjustment is disabled. Skipping CPI data fetch.")
        return None

    if os.path.exists(CPI_DATA_FILE):
        print(f"Loading CPI data from local file: {CPI_DATA_FILE}")
        cpi_data = pd.read_csv(CPI_DATA_FILE, index_col='Date', parse_dates=True)['CPI']
        return cpi_data.resample('M').last()

    if not FRED_API_KEY:
        print("Warning: FRED API Key is not set. Cannot fetch CPI data. Disabling inflation adjustment.")
        ADJUST_FOR_INFLATION = False
        return None

    print(f"Fetching CPI data from {start_year}-01-01 to {end_date_str}...")
    try:
        # Fetch data starting a bit earlier to ensure we have data for the first month
        cpi_data = fred.get_series('CPIAUCSL', observation_start=f'{start_year-1}-12-01', observation_end=end_date_str)
        if cpi_data.empty:
            print(f"Error: Could not fetch CPI data for the specified period.")
            return None
        return cpi_data.resample('M').last() # Resample to monthly last value
    except Exception as e:
        print(f"Error fetching CPI data: {e}. Disabling inflation adjustment.")
        ADJUST_FOR_INFLATION = False
        return None

# --- Inflation Adjustment ---

def adjust_to_real_dollars(nominal_value, date, cpi_data, target_cpi_value):
    """
    Adjusts a nominal value to real 2025 dollars using CPI data.
    """
    if not ADJUST_FOR_INFLATION or cpi_data is None or cpi_data.empty:
        return nominal_value # Return nominal if inflation adjustment is off or data is missing

    # Find the CPI value for the given date
    # Use .asof() to get the last available CPI value on or before the date
    cpi_at_date = cpi_data.asof(date)

    if pd.isna(cpi_at_date) or target_cpi_value is None or pd.isna(target_cpi_value) or target_cpi_value == 0:
        # Fallback if CPI data for the specific date or target CPI is missing/invalid
        # This can happen if the date is outside the CPI data range, or data is sparse.
        print(f"Warning: CPI data missing for {date.strftime('%Y-%m-%d')} or target CPI invalid. Cannot adjust for inflation. Returning nominal value.")
        return nominal_value

    return nominal_value * (target_cpi_value / cpi_at_date)

# --- DCA Simulation Logic ---

def run_dca_simulation(sp500_data, cpi_data, start_year, end_date_str, monthly_contribution, adjust_for_inflation):
    """
    Simulates the DCA strategy for a single investor cohort.
    """
    portfolio_shares = 0
    total_nominal_invested = 0
    total_real_invested_at_time_of_investment = 0 # Track real investment at the time it's made
    investment_dates = []
    portfolio_history = []


    start_date = datetime(start_year, 1, 1)
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    # Get the target CPI value for May 31, 2025 (or the closest available date)
    target_cpi_value = None
    if adjust_for_inflation and cpi_data is not None and not cpi_data.empty:
        # Find the CPI value closest to the end_date for conversion
        target_cpi_value = cpi_data.asof(end_date)
        if pd.isna(target_cpi_value):
             # If exact end date CPI is not available, try to get the last available CPI
            target_cpi_value = cpi_data.iloc[-1] if not cpi_data.empty else None
            print(f"Warning: Target CPI for {end_date.strftime('%Y-%m-%d')} not found. Using last available CPI: {target_cpi_value}")

    current_month_date = start_date
    while current_month_date <= end_date:
        # Find the first trading day of the current month
        first_trading_day_of_month = None
        for day_offset in range(31): # Check up to 31 days to find a trading day
            potential_trading_day = current_month_date + pd.Timedelta(days=day_offset)
            if potential_trading_day > end_date: # Stop if we exceed the end date
                break
            # Fix: Check if the trading day exists in the data index
            trading_day_str = potential_trading_day.strftime('%Y-%m-%d')
            if trading_day_str in sp500_data.index.strftime('%Y-%m-%d'):
                first_trading_day_of_month = potential_trading_day
                break

        if first_trading_day_of_month is None:
            # If no trading day found in the month (e.g., data gap), skip this month
            print(f"Warning: No trading day found for {current_month_date.strftime('%Y-%m')}. Skipping investment for this month.")
            # Move to the next month
            if current_month_date.month == 12:
                current_month_date = datetime(current_month_date.year + 1, 1, 1)
            else:
                current_month_date = datetime(current_month_date.year, current_month_date.month + 1, 1)
            continue

        # Get the S&P 500 price on the first trading day
        # Fix: Use proper datetime indexing for pandas Series
        try:
            sp500_price = sp500_data.loc[first_trading_day_of_month]
        except KeyError:
            # Fallback if exact datetime doesn't work
            trading_day_str = first_trading_day_of_month.strftime('%Y-%m-%d')
            sp500_price = sp500_data.loc[trading_day_str]

        # Calculate shares bought
        shares_bought = monthly_contribution / sp500_price
        portfolio_shares += shares_bought
        total_nominal_invested += monthly_contribution
        investment_dates.append(first_trading_day_of_month)
        
        # Record portfolio history
        current_portfolio_value = portfolio_shares * sp500_price
        portfolio_history.append((first_trading_day_of_month, current_portfolio_value))


        # If adjusting for inflation, calculate the real value of this month's contribution
        if adjust_for_inflation:
            real_contribution = adjust_to_real_dollars(monthly_contribution, first_trading_day_of_month, cpi_data, target_cpi_value)
            total_real_invested_at_time_of_investment += real_contribution

        # Move to the next month
        if current_month_date.month == 12:
            current_month_date = datetime(current_month_date.year + 1, 1, 1)
        else:
            current_month_date = datetime(current_month_date.year, current_month_date.month + 1, 1)

    # Calculate final portfolio value
    # Fix: Handle final price retrieval properly
    try:
        final_sp500_price = sp500_data.loc[end_date]
    except KeyError:
        # Use the closest available date
        final_sp500_price = sp500_data.asof(end_date)
        if pd.isna(final_sp500_price):
            final_sp500_price = sp500_data.iloc[-1]
    
    final_nominal_portfolio_value = portfolio_shares * final_sp500_price

    # Calculate final real portfolio value
    final_real_portfolio_value = None
    if adjust_for_inflation:
        final_real_portfolio_value = adjust_to_real_dollars(final_nominal_portfolio_value, end_date, cpi_data, target_cpi_value)

    # Calculate total number of months invested
    total_months_invested = len(investment_dates)
    if total_months_invested == 0:
        # Handle case where no investments were made (e.g., very short period or data issues)
        return {
            'Start Year': start_year,
            'Total Months Invested': 0,
            'Total Amount Invested (Nominal)': 0,
            'Final Portfolio Value (Nominal)': 0,
            'Final Portfolio Value (Real)': 0,
            'Nominal CAGR': 0,
            'Real CAGR': 0,
            'Portfolio History': []
        }

    # Calculate Nominal CAGR
    # CAGR = ((Final Value / Total Invested)^(1/Years)) - 1
    # Years = Total Months / 12
    nominal_years = total_months_invested / 12
    nominal_cagr = ((final_nominal_portfolio_value / total_nominal_invested)**(1/nominal_years)) - 1 if total_nominal_invested > 0 and nominal_years > 0 else 0

    # Calculate Real CAGR
    real_cagr = None
    if adjust_for_inflation:
        real_years = total_months_invested / 12
        real_cagr = ((final_real_portfolio_value / total_real_invested_at_time_of_investment)**(1/real_years)) - 1 if total_real_invested_at_time_of_investment > 0 and real_years > 0 else 0

    return {
        'Start Year': start_year,
        'Total Months Invested': total_months_invested,
        'Total Amount Invested (Nominal)': total_nominal_invested,
        'Final Portfolio Value (Nominal)': final_nominal_portfolio_value,
        'Final Portfolio Value (Real)': final_real_portfolio_value if adjust_for_inflation else None,
        'Nominal CAGR': nominal_cagr,
        'Real CAGR': real_cagr if adjust_for_inflation else None,
        'Portfolio History': portfolio_history
    }

# --- Main Execution ---

if __name__ == "__main__":
    # Fetch all necessary data up to the latest possible end date for all cohorts
    # This ensures CPI data is available for 2025-05-31 for the inflation adjustment target
    max_start_year = min(START_YEARS)
    sp500_data = get_sp500_data(max_start_year, END_DATE)
    cpi_data = get_cpi_data(max_start_year, END_DATE)

    if sp500_data is None or sp500_data.empty:
        print("Fatal Error: S&P 500 data could not be retrieved. Exiting.")
        exit()

    all_simulation_results = []
    latest_portfolio_history = None
    for year in START_YEARS:
        print(f"\nRunning simulation for cohort starting in {year}...")
        result = run_dca_simulation(sp500_data, cpi_data, year, END_DATE, MONTHLY_CONTRIBUTION, ADJUST_FOR_INFLATION)
        all_simulation_results.append(result)
        if year == START_YEARS[-1]:
            latest_portfolio_history = result['Portfolio History']


    results_df = pd.DataFrame(all_simulation_results)

    # --- Output: Summary Table ---
    summary_output = "\n--- Summary Table ---\n"
    # Select and format columns for display
    display_cols = ['Start Year', 'Total Amount Invested (Nominal)', 'Final Portfolio Value (Nominal)', 'Nominal CAGR']
    if ADJUST_FOR_INFLATION:
        display_cols.insert(3, 'Final Portfolio Value (Real)')
        display_cols.append('Real CAGR')

    # Format monetary values and percentages
    formatted_df = results_df[display_cols].copy()
    for col in ['Total Amount Invested (Nominal)', 'Final Portfolio Value (Nominal)']:
        formatted_df[col] = formatted_df[col].apply(lambda x: f"${x:,.2f}")
    if ADJUST_FOR_INFLATION:
        formatted_df['Final Portfolio Value (Real)'] = formatted_df['Final Portfolio Value (Real)'].apply(lambda x: f"${x:,.2f}" if x is not None else "N/A")

    for col in ['Nominal CAGR']:
        formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.2%}")
    if ADJUST_FOR_INFLATION:
        formatted_df['Real CAGR'] = formatted_df['Real CAGR'].apply(lambda x: f"{x:.2%}" if x is not None else "N/A")

    summary_output += formatted_df.to_string(index=False)
    print(summary_output)
    with open("summary.txt", "w") as f:
        f.write(summary_output)

    # --- Output: CAGR by Investor Start Year Chart ---
    fig, ax = plt.subplots(figsize=(12, 7))
    sns.lineplot(x='Start Year', y='Nominal CAGR', data=results_df, marker='o', label='Nominal CAGR', ax=ax)
    if ADJUST_FOR_INFLATION:
        sns.lineplot(x='Start Year', y='Real CAGR', data=results_df, marker='o', label='Real CAGR', ax=ax)
    
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))
    
    plt.title('CAGR by Investor Start Year (S&P 500 DCA)')
    plt.xlabel('Investor Start Year')
    plt.ylabel('Compound Annual Growth Rate (CAGR)')
    plt.grid(True)
    plt.legend()
    plt.xticks(START_YEARS, rotation=45)
    plt.tight_layout()
    plt.show()

    # --- Output: Accumulated Value Over Time Chart ---
    if latest_portfolio_history:
        history_df = pd.DataFrame(latest_portfolio_history, columns=['Date', 'Portfolio Value'])
        plt.figure(figsize=(12, 7))
        sns.lineplot(x='Date', y='Portfolio Value', data=history_df, marker='o')
        plt.title(f'Accumulated Portfolio Value Over Time (Started {START_YEARS[-1]})')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value ($)')
        plt.grid(True)
        plt.tight_layout()
        plt.show()


    # --- Output: CAGR Distribution Plot ---
    plt.figure(figsize=(10, 6))
    if ADJUST_FOR_INFLATION:
        # Combine both CAGRs for a single distribution plot
        cagr_data = pd.DataFrame({
            'CAGR Type': ['Nominal'] * len(results_df) + ['Real'] * len(results_df),
            'CAGR Value': results_df['Nominal CAGR'].tolist() + results_df['Real CAGR'].tolist()
        })
        # Drop NaN values from Real CAGR if any exist (e.g., if adjustment failed for some cohorts)
        cagr_data.dropna(subset=['CAGR Value'], inplace=True)
        sns.histplot(data=cagr_data, x='CAGR Value', hue='CAGR Type', kde=True, palette='viridis', bins=10)
        ax = plt.gca()
        ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))
        plt.title('Distribution of Nominal and Real CAGRs')
    else:
        sns.histplot(results_df['Nominal CAGR'], kde=True, color='skyblue', bins=10)
        ax = plt.gca()
        ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))
        plt.title('Distribution of Nominal CAGRs')
    plt.xlabel('Compound Annual Growth Rate (CAGR)')
    plt.ylabel('Frequency')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.show()

    # --- Output: Statistical Summary ---
    statistical_summary = "\n--- Statistical Summary ---\n"
    statistical_summary += f"Mean Nominal CAGR: {results_df['Nominal CAGR'].mean():.2%}\n"
    statistical_summary += f"Standard Deviation of Nominal CAGRs: {results_df['Nominal CAGR'].std():.2%}\n"
    if ADJUST_FOR_INFLATION:
        # Filter out None/NaN values for real CAGR calculations
        real_cagrs = results_df['Real CAGR'].dropna()
        if not real_cagrs.empty:
            statistical_summary += f"Mean Real CAGR: {real_cagrs.mean():.2%}\n"
            statistical_summary += f"Standard Deviation of Real CAGRs: {real_cagrs.std():.2%}\n"
        else:
            statistical_summary += "Real CAGR statistics not available due to missing data.\n"
    print(statistical_summary)
    with open("summary.txt", "a") as f:
        f.write(statistical_summary)

    # --- Output: Performance Highlights ---
    performance_highlights = "\n--- Performance Highlights ---\n"
    best_nominal_year = results_df.loc[results_df['Nominal CAGR'].idxmax()]
    worst_nominal_year = results_df.loc[results_df['Nominal CAGR'].idxmin()]

    performance_highlights += f"Best Performing Entry Year (Nominal CAGR): {int(best_nominal_year['Start Year'])} ({best_nominal_year['Nominal CAGR']:.2%})\n"
    performance_highlights += f"Worst Performing Entry Year (Nominal CAGR): {int(worst_nominal_year['Start Year'])} ({worst_nominal_year['Nominal CAGR']:.2%})\n"

    if ADJUST_FOR_INFLATION:
        # Fix: Use the correct variable name
        valid_real_cagrs_df = results_df.dropna(subset=['Real CAGR'])
        if not valid_real_cagrs_df.empty:
            best_real_year = valid_real_cagrs_df.loc[valid_real_cagrs_df['Real CAGR'].idxmax()]
            worst_real_year = valid_real_cagrs_df.loc[valid_real_cagrs_df['Real CAGR'].idxmin()]
            performance_highlights += f"Best Performing Entry Year (Real CAGR): {int(best_real_year['Start Year'])} ({best_real_year['Real CAGR']:.2%})\n"
            performance_highlights += f"Worst Performing Entry Year (Real CAGR): {int(worst_real_year['Start Year'])} ({worst_real_year['Real CAGR']:.2%})\n"
        else:
            performance_highlights += "Real CAGR performance highlights not available due to missing data.\n"
    print(performance_highlights)
    with open("summary.txt", "a") as f:
        f.write(performance_highlights)
