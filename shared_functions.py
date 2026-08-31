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

    print(f"Loaded {len(data)} top-level elements from {input_file} with {len(chars_cnt)} chars")
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


# ------------------------------------------------------------
# Function: Init Progress
# ------------------------------------------------------------
def init_progress():

    # TODO - Implement check/switch NEW_RUN vs. RESUME
    # For now, this is just the NEW_RUN case
    progress_info = {
        "config": {
            "input_file": str(INPUT_FILE),
            "max_batch_size": MAX_BATCH_SIZE,
            "translatable_fields": list(TRANSLATABLE_FIELDS),
        },
        "batches": []
    }

    save_json_output(data=progress_info, output_file=PROGRESS_INFO_FILE)

    print(f"New Progress Info is now tracked by file {PROGRESS_INFO_FILE}")


# ------------------------------------------------------------
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
            "char_count": 0
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

            current_batch["status"] = "failed"
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

        # Protect Foundry @UUID[...] and @Embed[...] syntax
        translatable_to_protect["original"] = re.sub(
            r'@(UUID|Embed|Compendium)\[[^\]]*\]',
            create_and_register_placeholder,
            translatable_to_protect["original"]
        )

        # Protect inline rolls, checks, saves, etc.
        translatable_to_protect["original"] = re.sub(
            r'\[\[[^\]]*\]\]',
            create_and_register_placeholder,
            translatable_to_protect["original"]
        )

        translatables_with_placeholders.append(translatable_to_protect)

    print(f"Extracted {len(placeholders)} new protective placeholders from {len(translatables)} translatables")

    return translatables_with_placeholders, placeholders



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


def test_result_color(result):
    if result is True:
        return GREEN
    else:
        return RED
