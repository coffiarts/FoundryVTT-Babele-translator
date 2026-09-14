import config
import shared_functions as fn
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


# ------------------------------------------------------------
# Function: Prompt for Terminology Rebuild
# ------------------------------------------------------------
def prompt_for_terminology_rebuild() -> bool:

    LOGGER(f"TERMINOLOGY_FILE: {config.TERMINOLOGY_FILE}")

    if config.TERMINOLOGY_FILE.exists():

        question =\
            f"\n{config.MAGENTA}"\
            f"=== REBUILD TERMINOLOGY? ===\n" \
            f"Existing Terminology for this input file already exists at: {config.TERMINOLOGY_FILE}\n" \
            "Do you want to rebuild it online before translating?\n" \
            f"({config.YES.upper()}/{config.YES.lower()}): Rebuild terminology from scratch \n" \
            f"({config.NO.upper()}/{config.NO.lower()}) or (Enter): No, reuse existing Terminology (or continue, in case of aborts)\n" \
            f"?>{config.RESET} "

        return confirm_yes_no(question)

    else:

        return True


# ------------------------------------------------------------
# Function: Simple y/n prompt confirmation
# ------------------------------------------------------------
def confirm_yes_no(question="") -> bool:

    LOGGER(question)

    response_queue = queue.Queue()

    _request_queue.put({
        "type": "text",
        "question": question,
        "response_queue": response_queue
    })

    answer = response_queue.get()
    answer_is_yes = answer == config.YES

    LOGGER(f"{fn.log(f"Answer: {config.YES if answer_is_yes else config.NO}")}")

    return answer_is_yes


# ------------------------------------------------------------
# Function: Prompt Radio
# ------------------------------------------------------------
def prompt_radio(question, options):

    response_queue = queue.Queue()

    _request_queue.put({
        "type": "radio",
        "question": question,
        "options": options,
        "response_queue": response_queue
    })

    return response_queue.get()


# ------------------------------------------------------------
# Function: Prompt confirmation for force new run
# ------------------------------------------------------------
def confirm_force_new_run():

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
        f"({config.YES.upper()}/{config.YES.lower()}): Discard and replace previous results.\n" \
        f"({config.NO.upper()}/{config.NO.lower()}) or (Enter)): No, just rerun Post-Processing (this will also skip Terminology rebuild!)\n" \
        f"?>{config.RESET} "

    return confirm_yes_no(question)


# ------------------------------------------------------------
# Function: Prompt confirmation for keeping batch after non-fatal errors
# ------------------------------------------------------------
def confirm_batch_nonfatal_errors():

    answer = input(
        f"\n{config.YELLOW}=== DO YOU WANT TO KEEP THIS BATCH ANYWAY? ===\n{config.RESET}"
        f"({config.GREEN}{config.YES.upper()}/{config.YES.lower()}): Yes, keep it and export errors as Review Items for later.{config.RESET}\n"
        f"({config.RED}{config.NO.upper()}/{config.NO.lower()}) or (Enter): No, abort. I will restart the process myself to retry from this Batch.{config.RESET}\n"
        f"{config.YELLOW}?>{config.RESET} "
    ).strip().lower()

    normalized_answer = True if answer == config.YES.lower() else False

    return normalized_answer


# ------------------------------------------------------------
# Function: Suggest Module Name
# Try to extract module name from input filename
# If not successful, return config.UNKNOWN_MODULE_NAME
# ------------------------------------------------------------
def suggest_module_name(input_file, input_type):
    suggested = config.UNKNOWN_MODULE_NAME

    if input_type == config.INPUT_TYPE_BABELE:
        if input_file.name.count(".") > 1:
            suggested = input_file.name[0: input_file.name.find('.')]

        return suggested

    elif input_type == config.INPUT_TYPE_LOCALIZATION:
        ignored_folder_names = {
            "lang",
            "language",
            "languages"
        }

        current = input_file.parent

        while True:

            folder_name = current.name.lower()

            if folder_name == config.INPUT_FOLDER_NAME.lower():
                return config.UNKNOWN_MODULE_NAME

            if folder_name not in {
                "lang",
                "language",
                "languages"
            }:
                return current.name

            current = current.parent

    return suggested

