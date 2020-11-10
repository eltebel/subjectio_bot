#!/home/blur/Desktop/projekty/subjectio/bot/bot_backend/.venv/bin/python

from botski.importy import *
from botski.config import *
from botski.models import *
from botski.db import *
from botski.tweepy_init import *
from botski.helpers import *

locale.setlocale(locale.LC_TIME, 'pl_PL.utf8')
print = functools.partial(print, flush=True) # unbuffered

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
app.debug = False
app.config['TEMPLATES_AUTO_RELOAD'] = True

# from flask_debugtoolbar import DebugToolbarExtension
# toolbar = DebugToolbarExtension(app)

@app.before_request
def do_before_request():
    if request.path != url_for('login') and not "/static/" in request.path:
        if not is_user_logged_in():
            return redirect(url_for('login'))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET'])
def login():
    if is_user_logged_in():
        return redirect(url_for('show_payloads'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    error = None
    if request.method == 'POST':
        l, p = request.form['post_username'], request.form['post_password']
        if valid_credentials(l, p):
            return log_the_user_in(l, p)
        else:
            error = 'Invalid username/password'
    return render_template('login.html', error=error)

def is_user_logged_in() -> bool:
    if not 'uid' in session:
        return False

    cookie_uuid = session['uid']
    if Sessions.objects(uuid=cookie_uuid):
        return True

    return False

def valid_credentials(u, p) -> bool:
    passwd = hashlib.sha256(p.encode('utf-8')).hexdigest()
    return (u == ADM_USERNAME and passwd == ADM_PASS_SHA256)

def log_the_user_in(username, password):
    # create_session(username, password)
    AccessesLog(
                when = datetime.datetime.now(),
                username = username,
                ip=request.remote_addr,
            ).save()

    UID = str(uuid.uuid4())
    Sessions(uuid = UID).save()
    session['uid'] = UID

    return redirect(url_for('show_payloads'))

def logout_user():
    UID = session['uid']
    session.pop('uuid', None)
    Sessions.objects(uuid = UID).delete()

@app.route('/show_payloads', methods=["GET", "POST"])
def show_payloads():
    payloads = Payloads.objects().order_by('-id') #descending by id
    for payload in payloads:
        payload_jobdone = JobQueue.objects.filter(Q(payload=payload) & Q(job_done=True))
        payload.how_many_times_sent = payload_jobdone.count()

    return render_template("show_payloads.html", payloads=payloads)

@app.route('/del_payload/<payload_id>', methods=["GET"])
def del_payload_post(payload_id:str):
    Payloads.objects(id=payload_id).delete()
    return redirect(url_for('show_payloads'))

@app.route('/change_status/<payload_id>/<int:status_nr>', methods=["GET"])
def change_status(payload_id:str, status_nr:int):

    app.logger.debug(get_this_function_name(sys._getframe().f_code, (payload_id, status_nr)))

    on_off = bool(status_nr)
    Payloads.objects(id=payload_id).update_one(active=on_off) # TODO: sprawdzaj czy zrobil update
    return redirect(url_for('show_payloads'))

@app.route('/add_payload', methods=["GET"])
def add_payload_view():
    return render_template("add_payload.html")

@app.route('/add_payload', methods=["POST"])
def add_payload_post():

        form = PayloadForm(meta={'csrf': False})

        # app.logger.debug(request.form)
        # app.logger.debug(form.uploaded_image)

        if not form.validate_on_submit(): # from flask_wtf
            return render_template("add_payload.html", form=form)

        filepath = save_img_to_dir(request.files["uploaded_image"], UPLOAD_FOLDER)
        if not filepath:
            return render_template("error.html", error = "Cannot save image (path: "+filepath+")")

        reduce_image_size(path_to_image=Path(filepath), width=REDUCE_UPLOADED_IMAGE_WIDTH)

        twitter_query = request.form["twitter_query"]
        twitter_comment = request.form["twitter_comment"]

        try:
            Payloads(
                        active=0,
                        uploaded_image=filepath,
                        twitter_query=twitter_query,
                        twitter_comment=twitter_comment,
                    ).save()
        except Exception as e:
            return render_template("error.html", error = e)

        return redirect(url_for('show_payloads'))

@app.route('/monitor', methods=["GET"])
def monitor():
    cmd = "cat logs/log_console.txt |tail -n 1000"
    monitor = subprocess.check_output(cmd, shell=True)  # returns the exit code in unix
    monitor = monitor.decode("utf-8")
    os_uname = ''.join(os.uname())
    return render_template("monitor.html", monitor=monitor, os_uname=os_uname)

# https://developer.twitter.com/ja/docs/basics/rate-limits
@app.route('/api', methods=["GET"])
def botski_api():
    temp_var = api.rate_limit_status()

    limits = {}
    doc = temp_var["resources"]
    for iter in doc.keys():
        for iter_inner in doc[iter]:
            inn = doc[iter][iter_inner]
            limit, remaining, reset = inn["limit"], inn["remaining"], inn["reset"]

            if limit != remaining:
                reset = time.strftime('%H:%M:%S', time.localtime(int(reset)))
                limits[iter_inner] = {"limit": limit, "remaining": remaining, "reset": reset}

    api_blocked = Settings.is_api_blocked()
    return render_template("api.html", limits=limits, api_blocked=api_blocked)

@app.route('/block_api/<int:on_off>', methods=["GET"])
def block_api(on_off:int):
    if on_off == 1:
        Settings.block_api()
    else:
        Settings.unblock_api()
    return redirect(url_for('botski_api'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route("/heartbeat")
def heartbeat():
    return jsonify({"status": "healthy"})

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', e=e)

@app.template_global() #function print() for jinja2
def print(n):
    return n

if __name__ == '__main__':
    # serve(app, host='0.0.0.0', port=5000, ident="hello")
    run_simple('localhost', 5000, app,
                 use_reloader=True, use_debugger=True, use_evalex=True)

# pprint(app.view_functions)

# TODO
# wykorzystaj get_this_function_name() do debugowania innych funkcji
# mozliwosc obejrzenia kolejki
# w panelu dorob suffix query search -> -replies
