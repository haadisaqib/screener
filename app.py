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
import threading
from zoneinfo import ZoneInfo
import pytz




def system_print(message):
    """Custom function to print system messages clearly separated from user input."""
    print(f"[INFO] {message}")

def print_clickable_link(text, url):
    """Prints a clickable hyperlink in the terminal."""
    escape_sequence = f"\033]8;;{url}\033\\{text}\033]8;;\033\\"
    print(escape_sequence)


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
        response = client.earnings_calendar(_from=current_date, to=end_date, symbol=ticker, international=False)
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
        print("\n" * 2)
        print(f"News for {ticker}:")
        for article in news:
            try:
                # Check if 'content' and 'title' keys exist in the article
                if 'content' in article and 'title' in article['content']:
                    print_clickable_link(f"{counter}. {article['content']['title']}", article['content']['clickThroughUrl']['url'])
                else:
                    print("Skipping article due to missing 'title'")
            except TypeError as e:
                pass
            counter += 1

def screener_1():
    stocks = get_T500()
    biggest_losers = get_stocks_biggest_losers(stocks)
    get_news(biggest_losers)

def screener_2():
    stocks = get_T500()
    upcoming_earnings(stocks)

def run_screener():
    cst = pytz.timezone("US/Central")
    while True:
        local_time = datetime.now(cst)
        try:
            if local_time.hour == 14 and local_time.minute == 0:
                screener_1()
            else:
            # Calculate the time until 14:00 CST today
                target_time = datetime(local_time.year, local_time.month, local_time.day, 14, 0, 0, tzinfo=cst)
            if local_time >= target_time:
                # If it's already past 14:00, calculate for the next day
                target_time += timedelta(days=1)

                # Calculate the time difference in seconds
                time_difference = (target_time - local_time).total_seconds()
                system_print(f"Not 14:00 CST, sleeping for {time_difference:.2f} seconds until 14:00 CST.")
                
                # Sleep for the calculated time
                time.sleep(time_difference)
        except Exception as e:
            system_print(f"An error occurred: {e}")

def main():
    # Start the screener in a separate thread
    screener_thread = threading.Thread(target=run_screener)
    screener_thread.daemon = True  # Allows the program to exit even if the thread is running
    screener_thread.start()
    time.sleep(1)

    # Allow user to run functions at runtime
    while True:
        user_input = input(">>")
        if user_input.startswith("get_stock_quote"):
            _, ticker = user_input.split()
            get_stock_quote(ticker)
        elif user_input.startswith("--help"):
            print("get_stock_quote <ticker>")
            print("get_options <ticker>")
            print("upcoming_earnings <list of ticker(s)>")
            print("screener 1 <default S&P 500>")
            print("screener 2 <default S&P 500>")
        elif user_input.startswith("get_options"):
            _, ticker = user_input.split()
            get_options(ticker)
        elif user_input.startswith("upcoming_earnings"):
            upcoming_earnings(get_T500())
        elif user_input.lower() == "exit" or user_input.lower() == "quit":
            print("Exiting program.")
            break
        elif user_input.lower() == "screener 1":
            screener_1()
        elif user_input.lower() == "screener 2":
            screener_2()
        else:
            print("Unknown command. try --help for command list.")

main()







