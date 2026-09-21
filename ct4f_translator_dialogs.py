import ct4f_config as config
import ct4f_exceptions as exceptions
import queue

_request_queue = queue.Queue()

LOGGER = print

# ===========================================
# Function: Set Logger
# Receives the shared logger from the main workflow
# If not invoked, logger will be the simple "print"
# ===========================================
def set_logger(logger):
    global LOGGER
    LOGGER = logger


# ===========================================
# Function: Get Request
#
# ===========================================
def get_request():

    return _request_queue.get_nowait()


# ===========================================
# Function: Put Request
#
# ===========================================
def put_request(request):

    _request_queue.put(request)


# ------------------------------------------------------------
# Function: Simple y/n prompt confirmation
# ------------------------------------------------------------
def confirm_yes_no(question="") -> bool:

    LOGGER(question)

    response_queue = queue.Queue()

    _request_queue.put({
        "type": config.PROMPT_TYPE_YESNO,
        "question": question,
        "response_queue": response_queue
    })

    answer = response_queue.get()

    if answer == config.CANCEL:
        raise exceptions.CancelledException()

    LOGGER(f"Answer: {answer}")

    return answer == config.YES


# ------------------------------------------------------------
# Function: Prompt Radio
# ------------------------------------------------------------
def prompt_radio(question, options):

    response_queue = queue.Queue()

    _request_queue.put({
        "type": config.PROMPT_TYPE_RADIO,
        "question": question,
        "options": options,
        "response_queue": response_queue
    })

    answer = response_queue.get()

    if answer == config.CANCEL:
        raise exceptions.CancelledException()

    return answer


# ------------------------------------------------------------
# Function: Confirm Unusual Lang File Name
# Lang files are conventionally named <language code>.json (e.g. en.json, pt-BR.json).
# Asks whether to continue anyway with a differently named file
# ------------------------------------------------------------
def confirm_unusual_lang_file_name() -> bool:

    question = \
        f"\n=== UNUSUAL FILE NAME FOR A LOCALIZATION FILE ===\n" \
        f"The selected file is named '{config.INPUT_FILE_NAME}', but Localization (lang) files " \
        f"are usually named <language code>.json (like en.json, or pt-BR.json).\n" \
        "Are you sure that this is a Localization file and not a Babele file?\n" \
        f"[{config.YES}] Yes, continue anyway.\n" \
        f"[{config.NO}] No, abort."

    return confirm_yes_no(question)


# ------------------------------------------------------------
# Function: Prompt confirmation for keeping batch after non-fatal errors
# ------------------------------------------------------------
def confirm_batch_nonfatal_errors():

    question = \
        f"\n=== DO YOU WANT TO KEEP THIS BATCH ANYWAY? ===\n" \
        f"({config.YES.upper()}/{config.YES.lower()}): Yes, keep it and export errors as Review Items for later.\n" \
        f"({config.NO.upper()}/{config.NO.lower()}) or (Enter): No, abort. I will restart the process myself to retry from this Batch."

    answer = confirm_yes_no(question)

    if answer == config.CANCEL:
        raise exceptions.CancelledException()

    return answer


