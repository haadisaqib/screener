from bs4 import BeautifulSoup
import requests
import finnhub
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import time
from tqdm import tqdm
import yfinance as yf
from tabulate import tabulate


def get_T500():
    
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    tickers = []  # Initialize an empty list to store tickers

    # Find the table with the tickers
    table = soup.find('table', {'id': 'constituents'})
    if not table:
        raise ValueError("Table with id 'constituents' not found on the page.")

    # Extract rows from the table
    rows = table.find_all('tr')[1:]  # Skip the header row

    # Loop through each row to extract tickers
    for row in rows:
        ticker_link = row.find('a', {'rel': 'nofollow'})
        if ticker_link:
            if '.' in ticker_link:
                ticker_link = ticker_link.replace('.', '-')
            if '$' in ticker_link:
                ticker_link = ticker_link.replace('$', '')
            ticker = ticker_link.text.strip()  # Extract the ticker text
            tickers.append(ticker)  # Append the ticker to the list

    # Debugging: Print the final list of tickers
    print(f"Tickers extracted: {tickers}")
    return tickers  # Return the full list of tickers


def upcoming_earnings(tickers):
    earnings_in_5days = []
    load_dotenv()
    apikey = os.getenv("finnhub_api_key")
    client = finnhub.Client(api_key=apikey)

    current_date = datetime.now().isoformat().split('T')[0]
    print(current_date)
        
    current_date_object = datetime.strptime(current_date, "%Y-%m-%d")
    end_date = current_date_object + timedelta(days=5)
    end_date = end_date.strftime("%Y-%m-%d")
    print(end_date)

    # Iterate over the list of tickers
    counter = 0
    
    for ticker in tqdm(tickers, desc="Processing Stocks"):
        response = client.earnings_calendar(_from=current_date, to='2025-10-12', symbol=ticker, international=False)
        if "earningsCalendar" in response and response["earningsCalendar"]:
            earnings_in_5days.append(ticker)
        time.sleep(1.1)
        counter +=1 

    print(earnings_in_5days)


def get_stock_quote(ticker):
    #hit api endpoint
    stock = yf.Ticker(ticker)
    current_price = stock.info['currentPrice']
    print(current_price)


def get_options(ticker_list):
    stock = yf.Ticker(ticker_list)
    
    # Get list of available option dates
    option_dates = stock.options
    
    # Convert option dates to datetime objects
    option_dates = [datetime.strptime(date, '%Y-%m-%d') for date in option_dates]
    
    # Calculate target date (45 days from now)
    target_date = datetime.now() + timedelta(days=45)
    
    # Find closest date to 45 DTE
    closest_date = min(option_dates, key=lambda x: abs((x - target_date).days))
    
    print(f"Closest option expiration to 45 DTE: {closest_date.strftime('%Y-%m-%d')}")
    
    #get options for that date
    options = stock.option_chain(closest_date.strftime('%Y-%m-%d'))
    print(options.puts.iloc[0:10])
    return options

def get_stocks_biggest_losers(ticker_list):
    # Create hashmap to store ticker:change pairs
    stock_changes = {}
    
    # Loop through tickers and calculate price change
    counter = 0
    for ticker in tqdm(ticker_list, total=len(ticker_list), desc="Processing Stocks"):
        try:
            stock = yf.Ticker(ticker)
            info = stock.fast_info
            current_price = info['lastPrice'] 
            prev_price = info['regularMarketPreviousClose']
            price_change_percentage = (current_price - prev_price) / prev_price * 100 
            stock_changes[ticker] = price_change_percentage
        except KeyError as e:
            print(f"Skipping {ticker} due to missing data: {e}")
        except Exception as e:
            print(f"An error occurred with {ticker}: {e}")
        counter += 1
        
    # Sort hashmap by values (price change) ascending
    sorted_stocks = dict(sorted(stock_changes.items(), key=lambda x: x[1]))

    # Get first 10 biggest losers
    biggest_losers = dict(list(sorted_stocks.items())[:10])

    table_data = [(ticker, f"{change:.2f}%") for ticker, change in biggest_losers.items()]
    table = tabulate(table_data, headers=["Ticker", "Percentage Change"], tablefmt="pretty")
    
    print(table)
    return biggest_losers


def get_news(ticker_list):
    counter = 1
    for ticker in ticker_list:
        news = yf.Ticker(ticker).news
        print(f"News for {ticker}:")
        for article in news:
            # Check if 'content' and 'title' keys exist in the article
            if 'content' in article and 'title' in article['content']:
                print(f"{counter}. {article['content']['title']}")
            else:
                print("Skipping article due to missing 'title'")
            counter += 1

def screener_1():
    stocks = get_T500()
    get_stocks_biggest_losers(stocks)
    get_news(stocks)

def screener_2():
    stocks = get_T500()
    upcoming_earnings(stocks)

# Main

def main():

    sample_list = ['TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'NFLX', 'DIS', 'PEP']
    # upcoming_earnings(stcoks)
    # get_stock_quote('AAPL')
    # get_options('AAPL')
    # from datetime import datetime, timedelta
    # import threading
    # import time
    # from zoneinfo import ZoneInfo

    # def run_screener_1():
    #     # Convert current CT time to ET for market hours
    #     ct_time = datetime.now(ZoneInfo("America/Chicago"))
    #     et_time = ct_time.astimezone(ZoneInfo("America/New_York"))
        
    #     # Calculate time until 10 mins before market close (3:50 PM ET)
    #     market_close_time = et_time.replace(hour=15, minute=50, second=0, microsecond=0)
        
    #     # If current time is past today's market close, schedule for next business day
    #     if et_time >= market_close_time:
    #         market_close_time += timedelta(days=1)
    #         # Skip weekends
    #         while market_close_time.weekday() > 4:  # 5 = Saturday, 6 = Sunday
    #             market_close_time += timedelta(days=1)
        
    #     # Calculate sleep duration
    #     sleep_duration = (market_close_time - et_time).total_seconds()
    #     if sleep_duration > 0:
    #         print(f"Screener 1 will run at {market_close_time.astimezone(ZoneInfo('America/Chicago')).strftime('%I:%M %p CT')}")
    #         time.sleep(sleep_duration)
    #         screener_1()

    # def handle_user_input():
    #     while True:
    #         command = input("\nEnter command (options/quote/earnings/exit):\n").lower().strip()
            
    #         if command == "exit":
    #             break
    #         elif command == "options":
    #             ticker = input("Enter ticker symbol: ")
    #             get_options(ticker)
    #         elif command == "quote":
    #             ticker = input("Enter ticker symbol: ")
    #             get_stock_quote(ticker)
    #         elif command == "earnings":
    #             screener_2()
    #         else:
    #             print("Invalid command. Available commands: options, quote, earnings, exit")

    # # Start screener_1 in a separate thread
    # screener_thread = threading.Thread(target=run_screener_1)
    # screener_thread.daemon = True  # Thread will exit when main program exits
    # screener_thread.start()

    # # Start user input handler in main thread
    # print("Starting command interface. Type 'exit' to quit.")
    # handle_user_input()


main()







