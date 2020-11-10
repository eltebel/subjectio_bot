from botski.importy import *
from botski.models import *
print = functools.partial(print, flush=True) # unbuffered

def convertTuple(tup):
    str = functools.reduce(operator.add, (tup))
    return str

def get_this_function_name(fun, *params):
    return str(fun.co_name) + "(" + str(convertTuple(params)) + ")"

def make_indent_json(json_str:str):
    return json.dumps(json_str, indent=4, sort_keys=True)

def reduce_image_size(path_to_image=None, width=800):
    # app.logger.debug(get_this_function_name(sys._getframe().f_code, (path_to_image, width)))
    try:
        img = Image.open(path_to_image) #pillow
        new_width  = width
        new_height = int(new_width * img.height / img.width) #

        image_resized = img.resize((new_width, new_height), PIL.Image.BILINEAR)
        image_resized.save(path_to_image)

    except FileNotFoundError:
        app.logger.debug("Provided image path is not found:"+path_to_image)

def save_img_to_dir(f, folder) -> str:
    filename, ext = os.path.splitext(secure_filename(f.filename))
    uuid_rand = str(uuid.uuid4())
    filename = uuid_rand + ext
    filepath = os.path.join(folder, filename)
    try:
        f.save(filepath)
    except Exception as e:
        print("save_img_to_dir(): cannot save file | " + e)
        return str()
    else:
        return filepath

def debug_bot(*msg):
    print(*msg)

def delete_tweet(tweet_id:int):
    debug_bot("[DELETE] delete tweet id:", tweet_id)
    try:
        api.destroy_status(tweet_id)
    except:
        print("error with: "+str(tweet_id))

def sleep_bot(sec:int, more_info=""):
    debug_bot("[WAIT] Now I need a rest for " + str(sec) +" seconds "+more_info)
    time.sleep(sec)
