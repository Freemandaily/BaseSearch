import requests
import logging,os
from datetime import datetime
from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

API_KEY =  os.environ.get('ApiKey')
BASE_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"
app = FastAPI()

class TweetSearch:
    def __init__(self,api_key):
        self.header = {
            "X-API-Key": api_key
        }
        self.params = {
            "query": '',  
            'cursor':"",
            'hash_next_page':True
            }
        self.all_tweets = []
        self.EarlyTweets = []


searcher = TweetSearch(API_KEY)
def search():
    try:
        while True:
            # Make the GET request to the TwitterAPI.io endpoint
            response = requests.get(BASE_URL, headers=searcher.header, params=searcher.params)
            data = response.json()
            tweets = data.get('tweets', [])
            if not tweets:
                logging.info("No tweets found for the given query. Checking Next Hours Tweets")
                break
            for tweet in tweets:
                tweet_info = {
                    "userName": tweet.get("author", {}).get("userName"),
                    "text": tweet.get("text"),
                    "createdAt": tweet.get("createdAt"),
                    'tweet_link': tweet.get('url')
                }
                searcher.all_tweets.append(tweet_info)
            if not data['next_cursor']:
                logging.warning("No more tweets found or reached the end of results.")
                break

            searcher.params['cursor'] = data['next_cursor']
            logging.info(f"Fetched {len(data['tweets'])} tweets, moving to next page...") 
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as err:
        logging.error(f"Error occurred: {err}")
    except ValueError as json_err:
        logging.error(f"Error parsing JSON response: {json_err}")

@app.get('/search/{keyword}/{date}')
def search_tweets(keyword:str,date:str,limit:int = 1,checkAlive:bool = False):
    if checkAlive:
        logging.info('Checking if Api is Alive')
        return {'Status':200}
    hour = 0
    while True:
        hour += 1
        keyword_date = f"{keyword} until:{date}_{hour}:00:00_UTC"
        searcher.params['query'] = keyword_date
        search()
        if searcher.all_tweets:
            logging.info(f"Fetched {len(searcher.all_tweets)} tweets for keyword: {keyword_date}")
            break
    for tweet in reversed(searcher.all_tweets):
        if len(searcher.EarlyTweets) == limit:
            break
        searcher.EarlyTweets.append(tweet)
    return searcher.EarlyTweets     





