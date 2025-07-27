# DCA Simulation Project

This project simulates Dollar Cost Averaging (DCA) strategies for S&P 500 investments across different investor cohorts starting from various years.

## Features

- Simulates DCA investments for multiple investor cohorts (1998-2025)
- Fetches real-time S&P 500 Total Return data from Yahoo Finance
- Downloads CPI data from FRED for inflation adjustment
- Calculates both nominal and real (inflation-adjusted) returns
- Generates visualizations and statistical analysis
- Supports both online data fetching and local CSV data usage

## Setup

1. **Clone the repository and navigate to the project directory**

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   - Copy `.env.example` to `.env`
   - Get a FRED API key from: https://fred.stlouisfed.org/docs/api/api_key.html
   - Update the `.env` file with your API key:
     ```
     FRED_API_KEY=your_actual_api_key_here
     ```

## Usage

### Download CPI Data (Optional)
If you want to download fresh CPI data:
```bash
python download_cpi.py
```

### Run the Simulation
```bash
python main.py
```

This will:
- Fetch S&P 500 data from Yahoo Finance
- Load CPI data (from local file if available, otherwise from FRED API)
- Run DCA simulations for all investor cohorts
- Generate charts and statistical summaries
- Save results to `summary.txt`

## Files

- `main.py` - Main simulation script
- `download_cpi.py` - Script to download CPI data from FRED
- `cpi_data.csv` - Local CPI data file (if available)
- `.env` - Environment variables (not tracked in git)
- `.env.example` - Template for environment variables
- `requirements.txt` - Python dependencies
- `result.txt` - Simulation output (generated)
- `summary.txt` - Summary statistics (generated)

## Security

- API keys are stored in environment variables and never committed to the repository
- The `.env` file containing sensitive information is ignored by git
- Use the `.env.example` template to set up your own environment variables

## Configuration

You can modify the following parameters in `main.py`:
- `START_YEARS` - List of investor cohort start years
- `END_DATE` - End date for all simulations
- `MONTHLY_CONTRIBUTION` - Monthly investment amount
- `ADJUST_FOR_INFLATION` - Enable/disable inflation adjustment

## Output

The simulation generates:
- Summary table with performance metrics
- CAGR charts by investor start year
- Portfolio value accumulation charts
- CAGR distribution plots
- Statistical summaries and performance highlights
