import pandas as pd
import plotly.graph_objects as go
import json
import os

from .config import (
    SIMULATION_RESULTS_FILE,
    PORTFOLIO_HISTORY_FILE,
    SUMMARY_OUTPUT_FILE,
    SUMMARY_HTML_FILE,
    ADJUST_FOR_INFLATION
)

def visualise_data():
    """Loads processed data and generates visualizations."""
    results_df = pd.read_csv(SIMULATION_RESULTS_FILE)
    with open(PORTFOLIO_HISTORY_FILE, 'r') as f:
        all_portfolio_histories = json.load(f)

    # Save summary to CSV (already implemented)
    results_df.to_csv(SUMMARY_OUTPUT_FILE, index=False)
    print(f"Summary data saved to {SUMMARY_OUTPUT_FILE}")

    # --- Generate comprehensive summary for HTML ---
    summary_content = ""

    # Summary Table
    summary_content += "<h2>--- Summary Table ---</h2>"
    display_cols = ['Start Year', 'Total Amount Invested (Nominal)', 'Final Portfolio Value (Nominal)', 'Nominal CAGR']
    if ADJUST_FOR_INFLATION:
        display_cols.insert(3, 'Final Portfolio Value (Real)')
        display_cols.append('Real CAGR')

    formatted_df = results_df[display_cols].copy()
    for col in ['Total Amount Invested (Nominal)', 'Final Portfolio Value (Nominal)']:
        formatted_df[col] = formatted_df[col].apply(lambda x: f"${x:,.2f}")
    if ADJUST_FOR_INFLATION:
        formatted_df['Final Portfolio Value (Real)'] = formatted_df['Final Portfolio Value (Real)'].apply(lambda x: f"${x:,.2f}" if x is not None else "N/A")

    for col in ['Nominal CAGR']:
        formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.2%}")
    if ADJUST_FOR_INFLATION:
        formatted_df['Real CAGR'] = formatted_df['Real CAGR'].apply(lambda x: f"{x:.2%}" if x is not None else "N/A")

    summary_content += formatted_df.to_html(index=False)

    # Statistical Summary
    summary_content += "<h2>--- Statistical Summary ---</h2>"
    summary_content += f"<p>Mean Nominal CAGR: {results_df['Nominal CAGR'].mean():.2%}</p>"
    summary_content += f"<p>Standard Deviation of Nominal CAGRs: {results_df['Nominal CAGR'].std():.2%}</p>"
    if ADJUST_FOR_INFLATION:
        real_cagrs = results_df['Real CAGR'].dropna()
        if not real_cagrs.empty:
            summary_content += f"<p>Mean Real CAGR: {real_cagrs.mean():.2%}</p>"
            summary_content += f"<p>Standard Deviation of Real CAGRs: {real_cagrs.std():.2%}</p>"
        else:
            summary_content += "<p>Real CAGR statistics not available due to missing data.</p>"

    # Performance Highlights
    summary_content += "<h2>--- Performance Highlights ---</h2>"
    best_nominal_year = results_df.loc[results_df['Nominal CAGR'].idxmax()]
    worst_nominal_year = results_df.loc[results_df['Nominal CAGR'].idxmin()]

    summary_content += f"<p>Best Performing Entry Year (Nominal CAGR): {int(best_nominal_year['Start Year'])} ({best_nominal_year['Nominal CAGR']:.2%})</p>"
    summary_content += f"<p>Worst Performing Entry Year (Nominal CAGR): {int(worst_nominal_year['Start Year'])} ({worst_nominal_year['Nominal CAGR']:.2%})</p>"

    if ADJUST_FOR_INFLATION:
        valid_real_cagrs_df = results_df.dropna(subset=['Real CAGR'])
        if not valid_real_cagrs_df.empty:
            best_real_year = valid_real_cagrs_df.loc[valid_real_cagrs_df['Real CAGR'].idxmax()]
            worst_real_year = valid_real_cagrs_df.loc[valid_real_cagrs_df['Real CAGR'].idxmin()]
            summary_content += f"<p>Best Performing Entry Year (Real CAGR): {int(best_real_year['Start Year'])} ({best_real_year['Real CAGR']:.2%})</p>"
            summary_content += f"<p>Worst Performing Entry Year (Real CAGR): {int(worst_real_year['Start Year'])} ({worst_real_year['Real CAGR']:.2%})</p>"
        else:
            summary_content += "<p>Real CAGR performance highlights not available due to missing data.</p>"

    # Ensure the output directory exists before saving
    os.makedirs(os.path.dirname(SUMMARY_HTML_FILE), exist_ok=True)

    summary_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>DCA Simulation Summary</title>
        <style>
            body {{ font-family: sans-serif; margin: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>DCA Simulation Summary</h1>
        {summary_content}
    </body>
    </html>
    """

    with open(SUMMARY_HTML_FILE, "w") as f:
        f.write(summary_html)
    print(f"Summary HTML generated: {SUMMARY_HTML_FILE}. Open this file in your browser to view the summary.")

    # Interactive Plot
    fig = go.Figure()

    for year, history in all_portfolio_histories.items():
        if history:
            history_df = pd.DataFrame(history, columns=['Date', 'Portfolio Value', 'Capital Invested', 'Profit'])
            cagr_info = results_df[results_df['Start Year'] == int(year)]
            nominal_cagr = cagr_info['Nominal CAGR'].values[0]
            real_cagr = cagr_info['Real CAGR'].values[0]
            fig.add_trace(
                go.Scatter(x=history_df['Date'], y=history_df['Portfolio Value'],
                           mode='lines+markers', name=f"{year} (Nominal CAGR: {nominal_cagr:.2%}, Real CAGR: {real_cagr:.2%})",
                           visible=(year == str(max(results_df['Start Year'])))))
            fig.add_trace(
                go.Scatter(x=history_df['Date'], y=history_df['Capital Invested'],
                           mode='lines', name=f"{year} - Capital Invested",
                           visible=(year == str(max(results_df['Start Year'])))))

    fig.update_layout(
        title_text="Accumulated Portfolio Value Over Time",
        xaxis_title="Date",
        yaxis_title="Value ($)",
        updatemenus=[
            dict(
                active=len(all_portfolio_histories) - 1,
                buttons=list([
                    dict(label=str(year), method="update",
                         args=[{"visible": [s_year == str(year) for s_year in all_portfolio_histories for _ in range(2)]},
                               {"title": f"Accumulated Portfolio Value (Started {year})"}])
                    for year in all_portfolio_histories
                ]),
            )
        ])
    fig.show()

if __name__ == "__main__":
    visualise_data()