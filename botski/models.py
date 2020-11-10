from botski.importy import *
from botski.helpers import *

class PayloadForm(FlaskForm):
    uploaded_image = FileField(validators=[FileRequired(), FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    twitter_query = StringField('twitter_query', validators=[Length(min=1, max=1024)])
    twitter_comment = StringField('twitter_comment', validators=[Length(min=1, max=280)])

class Users(Document):
    username = StringField(required=True)
    password = StringField(required=True)

class Sessions(Document):
    uuid = StringField(required=True, unique=True)

class AccessesLog(Document):
    when = DateTimeField(default=datetime.datetime.now)
    username = StringField(required=True)
    ip = StringField(required=True)

class FoundTweets(Document):
    found_at = DateTimeField(default=datetime.datetime.now)
    tweet_id = IntField(max_length=60, required = True, unique=True)
    tweet_user = StringField(max_length=100, required = True)
    tweet_text = StringField(max_length=280, required = True)
    tweet_created = StringField(max_length=100, required = True)

class Payloads(Document):
    active = BooleanField(required=True)
    twitter_query = StringField(max_length=500, required=True, unique=True)
    uploaded_image = StringField(required=True)
    twitter_comment = StringField(max_length=280, required=True)
    created = DateTimeField(default=datetime.datetime.now)

    def get_elements(activeOnly=True) -> list:
        return Payloads.objects(active=activeOnly)

class JobQueue(Document):
    added = DateTimeField(default=datetime.datetime.now)
    tweet = ReferenceField(FoundTweets, required=True, unique=True)
    tweet_sent_id = IntField(max_length=60, default=None)
    payload = ReferenceField(Payloads, required=True, reverse_delete_rule=mongoengine.CASCADE)
    job_done = BooleanField(default=False) #TODO przydalaby się data zakonczenia
    payload_sent_at = DateTimeField(default=None)

    def get_elements(job_done=False):
        return JobQueue.objects(job_done=job_done)

    def get_newest_tweet(payload_obj):
        payload_object = JobQueue.objects(payload=payload_obj)
        # debug_bot(f'get_newest_tweet() {payload_object}')
        payload_sorted = payload_object.order_by("-added").limit(-1).first()
        # debug_bot(f'get_newest_tweet() {payload_sorted}')
        return payload_sorted

    def get_queue_length(job_done=False):
        return JobQueue.get_elements(job_done=job_done).count()

class Settings(Document):
    api_block = BooleanField(required=True)

    def block_api(block=True):
        Settings.objects().update_one(api_block=bool(block))

    def unblock_api():
        Settings.block_api(block=False)

    def is_api_blocked():
        # debug_bot(f"[API] IS BLOCKED BY THE USER")
        return Settings.objects().first().api_block

class Time(Document):
    def estimateSleepTime() -> int:
        if Settings.is_api_blocked():
            return 15
        return 80

    def estimateSleepTimeForSendComment():
        return 36
