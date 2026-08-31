from config import *
import json
from openai import OpenAI
import re


# ------------------------------------------------------------
# Function: Load and return data (as list) from JSON input_file (path)
# ------------------------------------------------------------
def load_json_input(input_file):

    with input_file.open(
            "r",
            encoding="utf-8"
    ) as file:

        data = json.load(file)

    chars_cnt = to_prettified_json(data)

    # print(f"Loaded {len(data)} top-level elements from {input_file} with {len(chars_cnt)} chars")
    return data


# ----------------------------------------------------------------------------------
# Save data (as list) to JSON output_file (path)
# ----------------------------------------------------------------------------------
def save_json_output(data, output_file):

    json_string = to_prettified_json(data)

    with open(
            output_file,
            "w",
            encoding="utf-8"
    ) as file:

        file.write(json_string)

    print(f"File written to: {output_file} with {len(json_string)} chars")


# ------------------------------------------------------------
# Get JSON element
# ------------------------------------------------------------
def get_json_element(
        json_object,
        path):

    current = json_object

    for element in path:
        current = current[element]

    return current


# ------------------------------------------------------------
# Function: Set JSON Element
# ------------------------------------------------------------
def set_json_element(
        target_json_object,
        path,
        new_value):

    current = target_json_object

    for element in path[:-1]:
        current = current[element]

    current[path[-1]] = new_value


# ----------------------------------------------------------------------------------
# Convert data (list, dict) to formatted JSON string
# Recommended to use instead of vanilla json.dumps
# It applies useful cosmetics like condensing numeric elements in lists to single lines
# ----------------------------------------------------------------------------------
def to_prettified_json(data):
    json_string = (json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    ))

    json_string = re.sub(r'\n +([0-9-\]])', r' \1', json_string)
    return json_string


# ----------------------------------------------------------------------------------
# Convert a dict or list to multiline lines of pattern:
# "<key/index>: <value>\n"
# Typically used for logging enumerables to console
# ----------------------------------------------------------------------------------
def to_multiline_text(dictionary):

    text = ""

    if type(dictionary) == dict:
        for key, value in dictionary.items():
            text += f"{key}: {value}\n"

    if type(dictionary) == list:
        for index, value in enumerate(dictionary):
            text += f"{index}: {value}\n"

    return text



# ------------------------------------------------------------
# Function: Init Progress Info
# Used by Run Mode = NEW_RUN
# Returns a freshly created Progress Info
# ------------------------------------------------------------
def init_progress_info():

    print("Creating new Progress Info ...")

    current_config = get_resume_relevant_config()

    progress_info = {
        "config": current_config,
        "batches": []
    }

    save_json_output(data=progress_info, output_file=PROGRESS_INFO_FILE)

    print(f"... Done. New Progress Info is now tracked by file {PROGRESS_INFO_FILE}")

    return progress_info


# ------------------------------------------------------------
# Function: Validate Progress
# Used by Run Mode = RESUME
# Returns (if valid):
# - the existing Progress Info
# - the Batch to restart from (pickup_batch)
# (if invalid): an Error is thrown.
# ------------------------------------------------------------
def validate_progress_info():

    print("Validating existing Progress Info ...")

    progress_info = load_json_input(PROGRESS_INFO_FILE)

    # Check for proper state changes:
    completed_phase = True

    pickup_batch = None

    for batch in progress_info["batches"]:

        if completed_phase:

            if batch["status"] != COMPLETED:
                completed_phase = False

        else:

            if pickup_batch is None:
                pickup_batch = batch

            if batch["status"] == COMPLETED:
                raise ValueError(
                    "Corrupt ProgressInfo: "
                    f"COMPLETED batch id: (id={batch["id"]}) found after non-COMPLETED batch."
                )

    if completed_phase:

        raise ValueError(
            "Nothing to resume: "
            f"Picking up this process is not necessary. All {len(progress_info["batches"])} Batches already marked as {COMPLETED}."
        )

    else:

        print("... valid.")
        return progress_info, pickup_batch


#------------------------------------------------------------
# Function: Build and return Batches
# Traverse all Translatables (with placeholders) and bundle them into Batches,
# keeping their total text length within preconfigured MAX_BATCH_SIZE
# ------------------------------------------------------------
def build_batches(translatables_with_placeholders):

    batches = []

    def create_empty_batch():
        return {
            "id": len(batches),
            "translatable_ids": [],
            "char_count": 0,
            "status": UNPROCESSED
        }

    current_batch = create_empty_batch()

    error = None

    for translatable in translatables_with_placeholders:

        text_size = len(translatable["original"])

        # No Translatable must exceed the Batch size limit by itself, this requires an abort.
        if text_size > MAX_BATCH_SIZE:
            error = (
                f"Translatable {translatable['id']} " +
                f"contains {text_size} chars and exceeds " +
                f"MAX_BATCH_SIZE={MAX_BATCH_SIZE}" +
                f"\nProposed solution: Increase MAX_BATCH_SIZE in config.py and resume process."
            )

            current_batch["status"] = FAILED
            current_batch["error"] = error
            break

        if current_batch["char_count"] + text_size > MAX_BATCH_SIZE:
            # Batch is full: Close and send it to the list
            batches.append(current_batch)
            current_batch = create_empty_batch()

        current_batch["translatable_ids"].append(translatable["id"])
        current_batch["char_count"] += text_size

    # After loop is complete, don't forget to close and send off the last open batch
    batches.append(current_batch)

    if error is not None:

        raise ValueError({
            "error": error,
            "batches": batches
        })

    else:

        print(f"Built {len(batches)} Batches from {len(translatables_with_placeholders)} Translatables")

        return batches


# ------------------------------------------------------------
# Function: Load and return Batches from the
# preconfigured Batches JSON file (BATCHES_FILE)
# Optional: Filter the result by passing a set if batch_ids like {4} or {1, 5, 13}
# ------------------------------------------------------------
def load_batches(batch_ids = None):

    batches = load_json_input(BATCHES_FILE)

    if batch_ids is None:
        return batches

    else:
        filtered_batches = []

        for batch in batches:

            if batch["batch_id"] in batch_ids:
                filtered_batches.append(batch)

        return filtered_batches


# ------------------------------------------------------------
# Function: Load and return Translatables
# from the preconfigured Translatables JSON file (TRANSLATABLES_FILE)
# Optional:
# - use with_placeholders = True to return Translatables with Placeholders instead if original Translatables
# - Filter the result by passing one or both of
#   - a set if batch_ids like {4} or {1, 5, 13}
#   - a set if translatable_ids like 4} or {1, 5, 13}
# ------------------------------------------------------------
def load_translatables(
        batch_ids = None,
        translatable_ids = None,
        with_placeholders = False):

    source_file = (
        TRANSLATABLES_FILE
        if not with_placeholders
        else TRANSLATABLES_WITH_PLACEHOLDERS_FILE
    )

    translatables = load_json_input(source_file)

    if batch_ids is None and translatable_ids is None:
        return translatables

    else:
        batch_filtered_translatables = []

        if batch_ids is None:
            batch_filtered_translatables = translatables

        else:
            for translatable in translatables:

                if translatable["batch_id"] in batch_ids:
                    batch_filtered_translatables.append(translatable)

        id_filtered_translatables = []

        if translatable_ids is None:
            id_filtered_translatables = batch_filtered_translatables

        else:
            for translatable in batch_filtered_translatables:

                if translatable["id"] in translatable_ids:
                    id_filtered_translatables.append(translatable)

        return id_filtered_translatables


# ------------------------------------------------------------
# Function: Load fist Translatable for Batch
# ------------------------------------------------------------
def load_first_translatable_for_batch(batch):
    first_translatable_id = (
        batch["translatable_ids"][0]
    )

    first_translatable = load_translatables(
        translatable_ids={first_translatable_id},
        with_placeholders=True
    )[0]

    return first_translatable


# ------------------------------------------------------------
# Function: Load and return Placeholders
# from the preconfigured Placeholders JSON file (PLACEHOLDERS_FILE)
# ------------------------------------------------------------
def load_placeholders():

    return load_json_input(PLACEHOLDERS_FILE)


# --------------------------------------------------------------
# Function: Recursively extract Translatables from Babele input
# --------------------------------------------------------------
def extract_translatables_from_babele(input, translatables, current_path):

    if isinstance(input, dict):

        for key, item in input.items():

            if (
                    key in TRANSLATABLE_FIELDS
                    and isinstance(item, str)
            ):

                translatables.append({
                    "id": len(translatables),
                    "path": current_path + [key],
                    "original": item
                })

            elif isinstance(item, (dict, list)):

                extract_translatables_from_babele(
                    item,
                    translatables,
                    current_path+ [key]
                )

    elif isinstance(input, list):

        for index, item in enumerate(input):

            extract_translatables_from_babele(
                item,
                translatables,
                current_path + [index]
            )


# ------------------------------------------------------------
# Function: Protect with Placeholders
# - Scans all passed text for occurrences of Foundry-specific, non-translatable syntax
# - Replaces them with numbered placeholders of pattern <<<FOUNDRY_nnnnnn>>>
# - Returns the result (texts_with_placeholders), plus the list of generated placeholders
# ------------------------------------------------------------
def protect_with_placeholders(translatables):

    placeholders = {}
    translatables_with_placeholders = []

    def create_and_register_placeholder(match):

        placeholder_name = (
            f"<<<FOUNDRY_{len(placeholders):06d}>>>"
        )

        placeholders[
            placeholder_name
        ] = match.group(0)

        return placeholder_name

    for translatable in translatables:

        # copy orignal translatable
        translatable_to_protect = translatable.copy()

        for pattern in FOUNDRY_SYNTAX_PATTERNS:

            translatable_to_protect["original"] = re.sub(
                pattern,
                create_and_register_placeholder,
                translatable_to_protect["original"]
            )

        translatables_with_placeholders.append(translatable_to_protect)

    print(f"Extracted {len(placeholders)} new protective placeholders from {len(translatables)} translatables")

    return translatables_with_placeholders, placeholders


# ------------------------------------------------------------
# Function: Find Patterns
# Utility for matching against multiple patterns at one.
# Runs a RegEx check of <text> against all elements in <patterns>
# Returns all matches, plus the matching extract from text withing +/- <leading_trailing_chars> chars boundary
# ------------------------------------------------------------
def find_patterns(text, patterns, leading_trailing_chars = 100):

    matches = {}

    for pattern in patterns:

        match = re.search(pattern, text)

        if match:

            start = max(0, match.pos - leading_trailing_chars)
            end = min(len(text), match.pos + len(match.group(0)))

            fragment = text[start : end]

            matches[pattern] = fragment

    return matches


# ------------------------------------------------------------
# Function: Initialize API client
# ------------------------------------------------------------
def init_api_client():

    api_key = APIKEY_FILE.read_text(
        encoding="utf-8"
    ).strip()
    client = OpenAI(
        api_key=api_key
    )
    return client


# ------------------------------------------------------------
# Function: Apply translations (all at once)
# ------------------------------------------------------------
def apply_translations(
        babele_json,
        translatables,
        translations):

    for id, translation in translations.items():
        set_json_element(babele_json, translatables[id]["path"], translation)

    # TODO - apply any "on-top"" translations (like translator's watermark etc.)


# ------------------------------------------------------------
# Function: Get Resume-relevant config
# Delivers the current snapshot of all config parameters that
# need to remain stable between incremental process runs.
# The function's output serves for checking whether a Resume is allowed to start.
# ------------------------------------------------------------
def get_resume_relevant_config():

    return {
        "max_batch_size": MAX_BATCH_SIZE,
        "translatable_fields": sorted(TRANSLATABLE_FIELDS),
        "foundry_syntax_patterns": sorted(FOUNDRY_SYNTAX_PATTERNS)
    }


# ------------------------------------------------------------
# Function: Determine run mode
# Delivers the current snapshot of all config parameters that
# need to remain stable between incremental process runs.
# The function's output serves for checking whether a Resume is allowed to start.
# ------------------------------------------------------------
def determine_run_mode():

    if not PROGRESS_INFO_FILE.exists():
        return NEW_RUN

    progress_info = load_json_input(
        PROGRESS_INFO_FILE
    )

    current_config = get_resume_relevant_config()

    if progress_info["config"] != current_config:

        raise ValueError(
            f"CONFIGURATION MISMATCH\n"
            f"======================\n"
            f"At least one essential parameter in config.py "
            f"has changed since the last attempt to run this process.\n"
            f"The following parameters are not allowed to change when resuming a process for the same input file.\n"
            f"(File to be processed: {INPUT_FILE})\n\n"
            
            f"Current configuration:\n"
            f"----------------------\n"
            f"{to_multiline_text(current_config)}\n\n"
            
            f"Configuration values expected from last attempt:\n"
            f"------------------------------------------------\n"
            f"{to_multiline_text(progress_info['config'])}\n\n"
            
            f"Please either adjust config.py accordingly and retry, "
            f"or delete file {PROGRESS_INFO_FILE} to start a fresh process (discarding all intermediary results)."
        )

    return RESUME


# ------------------------------------------------------------
# Function: Cleanup progress files
# ------------------------------------------------------------
def cleanup_progress_files():

    print("Cleaning up progress files from previous runs (if any) ...")

    for file in [
        PROGRESS_INFO_FILE,
        TRANSLATABLES_FILE,
        TRANSLATABLES_WITH_PLACEHOLDERS_FILE,
        PLACEHOLDERS_FILE,
        BATCHES_FILE,
        TRANSLATIONS_WITH_PLACEHOLDERS_FILE,
        TRANSLATIONS_FINAL_FILE,
        POST_REVIEW_ITEMS_FILE
    ]:

        if file.exists():
            file.unlink()

            print(f"... Deleted: {file}")

    print("Done.")