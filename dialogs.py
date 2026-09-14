import config
import os
import math
import shared_functions as fn
from pathlib import Path
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
# Function: Prompt for input file
# ------------------------------------------------------------
def prompt_for_input_file(subdir=None, subdirs_traversed=[]):

    if subdir is not None:

        config.INPUT_FOLDER_NAME = Path(config.INPUT_FOLDER_NAME) / subdir
        # print(fn.log(f"DEBUG - subdir: {subdir}"))
        # print(fn.log(f"DEBUG - descending to: {config.INPUT_FOLDER_NAME}"))

    folder_entries = []

    for item in os.scandir(config.INPUT_FOLDER_NAME):

        size = (
            int(os.path.getsize(item.path)) / 1024
            if item.is_file()
            else None)

        if size is not None:
            if size > 1000:
                size = f"{math.ceil(size / 1024)} mb"
            else:
                size = f"{math.ceil(size)} kb"

        folder_entries.append({
            "name": item.name,
            "item": item,
            "size": size})

    folder_entries = sorted(folder_entries, key=lambda item: item["name"])

    if len(folder_entries) > 0:

        print(fn.log_header(f"SELECT file to translate (root input folder: {config.INPUT_FOLDER_NAME})", color=config.MAGENTA))
        print(fn.log(f"Use parameter config.py->INPUT_FOLDER_NAME to switch to another source folder.",color=config.MAGENTA))

        for i, entry in enumerate(folder_entries, start=1):

            if entry["item"].is_dir():
                print(fn.log(f"{i}. [dir] {entry["name"]}"))
            else:
                print(fn.log(f"{i}. {entry["name"]} [{entry["size"]}]"))

        while config.MODULE_NAME is None or len(config.MODULE_NAME) == 0:

            try:

                item_selection = int(
                    input("\nSelect file or directory ?> ")
                )

                if 1 <= item_selection <= len(folder_entries):

                    selection = folder_entries[item_selection - 1]

                    if (selection["item"].is_dir()):

                        subdirs_traversed.append(selection["name"])
                        prompt_for_input_file(subdir=selection["name"], subdirs_traversed=subdirs_traversed)
                        break

                    else:

                        config.INPUT_FILE_NAME = selection["name"]
                        config.INPUT_FILE = Path(config.INPUT_FOLDER_NAME) / config.INPUT_FILE_NAME
                        print(fn.log(f"DEBUG - INPUT_FILE: {config.INPUT_FILE}"))

                        config.INPUT_TYPE = prompt_for_input_type()

                        if config.INPUT_TYPE == config.INPUT_TYPE_BABELE:

                            config.MODULE_NAME = suggest_module_name()

                            if config.MODULE_NAME is None or len(config.MODULE_NAME) == 0:
                                print(fn.log(
                                    f"Warning: Can't derive module name from input filename \"{config.INPUT_FILE_NAME}\"\n"
                                    f"The filename does not to follow pattern <module-name>.<compendium-name>.json\n"
                                    f"Example: dnd-players-handbook.actors.json ", color=config.YELLOW)
                                )

                                config.MODULE_NAME = "unknown-module"


                                module_name_confirmed = confirm_yes_no(
                                    f"{config.MAGENTA}Do you want to use {config.BOLD}\"{config.MODULE_NAME}\"{config.RESET}{config.MAGENTA} as module/sub-directory name for the output?{config.RESET}\n"
                                    f"{config.YELLOW}Answering 'No' will abort the process.{config.RESET}")

                                if not module_name_confirmed:
                                    raise Exception(config.ABORTED_BY_USER_ERROR)

                        else:

                            prompt_for_module_name(subdirs_traversed)
                            print(f"DEBUG: MODULE_NAME selected: {config.MODULE_NAME}")

                else:

                    raise ValueError()

            except ValueError:

                print(fn.log(f"Invalid selection.", color=config.RED))

    else:

        raise ValueError(f"Input folder {config.INPUT_FOLDER_NAME} is empty.")


# ------------------------------------------------------------
# Function: Suggest Module Name
# Try to extract module name from input filename
# If not successful, return config.UNKNOWN_MODULE_NAME
# ------------------------------------------------------------
def suggest_module_name():

    suggested = config.UNKNOWN_MODULE_NAME

    if config.INPUT_FILE_NAME.count(".") > 1:
        suggested = config.INPUT_FILE_NAME[0: config.INPUT_FILE_NAME.find('.')]

    return suggested


# ------------------------------------------------------------
# Function: Prompt for Input Type
# ------------------------------------------------------------
def prompt_for_input_type() -> str | None:

    question = "Which type of file is this?"
    LOGGER(fn.log(question, color=config.MAGENTA))

    options = [
        config.INPUT_TYPE_BABELE,
        config.INPUT_TYPE_LOCALIZATION
    ]
    LOGGER(fn.log("\n".join(options), color=config.MAGENTA))

    input_type:str | None = prompt_radio(
        question,
        options
    )

    LOGGER(fn.log(f"Answer: {input_type}"))

    return input_type


# ------------------------------------------------------------
# Function: Prompt for module name
# ------------------------------------------------------------
def prompt_for_module_name(options):

    module_name = None

    print(f"\n{config.MAGENTA}Which one of these folder names represents the module name?{config.RESET}")

    for i, option in enumerate(options, start=1):

        print(fn.log(f"{i}. {option}"))

    while module_name is None:

        try:

            selection = int(
                input(f"?>{config.RESET} ")
            )

            if 1 <= selection <= len(options):

                module_name = options[selection - 1]

            else:

                raise ValueError()

        except ValueError:

            print(fn.log(f"Invalid selection.", color=config.RED))

    config.MODULE_NAME = module_name

