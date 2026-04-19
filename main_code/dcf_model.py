import yfinance as yf
import pandas as pd
import gspread
from datetime import datetime

def get_financial_data(ticker):
    company = yf.Ticker(ticker)
    # Get income statement, balance sheet, and cash flow statement
    income_stmt = company.financials
    balance_sheet = company.balance_sheet
    cash_flow = company.cashflow
    return income_stmt, balance_sheet, cash_flow

def calculate_dcf(income_stmt, balance_sheet, cash_flow, growth_rate=0.05, terminal_growth_rate=0.02, discount_rate=0.10):
    # Extract relevant data (example, adjust based on actual financial data structure)
    try:
        # Free Cash Flow (FCF) - Simplified calculation example
        # Typically: FCF = Operating Cash Flow - Capital Expenditures
        operating_cash_flow = cash_flow.loc["Operating Cash Flow"].iloc[0] # Most recent year
        capital_expenditures = cash_flow.loc["Capital Expenditure"].iloc[0] # Most recent year
        
        # Assuming FCF grows for 5 years
        fcf_projection = [operating_cash_flow - capital_expenditures] # Year 0
        for _ in range(5): # Project 5 years of FCF
            fcf_projection.append(fcf_projection[-1] * (1 + growth_rate))
        
        # Discounted FCF
        discounted_fcf = [fcf / ((1 + discount_rate)**(i+1)) for i, fcf in enumerate(fcf_projection[1:])] # Start from Year 1
        
        # Terminal Value
        terminal_value_fcf = fcf_projection[-1] * (1 + terminal_growth_rate) / (discount_rate - terminal_growth_rate)
        terminal_value_discounted = terminal_value_fcf / ((1 + discount_rate)**6) # Discounted to present year (Year 6 from Year 0)
        
        # Enterprise Value
        enterprise_value = sum(discounted_fcf) + terminal_value_discounted
        
        # Net Debt (example, adjust based on actual balance sheet structure)
        total_debt = balance_sheet.loc["Total Debt"].iloc[0]
        cash_and_equivalents = balance_sheet.loc["Cash And Cash Equivalents"].iloc[0]
        net_debt = total_debt - cash_and_equivalents
        
        # Equity Value
        equity_value = enterprise_value - net_debt
        
        return equity_value
    except KeyError as e:
        print(f"Missing financial data key: {e}. Please check the yfinance data structure.")
        return None
    except Exception as e:
        print(f"Error during DCF calculation: {e}")
        return None

def upload_to_google_sheets(ticker, valuation):
    try:
        gc = gspread.service_account(filename='credentials.json')
        sh = gc.open('NQ100_DATA')  # Open the specified spreadsheet
        worksheet_name = f"{ticker}_DCF"
        try:
            worksheet = sh.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")

        worksheet.clear()
        data_to_upload = [
            ["Metric", "Value"],
            ["Ticker", ticker],
            ["DCF Valuation", valuation]
        ]
        worksheet.update([data_to_upload[0]] + data_to_upload[1:]) # Update header and data
        print(f"DCF 估值數據已成功上傳到 Google Sheets 的工作表 '{worksheet_name}'。")
    except Exception as e:
        print(f"上傳 Google Sheets 失敗: {e}")

def main():
    ticker = "LITE"
    income_stmt, balance_sheet, cash_flow = get_financial_data(ticker)

    if income_stmt is not None and balance_sheet is not None and cash_flow is not None:
        dcf_valuation = calculate_dcf(income_stmt, balance_sheet, cash_flow)
        if dcf_valuation is not None:
            print(f"\n{ticker} 的 DCF 估值為: {dcf_valuation:,.2f}")
            upload_to_google_sheets(ticker, dcf_valuation)
        else:
            print(f"無法計算 {ticker} 的 DCF 估值。")
    else:
        print(f"無法抓取 {ticker} 的財務數據。")

if __name__ == "__main__":
    main()
