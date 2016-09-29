import praw
import pickle
import time
import os.path
import datetime
import re
import math
from collections import Counter


# define a class for convenient data storage
class RedditPost:
    def __init__(self, title_vec, selftext_vec, created_utc, url):
        self.title_vec = title_vec
        self.selftext_vec = selftext_vec
        self.created_utc = created_utc
        self.url = url


# login into Reddit (refer to PRAW and OAuth guide if you don't understand this)
r = praw.Reddit('Repost finder for r/jokes by /u/nikoliazekter v 1.0')
r.set_oauth_app_info(client_id='YOUR_ID',
                     client_secret='YOUR_SECRET',
                     redirect_uri='http://127.0.0.1:65010/authorize_callback')
r.refresh_access_information('YOUR_ACCESS_INFORMATION')
subreddit = r.get_subreddit('jokes')

# load a list of preprocessed posts from the file (and create new one if it doesn't exist)
# data is stored in a dictionary of type {post_id:RedditPost instance}
if not os.path.isfile("save.p"):
    save_file = open("save.p", "wb")
    pickle.dump({}, save_file)
    save_file.close()
save_file = open("save.p", "rb")
already_done = pickle.load(save_file)
save_file.close()

# convert text to vector representation
WORD = re.compile(r'\w+')


def text_to_vector(text):
    words = WORD.findall(text)
    return Counter(words)


# find cosine similarity between two vectors
def get_cosine(vec1, vec2):
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])

    sum1 = sum([vec1[x] ** 2 for x in vec1.keys()])
    sum2 = sum([vec2[x] ** 2 for x in vec2.keys()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    else:
        return float(numerator) / denominator


# check whether a post is a repost and return the comment
def check_repost(possible_repost):
    for post_id in already_done:
        original_post = already_done[post_id]
        # three conditions for a repost: posted later than the original,
        # has 50% title similarity and 80% text similarity with the original
        if (possible_repost.created_utc > original_post.created_utc) and (
                    get_cosine(text_to_vector(possible_repost.title), original_post.title_vec) > 0.5) and (
                    get_cosine(text_to_vector(possible_repost.selftext), original_post.selftext_vec) > 0.8):
            parsed_date = datetime.datetime.utcfromtimestamp(original_post.created_utc)
            comment = 'This is a repost of\n\n' + original_post.url + "\n\nwhich was posted on " + \
                      parsed_date.date().isoformat() + ' at ' + parsed_date.time().isoformat() + ' UTC.'
            comment += '\n\n*****\n\n'
            comment += 'Contact u/nikolizekter if you have any questions or suggestions regarding the bot.'
            comment += '\n\n*****\n\n'
            comment += 'GitHub code: https://github.com/nikoliazekter/RepostFinderBot'
            return comment
    return 'false'


# a variable for tracking whether new posts were submitted
added_posts = 0

# main loop
while True:
    for post in subreddit.get_new(limit=1000):
        if post.id not in already_done:
            result_comment = check_repost(post)
            if result_comment != 'false':
                post.add_comment(result_comment)
            already_done[post.id] = RedditPost(text_to_vector(post.title), text_to_vector(post.selftext),
                                               post.created_utc, post.url)
            added_posts += 1

    # write to a file only if new posts were submitted
    if added_posts > 0:
        added_posts = 0
        save_file = open("save.p", "wb")
        pickle.dump(already_done, save_file)
        save_file.close()
    # sleep for thirty seconds to give the bot some rest
    time.sleep(30)
