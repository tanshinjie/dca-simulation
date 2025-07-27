import pandas as pd
import numpy as np
from datetime import datetime
import os

from .config import (
    START_YEARS,
    SIMULATION_END_DATE,
    MONTHLY_CONTRIBUTION,
    ADJUST_FOR_INFLATION,
    CPI_DATA_FILE,
    SP500_DATA_FILE,
    SIMULATION_RESULTS_FILE,
    PORTFOLIO_HISTORY_FILE,
)

def adjust_to_real_dollars(nominal_value, date, cpi_data, target_cpi_value):
    if not ADJUST_FOR_INFLATION or cpi_data is None or cpi_data.empty:
        return nominal_value
    cpi_at_date = cpi_data.asof(date)
    if pd.isna(cpi_at_date) or target_cpi_value is None or pd.isna(target_cpi_value) or target_cpi_value == 0:
        return nominal_value
    return nominal_value * (target_cpi_value / cpi_at_date)

def run_dca_simulation(sp500_data, cpi_data, start_year, end_date_str, monthly_contribution, adjust_for_inflation):
    portfolio_shares = 0
    total_nominal_invested = 0
    total_real_invested_at_time_of_investment = 0
    investment_dates = []
    portfolio_history = []
    start_date = datetime(start_year, 1, 1)
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    target_cpi_value = None
    if adjust_for_inflation and cpi_data is not None and not cpi_data.empty:
        target_cpi_value = cpi_data.asof(end_date)
        if pd.isna(target_cpi_value):
            target_cpi_value = cpi_data.iloc[-1] if not cpi_data.empty else None

    current_month_date = start_date
    while current_month_date <= end_date:
        first_trading_day_of_month = None
        for day_offset in range(31):
            potential_trading_day = current_month_date + pd.Timedelta(days=day_offset)
            if potential_trading_day > end_date:
                break
            trading_day_str = potential_trading_day.strftime('%Y-%m-%d')
            if trading_day_str in sp500_data.index.strftime('%Y-%m-%d'):
                first_trading_day_of_month = potential_trading_day
                break
        if first_trading_day_of_month is None:
            if current_month_date.month == 12:
                current_month_date = datetime(current_month_date.year + 1, 1, 1)
            else:
                current_month_date = datetime(current_month_date.year, current_month_date.month + 1, 1)
            continue
        try:
            sp500_price = sp500_data.loc[first_trading_day_of_month]
        except KeyError:
            trading_day_str = first_trading_day_of_month.strftime('%Y-%m-%d')
            sp500_price = sp500_data.loc[trading_day_str]

        shares_bought = monthly_contribution / sp500_price
        portfolio_shares += shares_bought
        total_nominal_invested += monthly_contribution
        investment_dates.append(first_trading_day_of_month)
        current_portfolio_value = portfolio_shares * sp500_price
        profit = current_portfolio_value - total_nominal_invested
        portfolio_history.append((first_trading_day_of_month.strftime('%Y-%m-%d'), current_portfolio_value, total_nominal_invested, profit))

        if adjust_for_inflation:
            real_contribution = adjust_to_real_dollars(monthly_contribution, first_trading_day_of_month, cpi_data, target_cpi_value)
            total_real_invested_at_time_of_investment += real_contribution
        if current_month_date.month == 12:
            current_month_date = datetime(current_month_date.year + 1, 1, 1)
        else:
            current_month_date = datetime(current_month_date.year, current_month_date.month + 1, 1)

    try:
        final_sp500_price = sp500_data.loc[end_date]
    except KeyError:
        final_sp500_price = sp500_data.asof(end_date)
        if pd.isna(final_sp500_price):
            final_sp500_price = sp500_data.iloc[-1]
    final_nominal_portfolio_value = portfolio_shares * final_sp500_price
    final_real_portfolio_value = None
    if adjust_for_inflation:
        final_real_portfolio_value = adjust_to_real_dollars(final_nominal_portfolio_value, end_date, cpi_data, target_cpi_value)
    total_months_invested = len(investment_dates)
    if total_months_invested == 0:
        return {
            'Start Year': start_year, 'Total Months Invested': 0, 'Total Amount Invested (Nominal)': 0,
            'Final Portfolio Value (Nominal)': 0, 'Final Portfolio Value (Real)': 0, 'Nominal CAGR': 0, 'Real CAGR': 0,
            'Portfolio History': []
        }
    nominal_years = total_months_invested / 12
    nominal_cagr = ((final_nominal_portfolio_value / total_nominal_invested)**(1/nominal_years)) - 1 if total_nominal_invested > 0 and nominal_years > 0 else 0
    real_cagr = None
    if adjust_for_inflation:
        real_years = total_months_invested / 12
        real_cagr = ((final_real_portfolio_value / total_real_invested_at_time_of_investment)**(1/real_years)) - 1 if total_real_invested_at_time_of_investment > 0 and real_years > 0 else 0
    return {
        'Start Year': start_year, 'Total Months Invested': total_months_invested, 'Total Amount Invested (Nominal)': total_nominal_invested,
        'Final Portfolio Value (Nominal)': final_nominal_portfolio_value, 'Final Portfolio Value (Real)': final_real_portfolio_value if adjust_for_inflation else None,
        'Nominal CAGR': nominal_cagr, 'Real CAGR': real_cagr if adjust_for_inflation else None, 'Portfolio History': portfolio_history
    }

def process_data():
    """Runs the DCA simulation and saves the results."""
    sp500_data = pd.read_csv(SP500_DATA_FILE, index_col='Date', parse_dates=True).iloc[:, 0]
    cpi_data = pd.read_csv(CPI_DATA_FILE, index_col='Date', parse_dates=True)['CPI']
    all_simulation_results = []
    all_portfolio_histories = {}
    for year in START_YEARS:
        print(f"Processing simulation for cohort starting in {year}...")
        result = run_dca_simulation(sp500_data, cpi_data, year, SIMULATION_END_DATE, MONTHLY_CONTRIBUTION, ADJUST_FOR_INFLATION)
        all_simulation_results.append(result)
        all_portfolio_histories[year] = result['Portfolio History']
    results_df = pd.DataFrame(all_simulation_results)
    results_df.to_csv(SIMULATION_RESULTS_FILE, index=False)
    # Ensure the output directory exists before saving
    os.makedirs(os.path.dirname(PORTFOLIO_HISTORY_FILE), exist_ok=True)
    pd.Series(all_portfolio_histories).to_json(PORTFOLIO_HISTORY_FILE)
    print(f"Simulation results saved to {SIMULATION_RESULTS_FILE}")
    print(f"Portfolio history saved to {PORTFOLIO_HISTORY_FILE}")

if __name__ == "__main__":
    process_data()