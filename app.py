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
# Main

def main():

    sample_list = ['TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'NFLX', 'DIS', 'PEP']
    # upcoming_earnings(stcoks)
    # get_stock_quote('AAPL')
    # get_options('AAPL')
    #run get 500 stocks function market open every day
    while True:
        if datetime.now().hour == 9 and datetime.now().minute == 30:
            get_stocks_biggest_losers(stocks)
            time.sleep(60)
        else:
            print("Waiting for market open...")
            time.sleep(1)

    
main()







