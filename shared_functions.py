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
# Convert a flat dict or list of type <key/index>: <text> to multiline lines of pattern:
# "<key/index>: <text>\n"
# Typically used for logging enumerables to console
# value_char_limit formats <text> as "<first n chars of text> ..."
# ----------------------------------------------------------------------------------
def to_multiline_text(input, value_char_limit=None, row_limit=None, text=""):

    text = ""
    counter = 0

    if type(input) == dict:
        for key, value in input.items():

            label = key

            if row_limit is not None and ++counter > row_limit:
                break

            print_value = value if value_char_limit is None else f"{value[:value_char_limit]} ..."
            text += f"\n{label}: {print_value}"

    if type(input) == list:
        for index, value in enumerate(input):

            label = index

            if row_limit is not None and ++counter > row_limit:
                break

            print_value = value if value_char_limit is None else f"{value[:value_char_limit]} ..."
            text += f"\n{label}: {print_value}"

    if row_limit is not None:
        text += "...\n"

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

    resume_batch = None

    for batch in progress_info["batches"]:

        if completed_phase:

            if batch["status"] != COMPLETED:
                completed_phase = False

                if resume_batch is None:
                    resume_batch = batch

        else:

            if batch["status"]  == COMPLETED:
                raise ValueError(
                    "Corrupt ProgressInfo: "
                    f"COMPLETED batch id: (id={batch["id"]}) found after non-COMPLETED batch."
                )

    if completed_phase:

        raise ValueError(
            "Nothing to resume: "
            f"Picking up this process is not necessary. All {len(progress_info["batches"])} Batches already marked as {COMPLETED}.\n"
            f"To run a fresh translation, please delete contents of folder '{PROGRESS_INFO_FOLDER_NAME}'."
        )

    else:

        print("... valid.")
        return progress_info, resume_batch


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
            # set_batch_status(current_batch, FAILED, )
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
        translatable_ids = None,
        with_placeholders = False):

    source_file = (
        TRANSLATABLES_FILE
        if not with_placeholders
        else TRANSLATABLES_WITH_PLACEHOLDERS_FILE
    )

    translatables = load_json_input(source_file)

    if translatable_ids is None:
        return translatables

    else:
        filtered_translatables = []

        for translatable in translatables:

            if translatable["id"] in translatable_ids:
                filtered_translatables.append(translatable)

    return filtered_translatables


# ------------------------------------------------------------
# Function: Load Translatables for Batch
# Optional parameters:
# - with_placeholders (True/False): Return placeholders-protected versions (default) or those without placeholders
# - limit: Limit list returned to the leading n elements
# ------------------------------------------------------------
def load_translatables_for_batch(
        batch,
        with_placeholders = True,
        limit = None):

    translatables = []

    if limit is not None and type(limit) == int and limit > 0:
        translatable_ids = (
            batch["translatable_ids"][:limit]
        )

        # Load limited list
        translatables = load_translatables(translatable_ids, with_placeholders)

    else:

        # load'em all (for this batch)
        translatables = load_translatables(
            batch["translatable_ids"],
            with_placeholders=with_placeholders)

    return translatables


# ------------------------------------------------------------
# Function: Load Translations for Batch
# ------------------------------------------------------------
def load_translations_for_batch(
        batch,
        with_placeholders = True,
        limit = None):

    file = (
        TRANSLATIONS_FINAL_FILE
        if not with_placeholders
        else TRANSLATIONS_WITH_PLACEHOLDERS_FILE
    )

    translations = load_json_input(file)[:limit]

    return translations

# ------------------------------------------------------------
# Function: Load Translations Final
# These require a dedicated load functions to force dict keys
# to numeric format
# ------------------------------------------------------------
def load_translations_final():

    translations = load_json_input(
        TRANSLATIONS_FINAL_FILE
    )

    return {
        int(id): translation
        for id, translation in translations.items()
    }

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
# - Replaces them with numbered placeholders of pattern PLACEHOLDER_PATTERN
# - Returns the result (texts_with_placeholders), plus the list of generated placeholders
# ------------------------------------------------------------
def protect_with_placeholders(translatables):

    placeholders = {}
    translatables_with_placeholders = []

    def create_and_register_placeholder(match):

        placeholder_number_digit_length = re.search(
            r'\\d{(\d)}',
            PLACEHOLDER_PATTERN
        )[1]

        placeholder_name = re.sub(
            r'\\d{\d}',
            f"{str(len(placeholders)).zfill(int(placeholder_number_digit_length))}",
            PLACEHOLDER_PATTERN
        ) # yields something like <<<FOUNDRY_000003>>>

        placeholders[
            placeholder_name
        ] = match.group(0)

        return placeholder_name

    for translatable in translatables:

        # copy original translatable
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
        translations_final):

    for translatable in translatables:
        set_json_element(babele_json, translatable["path"], translations_final[translatable["id"]])

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


# ------------------------------------------------------------
# Function: Total Char Count
# Calculate the sum of all chars in text list <list>
# by extracting each element's text node identified <node_name>
# ------------------------------------------------------------
def total_char_count(list, node_name) -> int:
    return len("\n".join(
        item[node_name]
        for item in list
    ))


# ------------------------------------------------------------
# Function: Post-Mortem Dump
# Created after unexpected error during the LLM API Call
# ------------------------------------------------------------
def post_mortem_dump(
        title,
        details,
        response_metadata=None,
        raw_response=None,
        batch_payload=None,
        translations_with_placeholders=None,
        integrity_errors=None
):

    with open(
            ERRORS_FILE,
            "w",
            encoding="utf-8"
    ) as file:

        file.write(
            "====================================================\n"
        )

        file.write(
            f"{title}\n"
        )

        file.write(
            "====================================================\n\n"
        )

        file.write(
            f"{details}\n\n"
        )
        print(
            f"Response metadata: {response_metadata}"
        )

        if response_metadata is not None:


            file.write(
                "====================================================\n"
                "RESPONSE METADATA\n"
                "====================================================\n\n"
            )

            file.write(
                json.dumps(
                    response_metadata,
                    indent=2,
                    ensure_ascii=False
                )
            )

            file.write("\n\n")

        if raw_response is not None:


            file.write(
                "====================================================\n"
                "RAW RESPONSE METADATA\n"
                "====================================================\n\n"
            )

            file.write(
                json.dumps(
                    raw_response,
                    indent=2,
                    ensure_ascii=False
                )
            )

            file.write("\n\n")

        if batch_payload is not None:

            file.write(
                "====================================================\n"
                "BATCH PAYLOAD\n"
                "====================================================\n\n"
            )

            file.write(
                json.dumps(
                    batch_payload,
                    indent=2,
                    ensure_ascii=False
                )
            )

            file.write("\n\n")

        if translations_with_placeholders is not None:

            file.write(
                "====================================================\n"
                "COMPLETED TRANSLATIONS (still with Placeholders)\n"
                "====================================================\n\n"
            )

            file.write(
                json.dumps(
                    translations_with_placeholders,
                    indent=2,
                    ensure_ascii=False
                )
            )

            file.write("\n\n")

        if integrity_errors is not None:

            file.write(
                "====================================================\n"
                "COLLECTED INTEGRITY ERRORS\n"
                "====================================================\n\n"
            )

            file.write(
                json.dumps(
                    integrity_errors,
                    indent=2,
                    ensure_ascii=False
                )
            )

            file.write("\n\n")

    print(
        f"\n❌{RED}POST-MORTEM DUMP WRITTEN TO:{COLOR_RESET}"
    )

    print(
        f"{RED}{ERRORS_FILE}{COLOR_RESET}"
    )

# ------------------------------------------------------------
# Function: Save Batch
# Writes the current state of <batch> to bith the Batches and ProgressInfo file,
# thus keeping both related files in sync.
# The full list data <all_batches> and <all_progress_info> nned to be passed
# along with the batch to ensure consistency, because the updates requires
# a full rewrite of both files
# ------------------------------------------------------------
def save_batch(updated_batch, all_batches, all_progress_info):

    all_batches[updated_batch["id"]] = updated_batch

    for entry in all_progress_info["batches"]:
        if entry["id"] == updated_batch["id"]:
            for key in entry:
                entry[key] = updated_batch[key]

    save_json_output(all_batches, BATCHES_FILE)
    save_json_output(all_progress_info, PROGRESS_INFO_FILE)


# ------------------------------------------------------------
# Function: Verify placeholder integrity
# ------------------------------------------------------------
def create_placeholder_review_items(
        translatables_with_placeholders,
        translations_with_placeholders):

    review_items = []

    translations_by_id = {
        translation["id"]: translation
        for translation in translations_with_placeholders
    }

    for translatable in translatables_with_placeholders:

        new_review_items = verify_placeholder_integrity(
                len(review_items),
                translatable["original"],
                translations_by_id[
                    translatable["id"]
                ]["translation"]
        )

        review_items.extend(new_review_items)

    return review_items


def verify_placeholder_integrity(
        next_id,
        original_text_with_placeholders,
        translated_text,
        trailing_chars=100):

    new_review_items = []

    # Collect all expected placeholders from original
    expected_placeholders = re.findall(
            PLACEHOLDER_PATTERN,
            original_text_with_placeholders
    )

    # Check for each expected placeholder whether it is present in the translation
    for placeholder in expected_placeholders:

        count = translated_text.count(
            placeholder
        )

        if count != 1:

            position = (
                original_text_with_placeholders.find(
                    placeholder
                )
            )

            start = max(
                0,
                position - 200
            )

            end = min(
                len(original_text_with_placeholders),
                position + len(placeholder) + trailing_chars
            )


            new_review_items.append( {
                "id": next_id,
                "type": "placeholder_translation_error",
                "details": {
                    "placeholder": placeholder,
                    "count": count,
                    "original_context":
                        "... " + original_text_with_placeholders[start:end] + " ...",
                    "translated_context":
                        "... " + translated_text[max(0, position - trailing_chars):
                                        min(len(translated_text), position + trailing_chars)] + " ..."
                }
            })

            next_id = next_id + 1

    return new_review_items

