import ct4f_config as config
import ct4f_core_functions as fn
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

    LOGGER(f"{fn.log(f"Answer: {answer}")}")

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
# Function: Prompt for Terminology Rebuild
# ------------------------------------------------------------
def prompt_for_terminology_rebuild() -> bool:

    LOGGER(f"TERMINOLOGY_FILE: {config.TERMINOLOGY_FILE}")

    if config.TERMINOLOGY_FILE.exists():

        question = \
            f"\n{config.MAGENTA}" \
            f"=== REBUILD TERMINOLOGY? ===\n" \
            f"Found existing Terminology for this input file: {config.TERMINOLOGY_FILE}\n" \
            "Do you want to rebuild it online before translating?\n" \
            f"[{config.YES}] Rebuild terminology from scratch (replace) \n" \
            f"[{config.NO}] No, reuse existing Terminology (or continue, in case of aborts)"

        return confirm_yes_no(question)

    else:

        return True


# ------------------------------------------------------------
# Function: Confirm Replacement of Results
# ------------------------------------------------------------
def confirm_replace_results():

    text_if_output_still_exists = (
        f"A translated output file can still be found at: {config.OUTPUT_FILE}\n"
        if config.OUTPUT_FILE.exists()
        else ""
    )

    question =\
        f"\n{config.MAGENTA}=== REPLACE PREVIOUS RESULTS? ===\n" \
        f"The last run for this file is marked as fully {config.COMPLETED}.\n" \
        f"{text_if_output_still_exists}" \
        "Do you want to discard the results and start a complete, FRESH translation?\n" \
        "Or do you want to keep them and just rerun Post-Processing steps (integrity checks and rebuilding of the output file)?\n" \
        f"[{config.YES}] Discard and replace previous results.\n" \
        f"[{config.NO}] No, just rerun Post-Processing (this will also skip Terminology rebuild!)"

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


