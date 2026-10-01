import lib.cfbt_config as config
import lib.cfbt_exceptions as exceptions
import lib.cfbt_i18n as i18n
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
# <key> is a language file key. The log gets the English text, the dialog the localized one.
# {yes}, {no} and {show_log} name the dialog's buttons in the respective language.
# A parameter may also be a function: it is called with the translation function to use
# (English for the log, localized for the dialog), for parameters that contain texts of their own
# ------------------------------------------------------------
def confirm_yes_no(key, **params) -> bool:

    def resolve(translate):
        return {name: value(translate) if callable(value) else value for name, value in params.items()}

    LOGGER(i18n.t_en(
        key, yes=i18n.t_en("dialog.yes"), no=i18n.t_en("dialog.no"), show_log=i18n.t_en("dialog.show_log"),
        **resolve(i18n.t_en)
    ))

    response_queue = queue.Queue()

    _request_queue.put({
        "type": config.PROMPT_TYPE_YESNO,
        "question": i18n.t(
            key, yes=i18n.t("dialog.yes"), no=i18n.t("dialog.no"), show_log=i18n.t("dialog.show_log"),
            **resolve(i18n.t)
        ),
        "response_queue": response_queue
    })

    answer = response_queue.get()

    if answer == config.CANCEL:
        raise exceptions.CancelledException()

    LOGGER(f"Answer: {answer}")

    return answer == config.YES


# ------------------------------------------------------------
# Function: Confirm Unusual Lang File Name
# Lang files are conventionally named <language code>.json (e.g. en.json, pt-BR.json).
# Asks whether to continue anyway with a differently named file
# ------------------------------------------------------------
def confirm_unusual_lang_file_name() -> bool:

    return confirm_yes_no("prompt.unusual_lang_file_name", file=config.INPUT_FILE_NAME)


# ------------------------------------------------------------
# Function: Confirm Discard Progress
# Asked if settings have changed since the last run of this input file.
# Returns True if the existing progress may be discarded
# ------------------------------------------------------------
def confirm_discard_progress(differences) -> bool:

    def changes(translate):
        return "\n".join(
            translate("prompt.input_file_changed") if name == "INPUT_FILE_HASH"
            else f"- {name}: {change['stored']}  =>  {change['current']}"
            for name, change in differences.items()
        )

    return confirm_yes_no("prompt.discard_progress", changes=changes)


# ------------------------------------------------------------
# Function: Prompt confirmation for keeping batch after non-fatal errors
# ------------------------------------------------------------
def confirm_batch_nonfatal_errors(batch_id, batch_cnt, error_count) -> bool:

    answer = confirm_yes_no(
        "prompt.batch_nonfatal_errors",
        batch=batch_id + 1,
        batches=batch_cnt,
        count=error_count
    )

    if answer == config.CANCEL:
        raise exceptions.CancelledException()

    return answer


# ------------------------------------------------------------
# Function: Confirm Overwrite Terminology
# Asked when a new run finds a terminology file that is not part of any progress
# ------------------------------------------------------------
def confirm_overwrite_terminology(file_path) -> bool:

    return confirm_yes_no("prompt.overwrite_terminology", file=file_path)
