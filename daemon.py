#!/home/blur/Desktop/projekty/subjectio/bot/bot_backend/.venv/bin/python

# import sys
# sys.path.append(".")

from botski.importy import *
from botski.config import *
from botski.models import *
from botski.db import *
from botski.tweepy_init import *
from botski.helpers import *

locale.setlocale(locale.LC_TIME, 'pl_PL.utf8')

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
app.debug = True

# from flask_debugtoolbar import DebugToolbarExtension
# toolbar = DebugToolbarExtension(app)

def check_is_api_blocked(func=None):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        if Settings.is_api_blocked():
            debug_bot(f"[API] IN {func.__name__}() API IS BLOCKED BY THE USER")
            return None
        return func(*args, **kwargs)
    return inner

@check_is_api_blocked
def send_comment(task:JobQueue, REALLY=False):

    tweet_id = task.tweet.tweet_id
    comment_text = task.payload.twitter_comment
    photo_path = task.payload.uploaded_image

    debug_bot("[API] Comment will be sent for tweet ID:", tweet_id, "WITH TEXT:",
                        comment_text, "WITH PHOTO:", photo_path)

    if not REALLY:
        return

    image = (photo_path)
    media_ids = [api.media_upload(image).media_id_string]
    tweet = None

    try:
        tweet = api.update_status(status = comment_text,
                                  in_reply_to_status_id = tweet_id,
                                  auto_populate_reply_metadata=True,
                                  media_ids = media_ids)
        debug_bot("[API] Comment SENT!")

    except tweepy.error.TweepError as e:
        debug_bot(f"[ERROR] {e}")
        # debug_bot(f"[API_CODE] {e.api_code}")
        handle_sending_error(task, e.api_code)

    return tweet

def handle_sending_error(task:JobQueue, tweepy_api_code):
    if tweepy_api_code == 433: # [{'code': 433, 'message': 'The original Tweet author restricted who can reply to this Tweet.'}]
        mark_task_as_done(task)

    if tweepy_api_code == 385: # [{'code': 385, 'message': 'You attempted to reply to a Tweet that is deleted or not visible to you.'}]
        mark_task_as_done(task)

    # [{'code': 186, 'message': 'Tweet needs to be a bit shorter.'}]
    # [{'code': 326, 'message': 'To protect our users from spam and other malicious activity, this account is temporarily locked. Please log in to https://twitter.com to unlock your account.'}]

def build_query_for_payload(payload:Payloads) -> str:
    query = payload["twitter_query"] + " " + ADDITIONAL_QUERY_SUFFIX
    return query

def get_latest_tweet_for_payload(payload:Payloads):
    newest_tweet = JobQueue.get_newest_tweet(payload)
    since_id = None
    if hasattr(newest_tweet, 'tweet'):
        since_id = newest_tweet.tweet.tweet_id
        debug_bot(f'[INFO] Latest found tweet for payload -> since_id={since_id}')
    return since_id

@check_is_api_blocked
def find_tweets_for_payload(payload:Payloads) -> tweepy.cursor.ItemIterator:

    since_id = get_latest_tweet_for_payload(payload)
    query = build_query_for_payload(payload)

    debug_bot("[API] Looking tweets for query:", query)
    tweepy_cursor = tweepy.Cursor(api.search, since_id = since_id,
                                  result_type="recent", q=query,
                                  count=HOW_MANY_TWEETS_TO_FIND).items(HOW_MANY_TWEETS_TO_FIND)
    return tweepy_cursor

def save_found_tweets_into_database(tweepy_cursor:tweepy.cursor.ItemIterator, payload:Payloads) -> list:
    try: # strange error from 12.10.2020.txt
        for tweet in tweepy_cursor:
            tweet_id = int(tweet.id_str)
            try:
                debug_bot(f"[DB] Add tweet with id: {tweet_id}")
                FoundTweets( tweet_id = int(tweet_id),
                             tweet_user = str(tweet.user.screen_name),
                             tweet_created = str(tweet.created_at),
                             tweet_text = str(tweet.text)).save()
            except mongoengine.errors.NotUniqueError:
                debug_bot("[DB] DUPLICATED in FoundTweets!")

            try:
                debug_bot("[DB] Add to JobQueue tweet_id:", int(tweet_id))
                payload = Payloads.objects(id=payload.id).first()
                tweet = FoundTweets.objects(tweet_id=tweet.id_str).first()
                JobQueue(payload = payload, tweet = tweet).save()
            except mongoengine.errors.NotUniqueError:
                debug_bot("[DB] DUPLICATED in JobQueue!")
    except tweepy.error.TweepError as e:
        debug_bot(f"[ERROR] {e}")

    return True

def mark_task_as_done(task):
    JobQueue.objects(tweet=task.tweet).update_one(job_done=True)
    debug_bot("[QUEUE] From now this task is marked as done.")

def process_queue_and_send(queue):

    tweet_id = None
    sent_tweet = None
    task_number = 0

    for task in queue:
        debug_bot("\n[PROCESS_QUEUE] processing JobQueue id:", task.id)

        if not hasattr(task, 'payload'):
            debug_bot(f"[PROCESS_QUEUE] skip task: {task.id} because his payload has been deleted in the meantime")
            continue

        if task.payload.active == False:
            debug_bot("[PROCESS_QUEUE] delete task with tweet_id:", task.tweet.tweet_id,
                      "because his payload has been turned off")
            # DODATKOWO TUTAJ POTRZEBNY JEST TRY
            JobQueue.objects(tweet=task.tweet).delete()
            FoundTweets.objects(tweet_id=int(task.tweet.tweet_id)).delete()
            continue

        if task_number > 0:
            sleep_time = Time.estimateSleepTimeForSendComment()
            sleep_bot(sleep_time, more_info="before I can send next tweet")
        task_number += 1

        debug_bot("[PROCESS_QUEUE] Preparing to send comment Nº", task_number, "/", len(queue))
        try:
            sent_tweet = send_comment(task, REALLY=True)
        # except tweepy.error.TweepError as e:
        #     if e.api_code == "433": # TODO# TODO
        #         mark_task_as_done(task) # TODO
        except Exception as e:
            debug_bot(f"[ERROR] {e}")
            raise

        if sent_tweet:
            sent_at = datetime.datetime.now()
            new_tweet_id = sent_tweet.id_str

            JobQueue.objects(tweet=task.tweet).update_one(tweet_sent_id=new_tweet_id)
            debug_bot("[QUEUE] New ID for sent tweet:", new_tweet_id)

            JobQueue.objects(tweet=task.tweet).update_one(payload_sent_at=sent_at)
            debug_bot("[QUEUE] Payload sent at:", sent_at)

            mark_task_as_done(task)

        # break

def main(loop_nr, uptime):
    now = datetime.datetime.now()
    queue = JobQueue.get_elements(job_done=False)
    active_payloads:QuerySet = Payloads.get_elements(activeOnly=True)

    debug_bot(f"\n+--------------------------------------------------------------------")
    debug_bot(f"|      Bot iteration nr {loop_nr}, queue size: {len(queue)}, active payloads: {len(active_payloads)}")
    debug_bot(f"|      init: {now}, uptime: {now - uptime}                               ")
    debug_bot(f"+--------------------------------------------------------------------\n")

    if queue:
        process_queue_and_send(queue)
    else:
        debug_bot("[QUEUE] There is nothing to do at the moment")

    for payload in active_payloads:
        found_tweets_for_payload = find_tweets_for_payload(payload)
        if found_tweets_for_payload:
            save_found_tweets_into_database(found_tweets_for_payload, payload)

    sleep_time = Time.estimateSleepTime()
    sleep_bot(sleep_time)

def get_payloads(activeOnly=True) -> list:
    return Payloads.objects(active=activeOnly)

def get_actual_api_limits() -> dict:
    return api.rate_limit_status()

if __name__ == "__main__":
    loop_nr = 0
    uptime = datetime.datetime.now()
    while True:
        loop_nr += 1
        main(loop_nr, uptime)
