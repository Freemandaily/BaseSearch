import requests,re
import logging
from fastapi import FastAPI
import time,os,sys
import asyncio,aiohttp
from datetime import datetime,timedelta


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


API_KEY =  os.environ.get('ApiKey')
BASE_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"
app = FastAPI()

header = {
            "X-API-Key": API_KEY
        }

def search(params):
    from datetime import timedelta,datetime
    all_tweets = []
    try:
        while True:
            # Make the GET request to the TwitterAPI.io endpoint
            response = requests.get(BASE_URL, headers=header, params=params)
            data = response.json()
            tweets = data.get('tweets', [])
            if not tweets:
                logging.info("No tweets found for the given query. Checking Next Hours Tweets")
                if all_tweets:
                    return all_tweets
                break
            for tweet in tweets:
                dt = datetime.strptime(tweet.get("createdAt"), "%a %b %d %H:%M:%S %z %Y")
                date_utc_plus_one = dt + timedelta(hours=1)
                tweet_date = date_utc_plus_one.strftime("%a %b %d %H:%M:%S %z %Y")
                tweet_info = {
                    "userName": tweet.get("author", {}).get("userName"),
                    "text": tweet.get("text"),
                    "createdAt": tweet_date,
                    'tweet_link': tweet.get('url')
                }
                all_tweets.append(tweet_info)
            if not data['next_cursor']:
                logging.warning("No more tweets found or reached the end of results.")
                return all_tweets

            params['cursor'] = data['next_cursor']
            logging.info(f"Fetched {len(data['tweets'])} tweets, moving to next page...") 
    
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as err:
        logging.error(f"Error occurred: {err}")
    except ValueError as json_err:
        logging.error(f"Error parsing JSON response: {json_err}")

@app.get('/search/{keyword}/{date}')
def search_tweets(keyword:str,date:str,from_date:str|None = None,limit:int = 1,checkAlive:bool = False):
    if from_date:
        keyword = f"{keyword} since:{from_date}"
    EarlyTweets = []
    if checkAlive:
        logging.info('Checking if Api is Alive')
        return {'Status':200}
    hour = 0
    while True:
        hour += 1
        keyword_date = f"{keyword} until:{date}_{hour}:00:00_UTC"
        params = {
            "query": keyword_date,
            'cursor':"",
            'hash_next_page':True
            }
        params['query'] = keyword_date
        if hour == 24:
            logging.warning("Reached 24 hours limit, stopping search.")
            if all_tweets:
                break
            return {'Error': 'No tweets found for the given query. Change the keyword or date.'}
        all_tweets= search(params)
        if all_tweets and len(all_tweets) >= limit:
            logging.info(f"Fetched {len(all_tweets)} tweets for keyword: {keyword_date}")
            break
    for tweet in reversed(all_tweets):
        if len(EarlyTweets) == limit:
            break
        EarlyTweets.append(tweet)
    return EarlyTweets 


def link_search(tweet_id:str):
    from datetime import datetime,timedelta
    logging.info(f'Searchig Tweet With Id')
    url = f"https://api.twitterapi.io/twitter/tweets?tweet_ids={tweet_id}"
        
    header = {
                "X-API-Key": API_KEY
            }
    response = requests.get(url=url,headers=header)
    if response.status_code == 200:
        result = response.json()
        tweets = result['tweets']
        
        if tweets:
            dt = datetime.strptime(tweets[0]["createdAt"], "%a %b %d %H:%M:%S %z %Y")
            date_utc_plus_one = dt + timedelta(hours=1)
            tweet_date = date_utc_plus_one.strftime("%Y-%m-%d %H:%M:%S")
            contract_patterns = r'\b(0x[a-fA-F0-9]{40}|[1-9A-HJ-NP-Za-km-z]{32,44}|T[1-9A-HJ-NP-Za-km-z]{33})\b'
            ticker_partterns = r'\$[A-Za-z0-9_-]+'
            ticker_names = re.findall(ticker_partterns,tweets[0]['text'])
            contracts  = re.findall(contract_patterns,tweets[0]['text']) 
            tweet_info = {
                'ticker_names':ticker_names,
                'contracts':contracts,
                'date_tweeted':tweet_date,
                'followers':tweets[0]['author']['followers']
            }
            return tweet_info
        else:
            return {'Error':'Couldnt Search With This Link'}
    else:
        print(response.status_code)
        return {'Error': f'Couldnt Search With Link. Code {response.status_code}'}



@app.get('/link_search')
def search_with_link(url:str):
    url = url.lower()
    if url.startswith('https://x.com/'):
        try:
            tweet_id = url.split('/')[-1]
            username = url.split('/')[-3]
            if len(tweet_id) == 19 and isinstance(int(tweet_id),int):
                tweet_data = link_search(tweet_id=tweet_id)
                return tweet_data
            else:
                return {'Error':'Invalid Tweet_id'}
        except:
            return {'Error':'Invalid X link'}
    else:
        return {'Error': 'Invalid X Link: Link is not X link'}



async def Process_price_Data(price_data):
    logging.info('Processing Price Data')
    timeframeData = price_data['Timeframe_minute']
    timeframe = list(timeframeData.keys())[0]
    start_timestamp = price_data['start_time']
    end_timestamp = price_data['end_time']
    bybit_price_info = timeframeData[timeframe]
                # 'lastprice'                                                                    start price
    price_info = [float(price) for data in bybit_price_info for index, price in enumerate(data) if index in [1,2,3,4]]
    timestamp_info = [timestamp for data in bybit_price_info for index, timestamp in enumerate(data) if index in [0]]

    if start_timestamp in timestamp_info:
        entry_price = price_info[-1]
        price_info = price_info[:-4]
    else:
        entry_price = price_info[-4]
    close_price = price_info[3] 
    peak_price = round(max(price_info),7)
    lowest_price = round(min(price_info),7)
    max_so_far = price_info[-4]
    max_drawdown  = 0 
    
    percentage_change = str(round(((close_price - entry_price)/entry_price) * 100,3)) + '%'
    entry_to_peak = str(round(((peak_price - entry_price) /entry_price) * 100,3)) +'%'
    entry_price = "{:.13f}".format(entry_price).rstrip("0") 
    close_price = "{:.13f}".format(close_price).rstrip("0")
    lowest_price =  "{:.13f}".format(lowest_price).rstrip("0")
    peak_price = "{:.13f}".format(peak_price).rstrip("0")

    for price in reversed(price_info):# Using Reversed Here Beacause the price data started from the last item of the  list.
        if price > max_so_far :
            max_so_far = price
        drawadown = (( price - max_so_far) / max_so_far) * 100
        max_drawdown = min(drawadown,max_drawdown)

    if int(timeframe) >= 60:
        hour = int(timeframe) // 60
        minute_check = int(timeframe) % 60
        if minute_check > 0:
            timeframe = f'{hour}hr:{minute_check}m'
        else:
            timeframe = f'{hour}hr'
    else:
        timeframe = f'{timeframe}m'
    price_info = {
                'timeframe':timeframe,
                'Entry_Price': entry_price,
                'Price':close_price,
                '%_Change':percentage_change,
                'Peak_Price':peak_price,
                '%_Entry_to_Peak': entry_to_peak,
                'lowest_Price' : lowest_price,
                'Max_Drawdown': round(max_drawdown,7)
                            }
    return price_info 
     




async def Fetch_Price(session,params,end_time,limit):
    logging.info('Fetching Prices')
    params['end_time'] = end_time
    params['limit'] = limit
    # url = 'https://bybit-ohlcv.onrender.com/bybit/ohlcv'
    url = 'https://bybit-ohlcv2.onrender.com/bybit/ohlcv'
   
    async with session.get(url=url,params=params) as response:
        if response.status == 200:
            await asyncio.sleep(4)
            result = await response.json()
            if result['result']:
                price_data = result['result']['list']
                return {'Timeframe_minute':{limit:price_data},'start_time':params['start_time'],'end_time':end_time}
            logging.error(f'Empty Price Data. Check Your Parameters')
            return {'Error':f'Empty Price Data. Check Your Parameters'}
        logging.error(f'Unable to Fetch Price: code= {response.status }')
        return {'Error':f'Unable to Fetch Price: code= {response.status }'}

async def fetch_symbol(symbol:str):
    logging.info('Fetcing Symbol From Bybit')
    # url = 'https://bybit-ohlcv.onrender.com/bybit/tickers'
    url = 'https://bybit-ohlcv2.onrender.com/bybit/ticker'
    params = {
        'symbol':symbol
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url=url,params=params) as response:
            if response.status == 200:
                result = await response.text()
                return result[1:-1]

async def time_Convert(time_str:str,timeframe):
    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    added_timeframe = dt + timedelta(minutes=timeframe)
    end_time = str(int(time.mktime(time.strptime(str(added_timeframe), "%Y-%m-%d %H:%M:%S"))) * 1000)
    return end_time

async def Bybit_Price_data(symbol:str,timeframes:str|list,start_date_time:str):
    logging.info('Activating Bybit Price Searcher')
    start_time = str(int(time.mktime(time.strptime(start_date_time, "%Y-%m-%d %H:%M:%S"))) * 1000)
    if isinstance(timeframes,list):
        limits = [timeframe for timeframe in timeframes]
        times_tasks = [time_Convert(start_date_time,timeframe) for timeframe in timeframes]
        end_times = await asyncio.gather(*times_tasks)
    elif isinstance(timeframes,str) or isinstance(timeframes,int):
        limits = [timeframes]
        times_tasks = [time_Convert(start_date_time,limit) for limit in limits]
        end_times = await asyncio.gather(*times_tasks)
    
    symbol_task = asyncio.create_task(fetch_symbol(symbol))
    symbol_pair = await symbol_task
    try:
        symbol_error = symbol_pair[1:]
        if symbol_error.startswith('Error'):
            return {f'${symbol}': 'Not On Bybit'}
    except:
        pass
    params = {
            "symbol":str(symbol_pair),
            'interval':1,
            "start_time": start_time
        }
    async with aiohttp.ClientSession() as session:
        prices_Fetch = [Fetch_Price(session=session,params=params,end_time=end_times[index],limit=limit) for index, limit in enumerate(limits) ]
        timeframe_Prices = await asyncio.gather(*prices_Fetch)
        Process_price_task = [Process_price_Data(timeframe_price_data) for timeframe_price_data in timeframe_Prices]
        price_infos = await asyncio.gather(*Process_price_task)
        return {f'${symbol}':price_infos}


def process_timeframe(input_string):
    items = input_string.split(',')
    result = []
    
    for item in items:
        if ':' in item:
            hours, minutes = map(int, item.split(':'))
            total_minutes = hours * 60 + minutes
            result.append(total_minutes)
        else:
            result.append(int(item))
    return sorted(result)

# Search Tweet and grab Ticker mentioned then Get price price Using Tweet date time
@app.get("/link")
def process_link(tweet_url:str,timeframe:str):
    timeframes = process_timeframe(timeframe)
    logging.info('Ready To Search Tweet With Tweet Link')
    # url = 'https://basesearch.onrender.com/link_search/'
    url = 'https://basesearch2.onrender.com/link_search/'
    params = {
        'url':tweet_url
    }
    reaponse = requests.get(url=url,params=params)
    result = reaponse.json()
    ticker_names = result['ticker_names']
    ticker_names =  list(set([ticker[1:] for ticker in ticker_names]))
    tweeted_date = result['date_tweeted'][:-3]+':00'
    
    async def main():
        search_tasks = [Bybit_Price_data(symbol=ticker,timeframes=timeframes,start_date_time=tweeted_date) for ticker in ticker_names]
        ticker_price_data = await asyncio.gather(*search_tasks)
        ticker_price_data.append({'date_tweeted':tweeted_date})
        return ticker_price_data

    ticker_price_data = asyncio.run(main())
    return ticker_price_data

#Search Ticker On  Cex
@app.get("/ticker")
def process_link(tickers:str,start_date:str,timeframe:str):
    logging.info('Ready To Search Ticker On Cex')
    timeframes = process_timeframe(timeframe)
    tickers = list(set(tickers.split()))
    start_date_time = str(start_date)
    
    async def main():
        search_tasks = [Bybit_Price_data(symbol=ticker,timeframes=timeframes,start_date_time=start_date_time) for ticker in tickers]
        ticker_price_data = await asyncio.gather(*search_tasks)
        ticker_price_data.append({'date_tweeted':start_date_time})
        return ticker_price_data
    ticker_price_data = asyncio.run(main())
    return ticker_price_data


