import config
import json
import os
import re
from pathlib import Path
from openai import OpenAI

# ------------------------------------------------------------
# Function: Load and return data (as list) from JSON input_file (path)
# ------------------------------------------------------------
def load_json_input(input_file):

    with input_file.open(
            "r",
            encoding="utf-8"
    ) as file:

        data = json.load(file)

    # chars_cnt = to_prettified_json(data)
    # print(f"DEBUG - Loaded {len(data)} top-level elements from {input_file} with {len(chars_cnt)} chars")

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

    # print(f"File written to: {output_file} with {len(json_string)} chars")


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
def to_multiline_text(input, value_char_limit=None, row_limit=None):

    text = ""
    counter = 0

    for key, value in input.items():

        label = key

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

    save_json_output(data=progress_info, output_file=config.PROGRESS_INFO_FILE)

    print(f"... Done. New Progress Info is now tracked by file {config.PROGRESS_INFO_FILE}")

    return progress_info


# ------------------------------------------------------------
# Function: Validate Progress
# Used by Run Mode = RESUME
# Checks if the status sequence of subsequent Batches is valid for being resumed.
# As each Batch's lifecycle consists of two separate loops (first: Terminology, then: Translation),
# these sequences need to be checked separately
# Returns (if valid):
# - the existing Progress Info
# - the Batch to restart from (resume_batch)
# (if invalid): an Error is thrown.
# ------------------------------------------------------------
def validate_progress_info(progress_info=None):

    print("Validating existing Progress Info ...")

    if progress_info is None:
        progress_info = load_json_input(config.PROGRESS_INFO_FILE)

    # Check for proper status sequence:
    try:

        terminology_completed = validate_status_sequence(
            progress_info["batches"],
            config.TERMINOLOGY_STATUS
        )

        print(f"Terminology loop completed: {terminology_completed}")

        translation_completed = validate_status_sequence(
            progress_info["batches"],
            config.TRANSLATION_STATUS
        )

        print(f"Translation loop completed: {translation_completed}")

    except ValueError:

        raise

    print("... valid.")

    resume_batch = find_resume_batch(
        progress_info
    )

    if resume_batch is None:
        raise ValueError(
            "Internal consistency error: "
            "Run mode RESUME detected, but no resume batch found."
        )

    return progress_info, resume_batch


# ------------------------------------------------------------
# Function: Validate Status Sequence
# Does the detailed checks for validate_progress_info(), for a specific
# status_phase (TERMINOLOGY_STATUS vs. TRANSLATION_STATUS)
# ------------------------------------------------------------
def validate_status_sequence(
        batches_progress_info,
        status_phase):

    phase_completed = True

    for batch_progress_info in batches_progress_info:

        if phase_completed:

            if batch_progress_info[status_phase] != config.COMPLETED:
                phase_completed = False

        else:

            if batch_progress_info[status_phase] == config.COMPLETED:

                raise ValueError(
                    f"Corrupt ProgressInfo: "
                    f"{status_phase}="
                    f"{config.COMPLETED} found after non-"
                    f"{config.COMPLETED} batch "
                    f"(id={batch_progress_info['id']})."
                )

    return phase_completed


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
            f"{config.TERMINOLOGY_STATUS}": config.UNPROCESSED,
            f"{config.TRANSLATION_STATUS}": config.UNPROCESSED
        }

    current_batch = create_empty_batch()

    error = None

    for translatable in translatables_with_placeholders:

        text_size = len(translatable["original"])

        # No Translatable must exceed the Batch size limit by itself, this requires an abort.
        if text_size > config.MAX_BATCH_SIZE:
            error = (
                f"Translatable {translatable['id']} " +
                f"contains {text_size} chars and exceeds " +
                f"MAX_BATCH_SIZE={config.MAX_BATCH_SIZE}" +
                f"\nProposed solution: Increase MAX_BATCH_SIZE in config.py and resume process."
            )

            current_batch[config.TERMINOLOGY_STATUS] = config.FAILED
            current_batch[config.ERROR] = error
            # set_batch_status(current_batch, FAILED, )
            break

        if current_batch["char_count"] + text_size > config.MAX_BATCH_SIZE:
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

    batches = load_json_input(config.BATCHES_FILE)

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
        config.TRANSLATABLES_FILE
        if not with_placeholders
        else config.TRANSLATABLES_WITH_PLACEHOLDERS_FILE
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
        config.TRANSLATIONS_FINAL_FILE
        if not with_placeholders
        else config.TRANSLATIONS_WITH_PLACEHOLDERS_FILE
    )

    translation_ids = set(
        batch["translatable_ids"]
    )

    translations = [
        translation
        for translation in load_json_input(file)
        if translation["id"] in translation_ids
    ]

    if limit is not None:
        translations = translations[:limit]

    return translations

# ------------------------------------------------------------
# Function: Load Translations Final
# These require a dedicated load functions to force dict keys
# to numeric format
# ------------------------------------------------------------
def load_translations_final():

    translations = load_json_input(
        config.TRANSLATIONS_FINAL_FILE
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

    return load_json_input(config.PLACEHOLDERS_FILE)


# --------------------------------------------------------------
# Function: Recursively extract Translatables from Babele input
# --------------------------------------------------------------
def extract_translatables_from_input(input, translatables, current_path):

    if isinstance(input, dict):

        for key, item in input.items():

            if (
                    key in config.TRANSLATABLE_FIELDS
                    and isinstance(item, str)
            ):

                translatables.append({
                    "id": len(translatables),
                    "path": current_path + [key],
                    "original": item
                })

            elif (
                    key in config.TRANSLATABLE_CONTAINERS
                    and isinstance(item, dict)
            ):

                for sub_key, sub_item in item.items():

                    if isinstance(sub_item, str):

                        translatables.append({
                            "id": len(translatables),
                            "path": current_path + [key, sub_key],
                            "original": sub_item
                        })

            elif isinstance(item, (dict, list)):

                extract_translatables_from_input(
                    item,
                    translatables,
                    current_path+ [key]
                )

    elif isinstance(input, list):

        for index, item in enumerate(input):

            extract_translatables_from_input(
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
            config.PLACEHOLDER_PATTERN
        )[1]

        placeholder_name = re.sub(
            r'\\d{\d}',
            f"{str(len(placeholders)).zfill(int(placeholder_number_digit_length))}",
            config.PLACEHOLDER_PATTERN
        ) # yields something like <<<FOUNDRY_000003>>>

        placeholders[
            placeholder_name
        ] = match.group(0)

        return placeholder_name

    for translatable in translatables:

        # copy original translatable
        translatable_to_protect = translatable.copy()

        for pattern in config.FOUNDRY_SYNTAX_PATTERNS:

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

    api_key = config.APIKEY_FILE.read_text(
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
        "MAX_BATCH_SIZE": config.MAX_BATCH_SIZE,
        "TRANSLATABLE_FIELDS": sorted(config.TRANSLATABLE_FIELDS),
        "TRANSLATABLE_CONTAINERS": sorted(config.TRANSLATABLE_CONTAINERS),
        "FOUNDRY_SYNTAX_PATTERNS": sorted(config.FOUNDRY_SYNTAX_PATTERNS),
        "MOCK_MODE": config.MOCK_MODE,
    }


# ------------------------------------------------------------
# Function: Validate Resume-relevant config
# Used prior to Resume run scenario:
# Checks if any of the parameters defined by get_resume_relevant_config()
# have changed since last run. If so, an Exception is thrown
# ------------------------------------------------------------
def validate_resume_relevant_config(progress_info=None):

    current_config = get_resume_relevant_config()

    if progress_info is None:
        progress_info = load_json_input(config.PROGRESS_INFO_FILE)

    if progress_info["config"] != current_config:

        raise ValueError(
            f"CONFIGURATION MISMATCH\n"
            f"======================\n"
            f"At least one essential parameter in config.py "
            f"has changed since the last attempt to run this process.\n"
            f"The following parameters are not allowed to change when resuming a process for the same input file.\n"
            f"(File to be processed: {config.INPUT_FILE})\n\n"

            f"Current configuration:\n"
            f"----------------------\n"
            f"{to_multiline_text(current_config)}\n\n"

            f"Configuration values expected from last attempt:\n"
            f"------------------------------------------------\n"
            f"{to_multiline_text(progress_info['config'])}\n\n"

            f"Please either adjust config.py accordingly and retry, "
            f"or start a fresh process for file {config.PROGRESS_INFO_FILE} (discarding all hitherto results)."
        )


# ------------------------------------------------------------
# Function: Determine run mode
# Delivers the current snapshot of all config parameters that
# need to remain stable between incremental process runs.
# The function's output serves for checking whether a Resume is allowed to start.
# ------------------------------------------------------------
def determine_run_mode():

    if not config.PROGRESS_INFO_FILE.exists():
        return config.NEW_RUN

    progress_info = load_json_input(
        config.PROGRESS_INFO_FILE
    )

    if len(progress_info["batches"]) == 0:
        return config.NEW_RUN

    if find_resume_batch(progress_info) is None:

        # Run is already complete. So we need to ask the user what they want:
        if prompt_for_force_new_run():

            return config.NEW_RUN

        else:

            return config.POSTPROCESSING_ONLY

    return config.RESUME


# ------------------------------------------------------------
# Function: Cleanup progress files
# ------------------------------------------------------------
def cleanup_progress_files():

    print("Cleaning up progress files from previous runs (if any) ...")

    for file in [
        config.PROGRESS_INFO_FILE,
        config.TRANSLATABLES_FILE,
        config.TRANSLATABLES_WITH_PLACEHOLDERS_FILE,
        config.PLACEHOLDERS_FILE,
        config.BATCHES_FILE,
        config.TRANSLATIONS_WITH_PLACEHOLDERS_FILE,
        config.TRANSLATIONS_FINAL_FILE,
        config.REVIEW_ITEMS_FILE
    ]:

        if file.exists():
            file.unlink()

            print(f"... Deleted: {file}")

    print("Done.")


# ------------------------------------------------------------
# Function: Delete file
# ------------------------------------------------------------
def delete_file(file):

    if file.exists():
        file.unlink()


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
        master_terminology=None,
        translations_with_placeholders=None
):

    with open(
            config.ERRORS_FILE,
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

        if master_terminology is not None:

            file.write(
                "====================================================\n"
                "MASTER TERMINOLOGY\n"
                "====================================================\n\n"
            )

            file.write(
                json.dumps(
                    master_terminology,
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

    print(
        f"\n❌{config.RED}POST-MORTEM DUMP WRITTEN TO:{config.COLOR_RESET}"
    )

    print(
        f"{config.RED}{config.ERRORS_FILE}{config.COLOR_RESET}"
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

    save_json_output(all_batches, config.BATCHES_FILE)
    save_json_output(all_progress_info, config.PROGRESS_INFO_FILE)


# ------------------------------------------------------------
# Function: Save Batches
# This is the "bulk version" of save_batch().
# Used for updating all Batches at once to avoid multiple file writes.
# ------------------------------------------------------------
def save_batches(all_batches, progress_info):

    progress_info["batches"] = all_batches

    save_json_output(all_batches, config.BATCHES_FILE)
    save_json_output(progress_info, config.PROGRESS_INFO_FILE)


# ------------------------------------------------------------
# Function: Identify Review Items
# ------------------------------------------------------------
def identify_review_items(
        translatables_with_placeholders,
        translations_with_placeholders):

    review_items = []

    translations_by_id = {
        translation["id"]: translation
        for translation in translations_with_placeholders
    }

    all_placeholders = load_placeholders()

    for translatable in translatables_with_placeholders:

        new_review_items = verify_placeholder_integrity(
                next_id=len(review_items),
                original_text_with_placeholders=translatable["original"],
                translated_text=translations_by_id[
                    translatable["id"]
                ]["translation"],
                all_placeholders=all_placeholders
        )

        review_items.extend(new_review_items)

    return review_items


# ------------------------------------------------------------
# Function: Verify Placeholder Integrity
# ------------------------------------------------------------
def verify_placeholder_integrity(
        next_id,
        original_text_with_placeholders,
        translated_text,
        all_placeholders,
        trailing_chars=300):

    new_review_items = []

    # Collect all expected placeholders from original
    expected_placeholders = re.findall(
        config.PLACEHOLDER_PATTERN,
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
                position - trailing_chars
            )

            end = min(
                len(original_text_with_placeholders),
                position + len(placeholder) + trailing_chars
            )


            new_review_items.append( {
                "id": next_id,
                "type": config.PLACEHOLDER_TRANSLATION_ERROR,
                "details": {
                    "placeholder": placeholder,
                    "original_value": all_placeholders[placeholder],
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


# ------------------------------------------------------------
# Function: Verify Translation Completeness
# ------------------------------------------------------------
def verify_translation_completeness(batch, batches_cnt, batch_payload, translations):
    expected_ids = {
        item["id"]
        for item in batch_payload
    }

    returned_ids = {
        item["id"]
        for item in translations
    }

    missing_ids = expected_ids - returned_ids
    extra_ids = returned_ids - expected_ids

    if missing_ids or extra_ids:
        raise ValueError(
            f"❌ Mismatch between Translatables and Translations in {batch['id'] + 1}/{batches_cnt}:\n"
            f"Missing Translations (IDs) {missing_ids}.\n"
            f"Unexpected Translations (IDs) {extra_ids}.\n"
            f"Aborting process.\n"
            f"Please check the following files for details about the missing/extra texts:\n"
            f"- {config.TRANSLATABLES_WITH_PLACEHOLDERS_FILE}:\n"
            f"- {config.TRANSLATIONS_WITH_PLACEHOLDERS_FILE}:\n"
            f"This is usually a temporary API failure. Just resume the process to try again (it will automatcally resume from this Batch).\n"
        )



# ------------------------------------------------------------
# Function: Restore Foundry Syntax
# ------------------------------------------------------------
def restore_foundry_syntax(
        text_with_placeholders,
        placeholders
):
    for placeholder, original in placeholders.items():

        text_with_placeholders = text_with_placeholders.replace(
            placeholder,
            original
        )

    return text_with_placeholders


# ------------------------------------------------------------
# Function: Deduplicate Terminology
# ------------------------------------------------------------
def deduplicate_terminology(master_terminology):

    unique_terms = {}

    for term in master_terminology["terms"]:

        original = term["original"]

        if original not in unique_terms:
            unique_terms[original] = term

    master_terminology["terms"] = list(
        unique_terms.values()
    )

    return master_terminology


# ------------------------------------------------------------
# Function: Prompt for Terminology Rebuild
# ------------------------------------------------------------
def prompt_for_terminology_rebuild():

    if config.TERMINOLOGY_FILE.exists():
        answer = input(
            f"\n{config.MAGENTA}=== REBUILD TERMINOLOGY? ===\n"
            f"Existing Terminology for this input file already exists at: {config.TERMINOLOGY_FILE}\n"
            "Do you want to rebuild it online before translating?\n"
            f"({config.YES.lower()}) = Rebuild\n"
            f"({config.NO.lower()}) or (Enter): No, reuse existing Terminology\n"
            f"?> {config.COLOR_RESET}"
        ).strip().lower()

        normalized_answer = True if answer == config.YES.lower() else False

        config.REBUILD_TERMINOLOGY_IF_EXISTS = normalized_answer


# ------------------------------------------------------------
# Function: Prompt for force new run
# ------------------------------------------------------------
def prompt_for_force_new_run():

    text_if_output_still_exists = (
        f"A translated output file can still be found at: {config.OUTPUT_FILE}\n"
        if config.OUTPUT_FILE.exists()
        else ""
    )

    answer = input(
        f"\n{config.MAGENTA}=== REPLACE PREVIOUS RESULTS? ===\n"
        f"The last run for this file is marked as fully {config.COMPLETED}.\n"
        f"{text_if_output_still_exists}"
        "Do you want to discard the results and start a complete, FRESH translation?\n"
        "Or do you want to keep them and just rerun Post-Processing steps (integrity checks and rebuilding of the output file)?\n"
        f"({config.YES.lower()}) = Discard and replace previous results.\n"
        f"({config.NO.lower()}) or (Enter): No, just rerun Post-Processing (this will also skip Terminology rebuild!)\n"
        f"?> {config.COLOR_RESET}"
    ).strip().lower()

    normalized_answer = True if answer == config.YES.lower() else False

    return normalized_answer


# ------------------------------------------------------------
# Function: Prompt for input file
# ------------------------------------------------------------
def prompt_for_input_file():

    global INPUT_FILE_NAME

    json_files = sorted(
        [
            file.name
            for file in Path(config.INPUT_FOLDER_NAME).glob("*.json")
        ]
    )

    print(
        f"\n{config.MAGENTA}"
        f"=== SELECT INPUT FILE (from subfolder: {config.INPUT_FOLDER_NAME}) ==="
        f"\nUse parameter config.py->INPUT_FOLDER_NAME to switch to another subfolder."
        f"{config.COLOR_RESET}")

    for i, file_name in enumerate(json_files, start=1):
        print(f"{i}. {file_name}")

    while True:

        try:

            selection = int(
                input("\nSelect file ?> ")
            )

            if 1 <= selection <= len(json_files):
                init_dynamic_paths(json_files[selection - 1])
                break

        except ValueError:
            pass

        print(f"{config.RED}Invalid selection.{config.COLOR_RESET}")


# ------------------------------------------------------------
# Function: Init dynamic paths
# ------------------------------------------------------------
def init_dynamic_paths(input_file_name):

    config.INPUT_FILE_NAME = input_file_name
    config.INPUT_FILE = Path(config.INPUT_FOLDER_NAME) / config.INPUT_FILE_NAME
    config.REVIEW_ITEMS_FILE_NAME = f"{config.INPUT_FILE_NAME.removesuffix(".json")}-review-items.json"
    config.OUTPUT_FILE = Path(config.OUTPUT_FOLDER_NAME) / config.INPUT_FILE_NAME
    config.TERMINOLOGY_FILE_NAME = f"{config.INPUT_FILE_NAME.removesuffix(".json")}-terminology.json"

    # create subfolders if necessary
    progress_subfolder_name = Path(config.PROGRESS_FOLDER_NAME) / config.INPUT_FILE_NAME.removesuffix(".json")
    if not os.path.exists(config.PROGRESS_FOLDER_NAME):
        os.makedirs(config.PROGRESS_FOLDER_NAME)
    if not os.path.exists(progress_subfolder_name):
        os.makedirs(progress_subfolder_name)
    if not os.path.exists(config.OUTPUT_FOLDER_NAME):
        os.makedirs(config.OUTPUT_FOLDER_NAME)

    config.PROGRESS_INFO_FILE = Path(progress_subfolder_name) / config.PROGRESS_INFO_FILE_NAME
    config.TRANSLATABLES_FILE = Path(progress_subfolder_name) / config.TRANSLATABLES_FILE_NAME
    config.TRANSLATABLES_WITH_PLACEHOLDERS_FILE = Path(progress_subfolder_name) / config.TRANSLATABLES_WITH_PLACEHOLDERS_FILE_NAME
    config.PLACEHOLDERS_FILE = Path(progress_subfolder_name) / config.PLACEHOLDERS_FILE_NAME
    config.BATCHES_FILE = Path(progress_subfolder_name) / config.BATCHES_FILE_NAME
    config.TERMINOLOGY_FILE = Path(config.TERMINOLOGY_FOLDER_NAME) / config.TERMINOLOGY_FILE_NAME
    config.TRANSLATIONS_WITH_PLACEHOLDERS_FILE = Path(progress_subfolder_name) / config.TRANSLATIONS_WITH_PLACEHOLDERS_FILE_NAME
    config.TRANSLATIONS_FINAL_FILE = Path(progress_subfolder_name) / config.TRANSLATIONS_FINAL_FILE_NAME
    config.ERRORS_FILE = Path(progress_subfolder_name) / config.ERRORS_FILE_NAME
    config.REVIEW_ITEMS_FILE = Path(config.OUTPUT_FOLDER_NAME) / config.REVIEW_ITEMS_FILE_NAME


# ------------------------------------------------------------
# Function: Find Resume Batch
# ------------------------------------------------------------
def find_resume_batch(progress_info):

    for batch_progress_info in progress_info["batches"]:

        if (
                batch_progress_info[config.TERMINOLOGY_STATUS] != config.COMPLETED
                or
                batch_progress_info[config.TRANSLATION_STATUS] != config.COMPLETED
        ):
            return batch_progress_info

    return None



