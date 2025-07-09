import tweepy,json,re,logging,os
from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

with open('key.json','r') as file:
    keys = json.load(file)
    bearerToken =keys['bearerToken']

client = tweepy.Client(bearer_token=bearerToken)
app = FastAPI()



def checkDuplicateUser(user_tweet,username,tweet_date):
    from datetime import datetime
    add = True
    try:
        for index,tweet in enumerate(user_tweet):
            if tweet['username'] == username and datetime.strptime(tweet['created_at'],"%Y-%m-%d %H:%M") > datetime.strptime(tweet_date,"%Y-%m-%d %H:%M"):
                del user_tweet[index]
                add = True
                break
            elif tweet['username'] == username and datetime.strptime(tweet['created_at'],"%Y-%m-%d %H:%M") < datetime.strptime(tweet_date,"%Y-%m-%d %H:%M"):
                add = False
                break
            else:
                add = True
    except Exception as e:
        add = True
    return user_tweet, add



def TweetSearch(keywords:str):
    users_tweet = []
    try:
        for response in tweepy.Paginator(client.search_recent_tweets,
                                        keywords,
                                        max_results=100,
                                        limit=5,
                                        user_fields=['public_metrics','username'],
                                        tweet_fields=['author_id','created_at','public_metrics'],
                                        expansions=['author_id']
                                        ):
            user_map = {user.id: user for user in response.includes.get('users', [])}
            for tweet in response.data:
                user = user_map.get(tweet.author_id)
                if user:
                    metrics = user.public_metrics
                    username = user.username
                    follower_count = metrics['followers_count']
                else:
                    continue
                tweet_date = tweet.created_at.strftime("%Y-%m-%d %H:%M")
                # Flter account with low followesr account Out
                follower_threshold = 1000
                if int(follower_count) < int(follower_threshold):
                    continue
                users_tweet,affirm = checkDuplicateUser(users_tweet,username,tweet_date)
                if affirm is True:
                    tweet_dict = {
                            'Username': username,
                            'Followers':follower_count,
                            'Tweeted_date':tweet_date,
                            'Tweet_text': re.sub(r'\n+','. ',tweet.text),
                            'Tweet_link': f'https://x.com/{username}/status/{tweet.id}'
                            }
                    users_tweet.append(tweet_dict)
    except Exception as e:
        logging.error(f'Error Spoted issue:{e}')
        return e
    return users_tweet

@app.get('/search/{query}')
def search(query:str,limit:int = 10,checkAlive:bool = False):
    if checkAlive:
        logging.info('Checking if Api is Alive')
        return {'Status':200}
    logging.info('Requesting For Data')
    SearchedResult = TweetSearch(query)
    RequestedResult = list()
    for result in reversed(SearchedResult):

        if len(RequestedResult) == limit:
            break
        RequestedResult.append(result)
    logging.info('Retrieving Data')
    return RequestedResult
