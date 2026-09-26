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
# Function: Confirm Discard Progress
# Asked if settings have changed since the last run of this input file.
# Returns True if the existing progress may be discarded
# ------------------------------------------------------------
def confirm_discard_progress(differences) -> bool:

    changed = "\n".join(
        f"- {name}: {change['stored']}  =>  {change['current']}"
        for name, change in differences.items()
    )

    question = \
        f"\n=== SETTINGS CHANGED SINCE THE LAST RUN ===\n" \
        f"These settings differ from those of the existing progress for this input file:\n" \
        f"{changed}\n" \
        "They cannot be applied to a process that is already under way.\n" \
        f"[{config.YES}] Discard the existing progress and start fresh with the current settings.\n" \
        f"[{config.NO}] No, keep the progress (restore the previous settings yourself, then prepare again)."

    return confirm_yes_no(question)


# ------------------------------------------------------------
# Function: Prompt confirmation for keeping batch after non-fatal errors
# ------------------------------------------------------------
def confirm_batch_nonfatal_errors(batch_id, batch_cnt, error_count) -> bool:

    question = \
        f"Batch {batch_id + 1}/{batch_cnt} contains {error_count} placeholder translation error(s).\n" \
        "Click 'Show Log' to investigate the details.\n\n" \
        "Do you want to keep this batch anyway (exporting the errors as Review Items for later), " \
        "or discard it so it gets retried on the next run?"

    answer = confirm_yes_no(question)

    if answer == config.CANCEL:
        raise exceptions.CancelledException()

    return answer


# ------------------------------------------------------------
# Function: Confirm Overwrite Terminology
# Asked when a new run finds a terminology file that is not part of any progress
# ------------------------------------------------------------
def confirm_overwrite_terminology(file_path) -> bool:

    question = \
        f"\n=== EXISTING TERMINOLOGY FILE WILL BE OVERWRITTEN ===\n" \
        f"There is already a terminology file for this input:\n{file_path}\n" \
        "It will be replaced by a freshly built terminology.\n" \
        "Any changes you might have made to it manually will be lost!\n" \
        "If you consider it final, save it in another location before proceeding.\n" \
        f"[{config.YES}] Yes, overwrite it.\n" \
        f"[{config.NO}] No, abort (so you can move the file first)."

    return confirm_yes_no(question)
